# Written by Encore_YAMNet.ipynb. Edit the code in the notebook, not in this file.
"""Acoustic prior: role scores computed directly from the acoustic descriptors.

This is the role scorer that works on day one, before any human labels exist. It is NOT a
trained model. It turns each role's definition into a few fuzzy conditions on measured
properties of the sound, for example:

    Kick / Low Hit   = a single hit  AND short  AND dark (low-frequency)
    Hi-Hat / Tick    = a single hit  AND very short  AND bright
    Pad / Drone      = pitched  AND long  AND not a hit  AND steady

It never looks at WHAT made the sound, so it applies to any recording. Its weakness is that
the thresholds below are engineering judgement. They were chosen from the role definitions
and from looking at descriptor ranges on real recordings, and they have not been validated
against human role labels. `scripts/evaluate_roles.py` measures exactly that once labels
exist, and the learned model only replaces this prior if it beats it on unseen categories.
"""
from __future__ import annotations

import math

from . import config as C


def ramp(x: float, lo: float, hi: float) -> float:
    """0 below `lo`, 1 above `hi`, straight line in between."""
    if hi == lo:
        return float(x >= hi)
    return float(min(max((x - lo) / (hi - lo), 0.0), 1.0))


def _log2(x: float) -> float:
    return math.log2(max(x, 1.0))


def compute_traits(d: dict) -> dict:
    """Fuzzy yes/no properties of the sound, each between 0 and 1."""
    eff = d["effective_duration_s"]   # all the time the recording is "on"
    event = d["event_duration_s"]     # the loudest single event only
    lc = _log2(d["centroid_hz"])

    # a "hit": energy concentrated in a fast-rising, quickly decaying burst
    hit = (1 - ramp(d["sustain_ratio"], 0.15, 0.35)) * (1 - ramp(d["attack_ms"], 20, 80))
    pitched = max(ramp(d["voiced_fraction"], 0.15, 0.5), 0.7 * ramp(d["pitch_clarity"], 0.55, 0.85))
    dark = max(1 - ramp(lc, _log2(300), _log2(800)), ramp(d["low_ratio"], 0.35, 0.7))
    bright = max(ramp(lc, _log2(1800), _log2(3500)), ramp(d["high_ratio"], 0.15, 0.5))
    bright = min(bright, 1 - dark)
    f0 = d["f0_hz"]
    low_pitch = pitched * (1 - ramp(_log2(f0), _log2(130), _log2(260))) if f0 > 0 else 0.0
    high_pitch = pitched * ramp(_log2(f0), _log2(130), _log2(260)) if f0 > 0 else 0.0
    moving = ramp(abs(d["centroid_drift_oct"]), 0.5, 1.5) * ramp(eff, 0.25, 0.6)

    return {
        "hit": hit,
        # Hit-type roles are judged on the single loudest event, so that knocking three
        # times instead of once does not change the answer.
        "short": 1 - ramp(event, 0.15, 0.5),
        "very_short": 1 - ramp(event, 0.08, 0.3),
        "long": ramp(eff, 0.4, 1.2),
        "pitched": pitched,
        "unpitched": 1 - pitched,
        "dark": dark,
        "bright": bright,
        "busy": ramp(d["onset_count"], 2, 6),          # several separate attacks
        "moving": moving,                              # spectrum sweeps up or down
        "steady": (1 - moving) * (1 - ramp(d["f0_std_semitones"], 1.0, 4.0)),
        "low_pitch": low_pitch,
        "high_pitch": high_pitch,
        "long_tail": (1 - ramp(d["attack_ms"], 20, 80)) * ramp(d["decay_ms"], 300, 1000),
    }


# A role that fails one of its conditions still gets up to this much "partial credit" for the
# conditions it does meet. Without it, every role after the first one or two would score
# exactly 0 on about half of all recordings, and the third suggestion would be an arbitrary
# pick. With it, the remaining places go to the roles that are acoustically closest. The value
# is below config.WEAK_ROLE_SCORE on purpose, so a suggestion that only exists because of
# partial credit is always reported as "weak".
PARTIAL_CREDIT = 0.25


def _mean(values: list) -> float:
    return float(sum(values) / len(values))


def prior_scores(d: dict) -> dict:
    """Role fit scores in [0, 1] for all five roles. These are heuristic fit scores,
    not probabilities.

    score = max(strict, PARTIAL_CREDIT * partial)
      strict   all of the role's conditions multiplied together (every one must hold)
      partial  the average of the same conditions (how many of them hold)
    """
    t = compute_traits(d)
    eff = d["effective_duration_s"]
    event = d["event_duration_s"]
    sweeping = ramp(abs(d["centroid_drift_oct"]), 0.5, 1.5)
    grainy = t["busy"] * (1 - ramp(d["sustain_ratio"], 0.2, 0.4))

    strict = {
        # hits, impacts, thumps, claps -- any single-event percussive sound
        "percussion": t["hit"] * (1 - ramp(event, 0.5, 1.0)),
        # repeating patterns: ticking, rattling, shaking, jingling
        "rhythmic": max(0.9 * grainy, 0.7 * t["busy"]) * (1 - t["long"]),
        # pitched or tonal: hums, whistles, bass, anything with a note
        "melodic": t["pitched"] * (0.5 + 0.5 * ramp(eff, 0.05, 0.3)),
        # sustained backgrounds, drones, washes, atmosphere
        "ambient": t["long"] * (1 - t["hit"]) * (0.5 + 0.5 * t["steady"]),
        # effects, sweeps, bursts, one-shot accents
        "transition": max(t["moving"], 0.7 * t["long_tail"],
                         0.5 * t["hit"] * ramp(d["decay_ms"], 300, 1000)),
    }
    partial = {
        "percussion": _mean([t["hit"], 1 - ramp(event, 0.5, 1.0)]),
        "rhythmic": _mean([t["busy"], 1 - t["long"], 1 - t["hit"]]),
        "melodic": _mean([t["pitched"], ramp(eff, 0.05, 0.3)]),
        "ambient": _mean([t["long"], 1 - t["hit"], t["steady"]]),
        "transition": max(_mean([sweeping, ramp(eff, 0.25, 0.6)]),
                         _mean([1 - ramp(d["attack_ms"], 20, 80), ramp(d["decay_ms"], 300, 1000)])),
    }
    return {role: float(min(max(strict[role], PARTIAL_CREDIT * partial[role], 0.0), 1.0))
            for role in C.ROLE_IDS}


def describe_character(d: dict) -> list[str]:
    """A few plain-language words about the sound, for display and for explaining results."""
    t = compute_traits(d)
    words = []
    if t["hit"] > 0.6:
        words.append("single hit" if t["busy"] < 0.5 else "series of hits")
    elif t["busy"] > 0.5:
        words.append("many small attacks")
    if t["long"] > 0.6:
        words.append("sustained")
    elif t["short"] > 0.6:
        words.append("short")
    if t["dark"] > 0.6:
        words.append("low / dark")
    elif t["bright"] > 0.6:
        words.append("bright")
    else:
        words.append("mid-range")
    if t["pitched"] > 0.6:
        words.append(f"pitched (about {d['f0_hz']:.0f} Hz)" if d["f0_hz"] > 0 else "tonal")
    elif t["pitched"] < 0.3:
        words.append("unpitched / noisy")
    if t["moving"] > 0.6:
        words.append("sweeping")
    if t["long_tail"] > 0.6:
        words.append("long ring-out")
    return words
