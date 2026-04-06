from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from renko.fsm import Direction, RenkoFSM


@dataclass(frozen=True)
class BacktestConfig:
    """Backtest configuration parameters."""

    brick_size: float = 0.0025
    sl_bricks: int = 3
    tp_bricks: int = 6
    spread_pips: float = 1.5
    lot_size: float = 0.01


@dataclass(frozen=True)
class Trade:
    """Single completed trade record."""

    entry_price: float
    exit_price: float
    direction: str
    pnl_pips: float
    entry_bar: int
    exit_bar: int


@dataclass(frozen=True)
class BacktestResult:
    """Backtest summary metrics."""

    trades: list[Trade]
    total_pnl_pips: float
    win_rate: float
    profit_factor: float
    max_drawdown_pips: float
    sharpe: float
    n_trades: int


def run_backtest(prices: list[float], config: BacktestConfig) -> BacktestResult:
    """Run zero-lookahead Renko backtest with one-brick delayed entry."""
    fsm = RenkoFSM(config.brick_size)
    bricks = []
    for p in prices:
        bricks.extend(fsm.feed(p))

    trades: list[Trade] = []
    signal_idx: int | None = None
    signal_dir: Direction | None = None

    for i in range(2, len(bricks) - 2):
        b0, b1, b2 = bricks[i - 2], bricks[i - 1], bricks[i]
        if b0.direction == b1.direction == b2.direction:
            signal_idx = b2.index
            signal_dir = b2.direction
            entry_brick = bricks[i + 1]
            entry = entry_brick.open_price
            spread = config.spread_pips / 10000.0
            entry = entry + spread if signal_dir == Direction.UP else entry - spread
            sl = entry - config.sl_bricks * config.brick_size if signal_dir == Direction.UP else entry + config.sl_bricks * config.brick_size
            tp = entry + config.tp_bricks * config.brick_size if signal_dir == Direction.UP else entry - config.tp_bricks * config.brick_size
            exit_price = bricks[-1].close_price
            exit_bar = bricks[-1].index
            for j in range(i + 2, len(bricks)):
                px = bricks[j].close_price
                if signal_dir == Direction.UP and (px <= sl or px >= tp):
                    exit_price, exit_bar = px, bricks[j].index
                    break
                if signal_dir == Direction.DOWN and (px >= sl or px <= tp):
                    exit_price, exit_bar = px, bricks[j].index
                    break
            pnl = (exit_price - entry) * 10000.0 if signal_dir == Direction.UP else (entry - exit_price) * 10000.0
            trades.append(Trade(entry, exit_price, signal_dir.value, pnl, entry_brick.index, exit_bar))

    pnls = np.array([t.pnl_pips for t in trades], dtype=float)
    total = float(np.sum(pnls)) if len(pnls) else 0.0
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    win_rate = float(len(wins) / len(trades)) if trades else 0.0
    profit_factor = float(np.sum(wins) / abs(np.sum(losses))) if len(losses) else 0.0
    equity = np.cumsum(pnls) if len(pnls) else np.array([0.0])
    peak = np.maximum.accumulate(equity)
    drawdowns = equity - peak
    max_dd = float(np.min(drawdowns)) if len(drawdowns) else 0.0
    sharpe = float(np.mean(pnls) / (np.std(pnls, ddof=1) + 1e-12) * np.sqrt(len(pnls))) if len(pnls) > 1 else 0.0

    return BacktestResult(trades, total, win_rate, profit_factor, max_dd, sharpe, len(trades))
