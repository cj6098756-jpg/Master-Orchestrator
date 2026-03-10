"""Agent runner pool — manages concurrent task execution.

Provides queued concurrency control so multiple worker tasks can
execute in parallel up to a configurable limit.
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import TYPE_CHECKING

from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    query,
)

from master_orchestrator.execution.models import TaskStatus, WorkerTask

if TYPE_CHECKING:
    from master_orchestrator.agents.registry import AgentRegistry
    from master_orchestrator.config import OrchestratorConfig
    from master_orchestrator.logging.logger import OrchestratorLogger


# System prompt template for worker agents during execution
WORKER_SYSTEM_PROMPT = """You are a Worker Agent executing a specific task.

## Your Task
{task_description}

## Context
- Task ID: {task_id}
- Priority: {priority}
- Source: {source_step}

## Instructions
1. Execute the task described above to the best of your ability
2. Use the tools available to you to complete the work
3. Be thorough but focused — complete this specific task, nothing more
4. When finished, provide a clear summary of what was accomplished
5. List any files created or modified
6. If you encounter blockers, describe them clearly

## Output
When complete, respond with a summary of:
- What was done
- Files created/modified (full paths)
- Any issues encountered
- Confidence in the result (0.0-1.0)
"""


class AgentPool:
    """Manages concurrent execution of worker tasks via Claude Agent SDK.

    Features:
    - Queued concurrency (configurable max_concurrent)
    - Per-task agent configuration from registry
    - Result collection and error handling
    - Progress tracking
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        registry: AgentRegistry,
        logger: OrchestratorLogger | None = None,
        max_concurrent: int = 3,
    ):
        self.config = config
        self.registry = registry
        self.logger = logger
        self.max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running: dict[str, asyncio.Task] = {}

    async def execute_task(self, task: WorkerTask) -> WorkerTask:
        """Execute a single WorkerTask via the Claude Agent SDK.

        Builds the appropriate agent configuration from the registry,
        dispatches the query, and populates the task's result fields.
        """
        async with self._semaphore:
            task.mark_running()

            if self.logger:
                self.logger.log_event(
                    "agent_pool",
                    f"Executing: [{task.assigned_agent}] {task.title}",
                )

            try:
                result_text = await self._run_agent(task)
                # Parse confidence from the result if present
                confidence = self._extract_confidence(result_text)
                artifacts = self._extract_artifacts(result_text)

                task.mark_completed(result_text, confidence)
                task.artifacts = artifacts

                if self.logger:
                    self.logger.log_event(
                        "agent_pool",
                        f"Completed: [{task.assigned_agent}] {task.title} "
                        f"(confidence: {confidence:.0%})",
                    )

            except Exception as e:
                error_msg = f"{type(e).__name__}: {e}"
                task.mark_failed(error_msg)

                if self.logger:
                    self.logger.log_event(
                        "agent_pool",
                        f"Failed: [{task.assigned_agent}] {task.title} — {error_msg}",
                    )

            return task

    async def execute_batch(
        self,
        tasks: list[WorkerTask],
    ) -> list[WorkerTask]:
        """Execute a batch of tasks concurrently (up to max_concurrent).

        Tasks are executed in parallel, respecting the semaphore limit.
        """
        if not tasks:
            return []

        if self.logger:
            self.logger.log_event(
                "agent_pool",
                f"Executing batch of {len(tasks)} tasks "
                f"(max {self.max_concurrent} concurrent)",
            )

        # Launch all tasks concurrently (semaphore controls actual concurrency)
        coros = [self.execute_task(task) for task in tasks]
        results = await asyncio.gather(*coros, return_exceptions=True)

        # Handle any exceptions from gather
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                tasks[i].mark_failed(f"Batch execution error: {result}")

        return tasks

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    async def _run_agent(self, task: WorkerTask) -> str:
        """Execute a single agent query for a task."""
        # Build the system prompt
        system_prompt = WORKER_SYSTEM_PROMPT.format(
            task_description=task.description,
            task_id=task.task_id,
            priority=task.priority.value,
            source_step=task.source_step or "N/A",
        )

        # Build the user prompt
        user_prompt = f"Execute this task:\n\n{task.description}"

        # Add input context if available
        if task.inputs:
            inputs_str = "\n".join(
                f"- {k}: {v}" for k, v in task.inputs.items()
            )
            user_prompt += f"\n\n## Additional Context\n{inputs_str}"

        # Get the agent template from registry for tool config
        template = self.registry.get(task.assigned_agent)
        tools = task.allowed_tools or (template.tools if template else ["Read", "Grep", "Glob"])

        # Determine model — use tier2 model for niche specialists
        model = self.config.models.tier1
        if template and template.tier == 2:
            model = template.model_override or self.config.models.tier2

        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            allowed_tools=tools,
            model=model,
            permission_mode=self.config.permission_mode,
            max_turns=task.max_turns,
        )

        if task.cwd or self.config.cwd:
            options.cwd = task.cwd or self.config.cwd

        result_text = ""
        async for message in query(prompt=user_prompt, options=options):
            if hasattr(message, "result") and message.result:
                result_text = message.result

        return result_text

    def _extract_confidence(self, text: str) -> float:
        """Extract a confidence score from the agent's output."""
        # Look for explicit confidence mentions
        patterns = [
            r'confidence[:\s]+([01]?\.\d+)',
            r'confidence[:\s]+(\d+)%',
            r'(\d+(?:\.\d+)?)\s*/\s*1\.0',
        ]
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                val = float(match.group(1))
                if val > 1.0:
                    val = val / 100.0  # Convert percentage
                return min(max(val, 0.0), 1.0)

        # Default based on whether result seems complete
        if len(text) > 200:
            return 0.7
        return 0.5

    def _extract_artifacts(self, text: str) -> list[str]:
        """Extract file paths from the agent's output."""
        artifacts = []
        # Look for common path patterns
        path_patterns = [
            r'(?:created|modified|wrote|saved|generated)[:\s]+[`"]?([/\\][\w/\\.\\-]+)[`"]?',
            r'`([/\\][\w/\\.\\-]+\.\w+)`',
        ]
        for pattern in path_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            artifacts.extend(matches)

        return list(set(artifacts))[:20]  # Deduplicate, cap at 20
