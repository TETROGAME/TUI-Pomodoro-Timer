from tuipomodoro.utils import format_progress_bar, format_time


class TestFormatTime:
    def test_zero(self):
        assert format_time(0) == "00:00:00"

    def test_seconds_only(self):
        assert format_time(45) == "00:00:45"

    def test_minutes_and_seconds(self):
        assert format_time(125) == "00:02:05"

    def test_hours_minutes_seconds(self):
        assert format_time(3661) == "01:01:01"

    def test_large_value(self):
        assert format_time(36000) == "10:00:00"

    def test_negative_clamps_to_zero(self):
        assert format_time(-10) == "00:00:00"

    def test_fractional_rounds(self):
        assert format_time(64.7) == "00:01:05"
        assert format_time(64.3) == "00:01:04"

    def test_exactly_one_hour(self):
        assert format_time(3600) == "01:00:00"

    def test_exactly_one_minute(self):
        assert format_time(60) == "00:01:00"


class TestFormatProgressBar:
    def test_empty(self):
        assert format_progress_bar(0.0, 10) == "██████████"

    def test_full(self):
        assert format_progress_bar(1.0, 10) == "░░░░░░░░░░"

    def test_half(self):
        bar = format_progress_bar(0.5, 10)
        assert len(bar) == 10
        assert bar.count("█") == 5
        assert bar.count("░") == 5

    def test_width_one(self):
        assert len(format_progress_bar(0.0, 1)) == 1
        assert len(format_progress_bar(1.0, 1)) == 1

    def test_ratio_above_one_no_clamp(self):
        bar = format_progress_bar(1.5, 10)
        assert bar.count("░") == 15
        assert bar.count("█") == 0

    def test_ratio_below_zero_no_clamp(self):
        bar = format_progress_bar(-0.5, 10)
        assert bar.count("░") == 0
        assert bar.count("█") == 15

    def test_exact_integer_fill(self):
        bar = format_progress_bar(0.3, 10)
        assert len(bar) == 10
        assert bar.count("░") == 3
        assert bar.count("█") == 7
