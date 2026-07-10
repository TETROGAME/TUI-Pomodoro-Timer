import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path

import tomli_w

from tuipomodoro.utils import format_toml


@dataclass
class Settings:
    """Dataclass to store and inject config settings into app"""

    mode: str = "cycles"  # timer | cycles

    # timer
    timer_duration: int = 15

    # cycles
    work_duration: int = 30
    break_duration: int = 5
    long_break_duration: int = 15
    cycles_before_long_break: int = 4

    # UI elements visibility
    show_progress_bar: bool = True
    show_timer: bool = True
    show_header: bool = True
    show_footer: bool = True

    # audio
    play_audio: bool = True
    audio_path: str = "audio/"
    audio_volume: float = 0.8

    @classmethod
    def load(cls, config_path: Path) -> "Settings":
        with open(config_path, mode="rb") as config:
            data = tomllib.load(config)
        return cls(**format_toml(data))

    def save(self, config_path: Path) -> None:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, mode="wb") as config:
            tomli_w.dump(asdict(self), config)
