# Written by Encore_YAMNet.ipynb. Edit the code in the notebook, not in this file.
"""Fitting and scoring the learned role model. Used by BOTH scripts/evaluate_roles.py and
scripts/train_roles.py, so the thing that gets evaluated is exactly the thing that ships.

Model: for each role, an L2-regularised logistic regression answering "is this role
acceptable for this clip?", on standardised features. Hyperparameters are fixed in advance
(C = 0.1, balanced class weights) and deliberately NOT tuned: with a few hundred clips,
tuning would mostly fit noise and inflate the reported numbers.

A role is only trained when it has at least MIN_POSITIVES acceptable clips (and as many
non-acceptable ones). Roles below that are left to the acoustic prior.

Feature set "emb+desc" is a LATE FUSION: one regression is trained on the 1024 embedding
dimensions and a separate one on the 19 descriptors, and their logits are averaged. Simply
concatenating the two would let 1024 embedding dimensions drown out 19 descriptors under a
shared L2 penalty. Averaging two linear models is itself a linear model on the concatenated
features (each block's weights halved), so the saved file format is the same for all sets.
"""
from __future__ import annotations

from math import comb

import numpy as np

from . import config as C
from .role_model import RoleModel, build_feature_vector  # noqa: F401  (re-exported for scripts)

MIN_POSITIVES = 5
REGULARISATION_C = 0.1


def fit_role_weights(X: np.ndarray, Y: np.ndarray, feature_set: str) -> RoleModel | None:
    """X: [n, d] features, Y: [n, R] 0/1 acceptable roles (columns in C.ROLE_IDS order)."""
    from sklearn.linear_model import LogisticRegression

    n = X.shape[0]
    covered = [j for j in range(len(C.ROLE_IDS)) if MIN_POSITIVES <= Y[:, j].sum() <= n - MIN_POSITIVES]
    if not covered:
        return None
    mean = X.mean(axis=0)
    scale = X.std(axis=0)
    scale[scale < 1e-6] = 1.0
    Z = (X - mean) / scale
    # column blocks that get their own independently trained regression
    blocks = [slice(0, 1024), slice(1024, X.shape[1])] if feature_set == "emb+desc" else [slice(0, X.shape[1])]
    coef = np.zeros((len(covered), X.shape[1]))
    intercept = np.zeros(len(covered))
    for row, j in enumerate(covered):
        for block in blocks:
            lr = LogisticRegression(C=REGULARISATION_C, class_weight="balanced", max_iter=5000)
            lr.fit(Z[:, block], Y[:, j])
            coef[row, block] = lr.coef_[0] / len(blocks)
            intercept[row] += lr.intercept_[0] / len(blocks)
    meta = {"role_ids": [C.ROLE_IDS[j] for j in covered], "feature_set": feature_set}
    return RoleModel(mean, scale, coef, intercept, meta)


def model_scores(model: RoleModel | None, X: np.ndarray, prior: np.ndarray) -> np.ndarray:
    """Scores [n, 10] exactly as inference combines them: learned where the model covers a
    role, acoustic prior elsewhere."""
    scores = prior.astype(np.float64).copy()
    if model is None:
        return scores
    Z = (X - model.mean) / model.scale
    probs = 1.0 / (1.0 + np.exp(-np.clip(Z @ model.coef.T + model.intercept, -30, 30)))
    for k, role in enumerate(model.role_ids):
        scores[:, C.ROLE_IDS.index(role)] = probs[:, k]
    return scores


# ----------------------------------------------------------------------------- metrics
def per_clip_metrics(scores: np.ndarray, Y: np.ndarray, k: int = 2) -> dict:
    """One value per clip for each metric.

    hit@k        1 if at least one of the top-k suggestions is acceptable
    precision@k  fraction of the top-k suggestions that are acceptable
    recall@k     fraction of the acceptable roles found in the top k (capped at k)
    top1         1 if the first suggestion is acceptable
    ap           average precision of the full ranking (1.0 = all acceptable roles on top)
    """
    order = np.argsort(-scores, axis=1, kind="stable")
    ranked = np.take_along_axis(Y, order, axis=1).astype(float)   # acceptability by rank
    n_pos = Y.sum(axis=1)
    topk = ranked[:, :k].sum(axis=1)
    precision_at_rank = np.cumsum(ranked, axis=1) / np.arange(1, Y.shape[1] + 1)
    return {
        f"hit@{k}": (topk > 0).astype(float),
        f"precision@{k}": topk / k,
        f"recall@{k}": topk / np.minimum(n_pos, k),
        "top1": ranked[:, 0],
        "ap": (precision_at_rank * ranked).sum(axis=1) / n_pos,
    }


def chance_metrics(Y: np.ndarray, k: int = 2) -> dict:
    """What a uniformly random ranking would score in expectation, per clip. Essential
    context: if raters tick two roles per clip out of five, random guessing already gets hit@2 = 0.60."""
    r = Y.shape[1]
    n_pos = Y.sum(axis=1)
    hit = np.array([1 - comb(r - int(p), k) / comb(r, k) for p in n_pos])
    return {f"hit@{k}": hit, f"precision@{k}": n_pos / r, f"recall@{k}": (k * n_pos / r) / np.minimum(n_pos, k),
            "top1": n_pos / r, "ap": np.full(len(n_pos), np.nan)}


def cluster_bootstrap_ci(values: np.ndarray, groups: np.ndarray, n_boot: int = 2000, seed: int = 0):
    """Mean and 95 % interval, resampling whole groups (sound categories) rather than clips,
    because clips of one category are not independent."""
    rng = np.random.default_rng(seed)
    uniq = np.unique(groups)
    sums = np.array([values[groups == g].sum() for g in uniq])
    counts = np.array([(groups == g).sum() for g in uniq])
    idx = rng.integers(0, len(uniq), size=(n_boot, len(uniq)))
    boots = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    return float(values.mean()), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))
