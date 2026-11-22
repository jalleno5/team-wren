# Written by Encore_YAMNet.ipynb. Edit the code in the notebook, not in this file.
"""The public entry point: classify_audio_file(audio_path) -> JSON-serialisable dict.

Pipeline for one file:

    load_audio()            decode, validate, trim, normalise           (audio_io.py)
    run_yamnet()            521 class scores + 1024-d embedding / frame (yamnet_model.py)
    compute_descriptors()   duration, attack, brightness, pitch, ...    (descriptors.py)
    role scores             learned model if one is installed,          (role_model.py)
                            otherwise the acoustic prior                (role_prior.py)

`analyze_audio_file` does the first three steps and is also what the training scripts call,
so training and inference cannot drift apart.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import config as C
from .audio_io import AudioRejected, PreparedAudio, load_audio
from .descriptors import compute_descriptors
from .role_model import load_role_model
from .role_prior import describe_character, prior_scores
from .yamnet_model import YAMNET_HANDLE, class_names, load_yamnet, run_yamnet

FLAG_MESSAGES = {
    "low_label_confidence": "YAMNet is not confident about any sound label. Treat the labels as guesses.",
    "weak_role_evidence": "No role fits this sound clearly. The suggestions are weak guesses.",
    "clipped": "The recording is clipped (too loud for the microphone). Results may be off.",
    "steady_or_noisy": "Little difference between loud and quiet parts: either a continuous sound "
                       "or strong background noise. The two cannot be told apart from one recording.",
    "truncated": f"Only the first {C.MAX_ANALYSIS_SECONDS:.0f} seconds were analysed.",
    "short_for_yamnet": "The sound is much shorter than YAMNet's 0.96 s window, so sound labels "
                        "are less reliable. Role suggestions are less affected.",
}
REVIEW_FLAGS = {"low_label_confidence", "weak_role_evidence", "clipped", "steady_or_noisy"}


@dataclass
class Analysis:
    prepared: PreparedAudio
    scores_mean: np.ndarray      # [521] YAMNet class scores averaged over frames
    embedding_mean: np.ndarray   # [1024] YAMNet embeddings averaged over frames
    n_frames: int
    descriptors: dict


def warm_up() -> None:
    """Load YAMNet now (takes a few seconds). Call once at backend start-up so the first
    user request is not slow."""
    load_yamnet()


def analyze_audio_file(audio_path: str | Path) -> Analysis:
    """Shared front half of the pipeline. Raises AudioRejected for unusable files."""
    prepared = load_audio(audio_path)
    scores, embeddings = run_yamnet(prepared.yamnet_input)
    return Analysis(
        prepared=prepared,
        scores_mean=scores.mean(axis=0),
        embedding_mean=embeddings.mean(axis=0),
        n_frames=int(scores.shape[0]),
        descriptors=compute_descriptors(prepared.active),
    )


def score_roles(embedding_mean: np.ndarray, descriptors: dict, method: str | None = None):
    """Scores for all five roles.

    Returns (scores, sources, method_info). When a trained role model is installed it scores
    the roles it was trained on; any role it could not be trained on (too few labelled
    examples) is scored by the acoustic prior, and `sources` says which is which.
    """
    method = method or os.environ.get("ENCORE_ROLE_METHOD", "auto")
    scores = prior_scores(descriptors)
    sources = {r: "acoustic_prior" for r in C.ROLE_IDS}
    info = {"roles": "acoustic-prior-v0", "role_model": None,
            "role_score_meaning": "heuristic fit score in [0, 1], not a probability"}
    if method == "prior":
        info["role_model_note"] = "learned model disabled (ENCORE_ROLE_METHOD=prior)"
        return scores, sources, info
    model, reason = load_role_model()
    if model is None:
        info["role_model_note"] = reason
        return scores, sources, info
    for role, p in model.predict(embedding_mean, descriptors).items():
        scores[role], sources[role] = p, "learned"
    meta = model.meta
    info.update(
        roles="learned-logreg-v1" + (" + acoustic-prior fallback" if len(model.role_ids) < len(C.ROLE_IDS) else ""),
        role_model={k: meta.get(k) for k in ("trained_at", "feature_set", "role_ids", "n_clips",
                                             "n_groups", "n_raters", "evaluation")},
        role_score_meaning="learned roles: model score in [0, 1] (uncalibrated); "
                           "acoustic_prior roles: heuristic fit score",
    )
    return scores, sources, info


def _strength(score: float) -> str:
    """Plain-word reading of a role score, so the UI does not have to invent thresholds."""
    if score >= C.STRONG_ROLE_SCORE:
        return "strong"
    return "moderate" if score >= C.WEAK_ROLE_SCORE else "weak"


def _roles_block(scores: dict | None, sources: dict | None, top_k: int):
    order = sorted(C.ROLE_IDS, key=lambda r: -scores[r]) if scores else []
    suggested = order[:top_k]
    all_roles = [{
        "role_id": r, "role": C.ROLE_NAMES[r], "description": C.ROLE_DESCRIPTIONS[r],
        "score": round(scores[r], 4) if scores else None,
        "strength": _strength(scores[r]) if scores else None,
        "source": sources[r] if sources else None,
        "suggested": r in suggested,
    } for r in C.ROLE_IDS]
    suggestions = [{"rank": i + 1, "role_id": r, "role": C.ROLE_NAMES[r],
                    "score": round(scores[r], 4), "strength": _strength(scores[r]),
                    "source": sources[r]}
                   for i, r in enumerate(suggested)]
    return suggestions, all_roles


def _method_block(extra: dict | None = None) -> dict:
    block = {
        "encore_version": C.VERSION,
        "preprocess_version": C.PREPROCESS_VERSION,
        "sound_labels": f"yamnet ({YAMNET_HANDLE}), mean class score over 0.96 s frames",
        "sound_label_score_meaning": "YAMNet sigmoid score in [0, 1] per class; scores do not sum to 1",
    }
    block.update(extra or {})
    return block


def classify_audio_file(audio_path: str | Path, top_k_labels: int = 5, top_k_roles: int = 2) -> dict:
    """Classify one audio file. Always returns a JSON-serialisable dict and never raises for
    a bad recording: check result["status"].

    status == "ok"        labels and roles are filled in; see result["review"] for caveats
    status == "rejected"  the file could not be analysed; see result["error"]. `all_roles`
                          is still present so the UI can let the user pick a role by hand.
    """
    try:
        analysis = analyze_audio_file(audio_path)
    except AudioRejected as rej:
        _, all_roles = _roles_block(None, None, top_k_roles)
        return {
            "status": "rejected",
            "error": {"code": rej.code, "message": rej.message},
            "sound_labels": [], "role_suggestions": [], "all_roles": all_roles,
            "sound_character": [],
            "review": {"needs_review": True, "flags": [rej.code], "messages": [rej.message]},
            "audio": None, "descriptors": None,
            "method": _method_block(),
        }

    names = class_names()
    top = np.argsort(analysis.scores_mean)[::-1][:top_k_labels]
    sound_labels = [{"rank": i + 1, "label": names[int(k)], "class_index": int(k),
                     "score": round(float(analysis.scores_mean[k]), 4)} for i, k in enumerate(top)]

    scores, sources, role_info = score_roles(analysis.embedding_mean, analysis.descriptors)
    suggestions, all_roles = _roles_block(scores, sources, top_k_roles)

    flags = list(analysis.prepared.flags)
    if sound_labels[0]["score"] < C.LOW_LABEL_SCORE:
        flags.append("low_label_confidence")
    if suggestions[0]["score"] < C.WEAK_ROLE_SCORE:
        flags.append("weak_role_evidence")
    if analysis.prepared.info["analysed_duration_s"] < 0.5:
        flags.append("short_for_yamnet")

    audio = dict(analysis.prepared.info, yamnet_frames=analysis.n_frames)
    return {
        "status": "ok",
        "error": None,
        "sound_labels": sound_labels,
        "role_suggestions": suggestions,
        "all_roles": all_roles,
        "sound_character": describe_character(analysis.descriptors),
        "review": {
            "needs_review": bool(REVIEW_FLAGS & set(flags)),
            "flags": flags,
            "messages": [FLAG_MESSAGES[f] for f in flags],
        },
        "audio": audio,
        "descriptors": {k: round(v, 4) for k, v in analysis.descriptors.items()},
        "method": _method_block(role_info),
    }
