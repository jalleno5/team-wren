# Written by Encore_YAMNet.ipynb. Edit the code in the notebook, not in this file.
"""Loading and running Google's pretrained YAMNet.

The model is the official TF2 SavedModel published as `google/yamnet/1`. It is downloaded
once into `models/yamnet/` and loaded from disk with plain `tf.saved_model.load`, so:

  * there is no dependency on the `tensorflow_hub` package (its current release fails to
    import on new setuptools versions because it still uses `pkg_resources`),
  * nothing is cached in /tmp (which Fedora wipes on reboot),
  * after the first download the project runs fully offline.

YAMNet takes a 16 kHz mono waveform and slides a 0.96 s window over it every 0.48 s.
For each window ("frame") it returns:
  scores      521 values, one per AudioSet class (independent sigmoids, NOT a softmax)
  embeddings  1024 values: the layer just before the classifier
"""
from __future__ import annotations

import csv
import shutil
import tarfile
import tempfile
import threading
import urllib.request
from pathlib import Path

import numpy as np

from . import config as C

YAMNET_HANDLE = "google/yamnet/1"
# Tried in order. All three serve the same official archive.
DOWNLOAD_URLS = [
    "https://tfhub.dev/google/yamnet/1?tf-hub-format=compressed",
    "https://storage.googleapis.com/tfhub-modules/google/yamnet/1.tar.gz",
    "https://www.kaggle.com/api/v1/models/google/yamnet/tensorFlow2/yamnet/1/download",
]

_lock = threading.Lock()
_model = None
_class_names: list[str] | None = None


def yamnet_is_downloaded(dest: Path | None = None) -> bool:
    dest = Path(dest or C.YAMNET_DIR)
    return (dest / "saved_model.pb").is_file() and (dest / "variables").is_dir()


def download_yamnet(dest: Path | None = None, verbose: bool = True) -> Path:
    """Download and unpack the YAMNet SavedModel into `dest` (default: models/yamnet)."""
    dest = Path(dest or C.YAMNET_DIR)
    if yamnet_is_downloaded(dest):
        return dest
    errors = []
    for url in DOWNLOAD_URLS:
        tmpdir = Path(tempfile.mkdtemp(prefix="yamnet_dl_"))
        try:
            if verbose:
                print(f"Downloading YAMNet from {url} ...")
            archive = tmpdir / "yamnet.tar.gz"
            req = urllib.request.Request(url, headers={"User-Agent": "encore-yamnet/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp, open(archive, "wb") as out:
                shutil.copyfileobj(resp, out)
            unpacked = tmpdir / "unpacked"
            unpacked.mkdir()
            with tarfile.open(archive) as tar:
                tar.extractall(unpacked, filter="data")  # "data" filter blocks path tricks
            # The archive root is the SavedModel itself; tolerate one level of nesting.
            roots = [p.parent for p in unpacked.rglob("saved_model.pb")]
            if not roots:
                raise RuntimeError("archive did not contain saved_model.pb")
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                shutil.rmtree(dest)
            shutil.move(str(roots[0]), str(dest))
            if verbose:
                print(f"YAMNet saved to {dest}")
            return dest
        except Exception as exc:  # try the next mirror
            errors.append(f"  {url}\n    -> {type(exc).__name__}: {exc}")
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    raise RuntimeError(
        "Could not download YAMNet. Tried:\n" + "\n".join(errors) + "\n\n"
        "Manual fix: download the TensorFlow 2 version of google/yamnet from "
        "https://www.kaggle.com/models/google/yamnet , unpack it, and place the folder that "
        f"contains saved_model.pb at:\n  {dest}"
    )


def load_yamnet():
    """Load the model once per process (thread-safe). Returns (model, class_names)."""
    global _model, _class_names
    if _model is not None:
        return _model, _class_names
    with _lock:
        if _model is not None:
            return _model, _class_names
        path = download_yamnet(verbose=True)
        import tensorflow as tf  # imported lazily: it takes a few seconds

        model = tf.saved_model.load(str(path))
        class_map = model.class_map_path().numpy().decode("utf-8")
        with open(class_map, newline="", encoding="utf-8") as f:
            names = [row["display_name"] for row in csv.DictReader(f)]
        if len(names) != 521:
            raise RuntimeError(f"Expected 521 YAMNet classes, found {len(names)}.")
        _model, _class_names = model, names
    return _model, _class_names


def class_names() -> list[str]:
    return load_yamnet()[1]


def run_yamnet(waveform: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Run YAMNet on a 16 kHz mono float32 waveform in [-1, 1].

    Returns (scores [n_frames, 521], embeddings [n_frames, 1024]).
    """
    model, _ = load_yamnet()
    out = model(np.asarray(waveform, dtype=np.float32))
    if isinstance(out, dict):
        # Models exported with the current version of Google's export script return a dict.
        scores, embeddings = out["predictions"], out["embeddings"]
    else:
        # The published google/yamnet/1 returns (scores, embeddings, log_mel_spectrogram).
        scores, embeddings = out[0], out[1]
    scores, embeddings = scores.numpy(), embeddings.numpy()
    if scores.ndim != 2 or scores.shape[1] != 521 or embeddings.shape[1] != 1024:
        raise RuntimeError(f"Unexpected YAMNet output shapes {scores.shape}, {embeddings.shape}.")
    return scores, embeddings
