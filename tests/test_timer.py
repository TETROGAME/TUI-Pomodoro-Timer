import pytest

from tuipomodoro.config import Settings
from tuipomodoro.timer import CycleManager, CyclePhase, PomodoroTimer, TimerState


class TestPomodoroTimer:
    def test_initial_state(self):
        t = PomodoroTimer(100)
        assert t.state == TimerState.IDLE
        assert t.duration == 100

    def test_start_transitions_to_running(self):
        t = PomodoroTimer(100)
        t.start(at=0.0)
        assert t.state == TimerState.RUNNING

    def test_start_sets_started_at(self):
        t = PomodoroTimer(100)
        t.start(at=10.0)
        assert t.started_at == 10.0

    def test_start_ignored_if_running(self):
        t = PomodoroTimer(100)
        t.start(at=0.0)
        t.start(at=5.0)
        assert t.started_at == 0.0

    def test_start_ignored_if_paused(self):
        t = PomodoroTimer(100)
        t.start(at=0.0)
        t.pause()
        t.start(at=50.0)
        assert t.state == TimerState.PAUSED

    def test_start_from_finished(self):
        t = PomodoroTimer(2)
        t.start(at=0.0)
        t.tick(2.0)
        assert t.state == TimerState.FINISHED
        t.start(at=3.0)
        assert t.state == TimerState.RUNNING

    def test_pause_transitions_to_paused(self):
        t = PomodoroTimer(100)
        t.start(at=0.0)
        t.pause()
        assert t.state == TimerState.PAUSED
        assert t.paused_at is not None

    def test_pause_ignored_if_idle(self):
        t = PomodoroTimer(100)
        t.pause()
        assert t.state == TimerState.IDLE

    def test_pause_ignored_if_paused(self):
        t = PomodoroTimer(100)
        t.start(at=0.0)
        t.pause()
        t.pause()
        assert t.state == TimerState.PAUSED

    def test_resume_transitions_to_running(self):
        t = PomodoroTimer(100)
        t.start(at=0.0)
        t.pause()
        t.resume()
        assert t.state == TimerState.RUNNING
        assert t.paused_at is None

    def test_resume_adjusts_started_at(self):
        t = PomodoroTimer(100)
        t.started_at = 0.0
        t.paused_at = 10.0
        t.state = TimerState.PAUSED
        old_started = t.started_at
        t.resume()
        assert t.state == TimerState.RUNNING
        assert t.paused_at is None
        assert t.started_at > old_started

    def test_resume_ignored_if_idle(self):
        t = PomodoroTimer(100)
        t.resume()
        assert t.state == TimerState.IDLE

    def test_resume_ignored_if_running(self):
        t = PomodoroTimer(100)
        t.start(at=0.0)
        t.resume()
        assert t.state == TimerState.RUNNING

    def test_snapshot_idle(self):
        t = PomodoroTimer(100)
        snap = t.snapshot(now=0.0)
        assert snap.state == TimerState.IDLE
        assert snap.remaining == 100

    def test_snapshot_running(self):
        t = PomodoroTimer(100)
        t.start(at=0.0)
        snap = t.snapshot(now=30.0)
        assert snap.state == TimerState.RUNNING
        assert snap.remaining == 70.0

    def test_snapshot_paused(self):
        t = PomodoroTimer(100)
        t.start(at=0.0)
        # Manually set paused state for deterministic test
        t.state = TimerState.PAUSED
        t.started_at = 0.0
        t.paused_at = 30.0
        snap = t.snapshot(now=50.0)
        assert snap.state == TimerState.PAUSED
        assert snap.remaining == 70.0

    def test_snapshot_finished_when_expired(self):
        t = PomodoroTimer(100)
        t.start(at=0.0)
        snap = t.snapshot(now=100.0)
        assert snap.state == TimerState.FINISHED
        assert snap.remaining == 0.0

    def test_snapshot_finished_state(self):
        t = PomodoroTimer(100)
        t.started_at = 0.0
        t.state = TimerState.FINISHED
        snap = t.snapshot(now=0.0)
        assert snap.state == TimerState.FINISHED
        assert snap.remaining == 0.0

    def test_tick_transitions_to_finished(self):
        t = PomodoroTimer(100)
        t.start(at=0.0)
        snap = t.tick(now=100.0)
        assert snap.state == TimerState.FINISHED
        assert t.state == TimerState.FINISHED

    def test_tick_advances_running(self):
        t = PomodoroTimer(100)
        t.start(at=0.0)
        snap = t.tick(now=50.0)
        assert snap.state == TimerState.RUNNING
        assert snap.remaining == 50.0

    def test_reset_from_running(self):
        t = PomodoroTimer(100)
        t.start(at=0.0)
        t.reset()
        assert t.state == TimerState.IDLE
        assert t.started_at is None
        assert t.paused_at is None

    def test_reset_from_paused(self):
        t = PomodoroTimer(100)
        t.start(at=0.0)
        t.pause()
        t.reset()
        assert t.state == TimerState.IDLE

    def test_invariant_violation_paused_without_paused_at(self):
        t = PomodoroTimer(100)
        t.state = TimerState.PAUSED
        t.started_at = 0.0
        t.paused_at = None
        with pytest.raises(RuntimeError, match="Invariant violation"):
            t.snapshot(now=50.0)


