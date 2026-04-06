from __future__ import annotations

from execution.lot_ladder import LOT_SIZE, LotLadder, LotTier


def test_starts_seed():
    l = LotLadder()
    assert l.current_tier() == LotTier.SEED


def test_promotes_after_three_wins():
    l = LotLadder()
    for _ in range(3):
        l.record_trade(10)
    assert l.current_tier() == LotTier.GROWTH


def test_demotes_on_loss():
    l = LotLadder()
    for _ in range(3):
        l.record_trade(10)
    l.record_trade(-1)
    assert l.current_tier() == LotTier.SEED


def test_lot_sizes():
    assert LOT_SIZE[LotTier.SEED] == 0.01
    assert LOT_SIZE[LotTier.HARVEST] == 0.05
