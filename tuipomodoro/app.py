from math import ceil
from time import monotonic

from textual.app import App, ComposeResult
from textual.reactive import Reactive, reactive
from textual.widget import Widget
from textual.widgets import Digits, Footer, Header, Static
from 

from tuipomodoro.timer import PomodoroTimer, TimerState
from tuipomodoro.utils import format_time


class TimerDisplay(Widget):
    """A widget to display remaining time"""

    def compose(self) -> ComposeResult:
        yield Digits(id="time")
        yield Static(id="progress")


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

    def watch_timer_state(self, old: TimerState, new: TimerState) -> None:
        if new == TimerState.FINISHED:
            self.query_one("#progress", Static).update("done!")

    def watch_remaining(self, old: float, new: float) -> None:
        self.query_one("#time", Digits).update(format_time(new))

    def _start_interval(self) -> None:
        self.update_time()
        self.set_interval(1, self.update_time)

    def update_time(self) -> None:
        self.remaining = self.timer.get_remaining()
        self.timer_state = self.timer.state

    def compose(self) -> ComposeResult:
        yield Header()
        yield Digits(id="time")
        yield Footer()
