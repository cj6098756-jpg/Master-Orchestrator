from __future__ import annotations

from dataclasses import dataclass
from math import log2

from renko.fsm import Direction, RenkoBrick


def velocity(bricks: list[RenkoBrick], window: int = 10) -> float:
    """Directional brick density proxy in the latest window."""
    if not bricks:
        return 0.0
    sample = bricks[-window:]
    last = bricks[-1].direction
    return len([b for b in sample if b.direction == last]) / max(1, window)


def acceleration(bricks: list[RenkoBrick], window: int = 10) -> float:
    """Velocity delta between latter and earlier halves."""
    if len(bricks) < 2:
        return 0.0
    sample = bricks[-window:]
    half = max(1, len(sample) // 2)
    first = sample[:half]
    second = sample[half:]
    if not second:
        return 0.0
    return velocity(first, len(first)) - velocity(second, len(second))


def shannon_entropy(bricks: list[RenkoBrick], window: int = 20) -> float:
    """Binary entropy of UP/DOWN brick frequencies."""
    sample = bricks[-window:]
    if len(sample) < 2:
        return 0.0
    up = sum(1 for b in sample if b.direction == Direction.UP)
    down = sum(1 for b in sample if b.direction == Direction.DOWN)
    total = up + down
    if total == 0:
        return 0.0
    h = 0.0
    for count in (up, down):
        if count > 0:
            p = count / total
            h -= p * log2(p)
    return h


def order_flow_imbalance(bricks: list[RenkoBrick], window: int = 20) -> float:
    """Normalized OFI in [-1,1]."""
    sample = bricks[-window:]
    if not sample:
        return 0.0
    up = sum(1 for b in sample if b.direction == Direction.UP)
    down = sum(1 for b in sample if b.direction == Direction.DOWN)
    total = up + down
    return 0.0 if total == 0 else (up - down) / total


@dataclass(frozen=True)
class RenkoFeatures:
    """Feature bundle used downstream by scoring and gating."""

    velocity: float
    acceleration: float
    entropy: float
    ofi: float
    window: int


def extract(bricks: list[RenkoBrick], window: int = 20) -> RenkoFeatures:
    """Extract feature set from brick stream."""
    return RenkoFeatures(
        velocity=velocity(bricks, window=min(window, 10)),
        acceleration=acceleration(bricks, window=min(window, 10)),
        entropy=shannon_entropy(bricks, window=window),
        ofi=order_flow_imbalance(bricks, window=window),
        window=window,
    )
