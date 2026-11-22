"""Assign database-classified samples to instruments actually played in a MIDI."""
from collections import Counter

import mido

from .render_midi_sounds import extract_notes

ROLES = {"percussion", "rhythmic", "melodic", "ambient", "transition"}
RHYTHMIC_DRUMS = {42, 44, 46, 54, 58, 69, 70, 73, 74, 78, 79}
ACCENT_DRUMS = {49, 52, 55, 57}


def instrument_roles(kind, number):
    """Ordered compatible roles for zero-based GM programs or drum pitches.

    This is an editable musical policy, not a prediction about the recording.
    Secondary choices stay compatible; drums never borrow melodic/ambient sounds.
    """
    if kind == "drum":
        if number in RHYTHMIC_DRUMS:
            return ("rhythmic", "percussion")
        if number in ACCENT_DRUMS:
            return ("transition", "percussion")
        return ("percussion", "rhythmic")
    if 88 <= number <= 95:  # Synth pads
        return ("ambient",)
    if 96 <= number <= 103:  # Synth effects
        return ("ambient", "transition")
    if 120 <= number <= 127:  # Sound effects
        return ("transition",)
    if 112 <= number <= 119:  # Percussive programs
        return ("percussion", "rhythmic", "melodic")
    return ("melodic",)


def validate_sounds(sounds):
    if not isinstance(sounds, list) or not sounds:
        raise ValueError("Provide at least one database-classified sound")
    seen = set()
    for sound in sounds:
        if not isinstance(sound, dict) or not isinstance(sound.get("file"), str) or not sound["file"]:
            raise ValueError("Each sound needs a file reference")
        if sound["file"] in seen:
            raise ValueError("Each sound may be selected only once")
        seen.add(sound["file"])
        role = sound.get("classification")
        if not isinstance(role, str) or role.casefold() not in ROLES:
            raise ValueError(f"Sound {sound['file']} needs a valid database classification")
        root = sound.get("root_note", 60)
        if isinstance(root, bool) or not isinstance(root, int) or not 0 <= root <= 127:
            raise ValueError("root_note must be an integer between 0 and 127")
        if "loop" in sound and not isinstance(sound["loop"], bool):
            raise ValueError("loop must be a boolean")


def build_role_mapping(sounds, midi_path, *, fallback="nearest"):
    """Assign by database role, preferring unused samples within the same role.

    Reuse is permitted when instruments outnumber compatible sounds. Unmatched
    instruments and unused sounds are reported rather than forced into a role.
    nearest permits the secondary roles above; omit permits primary roles only.
    No user/YAMNet class override is consulted. MIDI timing remains unchanged.
    """
    validate_sounds(sounds)
    if fallback not in {"nearest", "omit"}:
        raise ValueError("fallback must be nearest or omit")
    midi = mido.MidiFile(str(midi_path))
    if midi.type == 2:
        raise ValueError("Asynchronous type-2 MIDI is not supported")
    notes = extract_notes(midi)
    targets = sorted({("drum" if note[5] else "program", note[2] if note[5] else note[4])
                      for note in notes})
    if not targets:
        raise ValueError("MIDI has no playable notes")
    roles = [sound["classification"].casefold() for sound in sounds]
    choices = {}
    for target in targets:
        allowed = instrument_roles(*target)
        if fallback == "omit":
            allowed = allowed[:1]
        choices[target] = [(allowed.index(role), index) for index, role in enumerate(roles) if role in allowed]
    mapping = {"programs": {}, "drums": {}}
    used = Counter()
    assignments = []
    unmapped = []
    # Reserve scarce choices before broad ones. Input order breaks equal ties.
    for kind, number in sorted(targets, key=lambda t: (len(choices[t]), t)):
        candidates = choices[(kind, number)]
        if not candidates:
            unmapped.append({"kind": kind, "number": number,
                             "compatible_roles": list(instrument_roles(kind, number)),
                             "reason": "no_compatible_sound"})
            continue
        rank, index = min(candidates, key=lambda item: (item[0], used[item[1]], item[1]))
        sound = sounds[index]
        config = {"file": sound["file"]}
        if kind == "program":
            config.update(root_note=sound.get("root_note", 60),
                          loop=sound.get("loop", roles[index] == "ambient"))
        mapping["drums" if kind == "drum" else "programs"][str(number)] = config
        assignments.append({"kind": kind, "number": number, "file": sound["file"],
                            "input_index": index, "classification": sound["classification"],
                            "reason": "primary_role" if rank == 0 else "compatible_role",
                            "reused": used[index] > 0})
        used[index] += 1
    return {"mapping": mapping, "assignments": assignments, "unmapped": unmapped,
            "unused_sounds": [{"input_index": i, "file": sound["file"],
                               "classification": sound["classification"],
                               "reason": "no_available_instrument" if not any(
                                   i == index for options in choices.values() for _, index in options
                               ) else "surplus_sample"}
                              for i, sound in enumerate(sounds) if not used[i]],
            "skipped_sounds": []}
