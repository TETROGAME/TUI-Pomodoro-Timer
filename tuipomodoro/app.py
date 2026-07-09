from math import ceil
from time import monotonic

from textual.app import App, ComposeResult
from textual.containers import Center, VerticalGroup
from textual.getters import query_one
from textual.reactive import Reactive, reactive
from textual.widgets import Digits, Footer, Header, Static

from tuipomodoro.timer import PomodoroTimer, TimerState
from tuipomodoro.utils import format_progress_bar, format_time


class PomodoroTimerApp(App):
    """A textual Pomodoro Timer with audio playback support"""

    CSS_PATH = "PomodoroTimerApp.tcss"

    timer: PomodoroTimer
    remaining: Reactive[float] = reactive(0.0)
    timer_state: Reactive[TimerState] = reactive(TimerState.IDLE)

    def __init__(self, timer: PomodoroTimer, **kwargs):
        super().__init__(**kwargs)
        self.timer = timer

    def on_mount(self) -> None:
        self.timer.start()
        self.remaining = self.timer.duration
        self.timer_state = self.timer.state

        now = monotonic()
        self.set_timer(ceil(now) - now, self._start_interval)

        base_width = 24
        self.query_one("#progress", Static).update(
            format_progress_bar(0, width=max(base_width, 10))
        )

    def watch_timer_state(self, old: TimerState, new: TimerState) -> None:
        if new == TimerState.FINISHED:
            self.query_one("#progress", Static).update("done!")

    def watch_remaining(self, old: float, new: float) -> None:
        self.query_one("#time", Digits).update(format_time(new))
        ratio = 1 - new / self.timer.duration
        target_width = self.query_one("#time", Digits).size.width
        self.query_one("#progress", Static).update(
            format_progress_bar(ratio, width=target_width)
        )

    def _start_interval(self) -> None:
        self.update_time()
        self.set_interval(1, self.update_time)

    def update_time(self) -> None:
        self.remaining = self.timer.get_remaining()
        self.timer_state = self.timer.state

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
