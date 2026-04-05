from __future__ import annotations

from renko.fsm import Direction, EventType, MultiScaleFSM, RenkoFSM


def test_brick_formation_up():
    fsm = RenkoFSM(1.0)
    fsm.feed(100)
    bricks = fsm.feed(102.2)
    assert len(bricks) == 2
    assert all(b.direction == Direction.UP for b in bricks)


def test_reversal_requires_two_bricks():
    fsm = RenkoFSM(1.0)
    for p in [100, 101.1, 102.2]:
        fsm.feed(p)
    first = fsm.feed(100.9)
    assert len(first) == 0
    second = fsm.feed(99.8)
    assert len(second) >= 1
    assert second[0].direction == Direction.DOWN


def test_multiscale_alignment():
    ms = MultiScaleFSM()
    prices = [1.1 + i * 0.03 for i in range(30)]
    for p in prices:
        ms.feed(p)
    a = ms.alignment()
    assert a.aligned is True


def test_signal_events_trending():
    fsm = RenkoFSM(0.01)
    prices = [1 + i * 0.02 for i in range(100)]
    events = fsm.signal_events(prices)
    assert len(events) > 0
    assert events[0].event_type in {EventType.REVERSAL, EventType.CONTINUATION}


def test_no_lookahead_signal_index_progresses():
    fsm = RenkoFSM(0.5)
    prices = [10 + i * 0.7 for i in range(20)]
    events = fsm.signal_events(prices)
    assert all(events[i].brick_index <= events[i + 1].brick_index for i in range(len(events) - 1))
