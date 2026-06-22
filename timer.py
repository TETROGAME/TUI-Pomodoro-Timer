import time
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

    def get_remaining(self) -> float:
        if self.started_at is None:
            return -1
        elapsed = 0
        match self.state:
            case TimerState.RUNNING:
                elapsed = time.monotonic() - self.started_at
                remaining = self.duration - elapsed
                if remaining <= 0:
                    self.state = TimerState.FINISHED
                    return 0.0
                return remaining

            case TimerState.PAUSED:
                if self.paused_at is None:
                    elapsed = 0
                else:
                    elapsed = self.paused_at - self.started_at
                remaining = self.duration - elapsed
                if remaining <= 0:
                    self.state = TimerState.FINISHED
                    return 0.0
                return remaining

            case TimerState.FINISHED:
                return 0.0
            case _:
                return -1.0
