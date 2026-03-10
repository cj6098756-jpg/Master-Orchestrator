"""Output synthesizer — combines agent reports into structured final output."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from master_orchestrator.models.agent_output import AgentReport, OrchestrationResult
from master_orchestrator.models.task import TaskPlan
from master_orchestrator.prompts.orchestrator import build_synthesis_prompt

if TYPE_CHECKING:
    from master_orchestrator.agents.dispatch import AgentDispatcher
    from master_orchestrator.config import OrchestratorConfig
    from master_orchestrator.logging.logger import OrchestratorLogger


class OutputSynthesizer:
    """Synthesizes multi-agent findings into the structured 10-section output."""

    def __init__(
        self,
        config: OrchestratorConfig,
        dispatcher: AgentDispatcher,
        logger: OrchestratorLogger | None = None,
    ):
        self.config = config
        self.dispatcher = dispatcher
        self.logger = logger

    async def synthesize(
        self,
        objective: str,
        task_plan: TaskPlan,
        reports: list[AgentReport],
        iteration: int,
        session_id: str = "",
    ) -> OrchestrationResult:
        """Synthesize all agent reports into a final OrchestrationResult.

        Uses Claude to integrate findings across all agents into the
        10-section structured output format.

        Args:
            objective: Original user objective.
            task_plan: The task decomposition plan.
            reports: All collected AgentReport objects.
            iteration: Current iteration number.
            session_id: Session identifier.

        Returns:
            A complete OrchestrationResult.
        """
        if self.logger:
            self.logger.log_event(
                "synthesizer",
                f"Synthesizing {len(reports)} reports (iteration {iteration})",
            )

        # Build the synthesis prompt
        prompt = build_synthesis_prompt(objective, task_plan, reports, iteration)

        # Run synthesis via Claude
        raw_result = await self.dispatcher.dispatch_simple(
            prompt=prompt,
            model=self.config.models.primary,
            max_turns=5,
        )

        # Build the OrchestrationResult
        result = self._build_result(
            raw_synthesis=raw_result,
            objective=objective,
            task_plan=task_plan,
            reports=reports,
            iteration=iteration,
            session_id=session_id,
        )

        return result

    def _build_result(
        self,
        raw_synthesis: str,
        objective: str,
        task_plan: TaskPlan,
        reports: list[AgentReport],
        iteration: int,
        session_id: str,
    ) -> OrchestrationResult:
        """Build OrchestrationResult from the synthesis output.

        Tries to parse structured JSON first, falls back to using
        the raw text as the synthesis.
        """
        # Try to extract structured JSON from the synthesis
        parsed = self._try_parse_synthesis(raw_synthesis)

        if parsed:
            return OrchestrationResult(
                objective=parsed.get("objective", objective),
                confirmed_inputs=parsed.get("confirmed_inputs", []),
                assumptions=parsed.get("assumptions", task_plan.assumptions),
                missing_information=parsed.get(
                    "missing_information", task_plan.missing_information
                ),
                agent_plan=parsed.get("agent_plan", [
                    {"agent": s.assigned_agent, "task": s.description, "tier": s.tier}
                    for s in task_plan.subtasks
                ]),
                specialist_findings=reports,
                key_risks=parsed.get("key_risks", []),
                final_synthesis=parsed.get("final_synthesis", raw_synthesis),
                recommended_next_steps=parsed.get("recommended_next_steps", []),
                development_ready_output=parsed.get("development_ready_output"),
                iteration_count=iteration,
                session_id=session_id,
            )

        # Fallback: use raw synthesis text
        return OrchestrationResult(
            objective=objective,
            confirmed_inputs=[],
            assumptions=task_plan.assumptions,
            missing_information=task_plan.missing_information,
            agent_plan=[
                {"agent": s.assigned_agent, "task": s.description, "tier": s.tier}
                for s in task_plan.subtasks
            ],
            specialist_findings=reports,
            key_risks=[r for report in reports for r in report.risks_and_gaps],
            final_synthesis=raw_synthesis,
            recommended_next_steps=[],
            development_ready_output=None,
            iteration_count=iteration,
            session_id=session_id,
        )

    def _try_parse_synthesis(self, raw: str) -> dict | None:
        """Attempt to extract structured synthesis data."""
        # Try JSON code block
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if isinstance(data, dict) and "final_synthesis" in data:
                    return data
            except json.JSONDecodeError:
                pass

        # Try finding a JSON object with expected keys
        json_objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', raw, re.DOTALL)
        for json_str in sorted(json_objects, key=len, reverse=True):
            try:
                data = json.loads(json_str)
                if isinstance(data, dict) and "final_synthesis" in data:
                    return data
            except json.JSONDecodeError:
                continue

        return None

    # -----------------------------------------------------------------------
    # Formatting
    # -----------------------------------------------------------------------

    def format_result(
        self,
        result: OrchestrationResult,
        fmt: str = "markdown",
    ) -> str:
        """Format an OrchestrationResult for display.

        Args:
            result: The orchestration result to format.
            fmt: Output format — "markdown" or "json".

        Returns:
            Formatted string.
        """
        if fmt == "json":
            return json.dumps(result.to_dict(), indent=2, default=str)
        return self._format_markdown(result)

    def _format_markdown(self, result: OrchestrationResult) -> str:
        """Format result as a structured markdown report."""
        lines: list[str] = []

        lines.append("=" * 72)
        lines.append("MASTER ORCHESTRATOR — FINAL REPORT")
        lines.append("=" * 72)
        lines.append("")

        # 1. Objective
        lines.append("## 1. Objective")
        lines.append(result.objective)
        lines.append("")

        # 2. Confirmed Inputs
        lines.append("## 2. Confirmed Inputs")
        if result.confirmed_inputs:
            for ci in result.confirmed_inputs:
                lines.append(f"  - {ci}")
        else:
            lines.append("  (none identified)")
        lines.append("")

        # 3. Assumptions
        lines.append("## 3. Assumptions")
        if result.assumptions:
            for a in result.assumptions:
                lines.append(f"  - {a}")
        else:
            lines.append("  (none)")
        lines.append("")

        # 4. Missing Information
        lines.append("## 4. Missing Information")
        if result.missing_information:
            for mi in result.missing_information:
                lines.append(f"  - {mi}")
        else:
            lines.append("  (none)")
        lines.append("")

        # 5. Agent Plan
        lines.append("## 5. Agent Plan")
        for ap in result.agent_plan:
            tier = ap.get("tier", "?")
            lines.append(f"  - [{ap.get('agent', '?')}] (Tier {tier}): {ap.get('task', '')}")
        lines.append("")

        # 6. Specialist Findings
        lines.append("## 6. Specialist Findings")
        for r in result.specialist_findings:
            lines.append(f"  ### {r.agent_name} (confidence: {r.confidence_level:.0%})")
            lines.append(f"  Task: {r.task_assigned}")
            lines.append(f"  {r.findings[:500]}")
            if r.risks_and_gaps:
                lines.append(f"  Risks: {', '.join(r.risks_and_gaps[:3])}")
            if r.escalation_used:
                lines.append(f"  ESCALATION: {r.escalation_notes}")
            lines.append("")

        # 7. Key Risks
        lines.append("## 7. Key Risks / Constraints")
        if result.key_risks:
            for kr in result.key_risks:
                lines.append(f"  - {kr}")
        else:
            lines.append("  (none identified)")
        lines.append("")

        # 8. Final Synthesis
        lines.append("## 8. Final Synthesis")
        lines.append(result.final_synthesis)
        lines.append("")

        # 9. Recommended Next Steps
        lines.append("## 9. Recommended Next Steps")
        if result.recommended_next_steps:
            for i, step in enumerate(result.recommended_next_steps, 1):
                lines.append(f"  {i}. {step}")
        else:
            lines.append("  (none)")
        lines.append("")

        # 10. Development-Ready Output
        lines.append("## 10. Development-Ready Output")
        if result.development_ready_output:
            lines.append(result.development_ready_output)
        else:
            lines.append("  (not applicable or not produced)")
        lines.append("")

        # Footer
        lines.append("-" * 72)
        lines.append(
            f"Iterations: {result.iteration_count} | "
            f"Agents: {len(result.specialist_findings)} | "
            f"Avg Confidence: {result.avg_confidence:.0%} | "
            f"Session: {result.session_id or 'N/A'}"
        )
        if result.total_cost_usd is not None:
            lines.append(f"Estimated Cost: ${result.total_cost_usd:.4f}")
        lines.append("=" * 72)

        return "\n".join(lines)
