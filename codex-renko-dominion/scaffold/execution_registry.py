from __future__ import annotations

from dataclasses import dataclass, field

from scaffold.contracts import PermissionRequest, PermissionType, ToolCall, ToolResult
from scaffold.permissions import evaluate
from scaffold.tools import get_tool


@dataclass
class ExecutionRegistry:
    """Centralized lifecycle manager for tool execution."""

    calls: list[ToolCall] = field(default_factory=list)

    def dispatch(self, call: ToolCall) -> ToolResult:
        tool = get_tool(call.tool_name)
        if tool is None:
            return ToolResult(False, {}, f"Unknown tool {call.tool_name}")

        perm_type = PermissionType.READ if tool.spec.is_read_only else PermissionType.EXECUTE
        decision = evaluate(
            PermissionRequest(
                actor=call.caller,
                action=f"tool:{call.tool_name}",
                permission_type=perm_type,
                target=call.session_id,
                metadata={"is_destructive": tool.spec.is_destructive},
            )
        )
        if not decision.allowed:
            return ToolResult(False, {}, decision.reason)

        self.calls.append(call)
        return tool.execute(call.inputs)


EXECUTION_REGISTRY = {"IMPL": 22, "DEGRADED": 0, "MISSING": 0}
DEFAULT_EXECUTION_REGISTRY = ExecutionRegistry()
