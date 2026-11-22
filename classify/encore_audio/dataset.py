# Written by Encore_YAMNet.ipynb. Edit the code in the notebook, not in this file.
"""Training-side bookkeeping: the clip manifest, human labels and the feature file.

Nothing in here is needed at inference time. File formats (all plain CSV so they can be
opened in a spreadsheet and reviewed by a human):

data/manifest.csv            one row per clip
    clip_id    unique id
    path       audio file, relative to the project root
    source     where it came from: "team", "esc50", ...
    category   what made the sound (folder name / dataset class)
    group      LEAKAGE GROUP. Clips with the same group are never split between training
               and testing. Usually equal to category; the same real-world sound from two
               sources (our "clap" and ESC-50 "clapping") shares one group.
    origin     original file name, for traceability

data/labels/labels_<rater>.csv   one row per (clip, rater) decision; the newest row wins
    clip_id, rater, roles (role ids joined by ";"), best_role, unusable (0/1), labeled_at
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

import numpy as np

from . import config as C

DATA_DIR = C.PROJECT_ROOT / "data"
MANIFEST = DATA_DIR / "manifest.csv"
LABELS_DIR = DATA_DIR / "labels"
FEATURES_NPZ = DATA_DIR / "features" / "features.npz"
MANIFEST_FIELDS = ["clip_id", "path", "source", "category", "group", "origin"]
LABEL_FIELDS = ["clip_id", "rater", "roles", "best_role", "unusable", "labeled_at"]

# The same real-world sound under different names -> one leakage group.
GROUP_ALIASES = {
    "clapping": "clap", "claps": "clap",
    "door_wood_knock": "knock", "knocking": "knock",
    "keyboard": "keyboard_typing", "typing": "keyboard_typing",
    "can_opening": "soda_can_opening", "soda_can": "soda_can_opening", "soda": "soda_can_opening",
    "pouring_water": "water", "water_pouring": "water",
    "tongue_click": "tongue_clicking", "tongue": "tongue_clicking",
    "whistle": "whistling", "snapping": "snap", "finger_snap": "snap",
    "key": "keys", "coin": "coins", "zip": "zipper",
}


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.strip().lower()).strip("_")


def group_for(category: str) -> str:
    slug = slugify(category)
    return GROUP_ALIASES.get(slug, slug)


# ----------------------------------------------------------------------------- manifest
def read_manifest(path: Path = MANIFEST) -> list[dict]:
    if not Path(path).is_file():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_manifest(rows: list[dict], path: Path = MANIFEST) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    ids = [r["clip_id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate clip_id in manifest.")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["clip_id"]))


def merge_into_manifest(new_rows: list[dict]) -> tuple[int, int]:
    """Add or replace rows by clip_id. Returns (rows added, total rows)."""
    rows = {r["clip_id"]: r for r in read_manifest()}
    before = len(rows)
    rows.update({r["clip_id"]: r for r in new_rows})
    write_manifest(list(rows.values()))
    return len(rows) - before, len(rows)


# ----------------------------------------------------------------------------- labels
def read_labels(labels_dir: Path = LABELS_DIR) -> dict:
    """{clip_id: {rater: {"roles": set, "best_role": str, "unusable": bool}}}"""
    out: dict = {}
    for file in sorted(Path(labels_dir).glob("labels_*.csv")):
        with open(file, newline="", encoding="utf-8") as f:
            for row in sorted(csv.DictReader(f), key=lambda r: r["labeled_at"]):
                roles = {r for r in row["roles"].split(";") if r}
                unknown = roles - set(C.ROLE_IDS)
                if unknown:
                    raise ValueError(f"{file.name}: unknown role id(s) {sorted(unknown)}")
                out.setdefault(row["clip_id"], {})[row["rater"]] = {
                    "roles": roles, "best_role": row["best_role"], "unusable": row["unusable"] == "1"}
    return out


def append_label(rater: str, clip_id: str, roles: list[str], best_role: str, unusable: bool,
                 labeled_at: str, labels_dir: Path = LABELS_DIR) -> None:
    Path(labels_dir).mkdir(parents=True, exist_ok=True)
    file = Path(labels_dir) / f"labels_{slugify(rater)}.csv"
    is_new = not file.is_file()
    with open(file, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LABEL_FIELDS)
        if is_new:
            w.writeheader()
        w.writerow({"clip_id": clip_id, "rater": slugify(rater), "roles": ";".join(roles),
                    "best_role": best_role, "unusable": "1" if unusable else "0", "labeled_at": labeled_at})


def aggregate_labels(labels: dict) -> dict:
    """Combine raters into one target per clip.

    A role counts as ACCEPTABLE for a clip when at least half of the raters who judged the
    clip ticked it. Clips that at least half of their raters marked unusable are dropped.
    Returns {clip_id: {"y": 0/1 array[10], "votes": fraction array[10], "n_raters": int}}.
    """
    out = {}
    for clip_id, by_rater in labels.items():
        n = len(by_rater)
        if sum(v["unusable"] for v in by_rater.values()) * 2 >= n:
            continue
        usable = [v for v in by_rater.values() if not v["unusable"]]
        votes = np.array([sum(r in v["roles"] for v in usable) for r in C.ROLE_IDS], dtype=float) / len(usable)
        y = (votes >= 0.5).astype(int)
        if y.sum() == 0:
            continue
        out[clip_id] = {"y": y, "votes": votes, "n_raters": len(usable)}
    return out


def rater_agreement(labels: dict) -> dict:
    """How much do two humans agree? This is the ceiling any model should be judged against."""
    jaccards, shared = [], []
    for by_rater in labels.values():
        sets = [v["roles"] for v in by_rater.values() if not v["unusable"] and v["roles"]]
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                jaccards.append(len(sets[i] & sets[j]) / len(sets[i] | sets[j]))
                shared.append(bool(sets[i] & sets[j]))
    if not jaccards:
        return {"n_pairs": 0}
    return {"n_pairs": len(jaccards), "mean_jaccard": float(np.mean(jaccards)),
            "share_at_least_one_role": float(np.mean(shared))}


# ----------------------------------------------------------------------------- features
def load_features(path: Path = FEATURES_NPZ) -> dict:
    if not Path(path).is_file():
        raise FileNotFoundError(f"{path} not found. Run: python scripts/extract_features.py")
    with np.load(path, allow_pickle=False) as z:
        feats = {k: z[k] for k in z.files}
    version = str(feats["preprocess_version"])
    if version != C.PREPROCESS_VERSION:
        raise RuntimeError(f"Features were extracted with preprocessing {version}, the code is now "
                           f"{C.PREPROCESS_VERSION}. Re-run scripts/extract_features.py")
    return feats
