"""Turn trusted YAMNet/user labels into the sample renderer's mapping format."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

import mido

try:  # Support both package imports and direct CLI execution.
    from .render_midi_sounds import extract_notes
except ImportError:
    from render_midi_sounds import extract_notes

TABLE = Path(__file__).resolve().parent / "yamnet/class_instruments.csv"
DRUM_ROLES = {
    "low_hit": {35, 36, 41, 43, 45, 47, 48, 50, 60, 61, 62, 63, 64, 65, 66},
    "snare": {38, 39, 40}, "click": {37, 75, 76, 77},
    "noise_hit": {42, 44, 46}, "metal_hit": {49, 51, 52, 53, 55, 56, 57, 59, 80, 81},
    "shaker": {54, 58, 69, 70}, "scrape": {73, 74, 78, 79}, "wind": {71, 72},
    "mallet": {67, 68},
}
PROGRAM_ROLES = ["keys", "mallet", "keys", "plucked", "bass", "strings", "strings", "brass",
                 "wind", "wind", "lead", "pad", "pad", "plucked", "mallet", "effect"]


def load_class_table(path=TABLE):
    with Path(path).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 521 or {int(r["index"]) for r in rows} != set(range(521)):
        raise ValueError("Instrument table must cover all 521 YAMNet indices exactly once")
    for row in rows:
        row["index"], row["number"] = int(row["index"]), int(row["number"])
        if row["kind"] not in {"program", "drum"} or not 0 <= row["number"] <= 127:
            raise ValueError(f"Invalid instrument target for {row['display_name']}")
        if row["enabled"] not in {"true", "false"}:
            raise ValueError("enabled must be true or false")
        row["enabled"] = row["enabled"] == "true"
    return rows


def resolve_class(value, rows):
    """Accept an official class index, AudioSet MID, or full display name."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("Class must be a YAMNet name, index or AudioSet MID")
    key = str(value).strip().casefold()
    for row in rows:
        if key in {str(row["index"]), row["mid"].casefold(), row["display_name"].casefold()}:
            return row
    raise ValueError(f"Unknown YAMNet class: {value!r}")


def target_role(kind, number):
    if kind == "program":
        if number in {43, 47}:
            return "bass"
        if number in {52, 53, 54}:
            return "voice"
        return PROGRAM_ROLES[number // 8]
    return next((role for role, pitches in DRUM_ROLES.items() if number in pitches), "percussion")


def match_score(candidate, kind, number):
    target = candidate["target"]
    if target["kind"] == kind and target["number"] == number:
        return 0, "exact_instrument"
    if kind == target["kind"] == "program" and target["number"] // 8 == number // 8:
        return 1, "same_gm_family"
    role = target_role(kind, number)
    if target["kind"] == kind and target["role"] == role:
        return 2, "similar_role"
    if target["kind"] == kind:
        return 3, "same_kind_fallback"
    return 4, "cross_kind_fallback"


def build_sound_mapping(sounds, midi_path=None, *, fallback="nearest", table_path=TABLE):
    """Return {mapping, assignments, skipped_sounds, unused_sounds, unmapped}.

    sounds: [{file, yamnet_class, user_class?, root_note?, loop?, priority?}].
    User classes override model classes. Scores/confidences are deliberately not
    used. Higher priority wins ties, then original input order. With a MIDI,
    nearest covers every used program/drum pitch, reusing samples as necessary.
    fallback='omit' only allows exact instruments. Without MIDI only the table's
    preferred targets are emitted. No inference, pitch detection or audio I/O.
    """
    if fallback not in {"nearest", "omit"}:
        raise ValueError("fallback must be nearest or omit")
    if not isinstance(sounds, list) or not sounds:
        raise ValueError("Provide at least one classified sound")
    rows = load_class_table(table_path)
    candidates, skipped = [], []
    for index, sound in enumerate(sounds):
        if not isinstance(sound, dict) or not isinstance(sound.get("file"), str) or not sound["file"].strip():
            raise ValueError("Each sound needs a nonempty file name")
        value = sound.get("user_class")
        if value is None:
            value = sound.get("yamnet_class")
        target = resolve_class(value, rows)
        root = sound.get("root_note", 60)
        loop = sound.get("loop", False)
        priority = sound.get("priority", 0)
        if isinstance(root, bool) or not isinstance(root, int) or not 0 <= root <= 127:
            raise ValueError("root_note must be an integer between 0 and 127")
        if not isinstance(loop, bool):
            raise ValueError("loop must be a boolean")
        if isinstance(priority, bool) or not isinstance(priority, (float, int)) or not math.isfinite(priority):
            raise ValueError("priority must be a finite number")
        if not target["enabled"]:
            skipped.append({"input_index": index, "file": sound["file"],
                            "class": target["display_name"], "reason": "class_disabled"})
            continue
        candidates.append({"index": index, "file": sound["file"], "target": target,
                           "root_note": root, "loop": loop, "priority": priority,
                           "user_corrected": sound.get("user_class") is not None})
    if not candidates:
        raise ValueError("No usable sounds remain; Silence is disabled by default")

    if midi_path is not None:
        notes = extract_notes(mido.MidiFile(str(midi_path)))
        targets = {( "drum" if note[5] else "program", note[2] if note[5] else note[4]) for note in notes}
        if not targets:
            raise ValueError("MIDI has no playable notes")
    else:
        targets = {(c["target"]["kind"], c["target"]["number"]) for c in candidates}

    mapping = {"programs": {}, "drums": {}}
    assignments, unmapped, used = [], [], set()
    for kind, number in sorted(targets):
        ranked = sorted(candidates, key=lambda c: (match_score(c, kind, number)[0], -c["priority"], c["index"]))
        selected = ranked[0]
        score, reason = match_score(selected, kind, number)
        if fallback == "omit" and score != 0:
            unmapped.append({"kind": kind, "number": number})
            continue
        config = {"file": selected["file"]}
        if kind == "program":
            config.update(root_note=selected["root_note"], loop=selected["loop"])
        mapping["programs" if kind == "program" else "drums"][str(number)] = config
        used.add(selected["index"])
        assignments.append({"kind": kind, "number": number, "file": selected["file"],
                            "input_index": selected["index"], "class": selected["target"]["display_name"],
                            "preferred_instrument": selected["target"]["instrument"],
                            "user_corrected": selected["user_corrected"], "reason": reason})
    return {"mapping": mapping, "assignments": assignments, "skipped_sounds": skipped,
            "unused_sounds": [{"input_index": c["index"], "file": c["file"]} for c in candidates if c["index"] not in used],
            "unmapped": unmapped}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("classifications", type=Path, help="JSON array of classified sounds")
    parser.add_argument("--midi", type=Path, help="Cover instruments used by this MIDI")
    parser.add_argument("--output", type=Path, required=True, help="Renderer mapping JSON")
    parser.add_argument("--report", type=Path, help="Optional assignment report JSON")
    parser.add_argument("--fallback", choices=["nearest", "omit"], default="nearest")
    args = parser.parse_args()
    sounds = json.loads(args.classifications.read_text(encoding="utf-8"))
    result = build_sound_mapping(sounds, args.midi, fallback=args.fallback)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result["mapping"], indent=2) + "\n", encoding="utf-8")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
