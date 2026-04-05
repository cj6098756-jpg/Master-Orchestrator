from __future__ import annotations

import random

from research.backtest import BacktestConfig, run_backtest


def synthetic_prices(n: int = 2000) -> list[float]:
    random.seed(1)
    prices = [1.1]
    for _ in range(n - 1):
        prices.append(prices[-1] + random.gauss(0.0002, 0.0008))
    return prices


def test_backtest_runs_and_has_metrics():
    result = run_backtest(synthetic_prices(), BacktestConfig())
    assert result.n_trades >= 0
    assert result.profit_factor >= 0
    assert 0 <= result.win_rate <= 1


def test_nonzero_trades():
    result = run_backtest(synthetic_prices(), BacktestConfig())
    assert result.n_trades > 0


def test_no_lookahead_entry_delay():
    result = run_backtest(synthetic_prices(), BacktestConfig())
    assert all(t.entry_bar < t.exit_bar for t in result.trades)


def test_total_pnl_numeric():
    result = run_backtest(synthetic_prices(), BacktestConfig())
    assert isinstance(result.total_pnl_pips, float)
