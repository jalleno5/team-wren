# Written by Encore_YAMNet.ipynb. Edit the code in the notebook, not in this file.
"""The learned role model: file format, feature vector, loading and prediction.

The model is ten independent logistic regressions (one "is this role suitable?" question
per role) on top of frozen YAMNet embeddings plus the acoustic descriptors. That is small
enough to store as plain arrays:

    models/role_model.npz    mean, scale, coef, intercept     (numpy, no pickle)
    models/role_model.json   which roles, which features, versions, training summary

Prediction is three lines of numpy, so the backend needs neither scikit-learn nor the
training data:

    z = (x - mean) / scale
    logits = z @ coef.T + intercept
    probability = 1 / (1 + exp(-logits))
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from . import config as C
from .descriptors import DESCRIPTOR_VECTOR_NAMES, descriptor_vector

FEATURE_SETS = ("emb", "desc", "emb+desc")
FORMAT_VERSION = 1


def build_feature_vector(embedding_mean: np.ndarray, descriptors: dict, feature_set: str) -> np.ndarray:
    """The model input for one clip.

    embedding_mean: YAMNet's 1024-d embeddings averaged over the clip's frames.
    """
    if feature_set == "emb":
        return np.asarray(embedding_mean, dtype=np.float32)
    if feature_set == "desc":
        return descriptor_vector(descriptors)
    if feature_set == "emb+desc":
        return np.concatenate([np.asarray(embedding_mean, dtype=np.float32), descriptor_vector(descriptors)])
    raise ValueError(f"Unknown feature set {feature_set!r}. Use one of {FEATURE_SETS}.")


def feature_dim(feature_set: str) -> int:
    return {"emb": 1024, "desc": len(DESCRIPTOR_VECTOR_NAMES),
            "emb+desc": 1024 + len(DESCRIPTOR_VECTOR_NAMES)}[feature_set]


class RoleModel:
    def __init__(self, mean, scale, coef, intercept, meta: dict):
        self.mean, self.scale, self.coef, self.intercept = mean, scale, coef, intercept
        self.meta = meta
        self.role_ids: list[str] = meta["role_ids"]       # roles this model can score
        self.feature_set: str = meta["feature_set"]

    def predict(self, embedding_mean: np.ndarray, descriptors: dict) -> dict:
        """Probability-like score per covered role."""
        x = build_feature_vector(embedding_mean, descriptors, self.feature_set).astype(np.float64)
        z = (x - self.mean) / self.scale
        logits = z @ self.coef.T + self.intercept
        probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -30, 30)))
        return {role: float(p) for role, p in zip(self.role_ids, probs)}


def save_role_model(mean, scale, coef, intercept, meta: dict,
                    npz_path: Path = None, json_path: Path = None) -> None:
    npz_path = Path(npz_path or C.ROLE_MODEL_NPZ)
    json_path = Path(json_path or C.ROLE_MODEL_JSON)
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    meta = dict(meta, format_version=FORMAT_VERSION, preprocess_version=C.PREPROCESS_VERSION,
                encore_version=C.VERSION, all_role_ids=C.ROLE_IDS)
    np.savez(npz_path, mean=np.asarray(mean, np.float64), scale=np.asarray(scale, np.float64),
             coef=np.asarray(coef, np.float64), intercept=np.asarray(intercept, np.float64))
    json_path.write_text(json.dumps(meta, indent=2))


_cache: dict = {}


def load_role_model(npz_path: Path = None, json_path: Path = None):
    """Returns (RoleModel or None, reason). None means "use the acoustic prior"; `reason`
    says why, so the output can be honest about which method produced the suggestions."""
    npz_path = Path(npz_path or C.ROLE_MODEL_NPZ)
    json_path = Path(json_path or C.ROLE_MODEL_JSON)
    if not (npz_path.is_file() and json_path.is_file()):
        return None, "no trained role model found"
    key = (str(npz_path), npz_path.stat().st_mtime_ns, json_path.stat().st_mtime_ns)
    if key in _cache:
        return _cache[key]
    try:
        meta = json.loads(json_path.read_text())
        if meta.get("format_version") != FORMAT_VERSION:
            result = (None, "role model file format is not supported by this code version")
        elif meta.get("preprocess_version") != C.PREPROCESS_VERSION:
            result = (None, "role model was trained with different preprocessing; retrain it")
        elif not set(meta["role_ids"]) <= set(C.ROLE_IDS):
            result = (None, "role model contains unknown roles")
        else:
            with np.load(npz_path, allow_pickle=False) as z:
                arrays = [z["mean"], z["scale"], z["coef"], z["intercept"]]
            dim = feature_dim(meta["feature_set"])
            if arrays[0].shape != (dim,) or arrays[2].shape != (len(meta["role_ids"]), dim):
                result = (None, "role model arrays have the wrong shape")
            else:
                result = (RoleModel(*arrays, meta), "ok")
    except Exception as exc:
        result = (None, f"role model could not be loaded ({type(exc).__name__}: {exc})")
    _cache.clear()
    _cache[key] = result
    return result
