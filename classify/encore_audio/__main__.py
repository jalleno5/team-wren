# Written by Encore_YAMNet.ipynb. Edit the code in the notebook, not in this file.
"""Command line use:  python -m encore_audio path/to/clip.m4a [more files ...]"""
import json
import os
import sys

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")  # hide TensorFlow's startup chatter

from .classify import classify_audio_file  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    for path in sys.argv[1:]:
        print(json.dumps(classify_audio_file(path), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
