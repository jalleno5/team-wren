# Written by Encore_YAMNet.ipynb. Edit the code in the notebook, not in this file.
"""Shared constants.

Everything that training, evaluation and inference must agree on lives here, so there is
exactly one place to change it. If you change anything in the PREPROCESSING block, bump
PREPROCESS_VERSION and re-run feature extraction and training: a role model trained on one
preprocessing version is ignored at inference when the versions differ.
"""
from __future__ import annotations

import os
from pathlib import Path

VERSION = "0.1.0"

# --------------------------------------------------------------------------- paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = Path(os.environ.get("ENCORE_MODELS_DIR", PROJECT_ROOT / "models"))
YAMNET_DIR = Path(os.environ.get("ENCORE_YAMNET_DIR", MODELS_DIR / "yamnet"))
ROLE_MODEL_NPZ = MODELS_DIR / "role_model.npz"
ROLE_MODEL_JSON = MODELS_DIR / "role_model.json"

# --------------------------------------------------------------------------- preprocessing
PREPROCESS_VERSION = "pre-1"
SAMPLE_RATE = 16_000            # YAMNet's required sample rate
MAX_DECODE_SECONDS = 60.0       # never decode more than this from a file
MAX_ANALYSIS_SECONDS = 10.0     # after trimming, analyse at most this much
MIN_FILE_SECONDS = 0.05         # shorter than this is rejected as "too_short"
MIN_YAMNET_SAMPLES = 16_000     # short clips are zero-padded to 1.0 s for YAMNet
SILENCE_PEAK_DBFS = -50.0       # peak below this is rejected as "silent"
TRIM_BELOW_PEAK_DB = 40.0       # leading/trailing audio this far below the loudest frame is trimmed
TRIM_PRE_ROLL_S = 0.05
TRIM_POST_ROLL_S = 0.10
TARGET_PEAK = 0.9               # peak normalisation target (linear)

# --------------------------------------------------------------------------- review thresholds
LOW_LABEL_SCORE = 0.20          # top YAMNet score below this -> "low_label_confidence"
WEAK_ROLE_SCORE = 0.30          # a role score below this is "weak"; if even the top role is
                                # weak, the result gets the "weak_role_evidence" flag
STRONG_ROLE_SCORE = 0.60        # a role score at or above this is "strong"
CLIPPED_FRACTION = 0.001        # more than 0.1 % of samples at full scale -> "clipped"
LOW_CONTRAST_DB = 15.0          # loudest vs quietest parts closer than this -> "steady_or_noisy"

# --------------------------------------------------------------------------- the five roles
# (role_id, display name, description). The ORDER here is the canonical order everywhere:
# label files, model weights and the JSON output all use it.
ROLES: list[tuple[str, str, str]] = [
    ("percussion", "Percussion", "Hits, impacts, thumps, claps, and snaps"),
    ("rhythmic", "Rhythmic", "Repeating patterns: ticking, rattling, shaking"),
    ("melodic", "Melodic", "Pitched or tonal sounds, hums, whistles, bass"),
    ("ambient", "Ambient", "Sustained backgrounds, drones, textures, atmosphere"),
    ("transition", "Transition", "Effects, sweeps, bursts, and one-shot accents"),
]
ROLE_IDS: list[str] = [r[0] for r in ROLES]
ROLE_NAMES: dict[str, str] = {r[0]: r[1] for r in ROLES}
ROLE_DESCRIPTIONS: dict[str, str] = {r[0]: r[2] for r in ROLES}
