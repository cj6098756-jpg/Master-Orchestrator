from __future__ import annotations

from enum import Enum


class LotTier(str, Enum):
    """Lot ladder tiers."""

    SEED = "SEED"
    GROWTH = "GROWTH"
    MOMENTUM = "MOMENTUM"
    HARVEST = "HARVEST"


LOT_SIZE = {LotTier.SEED: 0.01, LotTier.GROWTH: 0.02, LotTier.MOMENTUM: 0.03, LotTier.HARVEST: 0.05}


class LotLadder:
    """Strict tiered position sizing model."""

    def __init__(self) -> None:
        self.consecutive_wins = 0
        self.tier = LotTier.SEED

    def current_tier(self) -> LotTier:
        """Return current ladder tier."""
        return self.tier

    def current_lot_size(self) -> float:
        """Return lot size for current tier."""
        return LOT_SIZE[self.tier]

    def record_trade(self, pnl: float) -> None:
        """Promote on 3 consecutive wins; demote to seed on any loss."""
        if pnl > 0:
            self.consecutive_wins += 1
            if self.consecutive_wins >= 3:
                self._promote()
                self.consecutive_wins = 0
        else:
            self._demote()

    def _promote(self) -> None:
        order = [LotTier.SEED, LotTier.GROWTH, LotTier.MOMENTUM, LotTier.HARVEST]
        idx = order.index(self.tier)
        if idx < len(order) - 1:
            self.tier = order[idx + 1]

    def _demote(self) -> None:
        self.tier = LotTier.SEED
        self.consecutive_wins = 0
