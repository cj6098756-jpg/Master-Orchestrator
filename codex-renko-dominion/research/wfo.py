from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from research.backtest import BacktestConfig, BacktestResult, run_backtest


@dataclass(frozen=True)
class WFOConfig:
    """Walk-forward optimization settings."""

    n_splits: int = 5
    train_ratio: float = 0.7


@dataclass(frozen=True)
class WFOResult:
    """Walk-forward optimization outputs."""

    is_splits: list[BacktestResult]
    oos_splits: list[BacktestResult]
    wfe: float
    passes_gate: bool


def run_wfo(prices: list[float], config: WFOConfig, bt_config: BacktestConfig) -> WFOResult:
    """Run fold-based IS/OOS backtests and compute WFE gate."""
    n = len(prices)
    fold_size = max(1, n // config.n_splits)
    is_results: list[BacktestResult] = []
    oos_results: list[BacktestResult] = []
    for i in range(config.n_splits):
        start = i * fold_size
        end = min(n, start + fold_size)
        fold = prices[start:end]
        if len(fold) < 20:
            continue
        split = int(len(fold) * config.train_ratio)
        train = fold[:split]
        test = fold[split:]
        if len(train) < 10 or len(test) < 10:
            continue
        is_results.append(run_backtest(train, bt_config))
        oos_results.append(run_backtest(test, bt_config))

    mean_is = float(np.mean([r.sharpe for r in is_results])) if is_results else 0.0
    mean_oos = float(np.mean([r.sharpe for r in oos_results])) if oos_results else 0.0
    wfe = mean_oos / mean_is if abs(mean_is) > 1e-12 else 0.0
    return WFOResult(is_results, oos_results, wfe, wfe >= 0.50)
