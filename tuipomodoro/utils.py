def format_time(raw_time: float) -> str:
    total_secs = max(0, round(raw_time))
    seconds = total_secs % 60
    minutes = (total_secs // 60) % 60
    hours = total_secs // 3600
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def format_progress_bar(ratio: float, width: int) -> str:
    filled = int(ratio * width)
    empty = width - filled
    progress_bar = empty * "█" + filled * "░"
    return progress_bar
