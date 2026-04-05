from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandNode:
    name: str
    depends_on: list[str]


COMMAND_NODES: list[CommandNode] = [
    CommandNode("boot", []),
    CommandNode("env-check", ["boot"]),
    CommandNode("schema", ["env-check"]),
    CommandNode("ingest", ["schema"]),
    CommandNode("hurst", ["ingest"]),
    CommandNode("renko", ["ingest"]),
    CommandNode("fct", ["renko", "hurst"]),
    CommandNode("doctrine", ["fct"]),
    CommandNode("backtest", ["renko", "fct"]),
    CommandNode("wfo", ["backtest"]),
    CommandNode("monte-carlo", ["backtest"]),
    CommandNode("crt", ["backtest"]),
    CommandNode("strategy", ["doctrine", "hurst", "fct"]),
    CommandNode("lot-ladder", ["strategy"]),
    CommandNode("send-order", ["lot-ladder", "doctrine"]),
    CommandNode("dashboard", ["backtest", "strategy"]),
    CommandNode("kairos", ["dashboard"]),
    CommandNode("parity-audit", ["boot", "query"]),
    CommandNode("mwp-run", ["query"]),
    CommandNode("session", ["boot"]),
    CommandNode("query", ["session"]),
    CommandNode("history", ["session"]),
]


def topological_order(target: str) -> list[str]:
    graph = {n.name: n.depends_on for n in COMMAND_NODES}
    seen: set[str] = set()
    temp: set[str] = set()
    out: list[str] = []

    def visit(node: str) -> None:
        if node in seen:
            return
        if node in temp:
            raise ValueError("Cycle detected")
        temp.add(node)
        for dep in graph.get(node, []):
            visit(dep)
        temp.remove(node)
        seen.add(node)
        out.append(node)

    visit(target)
    return out
