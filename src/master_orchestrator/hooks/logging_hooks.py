"""SDK hooks for audit logging of tool usage."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("master_orchestrator.hooks")


async def log_tool_use(
    input_data: dict[str, Any],
    tool_use_id: str,
    context: Any,
) -> dict:
    """PostToolUse hook — log every tool invocation for audit trail.

    Captures tool name, a summary of inputs, and the tool_use_id.
    """
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})

    # Summarize input (avoid logging full content)
    input_summary = str(tool_input)[:200] if tool_input else "no input"

    logger.debug(
        f"[hook:tool_use] {tool_name} (id={tool_use_id[:8]}): {input_summary}"
    )

    return {}


async def log_agent_spawn(
    input_data: dict[str, Any],
    tool_use_id: str,
    context: Any,
) -> dict:
    """PostToolUse hook on Agent tool — log subagent spawns.

    Tracks which subagents are being invoked by the orchestrator.
    """
    tool_input = input_data.get("tool_input", {})
    agent_type = tool_input.get("subagent_type", "unknown")
    description = tool_input.get("description", "no description")

    logger.info(
        f"[hook:agent_spawn] Agent spawned: {agent_type} — {description}"
    )

    return {}


def build_logging_hooks() -> dict:
    """Build the hooks dictionary for ClaudeAgentOptions.

    Returns a hooks dict that can be passed to the SDK for
    audit logging of all tool usage and agent spawns.
    """
    try:
        from claude_agent_sdk import HookMatcher

        return {
            "PostToolUse": [
                HookMatcher(matcher=".*", hooks=[log_tool_use]),
            ],
        }
    except ImportError:
        logger.warning("claude_agent_sdk not available; hooks disabled")
        return {}
