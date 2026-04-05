from __future__ import annotations

from dataclasses import asdict

from codex.doctrine import check_doctrine
from codex.fct import FCTInputs, score_fct
from research.backtest import BacktestConfig, run_backtest
from renko.regime import compute_hurst as _compute_hurst
from scaffold.tools import ToolDef, ToolRegistry, register_tool


def fct_score(**kwargs: float) -> dict:
    inputs = FCTInputs(**kwargs)
    return asdict(score_fct(inputs))


def run_backtest_tool(prices: list[float], brick_size: float = 0.0025) -> dict:
    return asdict(run_backtest(prices, BacktestConfig(brick_size=brick_size)))


def compute_hurst(prices: list[float]) -> dict:
    return asdict(_compute_hurst(prices))


def check_doctrine_tool(action_text: str) -> dict:
    return asdict(check_doctrine(action_text))


def assemble_tool_pool() -> ToolRegistry:
    register_tool(ToolDef("fct_score", "Score FCT metrics", {"type": "object"}, "scaffold.tool_pool"))
    register_tool(ToolDef("run_backtest", "Run Renko backtest", {"type": "object"}, "scaffold.tool_pool"))
    register_tool(ToolDef("compute_hurst", "Compute Hurst and regime", {"type": "object"}, "scaffold.tool_pool"))
    register_tool(ToolDef("check_doctrine", "Check doctrine constraints", {"type": "object"}, "scaffold.tool_pool"))
    return ToolRegistry()


def run_backtest(prices: list[float], brick_size: float = 0.0025) -> dict:
    return run_backtest_tool(prices, brick_size)


def check_doctrine(action_text: str) -> dict:
    return check_doctrine_tool(action_text)
