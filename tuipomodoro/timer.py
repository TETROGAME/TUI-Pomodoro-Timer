import time
from dataclasses import dataclass
from enum import Enum, auto

"""
List of possible timer states
"""


class TimerState(Enum):
    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    FINISHED = auto()


"""
Return value for snapshot calculation.
"""


@dataclass
class TimerSnapshot:
    state: TimerState
    remaining: float


"""
Store internal timer logic
"""


class PomodoroTimer:
    duration: float
    started_at: float | None
    paused_at: float | None
    state: TimerState

    def __init__(self, duration: float):
        self.duration = duration
        self.started_at = None
        self.paused_at = None
        self.state = TimerState.IDLE

    def start(self) -> None:
        if self.state not in (TimerState.IDLE, TimerState.FINISHED):
            return
        self.started_at = time.monotonic()
        self.paused_at = None
        self.state = TimerState.RUNNING

    def pause(self) -> None:
        if self.state != TimerState.RUNNING:
            return
        self.paused_at = time.monotonic()
        self.state = TimerState.PAUSED

    def resume(self) -> None:
        if self.state != TimerState.PAUSED:
            return
        if self.started_at is None or self.paused_at is None:
            return
        self.started_at += time.monotonic() - self.paused_at
        self.paused_at = None
        self.state = TimerState.RUNNING

    def _snapshot(self, now: float) -> TimerSnapshot:
        """Compute an immutable view of effective state and remaining time at `now`."""
        if self.state == TimerState.IDLE or self.started_at is None:
            return TimerSnapshot(TimerState.IDLE, self.duration)
        if self.state == TimerState.FINISHED:
            return TimerSnapshot(TimerState.FINISHED, 0.0)
        if self.state == TimerState.PAUSED:
            if self.paused_at is None:
                raise RuntimeError(
                    "Invariant violation: paused timer must have paused_at"
                )
            elapsed = self.paused_at - self.started_at
            remaining = self.duration - elapsed
            if remaining <= 0:
                return TimerSnapshot(TimerState.FINISHED, 0.0)
            return TimerSnapshot(TimerState.PAUSED, max(0.0, remaining))

        elapsed = now - self.started_at
        remaining = self.duration - elapsed
        if remaining <= 0:
            return TimerSnapshot(TimerState.FINISHED, 0.0)
        return TimerSnapshot(TimerState.RUNNING, max(0.0, remaining))

    def snapshot(self, now: float | None = None) -> TimerSnapshot:
        """Public pure read API: return timer snapshot without mutating internal state."""
        if now is None:
            now = time.monotonic()
        return self._snapshot(now)

    def update_state(self, now: float | None = None) -> None:
        """Commit only the computed state transition (e.g. RUNNING -> FINISHED)."""
        snapshot = self.snapshot(now)
        self.state = snapshot.state

    def tick(self, now: float | None = None) -> TimerSnapshot:
        """Advance state and return the same-step snapshot for consistent UI updates."""
        snapshot = self.snapshot(now)
        self.state = snapshot.state
        return snapshot

    def get_remaining(self, now: float | None = None) -> float:
        """Return remaining time in seconds as a pure read operation."""
        return self.snapshot(now).remaining

    def reset(self) -> None:
        """Resets timer to IDLE state without duration change"""
        self.started_at = None
        self.paused_at = None
        self.state = TimerState.IDLE
