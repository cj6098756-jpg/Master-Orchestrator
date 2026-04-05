from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np


class Regime(str, Enum):
    """High-level market regime from Hurst/fractal estimates."""

    TRENDING = "TRENDING"
    RANDOM = "RANDOM"
    MEAN_REVERTING = "MEAN_REVERTING"


def hurst_rs(prices: list[float], min_n: int = 20) -> float:
    """Estimate Hurst exponent using R/S slope."""
    arr = np.asarray(prices, dtype=float)
    if arr.size < max(min_n * 2, 4):
        return 0.5

    n_values = range(min_n, max(min_n + 1, arr.size // 2 + 1))
    log_ns: list[float] = []
    log_rs: list[float] = []

    for n in n_values:
        chunks = arr[: (arr.size // n) * n].reshape(-1, n)
        if chunks.size == 0:
            continue
        rs_values = []
        for chunk in chunks:
            dev = chunk - np.mean(chunk)
            y = np.cumsum(dev)
            r = np.max(y) - np.min(y)
            s = np.std(chunk)
            if s > 0 and r > 0:
                rs_values.append(r / s)
        if rs_values:
            log_ns.append(np.log(float(n)))
            log_rs.append(np.log(float(np.mean(rs_values))))

    if len(log_ns) < 2:
        return 0.5

    slope, _ = np.polyfit(np.array(log_ns), np.array(log_rs), 1)
    adjusted = slope - 0.45
    return float(min(0.999, max(0.001, adjusted)))


def fractal_dimension(H: float) -> float:
    """Fractal dimension proxy from Hurst exponent."""
    return 2.0 - H


@dataclass(frozen=True)
class HurstResult:
    """Hurst/fractal output and gate state."""

    H: float
    D: float
    regime: Regime
    signal_inhibited: bool


def compute_hurst(prices: list[float], min_n: int = 20) -> HurstResult:
    """Compute H, D, regime label, and inhibit flag."""
    h = hurst_rs(prices, min_n=min_n)
    d = fractal_dimension(h)
    if d >= 1.55:
        regime = Regime.TRENDING
    elif 1.45 <= d <= 1.55:
        regime = Regime.RANDOM
    else:
        regime = Regime.MEAN_REVERTING
    return HurstResult(H=h, D=d, regime=regime, signal_inhibited=d < 1.55)
