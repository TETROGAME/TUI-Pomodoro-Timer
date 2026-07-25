import queue
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from tuipomodoro.config import Settings
from tuipomodoro.timer import CyclePhase


class FadeAction(Enum):
    NONE = auto()
    FREEZE = auto()
    REMOVE = auto()


@dataclass
class Voice:
    name: str
    samples: np.ndarray
    samplerate: int
    position: int = 0
    loop: bool = False
    frozen: bool = False

    current_gain: float = 0.0
    target_gain: float = 0.0
    on_fade_complete: FadeAction = FadeAction.NONE

    fade_duration_samples: int = 0
    fade_samples_done: int = 0
    fade_start_gain: float = 0.0

    category: str = "ambiance"

    def start_fade(self, target: float, duration_samples: int) -> None:
        self.fade_start_gain = self.current_gain
        self.target_gain = target
        self.fade_duration_samples = duration_samples
        self.fade_samples_done = 0

    @property
    def is_fading(self) -> bool:
        return self.fade_samples_done < self.fade_duration_samples


class AudioManager:
    SAMPLERATE = 44100
    CHANNELS = 2
    BLOCKSIZE = 1024

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.enabled = self._probe_device()

        self._sound_cache: dict[str, np.ndarray] = {}

        self._voices: list[Voice] = []

        self._category_gains: dict[str, float] = {"ambiance": 1.0, "effect": 1.0}

        self._commands: queue.Queue = queue.Queue()

        self._stream: sd.OutputStream | None = None
        self._paused: bool = False

        if self.enabled:
            self._start_stream()

    def _probe_device(self) -> bool:
        """Return False if no audio device was found"""
        try:
            device_info = sd.query_devices(kind="output")
        except sd.PortAudioError:
            return False
        if device_info is None or device_info["max_output_channels"] < 1:
            return False
        return True

    def _start_stream(self) -> None:
        stream = sd.OutputStream(
            samplerate=self.SAMPLERATE,
            channels=self.CHANNELS,
            blocksize=self.BLOCKSIZE,
            callback=self._callback,
        )
        stream.start()
        self._stream = stream

    def shutdown(self) -> None:
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None

    def _callback(self, outdata, frames, time_info, status) -> None:
        outdata[:] = 0

        while not self._commands.empty():
            cmd_type, *args = self._commands.get_nowait()
            if cmd_type == "add_voice":
                self._voices.append(args[0])
            elif cmd_type == "remove_voice":
                self._voices = [v for v in self._voices if v is not args[0]]
            elif cmd_type == "set_category_gain":
                category, level = args
                self._category_gains[category] = level
            elif cmd_type == "set_voice_gain":
                voice, target, fade_ms = args
                fade_samples = int(fade_ms / 1000 * self.SAMPLERATE)
                voice.start_fade(target, fade_samples)
            elif cmd_type == "set_paused":
                self._paused = args[0]
            elif cmd_type == "pause_fade":
                fade_samples = args[0]
                for v in self._voices:
                    if v.category == "ambiance":
                        v.start_fade(0.0, fade_samples)
                        v.on_fade_complete = FadeAction.FREEZE
            elif cmd_type == "resume_fade":
                fade_samples = args[0]
                for v in self._voices:
                    if v.category == "ambiance" and v.frozen:
                        v.frozen = False
                        v.start_fade(self.settings.audio_volume, fade_samples)
            elif cmd_type == "stop_ambiance":
                fade_ms = args[0] if args else 500
                fade_samples = int(fade_ms / 1000 * self.SAMPLERATE)
                for v in self._voices:
                    if v.category == "ambiance":
                        v.start_fade(0.0, fade_samples)
                        v.on_fade_complete = FadeAction.REMOVE
            elif cmd_type == "reset":
                self._voices.clear()
            elif cmd_type == "unfreeze_all":
                for v in self._voices:
                    v.frozen = False
            elif cmd_type == "play_ambiance":
                name, samples, volume, fade_ms = args
                fade_samples = int(fade_ms / 1000 * self.SAMPLERATE)
                for v in self._voices:
                    if v.category == "ambiance" and v.name == name:
                        v.start_fade(volume, fade_samples)
                        break
                else:
                    for v in self._voices:
                        if v.category == "ambiance":
                            v.start_fade(0.0, fade_samples)
                            v.on_fade_complete = FadeAction.REMOVE
                    voice = Voice(
                        name=name,
                        samples=samples,
                        samplerate=self.SAMPLERATE,
                        loop=True,
                        current_gain=0.0,
                        target_gain=volume,
                        on_fade_complete=FadeAction.NONE,
                        category="ambiance",
                    )
                    voice.fade_start_gain = 0.0
                    voice.fade_duration_samples = fade_samples
                    voice.fade_samples_done = 0
                    self._voices.append(voice)
            elif cmd_type == "play_effect":
                name, samples, volume = args
                voice = Voice(
                    name=name,
                    samples=samples,
                    samplerate=self.SAMPLERATE,
                    loop=False,
                    current_gain=0.0,
                    target_gain=volume,
                    on_fade_complete=FadeAction.REMOVE,
                    category="effect",
                )
                voice.fade_start_gain = 0.0
                voice.fade_duration_samples = int(0.02 * self.SAMPLERATE)
                voice.fade_samples_done = 0
                self._voices.append(voice)

        if self._paused:
            return

        voices_to_remove: list[Voice] = []

        for voice in self._voices:
            if voice.frozen:
                continue

            available = len(voice.samples) - voice.position
            to_read = min(frames, available)

            if to_read <= 0:
                if voice.loop:
                    voice.position = 0
                    to_read = min(frames, len(voice.samples))
                else:
                    if voice.on_fade_complete == FadeAction.REMOVE:
                        voices_to_remove.append(voice)
                    continue

            chunk = voice.samples[voice.position : voice.position + to_read]

            if voice.is_fading:
                remaining_fade = voice.fade_duration_samples - voice.fade_samples_done
                to_fade = min(to_read, remaining_fade)
                if voice.fade_duration_samples > 0:
                    t_start = voice.fade_samples_done / voice.fade_duration_samples
                    t_end = (voice.fade_samples_done + to_fade) / voice.fade_duration_samples
                    t_values = np.linspace(t_start, t_end, to_fade, endpoint=False)
                    gains = voice.fade_start_gain + (voice.target_gain - voice.fade_start_gain) * t_values
                else:
                    gains = np.full(to_fade, voice.target_gain)

                voice.current_gain = gains[-1] if len(gains) > 0 else voice.target_gain
                voice.fade_samples_done += to_fade

                if voice.fade_samples_done >= voice.fade_duration_samples:
                    voice.current_gain = voice.target_gain
                    if voice.current_gain == 0.0 and voice.on_fade_complete == FadeAction.REMOVE:
                        voices_to_remove.append(voice)
                        continue
                    elif voice.current_gain == 0.0 and voice.on_fade_complete == FadeAction.FREEZE:
                        voice.frozen = True
                        continue

                if to_fade < to_read:
                    gains = np.concatenate([
                        gains,
                        np.full(to_read - to_fade, voice.current_gain),
                    ])
            else:
                gains = np.full(to_read, voice.current_gain)

            cat_gain = self._category_gains.get(voice.category, 1.0)
            gains *= cat_gain

            if chunk.ndim == 1:
                chunk_stereo = np.column_stack([chunk, chunk])
            else:
                chunk_stereo = chunk

            gains_2d = gains[:, np.newaxis]
            outdata[:to_read] += (chunk_stereo * gains_2d).astype(outdata.dtype)

            voice.position += to_read

        for voice in voices_to_remove:
            if voice in self._voices:
                self._voices.remove(voice)

    def validate_user_file(self, path: Path) -> bool:
        """Check if file is read correctly via soundfile and if it's mono or stereo"""
        try:
            info = sf.info(str(path))
        except (sf.LibsndfileError, RuntimeError):
            return False
        return info.channels in (1, 2)

    def _resample(
        self, data: np.ndarray, orig_rate: int, target_rate: int
    ) -> np.ndarray:
        """Bring sound to new samplerate using np.interp"""
        if orig_rate == target_rate:
            return data
        duration = len(data) / orig_rate
        orig_times = np.linspace(0, duration, num=len(data), endpoint=False)
        target_n = int(round(duration * target_rate))
        target_times = np.linspace(0, duration, num=target_n, endpoint=False)
        return np.interp(target_times, orig_times, data)

    def _load_and_cache(self, name: str, path: Path) -> np.ndarray:
        data, orig_rate = sf.read(path, dtype="float32")

        # mono
        if data.ndim == 1:
            mono = self._resample(data, orig_rate, self.SAMPLERATE)
            stereo = np.column_stack([mono, mono])
        # stereo
        else:
            left = self._resample(data[:, 0], orig_rate, self.SAMPLERATE)
            right = self._resample(data[:, 1], orig_rate, self.SAMPLERATE)
            stereo = np.column_stack([left, right])
        self._sound_cache[name] = stereo
        return stereo

    def _get_or_load(self, name: str, path: Path) -> np.ndarray:
        if name in self._sound_cache:
            return self._sound_cache[name]
        return self._load_and_cache(name, path)

    def play_ambiance(self, name: str, path: Path, fade_ms: int = 500) -> None:
        samples = self._get_or_load(name, path)
        self._commands.put(
            ("play_ambiance", name, samples, self.settings.audio_volume, fade_ms)
        )

    def stop_ambiance(self, fade_ms: int = 500) -> None:
        self._commands.put(("stop_ambiance", fade_ms))

    def play_effect(self, name: str) -> None:
        audio_dir = Path(__file__).parent.parent / "audio"
        path = audio_dir / name
        if not path.exists():
            return
        samples = self._get_or_load(name, path)
        self._commands.put(("play_effect", name, samples, self.settings.audio_volume))

    def on_phase_change(self, new_phase: CyclePhase) -> None:
        if not self.enabled:
            return

        audio_dir = Path(__file__).parent.parent / "audio"

        if new_phase == CyclePhase.WORK:
            file_name = self.settings.work_ambiance_file
            if file_name:
                self.play_ambiance(file_name, audio_dir / file_name)
        elif new_phase == CyclePhase.SHORT_BREAK:
            file_name = self.settings.break_ambiance_file
            if file_name:
                self.play_ambiance(file_name, audio_dir / file_name)
            else:
                self.stop_ambiance()
        elif new_phase == CyclePhase.LONG_BREAK:
            file_name = self.settings.break_ambiance_file
            if file_name:
                self.play_ambiance(file_name, audio_dir / file_name)
            else:
                self.stop_ambiance()
        elif new_phase == CyclePhase.TIMER:
            file_name = self.settings.timer_ambiance_file
            if file_name:
                self.play_ambiance(file_name, audio_dir / file_name)
            else:
                self.stop_ambiance()

    def pause(self) -> None:
        fade_samples = int(80 / 1000 * self.SAMPLERATE)
        self._commands.put(("pause_fade", fade_samples))

    def resume(self) -> None:
        fade_samples = int(80 / 1000 * self.SAMPLERATE)
        self._commands.put(("resume_fade", fade_samples))

    def reset(self) -> None:
        self._commands.put(("reset",))
        self._commands.put(("set_paused", False))
        self._commands.put(("unfreeze_all",))

    def set_category_gain(
        self, category: str, level: float, fade_ms: int = 200
    ) -> None:
        self._commands.put(("set_category_gain", category, level))
