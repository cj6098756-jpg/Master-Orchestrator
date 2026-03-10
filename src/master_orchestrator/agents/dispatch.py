"""Agent dispatch — executes SDK query() calls and collects structured results."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING, Any

from claude_agent_sdk import (
    AgentDefinition,
    ClaudeAgentOptions,
    query,
)

from master_orchestrator.models.agent_output import AgentReport

if TYPE_CHECKING:
    from master_orchestrator.config import OrchestratorConfig
    from master_orchestrator.logging.logger import OrchestratorLogger


class AgentDispatcher:
    """Dispatches tasks to specialist agents via the Claude Agent SDK.

    Handles query execution, result collection, and structured output parsing.
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        logger: OrchestratorLogger | None = None,
    ):
        self.config = config
        self.logger = logger

    async def dispatch_phase(
        self,
        prompt: str,
        system_prompt: str,
        agent_definitions: dict[str, AgentDefinition],
        hooks: dict | None = None,
    ) -> tuple[str, list[AgentReport], str | None]:
        """Execute a single dispatch phase (Tier 1 or Tier 2).

        Args:
            prompt: The user-facing prompt describing the task.
            system_prompt: The system prompt for the orchestrator.
            agent_definitions: Dict of agent key -> AgentDefinition.
            hooks: Optional SDK hooks for observation.

        Returns:
            Tuple of (raw_result_text, parsed_agent_reports, session_id).
        """
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            allowed_tools=["Read", "Grep", "Glob", "WebSearch", "WebFetch", "Agent"],
            agents=agent_definitions,
            model=self.config.models.primary,
            permission_mode=self.config.permission_mode,
            max_turns=self.config.max_turns_per_agent,
        )

        # Add optional settings
        if self.config.cwd:
            options.cwd = self.config.cwd
        if self.config.max_budget_usd:
            options.max_budget_usd = self.config.max_budget_usd
        if hooks:
            options.hooks = hooks

        session_id = None
        result_text = ""

        try:
            async for message in query(prompt=prompt, options=options):
                # Capture session ID from init message
                if hasattr(message, "session_id"):
                    session_id = message.session_id

                # Capture result text
                if hasattr(message, "result") and message.result:
                    result_text = message.result

                # Stream assistant messages for logging
                if hasattr(message, "content") and self.logger:
                    for block in message.content:
                        if hasattr(block, "text"):
                            self.logger.log_stream(block.text[:200])

        except Exception as e:
            error_msg = f"Agent dispatch failed: {type(e).__name__}: {e}"
            if self.logger:
                self.logger.log_error("dispatch", e)

            return (
                error_msg,
                [self._make_error_report(prompt, e)],
                None,
            )

        # Parse structured reports from the result
        reports = self._parse_agent_reports(result_text)

        return result_text, reports, session_id

    async def dispatch_simple(
        self,
        prompt: str,
        model: str | None = None,
        max_turns: int = 5,
    ) -> str:
        """Execute a simple one-shot query without subagents.

        Used for task decomposition and synthesis steps.
        """
        options = ClaudeAgentOptions(
            model=model or self.config.models.primary,
            max_turns=max_turns,
            permission_mode=self.config.permission_mode,
        )

        result_text = ""
        try:
            async for message in query(prompt=prompt, options=options):
                if hasattr(message, "result") and message.result:
                    result_text = message.result
        except Exception as e:
            if self.logger:
                self.logger.log_error("simple_dispatch", e)
            result_text = f"ERROR: {e}"

        return result_text

    # -----------------------------------------------------------------------
    # Report Parsing
    # -----------------------------------------------------------------------

    def _parse_agent_reports(self, raw_output: str) -> list[AgentReport]:
        """Parse structured AgentReport JSON objects from the output.

        Agents are instructed to return JSON reports. This method extracts
        them using multiple strategies:
        1. Look for JSON code blocks
        2. Look for raw JSON objects with expected fields
        3. Fall back to creating a single report from the full text
        """
        reports: list[AgentReport] = []

        # Strategy 1: Extract JSON from code blocks
        json_blocks = re.findall(
            r'```(?:json)?\s*(\{[^`]*?\})\s*```',
            raw_output,
            re.DOTALL,
        )

        for block in json_blocks:
            report = self._try_parse_report(block)
            if report:
                reports.append(report)

        # Strategy 2: Look for inline JSON objects with agent_name field
        if not reports:
            inline_jsons = re.findall(
                r'\{[^{}]*"agent_name"[^{}]*\}',
                raw_output,
                re.DOTALL,
            )
            for inline in inline_jsons:
                report = self._try_parse_report(inline)
                if report:
                    reports.append(report)

        # Strategy 3: Fallback — create a single report from the full text
        if not reports and raw_output.strip():
            reports.append(
                AgentReport(
                    agent_name="orchestrator_output",
                    task_assigned="full orchestration",
                    findings=raw_output[:2000],
                    confidence_level=0.5,
                    escalation_used=False,
                    recommended_output=raw_output[:1000],
                )
            )

        return reports

    def _try_parse_report(self, json_text: str) -> AgentReport | None:
        """Attempt to parse a JSON string into an AgentReport."""
        try:
            data = json.loads(json_text)
            if isinstance(data, dict) and "agent_name" in data:
                return AgentReport.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        return None

    def _make_error_report(
        self,
        prompt: str,
        error: Exception,
    ) -> AgentReport:
        """Create an error AgentReport when dispatch fails."""
        return AgentReport(
            agent_name="DISPATCH_ERROR",
            task_assigned=prompt[:200],
            findings=f"Agent dispatch failed: {type(error).__name__}: {error}",
            risks_and_gaps=[
                "Agent could not be reached",
                "Manual review required",
            ],
            confidence_level=0.0,
            escalation_used=True,
            escalation_notes=(
                f"Dispatch failure — {type(error).__name__}. "
                "Retry or manual intervention needed."
            ),
            recommended_output="Unable to provide recommendations due to dispatch failure.",
        )
