import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict

import tomli_w

SECTION_MAP = {
    "general": [
        "mode",
    ],
    "timer": [
        "timer",
    ],
    "cycles": [
        "work_duration",
        "break_duration",
        "long_break_duration",
        "cycles_before_long_break",
    ],
    "ui": [
        "show_progress_bar",
        "show_header",
        "show_footer",
        "show_timer",
    ],
    "colors": [
        "work_color",
        "break_color",
        "idle_color",
    ],
    "audio": [
        "play_audio",
        "audio_volume",
    ],
}


def format_toml(data: Dict[str, Any]) -> Dict[str, Any]:
    validated = dict()
    print(data)
    for group, parameters in SECTION_MAP.items():
        if group not in data:
            continue
        for parameter in parameters:
            if parameter in data[group]:
                validated[parameter] = data[group][parameter]
    return validated


@dataclass
class Settings:
    """Dataclass to store and inject config settings into app"""

    # general
    mode: str = "timer"  # timer | cycles

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

    # UI elements colors
    work_color: str = "#e06c75"
    break_color: str = "#61afef"
    idle_color: str = "#98c379"

    # audio
    play_audio: bool = True
    audio_volume: float = 0.8

    @classmethod
    def load(cls, config_path: Path | None = None) -> "Settings":
        """
        Factory method that loads config from ~/.config/tuipomodoro/config.toml.
        If such file is absent, creates default config
        """

        if config_path is None:
            config_path = Path.home() / ".config" / "tuipomodoro" / "config.toml"
        if not config_path.exists():
            return cls()
        with open(config_path, mode="rb") as config:
            data = tomllib.load(config)
        return cls(**format_toml(data))

    def save(self, config_path: Path) -> None:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, mode="wb") as config:
            tomli_w.dump(asdict(self), config)
