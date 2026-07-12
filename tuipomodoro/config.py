import tomllib
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, Optional

import tomli_w


def toml_field(default: Any, path: str):
    """
    Declare a Settings field together with the dotted TOML section path
    it lives under (e.g. "ui.colors.timer"). This is the single source
    of truth for both loading and saving - no separate map to keep in sync.
    """
    return field(default=default, metadata={"toml_path": path})


@dataclass
class Settings:
    """Dataclass to store and inject config settings into app"""

    # general
    mode: str = toml_field("timer", "general")  # timer | cycles

    # timer
    timer_duration: float = toml_field(15, "timer")

    # cycles
    work_duration: float = toml_field(30, "cycles")
    break_duration: float = toml_field(5, "cycles")
    long_break_duration: float = toml_field(15, "cycles")
    cycles_before_long_break: int = toml_field(4, "cycles")

    # UI elements visibility
    show_progress_bar: bool = toml_field(True, "ui.visibility")
    show_timer: bool = toml_field(True, "ui.visibility")
    show_header: bool = toml_field(True, "ui.visibility")
    show_footer: bool = toml_field(True, "ui.visibility")

    # UI elements colors - timer
    work_color: str = toml_field("#e06c75", "ui.colors.timer")
    break_color: str = toml_field("#61afef", "ui.colors.timer")
    timer_paused_color: str = toml_field("grey", "ui.colors.timer")
    idle_color: str = toml_field("#98c379", "ui.colors.timer")

    # UI elements colors - progress_bar
    progress_paused_color: str = toml_field("grey", "ui.colors.progress_bar")
    progress_active_color: str = toml_field("white", "ui.colors.progress_bar")

    # audio
    audio_enabled: bool = toml_field(True, "audio")
    audio_volume: float = toml_field(0.8, "audio")

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Settings":
        """
        Factory method that loads config from "config_path".
        If such file is absent, creates default config at ~/.config/tuipomodoro/config.toml.
        Any field missing from file falls back to the dataclass default.
        """
        if config_path is None:
            config_path = Path.home() / ".config" / "tuipomodoro" / "config.toml"
        if not config_path.exists():
            return cls()

        with open(config_path, mode="rb") as config:
            data = tomllib.load(config)

        kwargs: Dict[str, Any] = {}
        for f in fields(cls):
            section = data
            try:
                for key in f.metadata["toml_path"].split("."):
                    section = section[key]
                kwargs[f.name] = section[f.name]
            except (KeyError, TypeError):
                continue
        return cls(**kwargs)

    def save(self, config_path: Optional[Path] = None) -> None:
        """
        Format dataclass fields into dictionary suitable for saving to config
        """
        if config_path is None:
            config_path = Path.home() / ".config" / "tuipomodoro" / "config.toml"

        flat = asdict(self)
        data: Dict[str, Any] = {}
        for f in fields(self):
            target = data
            for key in f.metadata["toml_path"].split("."):
                target = target.setdefault(key, {})
            target[f.name] = flat[f.name]

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, mode="wb") as config:
            tomli_w.dump(data, config)
