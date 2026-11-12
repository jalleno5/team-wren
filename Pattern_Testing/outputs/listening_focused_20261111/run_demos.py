"""Two sample-aware prompt experiments, with explicit requested BPMs."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs"))
from artifact_paths import write_report
os.environ["HF_HOME"] = str(ROOT / "outputs/.model_cache/huggingface")
os.environ["MT3_CHECKPOINT_DIR"] = str(ROOT / "outputs/.model_cache/mt3")
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["OMP_NUM_THREADS"] = "8"
os.environ["PYTHONUNBUFFERED"] = "1"

import mido
import numpy as np
import soundfile as sf
from pipeline import inspect_midi
from Apply_Sounds.yamnet_mapping import build_sound_mapping
from Apply_Sounds.render_midi_sounds import apply_sounds, extract_notes

EXPERIMENTS = {
    "minimal_house_110": {
        "bpm": 110, "seed": 243,
        "prompt": "Minimal house groove at 110 BPM with a clear glockenspiel melody, deep fingered electric bass, steady bass drum, woodblock percussion and hand claps. Clean dry sound, sparse arrangement.",
    },
    "latin_bossa_90": {
        "bpm": 90, "seed": 242,
        "prompt": "Sparse relaxed Latin bossa nova instrumental at exactly 90 BPM in steady 4/4 time. Prominent playful marimba melody with occasional glockenspiel notes, warm fingered electric bass playing a simple syncopated bass line, dry woodblock rhythm, soft hand claps and finger snaps, gentle bass drum. Exclusive instrumentation: marimba, glockenspiel, electric bass, woodblock, hand claps, finger snaps, bass drum. Short distinct notes, spacious arrangement, clean dry studio recording.",
    },
}
EVERYDAY = [
    {"file": "door_knock.wav", "yamnet_class": "Knock"},
    {"file": "finger_snap.wav", "yamnet_class": "Finger snapping"},
    {"file": "hand_clap.wav", "yamnet_class": "Clapping"},
    {"file": "switch_click.wav", "yamnet_class": "Clicking"},
    {"file": "glass_clink.wav", "yamnet_class": "Chink, clink", "root_note": 84},
    {"file": "water_drop.wav", "yamnet_class": "Drip"},
]
MIXED = EVERYDAY + [
    {"file": "kick.wav", "yamnet_class": "Bass drum"},
    {"file": "bass.wav", "yamnet_class": "Bass guitar", "root_note": 60, "loop": True},
]


def save(path, data):
    write_report(path, data)


def command(args, log):
    with log.open("w", encoding="utf-8") as stream:
        subprocess.run([sys.executable, "-u", *map(str, args)], cwd=ROOT,
                       stdout=stream, stderr=subprocess.STDOUT, check=True)


def main():
    session = {}
    for genre, spec in EXPERIMENTS.items():
        folder = BASE / genre
        folder.mkdir(exist_ok=True)
        result = dict(spec, duration_requested=16, model="facebook/musicgen-small")
        started = time.monotonic()
        try:
            audio, midi = folder / "original.wav", folder / "transcribed.mid"
            if not audio.exists():
                print(f"{genre}: generating 16 seconds", flush=True)
                command([ROOT / "Music_Gen/musicgen_large_generator.py", "--prompt", spec["prompt"],
                         "--duration", 16, "--model", "facebook/musicgen-small", "--seed", spec["seed"],
                         "--output", audio], folder / "generation.log")
            if not midi.exists():
                print(f"{genre}: transcribing", flush=True)
                command([ROOT / "transcribe.py", audio, "--output", midi], folder / "transcription.log")
            result["midi"] = inspect_midi(midi)
            for variant, sounds in [("everyday", EVERYDAY), ("mixed", MIXED)]:
                print(f"{genre}: rendering {variant}", flush=True)
                mapping = build_sound_mapping(sounds, midi)
                save(folder / f"{variant}_mapping.json", mapping)
                result[variant] = apply_sounds(midi, mapping["mapping"], folder / f"{variant}.wav", sounds_dir=ROOT / "Sounds")
                counts = Counter()
                for start, duration, note, velocity, program, drum in extract_notes(mido.MidiFile(midi)):
                    entry = mapping["mapping"]["drums" if drum else "programs"].get(str(note if drum else program))
                    if entry:
                        counts[entry["file"]] += 1
                result[variant]["sample_note_counts"] = dict(counts)
            for variant in ["original", "everyday", "mixed"]:
                data, rate = sf.read(folder / f"{variant}.wav")
                assert np.isfinite(data).all() and np.abs(data).max() > 0
            result["status"] = "completed"
        except Exception as error:
            result.update(status="failed", error=str(error))
            print(f"{genre}: FAILED {error}", flush=True)
        result["elapsed_seconds"] = round(time.monotonic() - started, 2)
        save(folder / "result.json", result)
        session[genre] = result
        save(BASE / "session.json", session)
    print(json.dumps({genre: row["status"] for genre, row in session.items()}), flush=True)


if __name__ == "__main__":
    main()
