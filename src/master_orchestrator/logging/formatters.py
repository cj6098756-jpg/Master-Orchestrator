"""Log formatters for markdown and JSON output."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any


def format_markdown_log(event: dict[str, Any]) -> str:
    """Format a log event as a markdown entry."""
    timestamp = event.get("timestamp", datetime.now(timezone.utc).isoformat())
    source = event.get("source", "unknown")
    level = event.get("level", "INFO")
    message = event.get("message", "")

    return f"**[{timestamp}]** `{level}` *{source}*: {message}"


def format_json_log(event: dict[str, Any]) -> str:
    """Format a log event as a JSON line."""
    if "timestamp" not in event:
        event["timestamp"] = datetime.now(timezone.utc).isoformat()
    return json.dumps(event, default=str)


def format_agent_report_markdown(report_dict: dict) -> str:
    """Format an agent report dict as markdown."""
    lines = [
        f"### {report_dict.get('agent_name', 'Unknown Agent')}",
        f"- **Task:** {report_dict.get('task_assigned', 'N/A')}",
        f"- **Confidence:** {report_dict.get('confidence_level', 0):.0%}",
        f"- **Findings:** {report_dict.get('findings', 'N/A')[:300]}",
    ]

    risks = report_dict.get("risks_and_gaps", [])
    if risks:
        lines.append(f"- **Risks:** {', '.join(risks[:3])}")

    if report_dict.get("escalation_used"):
        lines.append(
            f"- **Escalation:** {report_dict.get('escalation_notes', 'N/A')}"
        )

    return "\n".join(lines)
