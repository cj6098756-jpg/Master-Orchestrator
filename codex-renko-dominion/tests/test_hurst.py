from __future__ import annotations

import random

from renko.regime import compute_hurst, fractal_dimension, hurst_rs


def test_trending_hurst_gt_half():
    prices = [1 + i * 0.01 for i in range(300)]
    assert hurst_rs(prices) > 0.5


def test_random_hurst_near_half():
    random.seed(42)
    prices = [1.0]
    for _ in range(400):
        prices.append(prices[-1] + random.gauss(0, 0.01))
    h = hurst_rs(prices)
    assert 0.2 < h < 0.8


def test_d_relation():
    h = 0.6
    assert fractal_dimension(h) == 1.4


def test_circuit_breaker():
    prices = [(-1) ** i * 0.1 + i * 0.0001 for i in range(400)]
    result = compute_hurst(prices)
    assert result.signal_inhibited == (result.D < 1.55)
