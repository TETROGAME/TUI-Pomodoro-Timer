from math import ceil
from time import monotonic

from textual.app import App, ComposeResult
from textual.containers import Center, VerticalGroup
from textual.reactive import Reactive, reactive
from textual.timer import Timer
from textual.widgets import Digits, Footer, Header, Static

from tuipomodoro.timer import PomodoroTimer, TimerState
from tuipomodoro.utils import format_progress_bar, format_time


class PomodoroTimerApp(App):
    """A textual Pomodoro Timer with audio playback support"""

    CSS_PATH = "PomodoroTimerApp.tcss"

    BINDINGS = [("space", "switch_state()", "Pause/resume timer")]

    timer: PomodoroTimer
    remaining: Reactive[float] = reactive(0.0)
    timer_state: Reactive[TimerState] = reactive(TimerState.IDLE)

    def __init__(self, timer: PomodoroTimer, **kwargs):
        super().__init__(**kwargs)
        self.timer = timer
        self._alignment_timer: Timer | None = None
        self._tick_timer: Timer | None = None

    def on_mount(self) -> None:
        # self.timer.start()
        self.remaining = self.timer.duration
        self.timer_state = self.timer.state

        self.query_one("#time", Digits).update(format_time(self.remaining))

        base_width = 24
        self.query_one("#progress", Static).update(
            format_progress_bar(1, width=max(base_width, 10))
        )

    def watch_timer_state(self, old: TimerState, new: TimerState) -> None:
        if new == TimerState.FINISHED:
            self.query_one("#progress", Static).update("done!")

    def watch_remaining(self, old: float, new: float) -> None:
        self.query_one("#time", Digits).update(format_time(new))
        if self.timer.duration <= 0:
            ratio = 1.0
        else:
            ratio = max(0.0, min(1.0, 1 - new / self.timer.duration))
        target_width = self.query_one("#time", Digits).size.width
        target_width = max(target_width, 10)
        self.query_one("#progress", Static).update(
            format_progress_bar(ratio, width=target_width)
        )

    def _start_interval(self) -> None:
        """Begin the steady 1-second tick loop after initial second-boundary alignment."""
        self._alignment_timer = None
        self.update_time()
        self._tick_timer = self.set_interval(1, self.update_time)

    def _stop_tick_loop(self) -> None:
        """Stop and clear both one-shot alignment and repeating tick timers."""
        if self._alignment_timer is not None:
            self._alignment_timer.stop()
            self._alignment_timer = None
        if self._tick_timer is not None:
            self._tick_timer.stop()
            self._tick_timer = None

    def _schedule_tick_loop(self) -> None:
        """Schedule a fresh aligned tick loop, replacing any previously running timers."""
        self._stop_tick_loop()
        now = monotonic()
        self._alignment_timer = self.set_timer(ceil(now) - now, self._start_interval)

    def update_time(self) -> None:
        """Sync app reactive fields from one timer tick and stop loop when finished."""
        now = monotonic()
        snapshot = self.timer.tick(now)
        self.remaining = snapshot.remaining
        self.timer_state = snapshot.state
        if snapshot.state == TimerState.FINISHED:
            self._stop_tick_loop()

    def action_switch_state(self) -> None:
        """Toggle pause/resume (space binding).

        - If running -> pause
        - If paused -> resume
        - If idle or finished -> start a fresh run
        After changing timer logic, mirror state and remaining into reactive fields
        so the UI updates immediately.
        """
        if self.timer.state == TimerState.RUNNING:
            self.timer.pause()
            self._stop_tick_loop()
        elif self.timer.state == TimerState.PAUSED:
            self.timer.resume()
            self._schedule_tick_loop()
        else:
            # Idle or Finished -> start/restart
            self.timer.start()
            self._schedule_tick_loop()

        # Mirror logic into app reactives so watchers fire immediately
        snapshot = self.timer.tick(monotonic())
        self.timer_state = snapshot.state
        self.remaining = snapshot.remaining

    def compose(self) -> ComposeResult:
        yield Header()
        yield Center(
            VerticalGroup(
                Digits(id="time"),
                Static(id="progress"),
                id="clock",
            ),
            id="clock-wrapper",
        )
        yield Footer()
