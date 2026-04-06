from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Protocol

from scaffold.contracts import ToolCall, ToolResult, ToolSpec


class ToolProtocol(Protocol):
    spec: ToolSpec

    def requires_approval(self) -> bool:
        ...

    def execute(self, inputs: dict) -> ToolResult:
        ...


@dataclass
class Tool:
    spec: ToolSpec
    handler: Callable[[dict], dict]

    def requires_approval(self) -> bool:
        return self.spec.is_destructive or not self.spec.is_read_only

    def execute(self, inputs: dict) -> ToolResult:
        try:
            output = self.handler(inputs)
            return ToolResult(ok=True, output=output)
        except Exception as exc:
            return ToolResult(ok=False, output={}, error=str(exc))


@dataclass
class ToolRegistry:
    _tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        self._tools[tool.spec.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all_tools(self) -> list[Tool]:
        return list(self._tools.values())

    def filter(self, *, read_only: bool | None = None, destructive: bool | None = None) -> list[Tool]:
        tools = self.all_tools()
        if read_only is not None:
            tools = [t for t in tools if t.spec.is_read_only == read_only]
        if destructive is not None:
            tools = [t for t in tools if t.spec.is_destructive == destructive]
        return tools

    def to_anthropic_format(self) -> list[dict]:
        return [
            {
                "name": t.spec.name,
                "description": t.spec.description,
                "input_schema": t.spec.input_schema,
            }
            for t in self.all_tools()
        ]


GLOBAL_REGISTRY = ToolRegistry()


def register_tool(tool: Tool) -> None:
    GLOBAL_REGISTRY.register(tool)


def get_tool(name: str) -> Tool | None:
    return GLOBAL_REGISTRY.get(name)


def get_tools() -> list[Tool]:
    return GLOBAL_REGISTRY.all_tools()


def render_tool_index() -> str:
    rows = [
        f"{t.spec.name:16s} | read_only={str(t.spec.is_read_only):5s} | destructive={str(t.spec.is_destructive):5s}"
        for t in get_tools()
    ]
    return "\n".join(rows) if rows else "(no tools)"


def execute_tool(name: str, inputs: dict) -> str:
    tool = get_tool(name)
    if tool is None:
        return json.dumps({"error": f"Unknown tool {name}"})
    result = tool.execute(inputs)
    return json.dumps(result.__dict__, default=str, indent=2)


def execute_tool_call(call: ToolCall) -> ToolResult:
    tool = get_tool(call.tool_name)
    if tool is None:
        return ToolResult(False, {}, f"Unknown tool {call.tool_name}")
    return tool.execute(call.inputs)
