from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
from scipy import stats


class CRTVerdict(str, Enum):
    """Controlled Research Trial verdict state."""

    REJECT = "REJECT"
    FAIL_TO_REJECT = "FAIL_TO_REJECT"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class CRTHypothesis:
    """Hypothesis metadata for CRT runs."""

    name: str
    description: str
    null: str = "mean return = 0"
    min_samples: int = 30


@dataclass(frozen=True)
class CRTResult:
    """CRT run output."""

    hypothesis: CRTHypothesis
    n_samples: int
    mean: float
    std: float
    test_stat: float
    p_value: float
    verdict: CRTVerdict
    is_significant: bool


def run_crt(hypothesis: CRTHypothesis, observations: list[float], alpha: float = 0.05) -> CRTResult:
    """Run one-sample t-test against mean zero."""
    n = len(observations)
    arr = np.asarray(observations, dtype=float)
    mean = float(np.mean(arr)) if n else 0.0
    std = float(np.std(arr, ddof=1)) if n > 1 else 0.0

    if n < hypothesis.min_samples:
        return CRTResult(hypothesis, n, mean, std, 0.0, 1.0, CRTVerdict.INSUFFICIENT_DATA, False)

    stat, p = stats.ttest_1samp(arr, popmean=0.0)
    verdict = CRTVerdict.REJECT if p < alpha else CRTVerdict.FAIL_TO_REJECT
    return CRTResult(hypothesis, n, mean, std, float(stat), float(p), verdict, p < alpha)
