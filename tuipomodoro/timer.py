import time
from dataclasses import dataclass
from enum import Enum, auto

from tuipomodoro.config import Settings


class TimerState(Enum):
    """List of possible timer states"""

    IDLE = auto()
    RUNNING = auto()
    PAUSED = auto()
    FINISHED = auto()


@dataclass
class TimerSnapshot:
    """Return value for snapshot calculation"""

    state: TimerState
    remaining: float


class CyclePhase(Enum):
    """List of possible cycle phases"""

    TIMER = auto()
    WORK = auto()
    SHORT_BREAK = auto()
    LONG_BREAK = auto()


class PomodoroTimer:
    """Store internal timer logic"""

    duration: float
    started_at: float | None
    paused_at: float | None
    state: TimerState

    def __init__(self, duration: float = 5):
        self.duration = duration
        self.started_at = None
        self.paused_at = None
        self.state = TimerState.IDLE

    def start(self, at: None | float = None) -> None:
        if self.state not in (TimerState.IDLE, TimerState.FINISHED):
            return
        self.started_at = at if at is not None else time.monotonic()
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

    def tick(self, now: float | None = None) -> TimerSnapshot:
        """Advance state and return the same-step snapshot for consistent UI updates."""
        snapshot = self.snapshot(now)
        self.state = snapshot.state
        return snapshot

    def reset(self) -> None:
        """Resets timer to IDLE state without duration change"""
        self.started_at = None
        self.paused_at = None
        self.state = TimerState.IDLE


class CycleManager:
    """Timer orchestrator that manages timer mode and cycle transitions"""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.current_cycle = 0
        if settings.mode == "timer":
            self.current_phase = CyclePhase.TIMER
            self.timer = self._make_timer(settings.timer_duration)
        else:
            self.current_phase = CyclePhase.WORK
            self.timer = self._make_timer(settings.work_duration)

    def _make_timer(self, duration_minutes: int) -> PomodoroTimer:
        return PomodoroTimer(duration_minutes * 60)

    @property
    def state(self) -> TimerState:
        return self.timer.state

    @property
    def duration(self) -> float:
        return self.timer.duration

    def tick(self, now: float | None = None) -> TimerSnapshot:
        snapshot = self.timer.tick(now)
        if snapshot.state == TimerState.FINISHED:
            self._advance_cycle(now)
            return self.timer.snapshot(now)
        return snapshot

    def snapshot(self, now: float | None = None) -> TimerSnapshot:
        return self.timer.snapshot(now)

    def _advance_cycle(self, now: float | None = None) -> None:
        if self.current_phase == CyclePhase.TIMER:
            return

        if self.current_phase == CyclePhase.WORK:
            self.current_cycle += 1
            if self.current_cycle % self.settings.cycles_before_long_break == 0:
                self.current_phase = CyclePhase.LONG_BREAK
                self.timer = self._make_timer(self.settings.long_break_duration)
            else:
                self.current_phase = CyclePhase.SHORT_BREAK
                self.timer = self._make_timer(self.settings.break_duration)
        else:
            self.current_phase = CyclePhase.WORK
            self.timer = self._make_timer(self.settings.work_duration)

        self.timer.start(at=now)

    def start(self) -> None:
        self.timer.start()

    def pause(self) -> None:
        self.timer.pause()

    def resume(self) -> None:
        self.timer.resume()

    def reset(self) -> None:
        self.timer.reset()
        if self.settings.mode == "cycles":
            self.current_phase = CyclePhase.WORK
            self.current_cycle = 0
            self.timer = self._make_timer(self.settings.work_duration)
