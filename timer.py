import time

"""
Store internal timer logic
"""


class PomodoroTimer:
    duration: float
    started_at: float | None
    running: bool

    def __init__(self, duration: float):
        self.duration = duration
        self.started_at = None
        self.running = False

    def start(self) -> None:
        self.started_at = time.monotonic()
        self.running = True

    def get_remaining(self) -> float:
        if self.started_at is not None:
            elapsed = time.monotonic() - self.started_at
            return self.duration - elapsed
        else:
            return -1
