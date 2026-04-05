from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np

from research.backtest import Trade


@dataclass(frozen=True)
class MonteCarloConfig:
    """Monte Carlo simulation settings."""

    n_simulations: int = 1000
    ruin_threshold_pips: float = -500.0


@dataclass(frozen=True)
class MonteCarloResult:
    """Monte Carlo simulation output summary."""

    p_ruin: float
    median_final_pnl: float
    p5_pnl: float
    p95_pnl: float
    passes_gate: bool


def run_monte_carlo(trades: list[Trade], config: MonteCarloConfig) -> MonteCarloResult:
    """Bootstrap trade order to estimate ruin and final PnL distribution."""
    pnls = [t.pnl_pips for t in trades]
    if not pnls:
        return MonteCarloResult(1.0, 0.0, 0.0, 0.0, False)

    ruined = 0
    finals: list[float] = []
    for _ in range(config.n_simulations):
        sample = random.choices(pnls, k=len(pnls))
        equity = np.cumsum(sample)
        if float(np.min(equity)) < config.ruin_threshold_pips:
            ruined += 1
        finals.append(float(equity[-1]))

    p_ruin = ruined / config.n_simulations
    return MonteCarloResult(
        p_ruin=p_ruin,
        median_final_pnl=float(np.median(finals)),
        p5_pnl=float(np.percentile(finals, 5)),
        p95_pnl=float(np.percentile(finals, 95)),
        passes_gate=p_ruin < 0.05,
    )
