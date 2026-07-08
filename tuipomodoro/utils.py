def format_time(raw_time: float) -> str:
    seconds = int(raw_time % 60)
    minutes = int(raw_time // 60)
    hours = int(raw_time // 3600)
    return f"{hours:02}:{minutes:02}:{seconds:02}"
