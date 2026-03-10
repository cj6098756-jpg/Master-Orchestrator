"""Tier 0 orchestrator system prompt and prompt builders."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from master_orchestrator.models.agent_output import AgentReport
    from master_orchestrator.models.task import TaskPlan


# ---------------------------------------------------------------------------
# Tier 0 System Prompt Template
# ---------------------------------------------------------------------------

ORCHESTRATOR_SYSTEM_PROMPT = """You are the Master Orchestrator (Tier 0).

Your role is to interpret the user's objective, decompose it into specialist tasks, dispatch to the appropriate agents via the Agent tool, validate their outputs, and synthesize a comprehensive final result.

## Available Specialist Agents

You have access to these agents via the Agent tool. Select only the agents relevant to the current objective.

### Tier 1 — Specialists (broad domain experts):
{tier1_agent_list}

### Tier 2 — Niche Specialists (deep domain experts):
{tier2_agent_list}

## Dispatch Protocol

1. Analyze the objective and identify which specialists are needed
2. Dispatch Tier 1 specialists FIRST — use the Agent tool to delegate specific subtasks
3. Review each agent's response for confidence level and escalation signals
4. If an agent reports confidence < {quality_threshold} or escalation_used = true, note the gap
5. The orchestrator code will handle Tier 2 dispatch in a second phase if needed

## Agent Output Requirements

When dispatching to agents, instruct each one to return a JSON report with:
- agent_name, task_assigned, inputs_used, assumptions
- findings (detailed analysis)
- risks_and_gaps (list of concerns)
- confidence_level (0.0 to 1.0)
- escalation_used (bool), escalation_notes
- recommended_output (actionable deliverable)

## Your Final Synthesis

After collecting all agent reports, produce a synthesis in this exact structure:

1. **Objective**: Restate the goal
2. **Confirmed Inputs**: What facts are established
3. **Assumptions**: What was assumed
4. **Missing Information**: What remains unknown
5. **Agent Plan**: Which agents were used and why
6. **Specialist Findings**: Per-agent summary
7. **Key Risks / Constraints**: Critical concerns
8. **Final Synthesis**: Integrated analysis and recommendations
9. **Recommended Next Steps**: Actionable items
10. **Development-Ready Output**: Implementation artifacts (if applicable)

## Iteration Context
{iteration_context}
"""


# ---------------------------------------------------------------------------
# Prompt Builders
# ---------------------------------------------------------------------------


def build_orchestrator_prompt(
    tier1_agents: dict[str, str],
    tier2_agents: dict[str, str],
    quality_threshold: float,
    iteration: int,
    max_iterations: int,
    accumulated_context: str = "",
) -> str:
    """Build the Tier 0 orchestrator system prompt.

    Args:
        tier1_agents: {key: description} for Tier 1 agents.
        tier2_agents: {key: description} for Tier 2 agents.
        quality_threshold: Confidence threshold for auto-completion.
        iteration: Current iteration number.
        max_iterations: Maximum iterations allowed.
        accumulated_context: Synthesis from previous iterations.
    """
    tier1_list = "\n".join(
        f"- **{key}**: {desc}" for key, desc in tier1_agents.items()
    )
    tier2_list = "\n".join(
        f"- **{key}**: {desc}" for key, desc in tier2_agents.items()
    )

    if accumulated_context:
        iteration_context = (
            f"Iteration {iteration} of {max_iterations}.\n\n"
            f"### Previous Iteration Findings:\n{accumulated_context}"
        )
    else:
        iteration_context = (
            f"Iteration {iteration} of {max_iterations}. First pass — no prior context."
        )

    return ORCHESTRATOR_SYSTEM_PROMPT.format(
        tier1_agent_list=tier1_list or "None selected for this phase.",
        tier2_agent_list=tier2_list or "None selected for this phase.",
        quality_threshold=quality_threshold,
        iteration_context=iteration_context,
    )


def build_tier2_dispatch_prompt(
    objective: str,
    tier1_findings: list[AgentReport],
    escalation_needs: list[dict],
) -> str:
    """Build the prompt for Tier 2 niche specialist dispatch.

    Includes Tier 1 findings as context and specific gaps to address.
    """
    findings_summary = "\n\n".join(
        f"### {r.agent_name} (confidence: {r.confidence_level:.0%})\n"
        f"**Findings:** {r.findings[:500]}...\n"
        f"**Gaps:** {', '.join(r.risks_and_gaps[:3])}\n"
        f"**Escalation notes:** {r.escalation_notes or 'None'}"
        for r in tier1_findings
    )

    gaps_summary = "\n".join(
        f"- [{e['from_agent']}] needs [{e['to_agent']}]: {e['reason']}"
        for e in escalation_needs
    )

    return f"""## Objective
{objective}

## Tier 1 Specialist Findings (for context)
{findings_summary}

## Identified Gaps Requiring Niche Expertise
{gaps_summary}

## Your Task
Use the available Tier 2 niche specialist agents to address the specific gaps identified above. Each niche specialist should provide deep expertise to fill what the Tier 1 specialists could not.

Dispatch each relevant Tier 2 agent and collect their structured reports. Then synthesize a gap-filling summary."""


def build_synthesis_prompt(
    objective: str,
    task_plan: TaskPlan,
    all_reports: list[AgentReport],
    iteration: int,
) -> str:
    """Build the prompt for final output synthesis."""
    reports_text = "\n\n".join(
        f"### {r.agent_name}\n"
        f"- **Task:** {r.task_assigned}\n"
        f"- **Confidence:** {r.confidence_level:.0%}\n"
        f"- **Findings:** {r.findings}\n"
        f"- **Risks:** {', '.join(r.risks_and_gaps)}\n"
        f"- **Recommendation:** {r.recommended_output}"
        for r in all_reports
    )

    plan_text = "\n".join(
        f"- {s.assigned_agent} (Tier {s.tier}): {s.description}"
        for s in task_plan.subtasks
    )

    return f"""Synthesize the following multi-agent findings into a comprehensive structured report.

## Objective
{objective}

## Agent Execution Plan
{plan_text}

## All Agent Reports ({len(all_reports)} total, iteration {iteration})
{reports_text}

## Task Plan Assumptions
{chr(10).join(f'- {a}' for a in task_plan.assumptions) if task_plan.assumptions else 'None'}

## Missing Information (from task decomposition)
{chr(10).join(f'- {m}' for m in task_plan.missing_information) if task_plan.missing_information else 'None'}

## Instructions
Produce the final 10-section synthesis:
1. Objective
2. Confirmed Inputs
3. Assumptions
4. Missing Information
5. Agent Plan
6. Specialist Findings
7. Key Risks / Constraints
8. Final Synthesis
9. Recommended Next Steps
10. Development-Ready Output (if the task is build-oriented)

Be specific, actionable, and explicit about remaining uncertainties."""
