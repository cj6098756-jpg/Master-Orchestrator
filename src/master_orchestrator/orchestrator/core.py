"""Master Orchestrator — top-level coordinator.

Tier 0: Interprets user objectives, allocates specialist agents,
validates outputs, and synthesizes final results.
Uses Ralph Wiggum iterative loops for progressive refinement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from master_orchestrator.agents.dispatch import AgentDispatcher
from master_orchestrator.agents.factory import AgentFactory
from master_orchestrator.agents.registry import AgentRegistry
from master_orchestrator.config import OrchestratorConfig, load_config
from master_orchestrator.logging.logger import OrchestratorLogger
from master_orchestrator.models.agent_output import OrchestrationResult
from master_orchestrator.orchestrator.ralph_loop import RalphLoop
from master_orchestrator.orchestrator.synthesizer import OutputSynthesizer
from master_orchestrator.orchestrator.task_parser import TaskParser
from master_orchestrator.session.manager import SessionManager


class MasterOrchestrator:
    """Tier 0: Master Orchestrator.

    Entry point for all orchestration runs. Ties together the registry,
    factory, dispatcher, parser, synthesizer, loop, and session manager.
    """

    def __init__(self, config: OrchestratorConfig | None = None):
        self.config = config or load_config()

        # Core components
        self.logger = OrchestratorLogger(self.config)
        self.registry = AgentRegistry(self.config.agents_config_path)
        self.factory = AgentFactory(self.registry, self.config)
        self.dispatcher = AgentDispatcher(self.config, self.logger)
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
