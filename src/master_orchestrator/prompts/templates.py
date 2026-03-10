"""Prompt templates for task decomposition."""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Task Decomposition Prompt
# ---------------------------------------------------------------------------

TASK_DECOMPOSITION_PROMPT = """Analyze the following objective and decompose it into a structured task plan.

## Objective
{objective}

## Available Agents

### Tier 1 — Specialists:
{tier1_agents}

### Tier 2 — Niche Specialists:
{tier2_agents}

## Instructions

Decompose the objective into concrete subtasks. For each subtask:
1. Assign it to the most appropriate agent from the lists above
2. Classify its type: research, analysis, strategy, development, product_design, workflow_automation, decision_support, or multi_domain_synthesis
3. Identify dependencies between subtasks (which must complete before others can start)
4. Note any assumptions you're making
5. Flag any missing information that would improve the plan

## Required Output Format

Return a valid JSON object:

```json
{{
  "objective": "restated objective",
  "task_types": ["development", "analysis"],
  "subtasks": [
    {{
      "id": "st-1",
      "description": "Research existing solutions...",
      "task_type": "research",
      "assigned_agent": "research",
      "tier": 1,
      "dependencies": [],
      "inputs": {{}},
      "status": "pending"
    }},
    {{
      "id": "st-2",
      "description": "Design system architecture...",
      "task_type": "development",
      "assigned_agent": "systems_architect",
      "tier": 1,
      "dependencies": ["st-1"],
      "inputs": {{}},
      "status": "pending"
    }}
  ],
  "assumptions": ["assumption 1"],
  "missing_information": ["what is unknown"]
}}
```

Rules:
- Use only agents from the provided lists
- Prefer Tier 1 agents; only include Tier 2 if the task clearly needs deep niche expertise
- Keep subtask count reasonable (3-8 for most objectives)
- Identify dependencies accurately — independent tasks have empty dependency lists
- Be specific in subtask descriptions
"""


def build_decomposition_prompt(
    objective: str,
    tier1_agents: dict[str, str],
    tier2_agents: dict[str, str],
) -> str:
    """Build the task decomposition prompt.

    Args:
        objective: The user's stated objective.
        tier1_agents: {key: description} for Tier 1 agents.
        tier2_agents: {key: description} for Tier 2 agents.
    """
    t1 = "\n".join(f"- **{k}**: {v}" for k, v in tier1_agents.items())
    t2 = "\n".join(f"- **{k}**: {v}" for k, v in tier2_agents.items())

    return TASK_DECOMPOSITION_PROMPT.format(
        objective=objective,
        tier1_agents=t1,
        tier2_agents=t2,
    )


# ---------------------------------------------------------------------------
# Iteration Context Template
# ---------------------------------------------------------------------------

ITERATION_CONTEXT_TEMPLATE = """### Iteration {iteration} of {max_iterations}

#### Previous Findings Summary
{findings_summary}

#### Identified Gaps
{gaps}

#### Quality Assessment
- Average confidence: {avg_confidence:.0%}
- Agents with low confidence: {low_confidence_agents}
- Pending escalations: {pending_escalations}

#### Focus for This Iteration
Address the gaps above. Improve confidence in areas where prior findings were weak. Build upon strong findings rather than repeating them.
"""


def build_iteration_context(
    iteration: int,
    max_iterations: int,
    findings_summary: str,
    gaps: str,
    avg_confidence: float,
    low_confidence_agents: str,
    pending_escalations: str,
) -> str:
    """Build the iteration context for the next Ralph Wiggum loop pass."""
    return ITERATION_CONTEXT_TEMPLATE.format(
        iteration=iteration,
        max_iterations=max_iterations,
        findings_summary=findings_summary,
        gaps=gaps,
        avg_confidence=avg_confidence,
        low_confidence_agents=low_confidence_agents,
        pending_escalations=pending_escalations,
    )
