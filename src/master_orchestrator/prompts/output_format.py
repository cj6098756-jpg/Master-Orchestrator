"""JSON schemas and format instructions for structured agent output."""

# ---------------------------------------------------------------------------
# Agent Report JSON Schema
# ---------------------------------------------------------------------------

AGENT_REPORT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "agent_name": {"type": "string", "description": "Name of the agent"},
        "task_assigned": {
            "type": "string",
            "description": "The specific task this agent was asked to complete",
        },
        "inputs_used": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of inputs, data sources, or context used",
        },
        "assumptions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Assumptions made during analysis",
        },
        "findings": {
            "type": "string",
            "description": "Detailed findings and analysis",
        },
        "risks_and_gaps": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Identified risks, gaps, or unresolved issues",
        },
        "confidence_level": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Confidence in findings (0.0 = no confidence, 1.0 = certain)",
        },
        "escalation_used": {
            "type": "boolean",
            "description": "Whether this agent needed to escalate to a niche specialist",
        },
        "escalation_notes": {
            "type": ["string", "null"],
            "description": "Details about what was escalated and why",
        },
        "recommended_output": {
            "type": "string",
            "description": "The agent's recommended output/deliverable to the orchestrator",
        },
    },
    "required": [
        "agent_name",
        "task_assigned",
        "findings",
        "confidence_level",
        "escalation_used",
        "recommended_output",
    ],
}


# ---------------------------------------------------------------------------
# Format Instructions (appended to every agent prompt)
# ---------------------------------------------------------------------------

AGENT_OUTPUT_INSTRUCTIONS = """
## Required Output Format

You MUST return your findings as a valid JSON object with these fields:

```json
{
  "agent_name": "Your Agent Name",
  "task_assigned": "The task you were given",
  "inputs_used": ["list", "of", "inputs", "and", "sources"],
  "assumptions": ["assumption 1", "assumption 2"],
  "findings": "Your detailed findings as a single string. Use markdown formatting.",
  "risks_and_gaps": ["risk 1", "gap 1", "uncertainty 1"],
  "confidence_level": 0.85,
  "escalation_used": false,
  "escalation_notes": null,
  "recommended_output": "Your actionable recommendation or deliverable."
}
```

Rules:
- confidence_level: 0.0 (no confidence) to 1.0 (certain)
- Set escalation_used to true if you lacked domain depth for any part of the task
- Include specific escalation_notes explaining what expertise is needed
- findings should be comprehensive but concise
- recommended_output should be actionable and implementation-ready when possible
"""


# ---------------------------------------------------------------------------
# Orchestrator Synthesis Schema
# ---------------------------------------------------------------------------

SYNTHESIS_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "objective": {"type": "string"},
        "confirmed_inputs": {
            "type": "array",
            "items": {"type": "string"},
        },
        "assumptions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "missing_information": {
            "type": "array",
            "items": {"type": "string"},
        },
        "agent_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "agent": {"type": "string"},
                    "task": {"type": "string"},
                    "tier": {"type": "integer"},
                },
            },
        },
        "key_risks": {
            "type": "array",
            "items": {"type": "string"},
        },
        "final_synthesis": {"type": "string"},
        "recommended_next_steps": {
            "type": "array",
            "items": {"type": "string"},
        },
        "development_ready_output": {
            "type": ["string", "null"],
        },
    },
    "required": [
        "objective",
        "final_synthesis",
        "recommended_next_steps",
    ],
}
