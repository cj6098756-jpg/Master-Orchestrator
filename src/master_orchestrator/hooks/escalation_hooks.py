"""SDK hooks for escalation detection from subagent output."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("master_orchestrator.hooks")

# Markers that indicate an agent needs escalation
ESCALATION_MARKERS = [
    "ESCALATION_NEEDED",
    "escalation_used\": true",
    "escalation_used\":true",
    "needs deeper expertise",
    "insufficient domain knowledge",
]


async def detect_escalation(
    input_data: dict[str, Any],
    tool_use_id: str,
    context: Any,
) -> dict:
    """PostToolUse hook on Agent tool — detect escalation signals.

    Inspects agent output for escalation markers and logs them.
    The actual escalation dispatch is handled by the RalphLoop,
    not by this hook (hooks are for observation only).
    """
    tool_result = str(input_data.get("tool_result", ""))

    for marker in ESCALATION_MARKERS:
        if marker.lower() in tool_result.lower():
            logger.warning(
                f"[hook:escalation] Escalation signal detected: "
                f"'{marker}' in tool_use {tool_use_id[:8]}"
            )
            break

    return {}


def build_escalation_hooks() -> dict:
    """Build hooks for escalation detection."""
    try:
        from claude_agent_sdk import HookMatcher

        return {
            "PostToolUse": [
                HookMatcher(matcher="Agent", hooks=[detect_escalation]),
            ],
        }
    except ImportError:
        logger.warning("claude_agent_sdk not available; escalation hooks disabled")
        return {}
