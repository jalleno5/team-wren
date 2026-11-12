"""Two short MusicGen -> YourMT3 trap attempts, with portable review reports."""
import json
import os
from pathlib import Path
import subprocess
import sys
from collections import Counter

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs"))
from artifact_paths import write_report

os.environ.update(HF_HOME=str(ROOT / "outputs/.model_cache/huggingface"),
                  MT3_CHECKPOINT_DIR=str(ROOT / "outputs/.model_cache/mt3"),
                  HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", OMP_NUM_THREADS="8",
                  PYTHONUNBUFFERED="1", PYTHONDONTWRITEBYTECODE="1")

import mido
import numpy as np
import soundfile as sf
from Apply_Sounds.render_midi_sounds import apply_sounds, extract_notes

PROMPT = "A simple trap instrumental at 90 BPM, punchy kick, crisp snare, ticking hi-hats, deep sub bass and a sparse bell melody. Clean dry recording."


def run(args, log):
    with log.open("w", encoding="utf-8") as stream:
        subprocess.run([sys.executable, "-u", *map(str, args)], cwd=ROOT,
                       stdout=stream, stderr=subprocess.STDOUT, check=True)


def mappings(notes):
    programs = {n[4] for n in notes if not n[5]}
    pitches = {n[2] for n in notes if n[5]}
    everyday, mixed = {"programs": {}, "drums": {}}, {"programs": {}, "drums": {}}
    for program in sorted(programs):
        everyday["programs"][str(program)] = {"file": "glass_clink.wav", "root_note": 84, "loop": False}
        mixed["programs"][str(program)] = ({"file": "bass.wav", "root_note": 29, "loop": True}
                                            if 32 <= program <= 39 or program == 43 else
                                            {"file": "glass_clink.wav", "root_note": 84, "loop": False})
    for pitch in sorted(pitches):
        if pitch in {35, 36, 41, 43, 45, 47, 48, 50, 60, 61, 62, 63, 64}:
            a, b = "door_knock.wav", "kick.wav"
        elif pitch in {38, 39, 40}:
            a = b = "hand_clap.wav"
        elif pitch in {37, 75, 76, 77}:
            a = b = "switch_click.wav"
        elif pitch in {49, 51, 52, 53, 55, 56, 57, 59, 80, 81}:
            a = b = "glass_clink.wav"
        else:
            # Use a short transient for hats/shakers instead of a 1.1 s paper hit.
            a = b = "finger_snap.wav"
        everyday["drums"][str(pitch)] = a
        mixed["drums"][str(pitch)] = b
    return {"everyday": everyday, "mixed": mixed}


def main():
    summaries = []
    for seed in [501, 502]:
        folder = OUT / f"take_{seed}"
        folder.mkdir(exist_ok=True)
        result = {"prompt": PROMPT, "seed": seed, "requested_bpm": 90,
                  "requested_seconds": 12, "model": "facebook/musicgen-small", "transcriber": "YourMT3+"}
        try:
            audio, midi = folder / "original.wav", folder / "transcribed.mid"
            if not audio.exists():
                print(f"Take {seed}: generating", flush=True)
                run([ROOT / "Music_Gen/musicgen_large_generator.py", "--prompt", PROMPT,
                     "--model", "facebook/musicgen-small", "--duration", 12,
                     "--seed", seed, "--output", audio], folder / "generation.log")
            if not midi.exists():
                print(f"Take {seed}: transcribing", flush=True)
                run([ROOT / "transcribe.py", audio, "--output", midi], folder / "transcription.log")
            notes = extract_notes(mido.MidiFile(midi))
            if not notes:
                raise ValueError("No MIDI notes recovered")
            duration = sf.info(audio).duration
            bins = sorted({int(n[0]) for n in notes})
            result["midi"] = {"notes": len(notes), "drum_notes": sum(n[5] for n in notes),
                              "melodic_notes": sum(not n[5] for n in notes),
                              "programs": sorted({n[4] for n in notes if not n[5]}),
                              "drums": sorted({n[2] for n in notes if n[5]}),
                              "seconds_with_note_onsets": bins,
                              "onset_bin_coverage": round(len(bins) / np.ceil(duration), 3)}
            for variant, mapping in mappings(notes).items():
                write_report(folder / f"{variant}_mapping.json", mapping)
                print(f"Take {seed}: rendering {variant}", flush=True)
                result[variant] = apply_sounds(midi, mapping, folder / f"{variant}.wav", sounds_dir=ROOT / "Sounds")
                counts = Counter()
                for n in notes:
                    entry = mapping["drums" if n[5] else "programs"][str(n[2] if n[5] else n[4])]
                    counts[entry if isinstance(entry, str) else entry["file"]] += 1
                result[variant]["sample_note_counts"] = dict(counts)
                waveform, rate = sf.read(folder / f"{variant}.wav")
                assert np.isfinite(waveform).all() and np.abs(waveform).max() > 0
            result["status"] = "completed"
            print(f"Take {seed}: {result['midi']}", flush=True)
        except Exception as exc:
            result.update(status="failed", error=type(exc).__name__)
            print(f"Take {seed} failed; see local log", flush=True)
        write_report(folder / "result.json", result)
        summaries.append(result)
        write_report(OUT / "session.json", summaries)
    print("Finished both attempts", flush=True)


if __name__ == "__main__":
    main()
