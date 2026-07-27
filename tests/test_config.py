import tomli_w

from tuipomodoro.config import Settings


class TestSettingsDefaults:
    def test_default_mode(self):
        assert Settings().mode == "timer"

    def test_default_timer_duration(self):
        assert Settings().timer_duration == 15

    def test_default_cycle_durations(self):
        s = Settings()
        assert s.work_duration == 30
        assert s.break_duration == 5
        assert s.long_break_duration == 15
        assert s.cycles_before_long_break == 4

    def test_default_visibility(self):
        s = Settings()
        assert s.show_progress_bar is True
        assert s.show_timer is True
        assert s.show_header is True
        assert s.show_footer is True

    def test_default_colors(self):
        s = Settings()
        assert s.work_color == "#e06c75"
        assert s.break_color == "#61afef"
        assert s.timer_paused_color == "grey"
        assert s.idle_color == "#98c379"
        assert s.progress_paused_color == "grey"
        assert s.progress_active_color == "white"

    def test_default_audio(self):
        s = Settings()
        assert s.audio_enabled is True
        assert s.audio_volume == 0.8
        assert s.tick_mode == "seconds"
        assert s.tick_threshold == 10.0
        assert s.warning_tick_threshold == 3.0
        assert s.fade_switch_duration == 500
        assert s.fade_pause_duration == 80


class TestSettingsLoad:
    def test_missing_file_returns_defaults(self, tmp_path):
        config_path = tmp_path / "nonexistent" / "config.toml"
        s = Settings.load(config_path)
        assert s.mode == "timer"
        assert s.work_duration == 30

    def test_full_config_load(self, tmp_path):
        config_path = tmp_path / "config.toml"
        data = {
            "general": {"mode": "cycles"},
            "timer": {"timer_duration": 20},
            "cycles": {
                "work_duration": 25,
                "break_duration": 10,
                "long_break_duration": 20,
                "cycles_before_long_break": 3,
            },
            "ui": {
                "visibility": {
                    "show_progress_bar": False,
                    "show_timer": True,
                    "show_header": False,
                    "show_footer": True,
                },
                "colors": {
                    "timer": {
                        "work_color": "#ff0000",
                        "break_color": "#00ff00",
                        "timer_paused_color": "blue",
                        "idle_color": "yellow",
                    },
                    "progress_bar": {
                        "progress_paused_color": "red",
                        "progress_active_color": "green",
                    },
                },
            },
            "audio": {
                "audio_enabled": False,
                "audio_volume": 0.5,
                "tick_mode": "percent",
                "tick_threshold": 0.2,
                "warning_tick_threshold": 0.05,
                "fade_switch_duration": 1000,
                "fade_pause_duration": 200,
            },
        }
        with open(config_path, "wb") as f:
            tomli_w.dump(data, f)

        s = Settings.load(config_path)
        assert s.mode == "cycles"
        assert s.timer_duration == 20
        assert s.work_duration == 25
        assert s.break_duration == 10
        assert s.long_break_duration == 20
        assert s.cycles_before_long_break == 3
        assert s.show_progress_bar is False
        assert s.show_header is False
        assert s.work_color == "#ff0000"
        assert s.progress_active_color == "green"
        assert s.audio_enabled is False
        assert s.audio_volume == 0.5
        assert s.tick_mode == "percent"
        assert s.tick_threshold == 0.2
        assert s.warning_tick_threshold == 0.05
        assert s.fade_switch_duration == 1000
        assert s.fade_pause_duration == 200

    def test_partial_config_fills_defaults(self, tmp_path):
        config_path = tmp_path / "config.toml"
        data = {"general": {"mode": "cycles"}}
        with open(config_path, "wb") as f:
            tomli_w.dump(data, f)

        s = Settings.load(config_path)
        assert s.mode == "cycles"
        assert s.work_duration == 30  # default
        assert s.audio_enabled is True  # default

    def test_empty_config_file(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text("")

        s = Settings.load(config_path)
        assert s.mode == "timer"
        assert s.work_duration == 30


class TestSettingsSave:
    def test_save_creates_directories(self, tmp_path):
        config_path = tmp_path / "nested" / "dir" / "config.toml"
        s = Settings()
        s.save(config_path)
        assert config_path.exists()

    def test_save_load_roundtrip(self, tmp_path):
        config_path = tmp_path / "config.toml"
        s = Settings(
            mode="cycles",
            timer_duration=20,
            work_duration=25,
            break_duration=10,
            long_break_duration=20,
            cycles_before_long_break=3,
            show_progress_bar=False,
            audio_volume=0.5,
        )
        s.save(config_path)
        loaded = Settings.load(config_path)
        assert loaded.mode == "cycles"
        assert loaded.timer_duration == 20
        assert loaded.work_duration == 25
        assert loaded.break_duration == 10
        assert loaded.long_break_duration == 20
        assert loaded.cycles_before_long_break == 3
        assert loaded.show_progress_bar is False
        assert loaded.audio_volume == 0.5
        # Defaults preserved
        assert loaded.show_header is True
        assert loaded.work_color == "#e06c75"

    def test_save_produces_valid_toml(self, tmp_path):
        config_path = tmp_path / "config.toml"
        Settings().save(config_path)
        content = config_path.read_text()
        assert "[general]" in content
        assert "[timer]" in content
        assert "[ui" in content
        assert "[audio]" in content

    def test_save_preserves_all_fields(self, tmp_path):
        config_path = tmp_path / "config.toml"
        s = Settings()
        s.save(config_path)
        loaded = Settings.load(config_path)
        assert loaded.mode == s.mode
        assert loaded.timer_duration == s.timer_duration
        assert loaded.work_duration == s.work_duration
        assert loaded.break_duration == s.break_duration
        assert loaded.long_break_duration == s.long_break_duration
        assert loaded.cycles_before_long_break == s.cycles_before_long_break
        assert loaded.show_progress_bar == s.show_progress_bar
        assert loaded.show_timer == s.show_timer
        assert loaded.show_header == s.show_header
        assert loaded.show_footer == s.show_footer
        assert loaded.work_color == s.work_color
        assert loaded.break_color == s.break_color
        assert loaded.timer_paused_color == s.timer_paused_color
        assert loaded.idle_color == s.idle_color
        assert loaded.progress_paused_color == s.progress_paused_color
        assert loaded.progress_active_color == s.progress_active_color
        assert loaded.audio_enabled == s.audio_enabled
        assert loaded.audio_volume == s.audio_volume
