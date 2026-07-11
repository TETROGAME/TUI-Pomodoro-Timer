from time import monotonic

from textual.app import App, ComposeResult
from textual.containers import Center, VerticalGroup
from textual.reactive import Reactive, reactive
from textual.timer import Timer
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
        self._tick_timer: Timer | None = None

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

    def _tick(self) -> None:
        """Fire one tick and schedule the next at the next second boundary."""
        self.update_time()
        now = monotonic()
        self._tick_timer = self.set_timer(1.0 - (now % 1.0), self._tick)

    def _stop_tick_loop(self) -> None:
        """Stop and clear tick timer."""
        if self._tick_timer is not None:
            self._tick_timer.stop()
            self._tick_timer = None

    def _schedule_tick_loop(self) -> None:
        """Schedule a fresh aligned tick loop."""
        self._stop_tick_loop()
        now = monotonic()
        self._tick_timer = self.set_timer(1.0 - (now % 1.0), self._tick)

    def update_time(self) -> None:
        """Sync app reactive fields from one timer tick and stop loop when finished."""
        now = monotonic()
        old_phase = self.manager.current_phase
        snapshot = self.manager.tick(now)
        self.remaining = snapshot.remaining
        self.timer_state = snapshot.state

        if self.manager.current_phase != old_phase:
            self._apply_phase()

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
        if self.manager.state == TimerState.RUNNING:
            self.manager.pause()
            self._stop_tick_loop()
        elif self.manager.state == TimerState.PAUSED:
            self.manager.resume()
            self._schedule_tick_loop()
        else:
            # Idle or Finished -> start/restart
            self.manager.start()
            self._schedule_tick_loop()

        # Mirror logic into app reactives so watchers fire immediately
        snapshot = self.manager.tick(monotonic())
        self.timer_state = snapshot.state
        self.remaining = snapshot.remaining

    def action_reset_timer(self) -> None:
        self.manager.reset()
        snapshot = self.manager.tick(monotonic())
        self.timer_state = snapshot.state
        self.remaining = snapshot.remaining
        self._stop_tick_loop()

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