class TestCycleManager:
    def _make_manager(self, **overrides) -> CycleManager:
        defaults = {
            "mode": "cycles",
            "work_duration": 30,
            "break_duration": 5,
            "long_break_duration": 15,
            "cycles_before_long_break": 4,
            "timer_duration": 15,
        }
        defaults.update(overrides)
        return CycleManager(Settings(**defaults))

    def test_cycles_mode_initial_phase(self):
        m = self._make_manager(mode="cycles")
        assert m.current_phase == CyclePhase.WORK
        assert m.timer.duration == 30 * 60

    def test_timer_mode_initial_phase(self):
        m = self._make_manager(mode="timer")
        assert m.current_phase == CyclePhase.TIMER
        assert m.timer.duration == 15 * 60

    def test_work_to_short_break(self):
        m = self._make_manager()
        m.timer.start(at=0.0)
        m.tick(now=30 * 60)  # work finishes
        assert m.current_phase == CyclePhase.SHORT_BREAK
        assert m.timer.duration == 5 * 60

    def test_short_break_to_work(self):
        m = self._make_manager()
        m.timer.start(at=0.0)
        m.tick(now=30 * 60)  # work -> short break
        m.tick(now=30 * 60 + 5 * 60)  # short break -> work
        assert m.current_phase == CyclePhase.WORK

    def test_long_break_after_cycles(self):
        m = self._make_manager(cycles_before_long_break=2)
        m.timer.start(at=0.0)
        m.tick(now=30 * 60)  # work -> short break (cycle 1)
        assert m.current_cycle == 1
        assert m.current_phase == CyclePhase.SHORT_BREAK
        m.tick(now=30 * 60 + 5 * 60)  # short break -> work
        m.tick(now=60 * 60 + 5 * 60)  # work -> long break (cycle 2)
        assert m.current_cycle == 2
        assert m.current_phase == CyclePhase.LONG_BREAK
        assert m.timer.duration == 15 * 60

    def test_long_break_to_work(self):
        m = self._make_manager(cycles_before_long_break=1)
        m.timer.start(at=0.0)
        m.tick(now=30 * 60)  # work -> long break
        assert m.current_phase == CyclePhase.LONG_BREAK
        m.tick(now=30 * 60 + 15 * 60)  # long break -> work
        assert m.current_phase == CyclePhase.WORK

    def test_timer_mode_stays_timer(self):
        m = self._make_manager(mode="timer")
        m.start()
        m.tick(now=15 * 60)
        assert m.current_phase == CyclePhase.TIMER

    def test_cycle_increments(self):
        m = self._make_manager()
        m.timer.start(at=0.0)
        m.tick(now=30 * 60)
        assert m.current_cycle == 1
        m.tick(now=30 * 60 + 5 * 60)
        m.tick(now=60 * 60 + 5 * 60)
        assert m.current_cycle == 2

    def test_reset_in_cycles_mode(self):
        m = self._make_manager()
        m.timer.start(at=0.0)
        m.tick(now=30 * 60)
        assert m.current_phase == CyclePhase.SHORT_BREAK
        m.reset()
        assert m.current_phase == CyclePhase.WORK
        assert m.current_cycle == 0

    def test_reset_in_timer_mode(self):
        m = self._make_manager(mode="timer")
        m.start()
        m.tick(now=15 * 60)
        m.reset()
        assert m.current_phase == CyclePhase.TIMER

    def test_state_property(self):
        m = self._make_manager()
        assert m.state == TimerState.IDLE
        m.start()
        assert m.state == TimerState.RUNNING

    def test_duration_property(self):
        m = self._make_manager(work_duration=25)
        assert m.duration == 25 * 60

    def test_pause_resume(self):
        m = self._make_manager()
        m.start()
        m.pause()
        assert m.state == TimerState.PAUSED
        m.resume()
        assert m.state == TimerState.RUNNING
