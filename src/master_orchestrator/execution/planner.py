"""Execution planner — converts OrchestrationResult into an ExecutionPlan.

Takes the structured 10-section report (specifically recommended_next_steps
and development_ready_output) and decomposes them into executable WorkerTasks
using Claude to intelligently assign agents and set priorities.
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from master_orchestrator.execution.models import (
    ExecutionPlan,
    TaskPriority,
    WorkerTask,
)

if TYPE_CHECKING:
    from master_orchestrator.agents.dispatch import AgentDispatcher
    from master_orchestrator.agents.registry import AgentRegistry
    from master_orchestrator.config import OrchestratorConfig
    from master_orchestrator.logging.logger import OrchestratorLogger
    from master_orchestrator.models.agent_output import OrchestrationResult


PLANNING_PROMPT = """You are an Execution Planner. Given the orchestration analysis below,
decompose the recommended next steps into concrete, executable worker tasks.

## Orchestration Result

**Objective:** {objective}

**Recommended Next Steps:**
{next_steps}

**Development-Ready Output:**
{dev_output}

**Key Risks:**
{risks}

## Available Worker Agents
{agent_list}

## Instructions

Produce a JSON array of task objects. Each task should be:
- Specific and actionable (a single agent can complete it)
- Assigned to the most appropriate agent from the list above
- Ordered by priority and dependency chain

Return a JSON object with this structure:
```json
{{
  "tasks": [
    {{
      "title": "Short task title",
      "description": "Full task description with enough context for the agent to execute",
      "assigned_agent": "registry_key_of_agent",
      "priority": "critical|high|medium|low",
      "dependencies": [],
      "allowed_tools": ["Read", "Write", "Edit", "Bash", "Grep", "Glob"]
    }}
  ]
}}
```

