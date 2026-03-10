"""Structured logging for orchestrator events."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from master_orchestrator.config import OrchestratorConfig
    from master_orchestrator.models.agent_output import AgentReport
    from master_orchestrator.models.task import TaskPlan


class OrchestratorLogger:
    """Logs orchestrator events to file and console.

    Provides structured logging for:
    - Task plan decomposition
    - Iteration start/end
    - Agent dispatch and results
    - Escalation events
    - Completion events
    - Errors
    """

    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.log_dir = Path(config.logging.log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.verbose = config.verbose

        # Set up Python logging
        self._logger = logging.getLogger("master_orchestrator")
        self._logger.setLevel(getattr(logging, config.logging.level, logging.INFO))

        # Console handler
        if not self._logger.handlers:
            console = logging.StreamHandler(sys.stderr)
            console.setLevel(logging.INFO if not self.verbose else logging.DEBUG)
            console.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%H:%M:%S",
            ))
            self._logger.addHandler(console)

            # File handler
            log_file = self.log_dir / "orchestrator.log"
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            ))
            self._logger.addHandler(file_handler)

    def log_event(self, source: str, message: str) -> None:
        """Log a general event."""
        self._logger.info(f"[{source}] {message}")

    def log_task_plan(self, plan: TaskPlan) -> None:
        """Log a task plan decomposition."""
        self._logger.info(
            f"[task_plan] Objective: {plan.objective[:80]} | "
            f"Subtasks: {len(plan.subtasks)} | "
            f"Types: {', '.join(t.value for t in plan.task_types)}"
        )
        if self.verbose:
            for st in plan.subtasks:
                self._logger.debug(
                    f"  [{st.id}] {st.assigned_agent} (Tier {st.tier}): "
                    f"{st.description[:60]}"
                )

    def log_iteration_start(self, iteration: int, max_iter: int) -> None:
        """Log the start of a Ralph Wiggum iteration."""
        self._logger.info(
            f"[ralph_loop] --- Iteration {iteration}/{max_iter} START ---"
        )

    def log_iteration_end(self, iteration: int) -> None:
        """Log the end of an iteration."""
        self._logger.info(
            f"[ralph_loop] --- Iteration {iteration} END ---"
        )

    def log_agent_dispatch(self, agent_key: str, tier: int) -> None:
        """Log when an agent is dispatched."""
        self._logger.info(f"[dispatch] Agent '{agent_key}' (Tier {tier}) dispatched")

    def log_agent_result(self, report: AgentReport) -> None:
        """Log an agent's report summary."""
        self._logger.info(
            f"[result] {report.agent_name}: "
            f"confidence={report.confidence_level:.0%} | "
            f"risks={len(report.risks_and_gaps)} | "
            f"escalation={'YES' if report.escalation_used else 'no'}"
        )

    def log_escalation(
        self, from_agent: str, to_agent: str, reason: str
    ) -> None:
        """Log an escalation from Tier 1 to Tier 2."""
        self._logger.warning(
            f"[escalation] {from_agent} -> {to_agent}: {reason[:100]}"
        )

    def log_completion(self, iteration: int, reason: str) -> None:
        """Log loop completion."""
        self._logger.info(
            f"[completion] Loop completed at iteration {iteration}: {reason}"
        )

    def log_error(self, context: str, error: Exception) -> None:
        """Log an error."""
        self._logger.error(
            f"[error] {context}: {type(error).__name__}: {error}"
        )

    def log_stream(self, text: str) -> None:
        """Log streaming output (verbose only)."""
        if self.verbose:
            self._logger.debug(f"[stream] {text[:100]}")

    def write_session_log(
        self,
        session_id: str,
        content: str,
    ) -> None:
        """Write a full session log to a dedicated file."""
        log_file = self.log_dir / f"session_{session_id}.md"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n---\n### {timestamp}\n\n{content}\n")
