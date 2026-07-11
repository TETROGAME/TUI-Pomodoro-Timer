import asyncio
from time import monotonic

from textual import work
from textual.app import App, ComposeResult
from textual.worker import Worker
from textual.containers import Center, VerticalGroup
from textual.reactive import Reactive, reactive
from textual.widgets import Digits, Footer, Header, Label, Static

from tuipomodoro.config import Settings
from tuipomodoro.timer import CycleManager, CyclePhase, TimerState
from tuipomodoro.utils import format_progress_bar, format_time


class PomodoroTimerApp(App):
    """A textual Pomodoro Timer with audio playback support"""

    CSS_PATH = "PomodoroTimerApp.tcss"

    BINDINGS = [
        ("space", "switch_state()", "Pause/resume timer"),
        ("r", "reset_timer()", "Reset timer"),
    ]

    manager: CycleManager
    remaining: Reactive[float] = reactive(0.0)
    timer_state: Reactive[TimerState] = reactive(TimerState.IDLE)

    def __init__(self, manager: CycleManager, settings: Settings, **kwargs):
        super().__init__(**kwargs)
        self.manager = manager
        self.settings = settings
        self._clock_worker: Worker | None = None

    def _apply_visibility(self) -> None:
        self.query_one(Header).visible = self.settings.show_header
        self.query_one("#time", Digits).visible = self.settings.show_timer
        self.query_one("#progress", Static).visible = self.settings.show_progress_bar
        self.query_one(Footer).visible = self.settings.show_footer

    def _apply_phase(self) -> None:
        phase_label = {
            CyclePhase.TIMER: "TIMER",
            CyclePhase.WORK: "WORK",
            CyclePhase.SHORT_BREAK: "SHORT BREAK",
            CyclePhase.LONG_BREAK: "LONG BREAK",
        }
        self.query_one("#cycle_name", Label).update(
            phase_label[self.manager.current_phase]
        )

    def _sync_ui(self) -> None:
        """Immediate UI sync from current timer state without ticking."""
        snapshot = self.manager.snapshot()
        self.remaining = snapshot.remaining
        self.timer_state = snapshot.state

    def _start_clock(self) -> None:
        self._clock_worker = self._run_clock()

    def _stop_clock(self) -> None:
        if self._clock_worker is not None:
            self._clock_worker.cancel()
            self._clock_worker = None

    def on_mount(self) -> None:
        self._apply_visibility()
        self.remaining = self.manager.duration
        self.timer_state = self.manager.state
        self._apply_phase()

        self.query_one("#time", Digits).update(format_time(self.remaining))

        base_width = 24
        self.query_one("#progress", Static).update(
            format_progress_bar(0, width=max(base_width, 10))
        )

    def watch_timer_state(self, old: TimerState, new: TimerState) -> None:
        self.sub_title = str(self.manager.state.name)

    def watch_remaining(self, old: float, new: float) -> None:
        self.query_one("#time", Digits).update(format_time(new))
        if self.manager.duration <= 0:
            ratio = 1.0
        else:
            ratio = max(0.0, min(1.0, 1 - new / self.manager.duration))
        target_width = self.query_one("#time", Digits).size.width
        target_width = max(target_width, 10)
        self.query_one("#progress", Static).update(
            format_progress_bar(ratio, width=target_width)
        )

    @work(exclusive=True)
    async def _run_clock(self) -> None:
        """Tick the timer every second."""
        while True:
            await asyncio.sleep(1.0)
            now = monotonic()
            old_phase = self.manager.current_phase
            snapshot = self.manager.tick(now)
            self.remaining = snapshot.remaining
            self.timer_state = snapshot.state
            if self.manager.current_phase != old_phase:
                self._apply_phase()
            if snapshot.state == TimerState.FINISHED:
                break

    def action_switch_state(self) -> None:
        """Toggle pause/resume (space binding)."""
        if self.manager.state == TimerState.RUNNING:
            self.manager.pause()
            self._stop_clock()
        elif self.manager.state == TimerState.PAUSED:
            self.manager.resume()
            self._start_clock()
        else:
            self.manager.start()
            self._start_clock()
        self._sync_ui()

    def action_reset_timer(self) -> None:
        self.manager.reset()
        self._stop_clock()
        self._sync_ui()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Center(
            VerticalGroup(
                Label(id="cycle_name"),
                Digits(id="time"),
                Static(id="progress"),
                id="clock",
            ),
            id="clock-wrapper",
        )
        yield Footer()
