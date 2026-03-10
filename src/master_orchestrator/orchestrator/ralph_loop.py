"""Ralph Wiggum iterative loop — the core orchestration engine.

Philosophy: iteration > perfection, failures as data.

The loop repeatedly dispatches specialist agents, evaluates their outputs,
escalates to niche specialists when needed, and refines the synthesis
until completion criteria are met.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from master_orchestrator.models.agent_output import AgentReport, OrchestrationResult
from master_orchestrator.models.session import SessionState
from master_orchestrator.models.task import TaskPlan
from master_orchestrator.prompts.orchestrator import (
    build_orchestrator_prompt,
    build_tier2_dispatch_prompt,
)
from master_orchestrator.prompts.templates import build_iteration_context

if TYPE_CHECKING:
    from master_orchestrator.agents.dispatch import AgentDispatcher
    from master_orchestrator.agents.factory import AgentFactory
    from master_orchestrator.agents.registry import AgentRegistry
    from master_orchestrator.config import OrchestratorConfig
    from master_orchestrator.logging.logger import OrchestratorLogger
    from master_orchestrator.orchestrator.synthesizer import OutputSynthesizer
    from master_orchestrator.orchestrator.task_parser import TaskParser
    from master_orchestrator.session.manager import SessionManager


class RalphLoop:
    """Ralph Wiggum iterative loop for multi-agent orchestration.

    The loop structure:
    1. Parse the objective into a TaskPlan
    2. LOOP (while not complete):
       a. Phase 1: Dispatch Tier 1 agents
       b. Evaluate: Check confidence, identify escalation needs
       c. Phase 2: Dispatch Tier 2 agents if gaps found
       d. Synthesize: Combine all findings
       e. Check completion criteria
       f. Feed synthesis back as context for next iteration
    3. Return final OrchestrationResult
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        registry: AgentRegistry,
        factory: AgentFactory,
        dispatcher: AgentDispatcher,
        task_parser: TaskParser,
        synthesizer: OutputSynthesizer,
        session_manager: SessionManager,
        logger: OrchestratorLogger,
    ):
        self.config = config
        self.registry = registry
        self.factory = factory
        self.dispatcher = dispatcher
        self.task_parser = task_parser
        self.synthesizer = synthesizer
        self.session_manager = session_manager
        self.logger = logger

    async def run(
        self,
        objective: str,
        max_iterations: int | None = None,
        completion_promise: str | None = None,
        resume_state: SessionState | None = None,
    ) -> OrchestrationResult:
        """Execute the full orchestration loop.

        Args:
            objective: The user's stated goal.
            max_iterations: Override for config max_iterations.
            completion_promise: Exact string to match for completion.
            resume_state: Previous session state to resume from.

        Returns:
            A complete OrchestrationResult.
        """
        max_iter = max_iterations or self.config.ralph_loop.max_iterations
        promise = completion_promise or self.config.ralph_loop.completion_promise
        session_id = (
            resume_state.session_id if resume_state
            else str(uuid.uuid4())[:12]
        )

        # Initialize or resume state
        if resume_state:
            all_reports = list(resume_state.agent_reports)
            iteration = resume_state.iteration_count
            accumulated_context = resume_state.accumulated_context
            task_plan = resume_state.task_plan or await self.task_parser.parse(objective)
            self.logger.log_event("ralph_loop", f"Resuming session {session_id} at iteration {iteration}")
        else:
            all_reports = []
            iteration = 0
            accumulated_context = ""
            self.logger.log_event("ralph_loop", f"Starting new session {session_id}")

            # Step 1: Parse objective into task plan
            self.logger.log_event("ralph_loop", "Decomposing objective into task plan")
            task_plan = await self.task_parser.parse(objective)

        self.logger.log_task_plan(task_plan)

        # Create session state for persistence
        session_state = SessionState(
            session_id=session_id,
            objective=objective,
            task_plan=task_plan,
            status="active",
        )

        # The synthesis result (updated each iteration)
        result: OrchestrationResult | None = None

        # Step 2: The Ralph Wiggum Loop
        while iteration < max_iter:
            iteration += 1
            self.logger.log_iteration_start(iteration, max_iter)

            # --- Phase 1: Tier 1 Dispatch ---
            tier1_keys = [s.assigned_agent for s in task_plan.tier1_subtasks]
            tier1_agents = self.factory.build_tier1_agents(tier1_keys)

            tier1_system_prompt = build_orchestrator_prompt(
                tier1_agents={k: t.description for k, t in self.registry.tier1_agents.items() if k in tier1_agents},
                tier2_agents={},  # No Tier 2 in Phase 1
                quality_threshold=self.config.ralph_loop.quality_threshold,
                iteration=iteration,
                max_iterations=max_iter,
                accumulated_context=accumulated_context,
            )

            tier1_prompt = f"## Objective\n{objective}\n\n## Task Plan\n"
            tier1_prompt += "\n".join(
                f"- [{s.assigned_agent}]: {s.description}"
                for s in task_plan.tier1_subtasks
            )

            self.logger.log_event(
                "ralph_loop",
                f"Phase 1: Dispatching {len(tier1_agents)} Tier 1 agents",
            )

            tier1_result, tier1_reports, sdk_session_id = (
                await self.dispatcher.dispatch_phase(
                    prompt=tier1_prompt,
                    system_prompt=tier1_system_prompt,
                    agent_definitions=tier1_agents,
                )
            )
            all_reports.extend(tier1_reports)

            if sdk_session_id:
                session_state.sdk_session_id = sdk_session_id

            # --- Evaluate: Check for escalation needs ---
            escalation_needs = self._evaluate_for_escalation(tier1_reports)

            # --- Phase 2: Tier 2 Dispatch (if needed) ---
            if escalation_needs:
                self.logger.log_event(
                    "ralph_loop",
                    f"Phase 2: {len(escalation_needs)} escalations detected",
                )

                # Build Tier 2 agents based on escalation needs
                from_agents = [e["from_agent"] for e in escalation_needs]
                tier2_agents = self.factory.build_escalation_agents(from_agents)

                if tier2_agents:
                    tier2_prompt = build_tier2_dispatch_prompt(
                        objective=objective,
                        tier1_findings=tier1_reports,
                        escalation_needs=escalation_needs,
                    )

                    tier2_system_prompt = build_orchestrator_prompt(
                        tier1_agents={},
                        tier2_agents={k: t.description for k, t in self.registry.tier2_agents.items() if k in tier2_agents},
                        quality_threshold=self.config.ralph_loop.quality_threshold,
                        iteration=iteration,
                        max_iterations=max_iter,
                        accumulated_context="",
                    )

                    self.logger.log_event(
                        "ralph_loop",
                        f"Phase 2: Dispatching {len(tier2_agents)} Tier 2 agents",
                    )

                    _, tier2_reports, _ = await self.dispatcher.dispatch_phase(
                        prompt=tier2_prompt,
                        system_prompt=tier2_system_prompt,
                        agent_definitions=tier2_agents,
                    )
                    all_reports.extend(tier2_reports)
            else:
                self.logger.log_event("ralph_loop", "No escalations needed")

            # --- Synthesize ---
            result = await self.synthesizer.synthesize(
                objective=objective,
                task_plan=task_plan,
                reports=all_reports,
                iteration=iteration,
                session_id=session_id,
            )

            # --- Check completion ---
            if self._is_complete(result, promise, all_reports, iteration, max_iter):
                self.logger.log_completion(iteration, "criteria_met")
                break

            # --- Feed synthesis back as context ---
            accumulated_context = self._build_iteration_context(
                result, all_reports, iteration, max_iter
            )
            self.logger.log_iteration_end(iteration)

            # --- Persist session state ---
            session_state.iteration_count = iteration
            session_state.agent_reports = all_reports
            session_state.accumulated_context = accumulated_context
            session_state.touch()
            self.session_manager.save(session_state)

        # Step 3: Finalize
        if result is None:
            # Should not happen, but safety net
            result = OrchestrationResult(
                objective=objective,
                final_synthesis="No iterations completed.",
                iteration_count=iteration,
                session_id=session_id,
            )

        result.iteration_count = iteration
        result.session_id = session_id

        # Save final session state
        session_state.status = "completed"
        session_state.iteration_count = iteration
        session_state.agent_reports = all_reports
        session_state.touch()
        self.session_manager.save(session_state)

        self.logger.log_event(
            "ralph_loop",
            f"Orchestration complete. {iteration} iterations, "
            f"{len(all_reports)} agent reports, "
            f"avg confidence: {result.avg_confidence:.0%}",
        )

        return result

    # -----------------------------------------------------------------------
    # Evaluation and Completion
    # -----------------------------------------------------------------------

    def _evaluate_for_escalation(
        self,
        reports: list[AgentReport],
    ) -> list[dict]:
        """Determine which Tier 1 findings need Tier 2 escalation.

        Escalation triggers:
        - Agent confidence < quality_threshold
        - Agent explicitly set escalation_used = True
        - Agent has significant risks/gaps
        """
        threshold = self.config.ralph_loop.quality_threshold
        escalations = []

        for report in reports:
            needs_escalation = (
                report.escalation_used
                or report.confidence_level < threshold
            )

            if needs_escalation:
                # Find Tier 2 targets for this agent
                targets = self.registry.get_escalation_targets(report.agent_name)
                if targets:
                    for target in targets:
                        reason = (
                            report.escalation_notes
                            or f"Low confidence ({report.confidence_level:.0%})"
                        )
                        escalations.append({
                            "from_agent": report.agent_name,
                            "to_agent": target,
                            "reason": reason,
                        })

                        self.logger.log_escalation(
                            from_agent=report.agent_name,
                            to_agent=target,
                            reason=reason,
                        )

        return escalations

    def _is_complete(
        self,
        result: OrchestrationResult,
        completion_promise: str | None,
        reports: list[AgentReport],
        iteration: int,
        max_iterations: int,
    ) -> bool:
        """Check if the loop should terminate.

        Completion criteria (any one sufficient):
        1. completion_promise exact match found in synthesis
        2. All agent confidence >= threshold AND no pending escalations
        3. Max iterations reached
        """
        # Criterion 3: Max iterations (always checked)
        if iteration >= max_iterations:
            self.logger.log_event(
                "ralph_loop", f"Max iterations ({max_iterations}) reached"
            )
            return True

        # Criterion 1: Completion promise match
        if completion_promise and completion_promise in result.final_synthesis:
            self.logger.log_event(
                "ralph_loop", f"Completion promise matched: '{completion_promise}'"
            )
            return True

        # Criterion 2: Quality threshold met
        threshold = self.config.ralph_loop.quality_threshold
        if reports:
            avg_confidence = sum(r.confidence_level for r in reports) / len(reports)
            no_pending_escalations = not any(
                r.escalation_used and not r.escalation_notes
                for r in reports
            )

            if avg_confidence >= threshold and no_pending_escalations:
                self.logger.log_event(
                    "ralph_loop",
                    f"Quality threshold met: avg confidence={avg_confidence:.0%}",
                )
                return True

        return False

    def _build_iteration_context(
        self,
        result: OrchestrationResult,
        reports: list[AgentReport],
        iteration: int,
        max_iterations: int,
    ) -> str:
        """Build context string for the next iteration.

        Summarizes current findings, gaps, and quality assessment
        so the next iteration can build upon prior work.
        """
        findings_summary = "\n".join(
            f"- [{r.agent_name}] ({r.confidence_level:.0%}): {r.findings[:200]}"
            for r in reports[-8:]  # Last 8 reports to avoid context overflow
        )

        gaps = "\n".join(
            f"- {gap}"
            for r in reports
            for gap in r.risks_and_gaps[:2]
        )

        low_confidence = [
            f"{r.agent_name} ({r.confidence_level:.0%})"
            for r in reports
            if r.confidence_level < self.config.ralph_loop.quality_threshold
        ]

        pending_esc = [
            r.agent_name
            for r in reports
            if r.escalation_used
        ]

        avg_conf = (
            sum(r.confidence_level for r in reports) / len(reports)
            if reports
            else 0.0
        )

        return build_iteration_context(
            iteration=iteration,
            max_iterations=max_iterations,
            findings_summary=findings_summary or "No findings yet.",
            gaps=gaps or "No gaps identified.",
            avg_confidence=avg_conf,
            low_confidence_agents=", ".join(low_confidence) or "None",
            pending_escalations=", ".join(pending_esc) or "None",
        )
