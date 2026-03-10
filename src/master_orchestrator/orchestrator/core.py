"""Master Orchestrator — top-level coordinator.

Tier 0: Interprets user objectives, allocates specialist agents,
validates outputs, and synthesizes final results.
Uses Ralph Wiggum iterative loops for progressive refinement.

Supports two phases:
1. Analysis: Ralph Wiggum loop → 10-section OrchestrationResult
2. Execution: OrchestrationResult → ExecutionPlan → WorkerTask dispatch
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from master_orchestrator.agents.dispatch import AgentDispatcher
from master_orchestrator.agents.factory import AgentFactory
from master_orchestrator.agents.registry import AgentRegistry
from master_orchestrator.config import OrchestratorConfig, load_config
from master_orchestrator.execution.engine import ExecutionEngine
from master_orchestrator.execution.models import ExecutionPlan
from master_orchestrator.logging.logger import OrchestratorLogger
from master_orchestrator.models.agent_output import OrchestrationResult
from master_orchestrator.orchestrator.ralph_loop import RalphLoop
from master_orchestrator.orchestrator.synthesizer import OutputSynthesizer
from master_orchestrator.orchestrator.task_parser import TaskParser
from master_orchestrator.session.manager import SessionManager


class MasterOrchestrator:
    """Tier 0: Master Orchestrator.

    Entry point for all orchestration runs. Ties together the registry,
    factory, dispatcher, parser, synthesizer, loop, session manager,
    and execution engine.

    Two-phase workflow:
      1. run()     → Analysis phase → OrchestrationResult (10-section report)
      2. execute() → Execution phase → ExecutionPlan with completed WorkerTasks
    """

    def __init__(self, config: OrchestratorConfig | None = None):
        self.config = config or load_config()

        # Core components
        self.logger = OrchestratorLogger(self.config)
        self.registry = AgentRegistry(self.config.agents_config_path)
        self.factory = AgentFactory(self.registry, self.config)
        self.dispatcher = AgentDispatcher(self.config, self.logger, self.registry)
        self.task_parser = TaskParser(
            self.registry, self.config, self.dispatcher, self.logger
        )
        self.synthesizer = OutputSynthesizer(
            self.config, self.dispatcher, self.logger
        )
        self.session_manager = SessionManager(self.config)
        self.ralph_loop = RalphLoop(
            config=self.config,
            registry=self.registry,
            factory=self.factory,
            dispatcher=self.dispatcher,
            task_parser=self.task_parser,
            synthesizer=self.synthesizer,
            session_manager=self.session_manager,
            logger=self.logger,
        )

        # Execution engine
        self.execution_engine = ExecutionEngine(
            config=self.config,
            registry=self.registry,
            dispatcher=self.dispatcher,
            logger=self.logger,
            max_concurrent=getattr(self.config, 'max_concurrent_tasks', 3),
        )

    async def run(
        self,
        objective: str,
        max_iterations: int | None = None,
        completion_promise: str | None = None,
    ) -> OrchestrationResult:
        """Execute a full orchestration run.

        Args:
            objective: The user's goal or task description.
            max_iterations: Override for config max_iterations.
            completion_promise: Exact string match for loop completion.

        Returns:
            A complete OrchestrationResult with the 10-section output.
        """
        self.logger.log_event("orchestrator", f"Starting orchestration: {objective[:100]}")

        result = await self.ralph_loop.run(
            objective=objective,
            max_iterations=max_iterations,
            completion_promise=completion_promise,
        )

        self.logger.log_event(
            "orchestrator",
            f"Orchestration complete: {result.iteration_count} iterations, "
            f"avg confidence: {result.avg_confidence:.0%}",
        )

        return result

    async def resume(
        self,
        session_id: str,
        max_iterations: int | None = None,
    ) -> OrchestrationResult:
        """Resume a previous orchestration session.

        Args:
            session_id: ID of the session to resume.
            max_iterations: Additional iterations to run.

        Returns:
            Updated OrchestrationResult.
        """
        state = self.session_manager.load(session_id)
        if state is None:
            raise ValueError(f"Session not found: {session_id}")

        self.logger.log_event("orchestrator", f"Resuming session: {session_id}")

        result = await self.ralph_loop.run(
            objective=state.objective,
            max_iterations=max_iterations,
            resume_state=state,
        )

        return result

    # ------------------------------------------------------------------
    # Execution Phase
    # ------------------------------------------------------------------

    async def plan_execution(
        self,
        result: OrchestrationResult,
    ) -> ExecutionPlan:
        """Create an execution plan from an orchestration result.

        Phase 2a: Converts the 10-section analysis into executable tasks.
        Returns the plan for user review before execution.
        """
        self.logger.log_event(
            "orchestrator",
            f"Planning execution for: {result.objective[:80]}",
        )
        return await self.execution_engine.plan(result)

    async def execute(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionPlan:
        """Execute an approved execution plan.

        Phase 2b: Dispatches worker tasks to the agent pool.
        """
        self.logger.log_event(
            "orchestrator",
            f"Executing plan {plan.plan_id}: {len(plan.tasks)} tasks",
        )
        return await self.execution_engine.execute(plan)

    async def run_and_execute(
        self,
        objective: str,
        max_iterations: int | None = None,
        auto_approve: bool = True,
    ) -> tuple[OrchestrationResult, ExecutionPlan]:
        """Full pipeline: analyze → plan → execute.

        Convenience method that runs both phases end-to-end.

        Returns:
            Tuple of (OrchestrationResult, ExecutionPlan).
        """
        # Phase 1: Analysis
        result = await self.run(
            objective=objective,
            max_iterations=max_iterations,
        )

        # Phase 2: Execution
        plan = await self.execution_engine.plan_and_execute(
            result, auto_approve=auto_approve
        )

        return result, plan

    def format_plan(self, plan: ExecutionPlan) -> str:
        """Format an ExecutionPlan for display."""
        return self.execution_engine.format_plan(plan)

    def format_execution_results(self, plan: ExecutionPlan) -> str:
        """Format execution results for display."""
        return self.execution_engine.format_results(plan)

    def format_result(
        self,
        result: OrchestrationResult,
        fmt: str | None = None,
    ) -> str:
        """Format an OrchestrationResult for display.

        Args:
            result: The orchestration result.
            fmt: Output format override ("markdown" or "json").

        Returns:
            Formatted string.
        """
        output_fmt = fmt or self.config.output_format
        return self.synthesizer.format_result(result, output_fmt)

    def list_sessions(self, limit: int = 10) -> list[dict[str, Any]]:
        """List recent orchestration sessions."""
        sessions = self.session_manager.list_sessions(limit)
        return [
            {
                "session_id": s.session_id,
                "objective": s.objective[:80],
                "status": s.status,
                "iterations": s.iteration_count,
                "created": s.created_at,
                "updated": s.last_updated,
            }
            for s in sessions
        ]

    def list_agents(self, tier: int | None = None) -> str:
        """Get a formatted list of available agents.

        Args:
            tier: Filter by tier (1 or 2). None for all.
        """
        if tier == 1:
            agents = self.registry.tier1_agents
            header = "Tier 1 — Specialists"
        elif tier == 2:
            agents = self.registry.tier2_agents
            header = "Tier 2 — Niche Specialists"
        else:
            return self.registry.summary()

        lines = [f"=== {header} ===", ""]
        for key, t in sorted(agents.items()):
            lines.append(f"  {key:<22} {t.name:<28} {t.description[:60]}")
        lines.append(f"\n  Total: {len(agents)} agents")
        return "\n".join(lines)

    def status(self) -> str:
        """Check system readiness and display status."""
        lines = [
            "=== Master Orchestrator — Status ===",
            "",
            f"  Config           : {self.config.config_path}",
            f"  Agents Config    : {self.config.agents_config_path}",
            f"  Model (primary)  : {self.config.models.primary}",
            f"  Model (Tier 1)   : {self.config.models.tier1}",
            f"  Model (Tier 2)   : {self.config.models.tier2}",
            f"  Max Iterations   : {self.config.ralph_loop.max_iterations}",
            f"  Quality Threshold: {self.config.ralph_loop.quality_threshold:.0%}",
            f"  Permission Mode  : {self.config.permission_mode}",
            f"  Session Dir      : {self.config.session_dir}",
            f"  Log Dir          : {self.config.logging.log_dir}",
            f"  Tier 1 Agents    : {len(self.registry.tier1_agents)}",
            f"  Tier 2 Agents    : {len(self.registry.tier2_agents)}",
            "",
        ]

        # Check for budget limit
        if self.config.max_budget_usd:
            lines.append(f"  Budget Limit     : ${self.config.max_budget_usd:.2f}")

        if self.config.ralph_loop.completion_promise:
            lines.append(
                f"  Completion Promise: {self.config.ralph_loop.completion_promise}"
            )

        lines.append("")
        return "\n".join(lines)
