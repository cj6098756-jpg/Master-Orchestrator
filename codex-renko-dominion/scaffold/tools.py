from __future__ import annotations

import importlib
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ToolDef:
    name: str
    description: str
    input_schema: dict
    module: str


class ToolRegistry:
    _tools: dict[str, ToolDef] = {}

    def register(self, tool: ToolDef) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def all_tools(self) -> list[ToolDef]:
        return list(self._tools.values())

    def to_anthropic_format(self) -> list[dict]:
        return [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in self.all_tools()]


GLOBAL_REGISTRY = ToolRegistry()


def register_tool(tool: ToolDef) -> None:
    GLOBAL_REGISTRY.register(tool)


def get_tool(name: str) -> ToolDef | None:
    return GLOBAL_REGISTRY.get(name)


def get_tools() -> list[ToolDef]:
    return GLOBAL_REGISTRY.all_tools()


def render_tool_index() -> str:
    rows = [f"{t.name:16s} | {t.module:24s} | {t.description}" for t in get_tools()]
    return "\n".join(rows) if rows else "(no tools)"


def execute_tool(name: str, inputs: dict) -> str:
    tool = get_tool(name)
    if tool is None:
        return json.dumps({"error": f"Unknown tool {name}"})
    mod = importlib.import_module(tool.module)
    fn = getattr(mod, name)
    result = fn(**inputs)
    return json.dumps(result, default=lambda o: o.__dict__, indent=2)
