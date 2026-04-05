from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from codex.doctrine import DoctrineResult, check_doctrine
from codex.fct import FCTInputs, FCTScore, score_fct
from execution.entropy_gate import GateResult, check_entropy_gate
from execution.lot_ladder import LotLadder
from renko.features import RenkoFeatures, extract
from renko.fsm import Direction, MultiScaleFSM, RenkoFSM, TierAlignment
from renko.regime import HurstResult, compute_hurst


@dataclass(frozen=True)
class TradeSignal:
    """Fully gated trade signal output."""

    direction: str
    lot_size: float
    fct_score: FCTScore
    hurst: HurstResult
    features: RenkoFeatures
    alignment: TierAlignment
    entropy_gate: GateResult
    doctrine: DoctrineResult
    timestamp: str


class SignalManager:
    """End-to-end Renko signal pipeline with hard gates."""

    def __init__(self) -> None:
        self.ms = MultiScaleFSM()
        self.trigger = RenkoFSM(0.0025)
        self.ladder = LotLadder()

    def process(self, prices: list[float]) -> TradeSignal | None:
        """Process price series and emit trade signal when all gates pass."""
        if len(prices) < 50:
            return None
        for p in prices:
            self.ms.feed(p)
            self.trigger.feed(p)
        bricks = self.trigger.signal_events(prices)
        renko_bricks = []
        fsm = RenkoFSM(0.0025)
        for p in prices:
            renko_bricks.extend(fsm.feed(p))
        if not renko_bricks:
            return None

        features = extract(renko_bricks)
        hurst = compute_hurst(prices)
        if hurst.signal_inhibited:
            return None

        gate = check_entropy_gate(features.entropy, features.ofi)
        if not gate.open:
            return None

        alignment = self.ms.alignment()
        trend_alignment = 1.0 if alignment.aligned else 0.4
        direction = self.trigger.direction
        if direction == Direction.NONE:
            return None

        inputs = FCTInputs(
            trend_alignment=trend_alignment,
            momentum_confirm=max(0.0, min(1.0, features.velocity)),
            volatility_profile=max(0.0, min(1.0, 1.0 - abs(features.acceleration))),
            regime_clarity=max(0.0, min(1.0, hurst.D - 1.0)),
            risk_reward_ratio=0.7,
            pattern_integrity=max(0.0, min(1.0, abs(features.ofi))),
            macro_alignment=0.6,
        )
        fct = score_fct(inputs)
        if not fct.is_tradeable():
            return None

        doctrine = check_doctrine(f"enter {direction.value.lower()} on fct grade {fct.grade}", fct)
        if not doctrine.allowed:
            return None

        return TradeSignal(
            direction=direction.value,
            lot_size=self.ladder.current_lot_size(),
            fct_score=fct,
            hurst=hurst,
            features=features,
            alignment=alignment,
            entropy_gate=gate,
            doctrine=doctrine,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
