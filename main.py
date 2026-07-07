from time import sleep

from rich.align import Align
from rich.console import Group
from rich.layout import Layout
from rich.live import Live
from rich.text import Text

from timer import PomodoroTimer, TimerState


def render_progress_bar(ratio: float, width: int) -> Text:
    progress_bar = Text()
    filled = int(ratio * width)
    empty = width - filled
    progress_bar.append("█" * filled)
    progress_bar.append("░" * empty)
    return progress_bar


def render_state(timer: PomodoroTimer, layout: Layout):
    remaining_time = timer.get_remaining()

    time_text = Align.center(format_time(remaining_time))

    ratio = 1 - remaining_time / timer.duration
    progress_bar = Align.center(render_progress_bar(ratio, width=10))

    layout["center"].update(
        Align.center(Group(time_text, progress_bar), vertical="middle")
    )


def format_time(raw_time: float) -> str:
    seconds = int(raw_time % 60)
    minutes = int(raw_time // 60)
    hours = int(raw_time // 3600)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def main():
    duration = 1 * 60
    timer = PomodoroTimer(duration)
    timer.start()

    layout = Layout()
    layout.split_column(
        Layout(ratio=1),
        Layout(name="center"),
        Layout(ratio=1),
    )

    with Live(layout, screen=True, refresh_per_second=4) as live:
        while timer.state != TimerState.FINISHED:
            render_state(timer, layout)
            sleep(0.25)


if __name__ == "__main__":
    main()
