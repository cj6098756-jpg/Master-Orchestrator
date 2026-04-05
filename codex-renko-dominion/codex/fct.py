from __future__ import annotations

from dataclasses import dataclass

FCT_WEIGHTS = {
    "trend_alignment": 0.20,
    "momentum_confirm": 0.18,
    "volatility_profile": 0.15,
    "regime_clarity": 0.15,
    "risk_reward_ratio": 0.13,
    "pattern_integrity": 0.11,
    "macro_alignment": 0.08,
}

assert abs(sum(FCT_WEIGHTS.values()) - 1.0) < 1e-12, "FCT weights must sum exactly to 1.0"


@dataclass(frozen=True)
class FCTInputs:
    """Inputs normalized to [0,1] for FCT scoring."""

    trend_alignment: float
    momentum_confirm: float
    volatility_profile: float
    regime_clarity: float
    risk_reward_ratio: float
    pattern_integrity: float
    macro_alignment: float

    def __post_init__(self) -> None:
        for name, value in self.__dict__.items():
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be in [0,1], got {value}")


@dataclass(frozen=True)
class FCTScore:
    """Composite FCT output."""

    value: float
    grade: str
    inputs: FCTInputs
    weights_used: dict[str, float]

    def is_tradeable(self) -> bool:
        """Only A/B grades are eligible for entry."""
        return self.grade in {"A", "B"}


def _grade(value: float) -> str:
    if value >= 0.80:
        return "A"
    if value >= 0.65:
        return "B"
    if value >= 0.50:
        return "C"
    if value >= 0.35:
        return "D"
    return "F"


def score_fct(inputs: FCTInputs) -> FCTScore:
    """Compute weighted FCT score and grade."""
    value = sum(getattr(inputs, key) * weight for key, weight in FCT_WEIGHTS.items())
    return FCTScore(value=float(value), grade=_grade(value), inputs=inputs, weights_used=dict(FCT_WEIGHTS))
