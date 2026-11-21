# Written by Encore_YAMNet.ipynb. Edit the code in the notebook, not in this file.
"""Acoustic descriptors: plain measurements of how a sound behaves.

These numbers describe the SOUND, not the object that made it: how long it is, how fast it
starts, where its energy sits in frequency, whether it has a pitch, whether it changes over
time. Musical roles are largely defined in exactly these terms ("deep thump", "short crisp
high hit", "sustained tone"), which is why they work on objects nobody has recorded before.

Only numpy and scipy are used, so there is nothing exotic to install.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import find_peaks, stft

from . import config as C
from .audio_io import frame_rms

# Fixed order of the numeric vector fed to the learned role model.
DESCRIPTOR_VECTOR_NAMES = [
    "log10_effective_duration_s", "log10_event_duration_s", "log10_attack_ms", "log10_decay_ms", "sustain_ratio",
    "temporal_centroid", "log1p_onset_count", "onset_rate_hz", "log2_centroid_hz",
    "log2_rolloff_hz", "low_ratio", "high_ratio", "flatness", "centroid_std_oct",
    "centroid_drift_oct", "voiced_fraction", "pitch_clarity", "log2_f0_hz", "f0_std_semitones",
]


# ----------------------------------------------------------------------------- envelope
def _envelope_features(x: np.ndarray, sr: int) -> dict:
    """Loudness-over-time shape, from an RMS envelope with 5 ms windows every 1 ms."""
    hop = sr // 1000
    env = frame_rms(x, 5 * hop, hop)
    peak_i = int(np.argmax(env))
    peak = float(env[peak_i]) + 1e-12
    lo, hi = 0.1 * peak, 0.9 * peak

    # Attack: time for the loudest event to rise from 10 % to 90 % of its peak level.
    below = np.flatnonzero(env[: peak_i + 1] < lo)
    t10 = int(below[-1]) + 1 if below.size else 0
    above = np.flatnonzero(env[t10 : peak_i + 1] >= hi)
    t90 = t10 + (int(above[0]) if above.size else peak_i - t10)
    attack_ms = float(max(t90 - t10, 1))

    # Decay: time from the peak until the level first falls below 10 % of the peak.
    after = np.flatnonzero(env[peak_i:] < lo)
    decay_ms = float(max(int(after[0]) if after.size else env.size - peak_i, 1))

    times = np.arange(env.size)
    return {
        "effective_duration_s": float(np.sum(env >= lo)) / 1000.0,  # time within 20 dB of peak
        # Length of the loudest single event: from where it rises above 10 % of its peak to
        # where it falls back below. Three knocks in one recording have a long effective
        # duration but a short event duration, and it is the single knock that would be
        # used as a drum hit.
        "event_duration_s": float(peak_i - t10 + decay_ms) / 1000.0,
        "attack_ms": attack_ms,
        "decay_ms": decay_ms,
        # mean level / peak level. A single decaying hit is ~0.1-0.25, a held tone ~0.6-0.9.
        "sustain_ratio": float(np.mean(env) / peak),
        # where the energy sits in time: 0 = all at the start, 0.5 = evenly spread
        "temporal_centroid": float(np.sum(times * env) / (np.sum(env) + 1e-12) / max(env.size, 1)),
    }


def _onset_features(x: np.ndarray, sr: int) -> dict:
    """Count distinct attacks: places where the level jumps by 6 dB or more within 30 ms."""
    hop = sr // 100
    env_db = 20.0 * np.log10(frame_rms(x, 2 * hop, hop) + 1e-9)
    top = float(env_db.max())
    padded = np.concatenate((np.full(3, top - 60.0), env_db))
    recent_min = np.minimum(np.minimum(padded[:-3], padded[1:-2]), padded[2:-1])
    rise = env_db - recent_min
    peaks, _ = find_peaks(rise, height=6.0, distance=5)  # at least 50 ms apart
    # the level must actually get reasonably loud shortly after the jump
    ahead = np.array([env_db[p : p + 4].max() for p in peaks]) if peaks.size else np.array([])
    count = int(np.sum(ahead >= top - 25.0))
    return {"onset_count": float(count), "onset_rate_hz": count / max(x.size / sr, 0.05)}


# ----------------------------------------------------------------------------- spectrum
def _spectral_features(x: np.ndarray, sr: int) -> dict:
    n_fft, hop = 512, sr // 100  # 32 ms windows every 10 ms
    if x.size < n_fft:
        x = np.pad(x, (0, n_fft - x.size))
    freqs, _, Z = stft(x, fs=sr, window="hann", nperseg=n_fft, noverlap=n_fft - hop,
                       boundary=None, padded=False)
    P = np.abs(Z) ** 2                       # [freq, time] power
    keep_f = freqs >= 50.0                   # ignore DC / handling rumble
    freqs, P = freqs[keep_f], P[keep_f]
    frame_energy = P.sum(axis=0)
    loud = frame_energy >= frame_energy.max() * 1e-3   # frames within 30 dB of the loudest
    P, frame_energy = P[:, loud], frame_energy[loud]
    S = P.sum(axis=1)                        # long-term spectrum of the loud frames
    total = float(S.sum()) + 1e-20

    centroid = float(np.sum(freqs * S) / total)
    rolloff = float(freqs[min(np.searchsorted(np.cumsum(S), 0.85 * total), freqs.size - 1)])

    # Flatness: ~0 for a pure tone, ~0.5 for white noise. Per frame, energy-weighted.
    band = (freqs >= 100.0) & (freqs <= 7500.0)
    Pb = P[band] + 1e-12
    flat_t = np.exp(np.mean(np.log(Pb), axis=0)) / np.mean(Pb, axis=0)
    flatness = float(np.sum(flat_t * frame_energy) / (frame_energy.sum() + 1e-20))

    # Does the spectrum move over time (a sweep, a zipper)? Track the per-frame centroid.
    cent_t = np.log2(np.sum(freqs[:, None] * P, axis=0) / (frame_energy + 1e-20) + 1e-9)
    w = frame_energy / (frame_energy.sum() + 1e-20)
    mean_c = float(np.sum(w * cent_t))
    centroid_std = float(np.sqrt(np.sum(w * (cent_t - mean_c) ** 2)))
    drift = 0.0
    t_idx = np.flatnonzero(loud).astype(np.float64)
    if t_idx.size >= 5:
        t = t_idx * hop / sr
        t_mean = float(np.sum(w * t))
        var_t = float(np.sum(w * (t - t_mean) ** 2))
        if var_t > 1e-9:
            slope = float(np.sum(w * (t - t_mean) * (cent_t - mean_c)) / var_t)  # octaves / s
            drift = slope * float(t[-1] - t[0])                                  # octaves total

    return {
        "centroid_hz": centroid,
        "rolloff_hz": rolloff,
        "low_ratio": float(S[freqs < 250.0].sum() / total),
        "high_ratio": float(S[freqs > 3000.0].sum() / total),
        "flatness": flatness,
        "centroid_std_oct": centroid_std,
        "centroid_drift_oct": drift,
    }


# ----------------------------------------------------------------------------- pitch
def _pitch_features(x: np.ndarray, sr: int, fmin: float = 60.0, fmax: float = 4000.0) -> dict:
    """Pitch tracking with the YIN algorithm (de Cheveigne & Kawahara, 2002).

    For each 64 ms frame we ask: is there a lag tau such that the frame looks like a copy of
    itself shifted by tau? If so the sound is periodic with pitch sr / tau.
    """
    frame, hop = 1024, 256
    tau_min, tau_max = int(sr / fmax), int(sr / fmin)
    win = frame - tau_max
    if x.size < frame:
        x = np.pad(x, (0, frame - x.size))
    x = x.astype(np.float64)
    starts = np.arange(0, x.size - frame + 1, hop)
    frames = np.stack([x[s : s + frame] for s in starts])
    rms = np.sqrt(np.mean(frames[:, :win] ** 2, axis=1))
    use = rms >= 0.1 * rms.max()
    frames = frames[use]

    # YIN difference function d(tau) and its cumulative-mean-normalised form d'(tau).
    base = frames[:, :win]
    d = np.zeros((frames.shape[0], tau_max + 1))
    for tau in range(1, tau_max + 1):
        d[:, tau] = np.sum((base - frames[:, tau : tau + win]) ** 2, axis=1)
    cmnd = np.ones_like(d)
    running = np.cumsum(d[:, 1:], axis=1)
    cmnd[:, 1:] = d[:, 1:] * np.arange(1, tau_max + 1) / (running + 1e-12)

    f0, clarity = [], []
    for row in cmnd:
        seg = row[tau_min : tau_max + 1]
        cand = np.flatnonzero(seg < 0.15)
        if cand.size:                      # first dip below threshold, walked down to its minimum
            i = int(cand[0])
            while i + 1 < seg.size and seg[i + 1] < seg[i]:
                i += 1
        else:
            i = int(np.argmin(seg))
        tau = float(i + tau_min)
        if 0 < i < seg.size - 1:           # parabolic interpolation for sub-sample accuracy
            a, b, c = seg[i - 1], seg[i], seg[i + 1]
            denom = a - 2 * b + c
            if abs(denom) > 1e-12:
                tau += 0.5 * (a - c) / denom
        clarity.append(1.0 - float(seg[i]))
        f0.append(sr / tau)
    f0, clarity = np.array(f0), np.clip(np.array(clarity), 0.0, 1.0)
    voiced = clarity >= 0.85               # i.e. d' < 0.15

    out = {
        "voiced_fraction": float(np.mean(voiced)) if voiced.size else 0.0,
        "pitch_clarity": float(np.median(clarity)) if clarity.size else 0.0,
        "f0_hz": 0.0,
        "f0_std_semitones": 0.0,
    }
    if np.any(voiced):
        semis = 12.0 * np.log2(f0[voiced])
        out["f0_hz"] = float(2.0 ** (np.median(semis) / 12.0))
        out["f0_std_semitones"] = float(np.std(semis))
    return out


# ----------------------------------------------------------------------------- public API
def compute_descriptors(active: np.ndarray, sr: int = C.SAMPLE_RATE) -> dict:
    """All descriptors for one trimmed, normalised waveform. Values are plain floats."""
    x = np.asarray(active, dtype=np.float64)
    d = {"duration_s": x.size / sr}
    d.update(_envelope_features(x, sr))
    d.update(_onset_features(x, sr))
    d.update(_spectral_features(x, sr))
    d.update(_pitch_features(x, sr))
    return {k: float(v) for k, v in d.items()}


def descriptor_vector(d: dict) -> np.ndarray:
    """Descriptors as a fixed-order numeric vector (see DESCRIPTOR_VECTOR_NAMES).
    Durations and frequencies are log-scaled because that is how we hear them."""
    f0 = d["f0_hz"]
    return np.array([
        np.log10(max(d["effective_duration_s"], 1e-3)),
        np.log10(max(d["event_duration_s"], 1e-3)),
        np.log10(max(d["attack_ms"], 1.0)),
        np.log10(max(d["decay_ms"], 1.0)),
        d["sustain_ratio"],
        d["temporal_centroid"],
        np.log1p(d["onset_count"]),
        d["onset_rate_hz"],
        np.log2(max(d["centroid_hz"], 20.0)),
        np.log2(max(d["rolloff_hz"], 20.0)),
        d["low_ratio"],
        d["high_ratio"],
        d["flatness"],
        d["centroid_std_oct"],
        d["centroid_drift_oct"],
        d["voiced_fraction"],
        d["pitch_clarity"],
        np.log2(f0) if f0 > 0 else 0.0,
        d["f0_std_semitones"],
    ], dtype=np.float32)
