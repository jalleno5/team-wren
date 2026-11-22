# Written by Encore_YAMNet.ipynb. Edit the code in the notebook, not in this file.
"""Encore audio classification: YAMNet sound labels + musical-role suggestions.

Backend usage:

    from encore_audio import classify_audio_file, warm_up
    warm_up()                                   # once, at start-up
    result = classify_audio_file("clip.m4a")    # JSON-serialisable dict
"""
from .classify import analyze_audio_file, classify_audio_file, warm_up
from .config import ROLE_IDS, ROLES, VERSION

__all__ = ["classify_audio_file", "analyze_audio_file", "warm_up", "ROLES", "ROLE_IDS", "VERSION"]
__version__ = VERSION