Rules:
- Use only agent keys from the Available Worker Agents list
- Dependencies should reference task titles of other tasks in the list
- Critical priority = must complete first or blocks everything
- Include specific file paths, code patterns, or commands when possible
- Each task should be completable in a single agent session (< 15 turns)
- For build tasks, include the allowed_tools the agent will need
"""


class ExecutionPlanner:
    """Converts orchestration analysis into an executable task plan."""

    def __init__(
        self,
        config: OrchestratorConfig,
        registry: AgentRegistry,
        dispatcher: AgentDispatcher,
        logger: OrchestratorLogger | None = None,
    ):
        self.config = config
        self.registry = registry
        self.dispatcher = dispatcher
        self.logger = logger

    async def plan(
        self,
        result: OrchestrationResult,
    ) -> ExecutionPlan:
        """Convert an OrchestrationResult into an ExecutionPlan.

        Uses Claude to intelligently decompose recommended_next_steps
        into structured WorkerTasks with agent assignments.
        """
        if self.logger:
            self.logger.log_event(
                "execution_planner",
                f"Planning execution for: {result.objective[:80]}",
            )

        # Build the agent list for the planning prompt
        agent_list = self._build_agent_list()

        # Format the planning prompt
        next_steps = "\n".join(
            f"{i}. {step}"
            for i, step in enumerate(result.recommended_next_steps, 1)
        ) or "No specific next steps provided."

        prompt = PLANNING_PROMPT.format(
            objective=result.objective,
            next_steps=next_steps,
            dev_output=result.development_ready_output or "None provided.",
            risks="\n".join(f"- {r}" for r in result.key_risks) or "None identified.",
            agent_list=agent_list,
        )

        # Ask Claude to decompose into tasks
        raw_result = await self.dispatcher.dispatch_simple(
            prompt=prompt,
            model=self.config.models.primary,
            max_turns=5,
        )

        # Parse the task list
        tasks = self._parse_tasks(raw_result)

        # Resolve dependencies (title references → task_id references)
        self._resolve_dependencies(tasks)

        plan = ExecutionPlan(
            session_id=result.session_id,
            objective=result.objective,
            tasks=tasks,
            status="draft",
        )

        if self.logger:
            self.logger.log_event(
                "execution_planner",
                f"Created plan with {len(tasks)} tasks: {plan.summary()}",
            )

        return plan

    def plan_from_steps(
        self,
        steps: list[str],
        objective: str = "",
        session_id: str = "",
    ) -> ExecutionPlan:
        """Create a simple execution plan from a list of step strings.

        This is the synchronous fast path — no Claude call, just maps
        each step to the most likely agent using keyword matching.
        """
        tasks = []
        for i, step in enumerate(steps):
            agent_key = self._match_agent_to_step(step)
            task = WorkerTask(
                title=step[:80],
                description=step,
                assigned_agent=agent_key,
                priority=TaskPriority.HIGH if i == 0 else TaskPriority.MEDIUM,
                source_step=step,
                allowed_tools=self._tools_for_agent(agent_key),
            )
            tasks.append(task)

        return ExecutionPlan(
            session_id=session_id,
            objective=objective,
            tasks=tasks,
            status="draft",
        )

    # -----------------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------------

    def _build_agent_list(self) -> str:
        """Build a formatted list of all available agents for the prompt."""
        lines = []
        lines.append("### Tier 1 — Specialists:")
        for key, t in self.registry.tier1_agents.items():
            lines.append(f"- **{key}**: {t.description[:100]}")
        lines.append("\n### Tier 2 — Niche Specialists:")
        for key, t in self.registry.tier2_agents.items():
            lines.append(f"- **{key}**: {t.description[:100]}")
        return "\n".join(lines)

    def _parse_tasks(self, raw: str) -> list[WorkerTask]:
        """Parse WorkerTask list from Claude's JSON output."""
        tasks: list[WorkerTask] = []

        # Try JSON code block first
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if isinstance(data, dict) and "tasks" in data:
                    for t in data["tasks"]:
                        tasks.append(self._task_from_dict(t))
                    return tasks
            except (json.JSONDecodeError, KeyError):
                pass

        # Try finding raw JSON object
        json_objects = re.findall(
            r'\{[^{}]*"tasks"\s*:\s*\[.*?\]\s*\}', raw, re.DOTALL
        )
        for obj_str in json_objects:
            try:
                data = json.loads(obj_str)
                if "tasks" in data:
                    for t in data["tasks"]:
                        tasks.append(self._task_from_dict(t))
                    return tasks
            except (json.JSONDecodeError, KeyError):
                continue

        # Fallback: create a single task from the raw output
        if raw.strip():
            tasks.append(WorkerTask(
                title="Execute analysis recommendations",
                description=raw[:2000],
                assigned_agent="engineering",
                priority=TaskPriority.MEDIUM,
                allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
            ))

        return tasks

    def _task_from_dict(self, data: dict) -> WorkerTask:
        """Convert a parsed dict into a WorkerTask."""
        agent_key = data.get("assigned_agent", "engineering")
        # Validate agent exists in registry
        if not self.registry.get(agent_key):
            resolved = self.registry.resolve_key(agent_key)
            agent_key = resolved or "engineering"

        priority = data.get("priority", "medium")
        try:
            task_priority = TaskPriority(priority)
        except ValueError:
            task_priority = TaskPriority.MEDIUM

        return WorkerTask(
            title=data.get("title", "Untitled task"),
            description=data.get("description", ""),
            assigned_agent=agent_key,
            priority=task_priority,
            dependencies=data.get("dependencies", []),
            allowed_tools=data.get(
                "allowed_tools", self._tools_for_agent(agent_key)
            ),
            source_step=data.get("source_step", ""),
        )

    def _resolve_dependencies(self, tasks: list[WorkerTask]) -> None:
        """Convert title-based dependency references to task_id references."""
        title_to_id = {t.title.lower(): t.task_id for t in tasks}

        for task in tasks:
            resolved_deps = []
            for dep in task.dependencies:
                dep_lower = dep.lower()
                if dep_lower in title_to_id:
                    resolved_deps.append(title_to_id[dep_lower])
                else:
                    # Fuzzy match
                    for title, tid in title_to_id.items():
                        if dep_lower in title or title in dep_lower:
                            resolved_deps.append(tid)
                            break
            task.dependencies = resolved_deps

    def _match_agent_to_step(self, step: str) -> str:
        """Simple keyword-based agent matching for synchronous planning."""
        step_lower = step.lower()

        keyword_map = {
            "engineering": ["implement", "build", "code", "create", "develop", "write code", "refactor"],
            "research": ["research", "investigate", "find", "search", "explore", "discover"],
            "systems_architect": ["architect", "design system", "infrastructure", "scale", "deploy"],
            "data_analyst": ["data", "analyze", "metrics", "statistics", "measure"],
            "risk_analyst": ["risk", "security", "threat", "vulnerability", "audit"],
            "product_strategy": ["product", "user", "market", "feature", "ux", "roadmap"],
            "workflow": ["automate", "pipeline", "ci/cd", "workflow", "process"],
            "synthesis": ["synthesize", "integrate", "combine", "summarize"],
            "testing": ["test", "qa", "quality", "coverage", "verify"],
            "devops": ["deploy", "docker", "kubernetes", "monitor", "infrastructure"],
            "api_design": ["api", "endpoint", "rest", "graphql", "schema"],
            "security": ["auth", "encrypt", "token", "permission", "access control"],
            "database_schema": ["database", "schema", "migration", "query", "sql"],
            "documentation": ["document", "readme", "docs", "guide"],
        }

        best_match = "engineering"  # Default
        best_score = 0

        for agent_key, keywords in keyword_map.items():
            score = sum(1 for kw in keywords if kw in step_lower)
            if score > best_score:
                best_score = score
                best_match = agent_key

        return best_match

    def _tools_for_agent(self, agent_key: str) -> list[str]:
        """Get the default tool set for an agent."""
        template = self.registry.get(agent_key)
        if template:
            return list(template.tools)
        return ["Read", "Grep", "Glob"]
