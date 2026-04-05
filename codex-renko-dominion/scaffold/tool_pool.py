from __future__ import annotations

from dataclasses import asdict

from codex.doctrine import check_doctrine as doctrine_check
from codex.fct import FCTInputs, score_fct
from research.backtest import BacktestConfig, run_backtest as backtest_run
from renko.regime import compute_hurst as hurst_run
from scaffold.contracts import ToolSpec
from scaffold.tools import GLOBAL_REGISTRY, Tool, ToolRegistry


def _fct_handler(inputs: dict) -> dict:
    return asdict(score_fct(FCTInputs(**inputs)))


def _backtest_handler(inputs: dict) -> dict:
    prices = inputs["prices"]
    brick_size = float(inputs.get("brick_size", 0.0025))
    return asdict(backtest_run(prices, BacktestConfig(brick_size=brick_size)))


def _hurst_handler(inputs: dict) -> dict:
    return asdict(hurst_run(inputs["prices"]))


def _doctrine_handler(inputs: dict) -> dict:
    return asdict(doctrine_check(inputs["action_text"]))


BUILTIN_TOOLS: tuple[Tool, ...] = (
    Tool(
        spec=ToolSpec(
            name="fct_score",
            description="Score FCT metrics",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            is_read_only=True,
            is_destructive=False,
            is_concurrency_safe=True,
        ),
        handler=_fct_handler,
    ),
    Tool(
        spec=ToolSpec(
            name="run_backtest",
            description="Run Renko backtest",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            is_read_only=True,
            is_destructive=False,
            is_concurrency_safe=True,
        ),
        handler=_backtest_handler,
    ),
    Tool(
        spec=ToolSpec(
            name="compute_hurst",
            description="Compute Hurst and regime",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            is_read_only=True,
            is_destructive=False,
            is_concurrency_safe=True,
        ),
        handler=_hurst_handler,
    ),
    Tool(
        spec=ToolSpec(
            name="check_doctrine",
            description="Check doctrine constraints",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            is_read_only=True,
            is_destructive=False,
            is_concurrency_safe=True,
        ),
        handler=_doctrine_handler,
    ),
)


def assemble_tool_pool(mode: str = "default", read_only_only: bool = False, runtime_target: str = "local") -> ToolRegistry:
    """Register built-in tools with mode/runtime filtering support."""
    _ = mode, runtime_target
    for tool in BUILTIN_TOOLS:
        if read_only_only and not tool.spec.is_read_only:
            continue
        GLOBAL_REGISTRY.register(tool)
    return GLOBAL_REGISTRY


def tools_for_mode(mode: str) -> list[Tool]:
    """Return filtered tool list by runtime mode."""
    if mode == "read-only":
        return GLOBAL_REGISTRY.filter(read_only=True)
    if mode == "execution":
        return GLOBAL_REGISTRY.filter(read_only=False)
    return GLOBAL_REGISTRY.all_tools()
