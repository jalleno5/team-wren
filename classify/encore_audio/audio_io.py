# Written by Encore_YAMNet.ipynb. Edit the code in the notebook, not in this file.
"""Audio loading and preprocessing.

One code path for every format and for training, evaluation and inference:

    file (m4a / wav / mp3 / anything ffmpeg reads)
      -> ffmpeg -> 16 kHz mono float32
      -> remove DC offset
      -> reject if empty / too short / silent
      -> trim leading and trailing near-silence
      -> cap at MAX_ANALYSIS_SECONDS
      -> peak-normalise
      -> (for YAMNet only) zero-pad to at least 1.0 s

ffmpeg is the only decoder, so a WAV and an M4A of the same sound go through identical
resampling and channel mixing.
"""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from . import config as C


class AudioRejected(Exception):
    """The file cannot be analysed. `code` is machine-readable, `message` is for humans."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class PreparedAudio:
    active: np.ndarray        # trimmed, normalised audio. Acoustic descriptors use this.
    yamnet_input: np.ndarray  # `active`, zero-padded to >= 1.0 s. YAMNet uses this.
    info: dict = field(default_factory=dict)   # JSON-serialisable facts about the recording
    flags: list = field(default_factory=list)  # review flags raised by preprocessing


_FFMPEG: str | None = None


def find_ffmpeg() -> str:
    """Use the ffmpeg binary that ships with the `imageio-ffmpeg` pip package, falling back
    to a system ffmpeg. This keeps the project runnable without a system-wide install."""
    global _FFMPEG
    if _FFMPEG:
        return _FFMPEG
    try:
        import imageio_ffmpeg

        _FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        _FFMPEG = shutil.which("ffmpeg")
    if not _FFMPEG:
        raise RuntimeError(
            "ffmpeg not found. Run `pip install imageio-ffmpeg` (bundles a binary) "
            "or install ffmpeg with your package manager."
        )
    return _FFMPEG


def decode_to_mono_16k(path: str | Path) -> np.ndarray:
    """Decode any audio file to 16 kHz mono float32 in [-1, 1]."""
    path = Path(path)
    if not path.is_file():
        raise AudioRejected("file_not_found", f"No such file: {path}")
    if path.stat().st_size == 0:
        raise AudioRejected("empty", "The file is empty (0 bytes).")
    cmd = [
        find_ffmpeg(), "-nostdin", "-v", "error",
        "-t", str(C.MAX_DECODE_SECONDS), "-i", str(path),
        "-vn", "-ac", "1", "-ar", str(C.SAMPLE_RATE), "-f", "f32le", "-",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=120)
    except subprocess.TimeoutExpired:
        raise AudioRejected("decode_failed", "ffmpeg timed out while decoding the file.")
    if proc.returncode != 0 or len(proc.stdout) < 4:
        detail = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        raise AudioRejected(
            "decode_failed",
            "Could not decode this file as audio" + (f": {detail[-1]}" if detail else "."),
        )
    usable = len(proc.stdout) - (len(proc.stdout) % 4)
    return np.frombuffer(proc.stdout[:usable], dtype="<f4").astype(np.float32)


def frame_rms(x: np.ndarray, win: int, hop: int) -> np.ndarray:
    """RMS level in windows of `win` samples taken every `hop` samples."""
    if len(x) < win:
        x = np.pad(x, (0, win - len(x)))
    csum = np.concatenate(([0.0], np.cumsum(x.astype(np.float64) ** 2)))
    starts = np.arange(0, len(x) - win + 1, hop)
    return np.sqrt(np.maximum(csum[starts + win] - csum[starts], 0.0) / win)


def _db(v) -> float:
    return float(20.0 * np.log10(max(float(v), 1e-12)))


def prepare_waveform(raw: np.ndarray) -> PreparedAudio:
    """Validate, trim and normalise a 16 kHz mono waveform. Raises AudioRejected."""
    sr = C.SAMPLE_RATE
    if raw.size == 0:
        raise AudioRejected("empty", "The file contains no audio samples.")
    if not np.all(np.isfinite(raw)):
        raise AudioRejected("decode_failed", "The decoded audio contains invalid samples.")
    file_seconds = raw.size / sr
    if file_seconds < C.MIN_FILE_SECONDS:
        raise AudioRejected(
            "too_short", f"Only {file_seconds * 1000:.0f} ms of audio. Record at least 50 ms."
        )

    x = raw.astype(np.float64) - float(np.mean(raw))  # remove DC offset
    peak = float(np.max(np.abs(x)))
    if _db(peak) < C.SILENCE_PEAK_DBFS:
        raise AudioRejected(
            "silent",
            f"The recording is silent or far too quiet (peak {_db(peak):.0f} dBFS). "
            "Check the microphone and record again.",
        )

    flags: list[str] = []
    clipped_fraction = float(np.mean(np.abs(raw) >= 0.999))
    if clipped_fraction > C.CLIPPED_FRACTION:
        flags.append("clipped")

    # Frame levels: 20 ms windows every 10 ms.
    win, hop = int(0.020 * sr), int(0.010 * sr)
    env_db = 20.0 * np.log10(frame_rms(x, win, hop) + 1e-9)
    top_db = float(env_db.max())
    floor_db = float(np.percentile(env_db, 10))
    contrast_db = top_db - floor_db
    if file_seconds >= 0.5 and contrast_db < C.LOW_CONTRAST_DB:
        # Honest ambiguity: from one recording we cannot tell a continuous sound (a hum,
        # running water) from a short sound buried in background noise.
        flags.append("steady_or_noisy")

    # Trim leading / trailing audio that is far below the loudest frame.
    active = np.flatnonzero(env_db >= top_db - C.TRIM_BELOW_PEAK_DB)
    start = max(0, int(active[0]) * hop - int(C.TRIM_PRE_ROLL_S * sr))
    end = min(x.size, int(active[-1]) * hop + win + int(C.TRIM_POST_ROLL_S * sr))
    trimmed = x[start:end].copy()

    max_len = int(C.MAX_ANALYSIS_SECONDS * sr)
    if trimmed.size > max_len:
        trimmed = trimmed[:max_len]
        fade = int(0.020 * sr)
        trimmed[-fade:] *= np.linspace(1.0, 0.0, fade)
        flags.append("truncated")

    gain = C.TARGET_PEAK / max(float(np.max(np.abs(trimmed))), 1e-9)
    active_wave = (trimmed * gain).astype(np.float32)

    yamnet_input = active_wave
    if yamnet_input.size < C.MIN_YAMNET_SAMPLES:
        yamnet_input = np.pad(yamnet_input, (0, C.MIN_YAMNET_SAMPLES - yamnet_input.size))

    info = {
        "file_duration_s": round(file_seconds, 3),
        "analysed_duration_s": round(active_wave.size / sr, 3),
        "sample_rate": sr,
        "peak_dbfs": round(_db(peak), 1),
        "noise_floor_dbfs": round(floor_db, 1),
        "contrast_db": round(contrast_db, 1),
        "clipped_fraction": round(clipped_fraction, 5),
        "gain_applied_db": round(_db(gain), 1),
    }
    return PreparedAudio(active=active_wave, yamnet_input=yamnet_input, info=info, flags=flags)


def load_audio(path: str | Path) -> PreparedAudio:
    """decode + prepare. This is the single entry point used everywhere."""
    return prepare_waveform(decode_to_mono_16k(path))
