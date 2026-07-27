from unittest.mock import patch

import pytest

from tuipomodoro.app import PomodoroTimerApp
from tuipomodoro.config import Settings
from tuipomodoro.timer import CycleManager, TimerState


@pytest.fixture()
def app():
    settings = Settings(mode="cycles", work_duration=30, break_duration=5)
    manager = CycleManager(settings)
    with patch("tuipomodoro.audio.AudioManager._probe_device", return_value=False):
        app = PomodoroTimerApp(manager, settings)
    return app


class TestInitialState:
    async def test_header_visible(self, app):
        async with app.run_test():
            assert app.query_one("Header").visible is True

    async def test_footer_visible(self, app):
        async with app.run_test():
            assert app.query_one("Footer").visible is True

    async def test_timer_shows_initial_duration(self, app):
        async with app.run_test():
            from textual.widgets import Digits

            digits = app.query_one("#time", Digits)
            assert "30:00" in digits.value

    async def test_phase_label_is_work(self, app):
        async with app.run_test():
            from textual.widgets import Label

            label = app.query_one("#cycle_name", Label)
            assert "WORK" in str(label.render())

    async def test_initial_state_is_idle(self, app):
        async with app.run_test():
            assert app.timer_state == TimerState.IDLE

    async def test_visibility_settings_hide_elements(self):
        settings = Settings(
            mode="cycles",
            show_header=False,
            show_footer=False,
            show_timer=False,
            show_progress_bar=False,
        )
        manager = CycleManager(settings)
        with patch("tuipomodoro.audio.AudioManager._probe_device", return_value=False):
            app = PomodoroTimerApp(manager, settings)
        async with app.run_test():
            assert app.query_one("Header").visible is False
            assert app.query_one("Footer").visible is False


class TestKeybindings:
    async def test_space_starts_timer(self, app):
        async with app.run_test() as pilot:
            await pilot.press("space")
            await pilot.pause()
            assert app.manager.state == TimerState.RUNNING

    async def test_space_pause_resume(self, app):
        async with app.run_test() as pilot:
            await pilot.press("space")
            await pilot.pause()
            assert app.manager.state == TimerState.RUNNING
            await pilot.press("space")
            await pilot.pause()
            assert app.manager.state == TimerState.PAUSED
            await pilot.press("space")
            await pilot.pause()
            assert app.manager.state == TimerState.RUNNING

    async def test_r_resets_timer(self, app):
        async with app.run_test() as pilot:
            await pilot.press("space")
            await pilot.pause()
            assert app.manager.state == TimerState.RUNNING
            await pilot.press("r")
            await pilot.pause()
            assert app.manager.state == TimerState.IDLE
            assert app.manager.current_cycle == 0

    async def test_r_resets_phase_label(self, app):
        async with app.run_test() as pilot:
            await pilot.press("r")
            await pilot.pause()
            from textual.widgets import Label

            label = app.query_one("#cycle_name", Label)
            assert "WORK" in str(label.render())


class TestSubtitle:
    async def test_subtitle_shows_state(self, app):
        async with app.run_test() as pilot:
            assert app.sub_title == "IDLE"
            await pilot.press("space")
            await pilot.pause()
            assert app.sub_title == "RUNNING"
            await pilot.press("space")
            await pilot.pause()
            assert app.sub_title == "PAUSED"
