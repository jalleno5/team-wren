"""Local listening experiment: four prompts, original + two sound mappings."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs"))
from artifact_paths import write_report
os.environ.setdefault("HF_HOME", str(ROOT / "outputs/.model_cache/huggingface"))
os.environ.setdefault("MT3_CHECKPOINT_DIR", str(ROOT / "outputs/.model_cache/mt3"))
os.environ.setdefault("PYTHONUNBUFFERED", "1")
os.environ.setdefault("OMP_NUM_THREADS", "8")

from pipeline import inspect_midi
from Apply_Sounds.yamnet_mapping import build_sound_mapping
from Apply_Sounds.render_midi_sounds import apply_sounds

PROMPTS = {
    "trap": "A dark instrumental trap beat, deep 808 bass, crisp snare backbeats, fast rolling hi hats, sparse minor key piano melody, 140 BPM, clean studio recording",
    "country": "An upbeat country instrumental groove, fingerpicked acoustic guitar, twangy banjo melody, warm electric bass, steady brushed drums, 100 BPM, clean studio recording",
    "pop": "A bright catchy pop instrumental, bouncy piano chords, simple memorable synth melody, warm bass line, punchy kick and snare, steady hi hats, 115 BPM, clean studio recording",
    "choir": "A slow uplifting gospel church hymn, warm choir singing sustained wordless ah harmonies, gentle church organ chords, soft piano, restrained percussion, reverent and peaceful, 75 BPM",
}


def write_json(path, value):
    write_report(path, value)


def command(args, log):
    with log.open("w", encoding="utf-8") as stream:
        subprocess.run([sys.executable, "-u", *map(str, args)], cwd=ROOT,
                       stdout=stream, stderr=subprocess.STDOUT, check=True)


def main():
    everyday = json.loads((ROOT / "Sounds/everyday_classifications.json").read_text())
    mixed = everyday + [
        {"file": "kick.wav", "yamnet_class": "Bass drum"},
        {"file": "snare.wav", "yamnet_class": "Snare drum"},
        {"file": "hi-hat.wav", "yamnet_class": "Hi-hat"},
        {"file": "bass.wav", "yamnet_class": "Bass guitar", "root_note": 60, "loop": True},
        {"file": "whoosh.wav", "yamnet_class": "Whoosh, swoosh, swish"},
    ]
    session = {}
    for index, (genre, prompt) in enumerate(PROMPTS.items()):
        folder = BASE / genre
        folder.mkdir(exist_ok=True)
        report = {"genre": genre, "prompt": prompt, "requested_seconds": 12,
                  "model": "facebook/musicgen-small", "seed": 104 + index}
        started = time.monotonic()
        try:
            audio, midi = folder / "original.wav", folder / "transcribed.mid"
            if not audio.is_file():
                print(f"{genre}: generating 12 seconds", flush=True)
                command([ROOT / "Music_Gen/musicgen_large_generator.py", "--prompt", prompt,
                         "--model", "facebook/musicgen-small", "--duration", "12",
                         "--seed", str(report["seed"]), "--output", audio], folder / "generation.log")
            if not midi.is_file():
                print(f"{genre}: transcribing", flush=True)
                command([ROOT / "transcribe.py", audio, "--output", midi], folder / "transcription.log")
            report["midi"] = inspect_midi(midi)
            for variant, sounds in [("everyday", everyday), ("mixed", mixed)]:
                print(f"{genre}: rendering {variant} sounds", flush=True)
                mapping = build_sound_mapping(sounds, midi)
                write_json(folder / f"{variant}_mapping.json", mapping)
                report[variant] = apply_sounds(midi, mapping["mapping"], folder / f"{variant}.wav", sounds_dir=ROOT / "Sounds")
            report["status"] = "completed"
        except Exception as error:
            report.update(status="failed", error=str(error))
            print(f"{genre}: FAILED {error}", flush=True)
        report["elapsed_seconds"] = round(time.monotonic() - started, 2)
        write_json(folder / "result.json", report)
        session[genre] = report
        write_json(BASE / "session.json", session)
    print(json.dumps({genre: row["status"] for genre, row in session.items()}), flush=True)


if __name__ == "__main__":
    main()
