"""Composable prompt -> WAV -> MIDI -> everyday-sound WAV pipeline."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

import mido

from Apply_Sounds.render_midi_sounds import apply_sounds, extract_notes

ROOT = Path(__file__).resolve().parent


def generate_music(prompt: str, output: Path, *, duration=10, model="facebook/musicgen-small") -> Path:
    """Use the existing MusicGen CLI in an isolated process to release GPU memory."""
    if not prompt.strip() or not 1 <= duration <= 30:
        raise ValueError("Provide a nonempty prompt and duration between 1 and 30 seconds")
    subprocess.run([
        sys.executable, str(ROOT / "Music_Gen/musicgen_large_generator.py"),
        "--prompt", prompt, "--duration", str(duration), "--model", model,
        "--output", str(output.resolve()),
    ], check=True)
    if not output.is_file():
        raise RuntimeError("MusicGen completed without producing a WAV")
    return output


def transcribe_audio(audio: Path, output: Path) -> Path:
    """Use this environment in a child process, releasing model memory on exit."""
    subprocess.run([sys.executable, str(ROOT / "transcribe.py"), str(audio.resolve()),
                    "--output", str(output.resolve())], check=True)
    inspect_midi(output)
    return output


def inspect_midi(path: Path) -> dict:
    notes = extract_notes(mido.MidiFile(str(path)))
    if not notes:
        raise ValueError("Transcription produced no playable MIDI notes")
    return {"notes": len(notes), "programs": sorted({n[4] for n in notes if not n[5]}),
            "drums": sorted({n[2] for n in notes if n[5]})}


def run_pipeline(prompt: str, output_dir: Path, *, duration=10, mapping=None,
                 sounds_dir=None, model="facebook/musicgen-small",
                 progress: Callable[[str], None] = lambda stage: None) -> dict:
    """Always return the generated WAV and downloadable MIDI; rendering is optional."""
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    progress("generating")
    audio = generate_music(prompt, output_dir / "generated.wav", duration=duration, model=model)
    progress("transcribing")
    midi = transcribe_audio(audio, output_dir / "transcribed.mid")
    result = {"artifacts": {"audio": audio.name, "midi": midi.name}, "midi": inspect_midi(midi)}
    # MIDI remains available even if the optional sample rendering fails.
    if mapping is not None:
        progress("rendering")
        try:
            result["render"] = apply_sounds(midi, mapping, output_dir / "rendered.wav", sounds_dir=sounds_dir)
            result["artifacts"]["rendered"] = "rendered.wav"
        except (ValueError, OSError, KeyError, TypeError) as exc:
            result["render_error"] = str(exc)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prompt")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/local")
    parser.add_argument("--duration", type=float, default=10)
    parser.add_argument("--model", default="facebook/musicgen-small")
    parser.add_argument("--mapping", type=Path)
    parser.add_argument("--sounds", type=Path, default=ROOT / "Sounds")
    args = parser.parse_args()
    result = run_pipeline(args.prompt, args.output_dir, duration=args.duration, model=args.model,
                          mapping=args.mapping, sounds_dir=args.sounds, progress=print)
    (args.output_dir / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
