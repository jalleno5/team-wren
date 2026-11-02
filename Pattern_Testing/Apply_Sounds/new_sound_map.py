"""Generate (and replace) sound_map.json using exactly one MIDI file.

Usage:
    python new_sound_map.py "../MIDI_sequences/example.mid"
    python new_sound_map.py "../MIDI_sequences/example.mid" --output custom_map.json

Relative input/output paths are resolved relative to this script's directory.
Requires: mido (included in the renderer's requirements.txt).
"""

import argparse
import json
from pathlib import Path

import mido


def main():
    parser = argparse.ArgumentParser(description="Overwrite sound_map.json with a template for one MIDI file.")
    parser.add_argument("midi_file", help="Path to one .mid or .midi file (required)")
    parser.add_argument("--output", default="sound_map.json", help="Output filename (default: sound_map.json)")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent

    def resolve(name):
        path = Path(name).expanduser()
        return path.resolve() if path.is_absolute() else (base / path).resolve()

    midi_path = resolve(args.midi_file)
    output_path = resolve(args.output)

    if not midi_path.is_file():
        parser.error(f"MIDI file not found: {midi_path}")
    if midi_path.suffix.lower() not in {".mid", ".midi"}:
        parser.error("Please provide a .mid or .midi file")

    try:
        midi = mido.MidiFile(str(midi_path))
        programs = [0] * 16  # Default MIDI instrument is program 0.
        used_programs = set()
        used_drums = set()

        # Merge tracks so program changes are processed in chronological order.
        for msg in mido.merge_tracks(midi.tracks):
            if msg.type == "program_change" and msg.channel != 9:
                programs[msg.channel] = msg.program
            elif msg.type == "note_on" and msg.velocity > 0:
                if msg.channel == 9:  # MIDI channel 10 (zero-based index 9) is percussion.
                    used_drums.add(msg.note)
                else:
                    used_programs.add(programs[msg.channel])
    except (OSError, ValueError, EOFError) as exc:
        parser.error(f"Could not read MIDI file: {exc}")

    if not used_programs and not used_drums:
        parser.error("No playable notes found; existing sound_map.json was not changed")

    mapping = {
        "programs": {
            str(program): {
                "file": f"REPLACE_WITH_SOUND_FOR_PROGRAM_{program}.wav",
                "root_note": 60,
                "loop": True,
            }
            for program in sorted(used_programs)
        },
        "drums": {
            str(note): f"REPLACE_WITH_SOUND_FOR_DRUM_{note}.wav"
            for note in sorted(used_drums)
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    print(f"MIDI: {midi_path}")
    print(f"Replaced mapping: {output_path}")
    print(f"Programs: {sorted(used_programs)}")
    print(f"Drum notes: {sorted(used_drums)}")
    print("Replace the placeholder 'file' values with sound filenames from ../Sounds.")


if __name__ == "__main__":
    main()
