def format_time(raw_time: float) -> str:
    seconds = int(raw_time % 60)
    minutes = int(raw_time // 60)
    hours = int(raw_time // 3600)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def format_progress_bar(ratio: float, width: int) -> str:
    filled = int(ratio * width)
    empty = width - filled
    progress_bar = filled * "█" + empty * "░"
    return progress_bar
