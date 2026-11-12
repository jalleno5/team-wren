"""Estimate source tempo independently of the requested text and MIDI metadata."""
import json
import os
from pathlib import Path

os.environ.setdefault("NUMBA_NUM_THREADS", "4")
import librosa
import mido
import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parent
summary = {}
for folder in ROOT.iterdir():
    if not folder.is_dir() or not (folder / "original.wav").exists():
        continue
    result = json.loads((folder / "result.json").read_text())
    audio, rate = sf.read(folder / "original.wav", dtype="float32", always_2d=True)
    waveform = librosa.resample(audio.mean(axis=1), orig_sr=rate, target_sr=22050)
    tempo, beats = librosa.beat.beat_track(y=waveform, sr=22050, hop_length=256, trim=False)
    estimated = float(np.asarray(tempo).reshape(-1)[0])
    tempos = sorted({round(mido.tempo2bpm(msg.tempo), 2) for track in mido.MidiFile(folder / "transcribed.mid").tracks
                     for msg in track if msg.type == "set_tempo"})
    summary[folder.name] = {"requested_bpm": result["bpm"], "estimated_audio_bpm": round(estimated, 2),
                            "detected_beats": len(beats), "midi_tempo_metadata_bpm": tempos,
                            "method": "librosa beat_track on original audio; no target BPM supplied",
                            "note": "Short-clip estimate; half/double-tempo ambiguity is possible. Audio/MIDI were not retimed."}
    print(folder.name, summary[folder.name], flush=True)
(ROOT / "tempo_analysis.json").write_text(json.dumps(summary, indent=2) + "\n")
