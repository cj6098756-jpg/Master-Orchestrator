"""Execution engine — top-level coordinator for task execution.

Orchestrates the full lifecycle:
1. Takes an OrchestrationResult (10-section analysis report)
2. Plans: Decomposes recommended_next_steps into WorkerTasks
3. Executes: Dispatches tasks to agent pool in dependency order
4. Tracks: Monitors progress, handles failures, produces summary
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from master_orchestrator.execution.models import (
    ExecutionPlan,
    TaskStatus,
    WorkerTask,
)
from master_orchestrator.execution.planner import ExecutionPlanner
from master_orchestrator.execution.pool import AgentPool

if TYPE_CHECKING:
    from master_orchestrator.agents.dispatch import AgentDispatcher
    from master_orchestrator.agents.registry import AgentRegistry
    from master_orchestrator.config import OrchestratorConfig
    from master_orchestrator.logging.logger import OrchestratorLogger
    from master_orchestrator.models.agent_output import OrchestrationResult


class ExecutionEngine:
    """Top-level execution coordinator.

    Bridges the gap between analysis (OrchestrationResult) and
    action (executed WorkerTasks). This is the "do it" phase that
    follows the "think about it" phase.

    Usage:
        engine = ExecutionEngine(config, registry, dispatcher, logger)
        plan = await engine.plan(orchestration_result)
        # User reviews and approves plan
        result = await engine.execute(plan)
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        registry: AgentRegistry,
        dispatcher: AgentDispatcher,
        logger: OrchestratorLogger | None = None,
        max_concurrent: int = 3,
    ):
        self.config = config
        self.registry = registry
        self.dispatcher = dispatcher
        self.logger = logger
        self.planner = ExecutionPlanner(config, registry, dispatcher, logger)
        self.pool = AgentPool(config, registry, logger, max_concurrent)

    async def plan(
        self,
        result: OrchestrationResult,
    ) -> ExecutionPlan:
        """Phase 1: Convert orchestration analysis into an execution plan.

        This step is separate from execute() so the user can review
        and approve the plan before tasks are dispatched.
        """
        if self.logger:
            self.logger.log_event(
                "execution_engine",
                f"Planning execution for session {result.session_id}",
            )

        plan = await self.planner.plan(result)
        return plan

    async def execute(
        self,
        plan: ExecutionPlan,
        max_waves: int = 10,
    ) -> ExecutionPlan:
        """Phase 2: Execute an approved plan by dispatching tasks.

        Executes in waves — each wave dispatches all ready tasks
        (those with no unmet dependencies), then waits for completion
        before starting the next wave.

        Args:
            plan: An approved ExecutionPlan.
            max_waves: Safety limit on execution waves.

        Returns:
            The plan with all task results populated.
        """
        plan.status = "executing"

        if self.logger:
            self.logger.log_event(
                "execution_engine",
                f"Starting execution: {len(plan.tasks)} tasks, max {max_waves} waves",
            )

        wave = 0
        while wave < max_waves and not plan.is_complete:
            wave += 1
            ready = plan.ready_tasks

            if not ready:
                # No tasks ready but plan not complete — deadlock or all failed
                if self.logger:
                    self.logger.log_event(
                        "execution_engine",
                        f"Wave {wave}: No ready tasks — checking for deadlock",
                    )

                # Check for blocked tasks with failed dependencies
                self._resolve_blocked_tasks(plan)
                ready = plan.ready_tasks

                if not ready:
                    if self.logger:
                        self.logger.log_event(
                            "execution_engine",
                            "Execution stalled — no more tasks can proceed",
                        )
                    break

            if self.logger:
                self.logger.log_event(
                    "execution_engine",
                    f"Wave {wave}: Dispatching {len(ready)} tasks | "
                    f"Progress: {plan.progress:.0%}",
                )

            # Execute this wave
            await self.pool.execute_batch(ready)

            if self.logger:
                completed = len(plan.completed_tasks)
                failed = len(plan.failed_tasks)
                total = len(plan.tasks)
                self.logger.log_event(
                    "execution_engine",
                    f"Wave {wave} complete: {completed}/{total} done, "
                    f"{failed} failed",
                )

        # Finalize
        plan.status = "completed" if plan.is_complete else "failed"

        if self.logger:
            self.logger.log_event(
                "execution_engine",
                f"Execution finished: {plan.summary()}",
            )

        return plan

    async def plan_and_execute(
        self,
        result: OrchestrationResult,
        auto_approve: bool = False,
    ) -> ExecutionPlan:
        """Convenience: plan + execute in one call.

        Args:
            result: OrchestrationResult from the analysis phase.
            auto_approve: If True, skip approval step (for CLI --auto flag).

        Returns:
            Executed plan with results.
        """
        plan = await self.plan(result)

        if not auto_approve:
            # In interactive mode, the caller should present the plan
            # to the user first. This method auto-approves.
            if self.logger:
                self.logger.log_event(
                    "execution_engine",
                    "Auto-executing plan (auto_approve=True)",
                )

        return await self.execute(plan)

    # -----------------------------------------------------------------------
    # Plan Persistence
    # -----------------------------------------------------------------------

    def save_plan(self, plan: ExecutionPlan, directory: str | Path = "sessions") -> Path:
        """Save an execution plan to disk."""
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / f"exec_{plan.plan_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(plan.to_dict(), f, indent=2, default=str)
        return file_path

    def load_plan(self, plan_id: str, directory: str | Path = "sessions") -> ExecutionPlan | None:
        """Load an execution plan from disk."""
        file_path = Path(directory) / f"exec_{plan_id}.json"
        if not file_path.exists():
            return None
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return ExecutionPlan.from_dict(data)

    # -----------------------------------------------------------------------
    # Formatting
    # -----------------------------------------------------------------------

    def format_plan(self, plan: ExecutionPlan) -> str:
        """Format an ExecutionPlan for display."""
        lines = [
            "=" * 72,
            "EXECUTION PLAN",
            "=" * 72,
            "",
            f"Plan ID  : {plan.plan_id}",
            f"Session  : {plan.session_id}",
            f"Objective: {plan.objective[:80]}",
            f"Status   : {plan.status}",
            f"Tasks    : {len(plan.tasks)}",
            "",
        ]

        for i, task in enumerate(plan.tasks, 1):
            status_icon = {
                "pending": "[ ]",
                "queued": "[~]",
                "running": "[>]",
                "completed": "[+]",
                "failed": "[X]",
                "blocked": "[!]",
                "cancelled": "[-]",
            }.get(task.status.value, "[?]")

            lines.append(
                f"  {status_icon} {i}. [{task.assigned_agent}] {task.title}"
            )
            lines.append(f"       Priority: {task.priority.value}")
            if task.dependencies:
                lines.append(f"       Depends on: {', '.join(task.dependencies)}")
            if task.status == TaskStatus.COMPLETED:
                lines.append(f"       Confidence: {task.confidence:.0%}")
                if task.artifacts:
                    lines.append(f"       Artifacts: {', '.join(task.artifacts[:5])}")
            if task.status == TaskStatus.FAILED:
                lines.append(f"       Error: {task.error}")
            lines.append("")

        lines.append("-" * 72)
        lines.append(plan.summary())
        lines.append("=" * 72)

        return "\n".join(lines)

    def format_results(self, plan: ExecutionPlan) -> str:
        """Format execution results for display."""
        lines = [
            "=" * 72,
            "EXECUTION RESULTS",
            "=" * 72,
            "",
            plan.summary(),
            "",
        ]

        for task in plan.tasks:
            if task.status == TaskStatus.COMPLETED:
                lines.append(f"### {task.title}")
                lines.append(f"Agent: {task.assigned_agent} | Confidence: {task.confidence:.0%}")
                lines.append("")
                # Truncate long results
                result_preview = task.result[:1000]
                if len(task.result) > 1000:
                    result_preview += "\n... (truncated)"
                lines.append(result_preview)
                if task.artifacts:
                    lines.append(f"\nArtifacts: {', '.join(task.artifacts)}")
                lines.append("")

            elif task.status == TaskStatus.FAILED:
                lines.append(f"### {task.title} [FAILED]")
                lines.append(f"Error: {task.error}")
                lines.append("")

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # Internal
    # -----------------------------------------------------------------------

    def _resolve_blocked_tasks(self, plan: ExecutionPlan) -> None:
        """Mark tasks as cancelled if their dependencies failed."""
        failed_ids = {t.task_id for t in plan.failed_tasks}

        for task in plan.tasks:
            if task.status != TaskStatus.PENDING:
                continue

            # Check if any dependency has failed
            blocked_by_failure = any(
                dep_id in failed_ids for dep_id in task.dependencies
            )

            if blocked_by_failure:
                task.status = TaskStatus.CANCELLED
                task.error = "Cancelled — dependency task failed"

                if self.logger:
                    self.logger.log_event(
                        "execution_engine",
                        f"Cancelled: {task.title} (dependency failed)",
                    )
