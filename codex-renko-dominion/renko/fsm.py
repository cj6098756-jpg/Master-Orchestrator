from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Direction(str, Enum):
    """Directional state for Renko logic."""

    UP = "UP"
    DOWN = "DOWN"
    NONE = "NONE"


class EventType(str, Enum):
    """Signal event categories."""

    CONTINUATION = "CONTINUATION"
    REVERSAL = "REVERSAL"


@dataclass(frozen=True)
class RenkoBrick:
    """A single confirmed Renko brick."""

    direction: Direction
    open_price: float
    close_price: float
    index: int


@dataclass(frozen=True)
class SignalEvent:
    """Signal event emitted on brick confirmation."""

    event_type: EventType
    direction: Direction
    sequence: int
    brick_index: int


@dataclass(frozen=True)
class TierAlignment:
    """Directional alignment across super, macro, and trigger tiers."""

    super_dir: Direction
    macro_dir: Direction
    trigger_dir: Direction
    aligned: bool


class RenkoFSM:
    """Event-driven Renko finite state machine with strict 2-brick reversals."""

    def __init__(self, brick_size: float) -> None:
        self.brick_size = brick_size
        self.direction = Direction.NONE
        self.open_price: float | None = None
        self.close_price: float | None = None
        self.sequence = 0
        self.pullback_depth = 0
        self.total_bricks = 0
        self._pending_reversal = 0
        self._pending_direction = Direction.NONE

    def feed(self, price: float) -> list[RenkoBrick]:
        """Feed one price and return all newly confirmed bricks."""
        if self.open_price is None:
            self.open_price = price
            self.close_price = price
            return []

        assert self.close_price is not None
        bricks: list[RenkoBrick] = []

        while True:
            up_ready = price >= self.close_price + self.brick_size
            down_ready = price <= self.close_price - self.brick_size
            if not up_ready and not down_ready:
                break

            candidate = Direction.UP if up_ready else Direction.DOWN
            if self.direction == Direction.NONE or candidate == self.direction:
                self._pending_reversal = 0
                self._pending_direction = Direction.NONE
                bricks.append(self._commit_brick(candidate))
                continue

            if self._pending_direction != candidate:
                self._pending_direction = candidate
                self._pending_reversal = 1
                self.pullback_depth = 1
                self._simulate_close(candidate)
                continue

            self._pending_reversal += 1
            self.pullback_depth = self._pending_reversal
            if self._pending_reversal >= 2:
                bricks.append(self._commit_brick(candidate))
                self._pending_reversal = 0
                self._pending_direction = Direction.NONE
            else:
                self._simulate_close(candidate)

        return bricks

    def _simulate_close(self, direction: Direction) -> None:
        assert self.close_price is not None
        if direction == Direction.UP:
            self.close_price += self.brick_size
        else:
            self.close_price -= self.brick_size

    def _commit_brick(self, direction: Direction) -> RenkoBrick:
        assert self.close_price is not None
        open_price = self.close_price
        close_price = open_price + self.brick_size if direction == Direction.UP else open_price - self.brick_size
        self.open_price = open_price
        self.close_price = close_price
        self.total_bricks += 1

        if self.direction == direction:
            self.sequence += 1
            self.pullback_depth = 0
        else:
            self.sequence = 1
            self.pullback_depth = 0
        self.direction = direction

        return RenkoBrick(direction=direction, open_price=open_price, close_price=close_price, index=self.total_bricks)

    def signal_events(self, prices: list[float]) -> list[SignalEvent]:
        """Run a full series and emit continuation/reversal events."""
        events: list[SignalEvent] = []
        prior_dir = self.direction
        for price in prices:
            new_bricks = self.feed(price)
            for brick in new_bricks:
                event_type = EventType.CONTINUATION if brick.direction == prior_dir else EventType.REVERSAL
                events.append(
                    SignalEvent(
                        event_type=event_type,
                        direction=brick.direction,
                        sequence=self.sequence,
                        brick_index=brick.index,
                    )
                )
                prior_dir = brick.direction
        return events


class MultiScaleFSM:
    """Three-tier Renko FSM bundle used for alignment checks."""

    def __init__(self) -> None:
        self.super_fsm = RenkoFSM(brick_size=0.0250)
        self.macro_fsm = RenkoFSM(brick_size=0.0100)
        self.trigger_fsm = RenkoFSM(brick_size=0.0025)

    def feed(self, price: float) -> None:
        """Feed all tier FSMs with the same incoming price."""
        self.super_fsm.feed(price)
        self.macro_fsm.feed(price)
        self.trigger_fsm.feed(price)

    def alignment(self) -> TierAlignment:
        """Return directional alignment across tiers."""
        super_dir = self.super_fsm.direction
        macro_dir = self.macro_fsm.direction
        trigger_dir = self.trigger_fsm.direction
        aligned = super_dir != Direction.NONE and super_dir == macro_dir == trigger_dir
        return TierAlignment(super_dir=super_dir, macro_dir=macro_dir, trigger_dir=trigger_dir, aligned=aligned)
