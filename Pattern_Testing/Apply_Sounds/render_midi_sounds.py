"""Render one MIDI file with user-provided audio samples.

Run from anywhere:
    python render_midi_sounds.py "../MIDI_sequences/beat1.mid"
    python render_midi_sounds.py "../MIDI_sequences/beat1.mid" --mapping sound_map.json

Paths in sound_map.json are relative to --sounds (../Sounds by default).
The required MIDI path and --mapping/--sounds/--output-dir paths are relative to this script.
"""

import argparse
import json
import subprocess
from collections import defaultdict
from pathlib import Path

import mido
import numpy as np
import soundfile as sf

SAMPLE_RATE = 44100


def resolve_path(value, base):
    path = Path(value).expanduser()
    return path if path.is_absolute() else (base / path).resolve()


def read_mapping(path, sounds_dir):
    raw = json.loads(path.read_text(encoding="utf-8"))
    instruments = {}
    drums = {}
    for key, entry in raw.get("programs", {}).items():
        program = int(key)
        if not 0 <= program <= 127:
            raise ValueError(f"MIDI program out of range: {program}")
        if isinstance(entry, str):
            entry = {"file": entry}
        instruments[program] = {
            "file": resolve_path(entry["file"], sounds_dir),
            "root_note": int(entry.get("root_note", 60)),
            "loop": bool(entry.get("loop", True)),
        }
    for key, entry in raw.get("drums", {}).items():
        note = int(key)
        if not 0 <= note <= 127:
            raise ValueError(f"Drum note out of range: {note}")
        if isinstance(entry, str):
            entry = {"file": entry}
        drums[note] = {"file": resolve_path(entry["file"], sounds_dir)}
    if not instruments and not drums:
        raise ValueError("Mapping must contain at least one program or drum note.")
    for item in [*instruments.values(), *drums.values()]:
        if not item["file"].is_file():
            raise FileNotFoundError(f"Audio sample not found: {item['file']}")
    return instruments, drums


def load_sample(path, cache):
    if path not in cache:
        try:
            data, rate = sf.read(path, always_2d=True, dtype="float32")
        except (RuntimeError, sf.LibsndfileError):
            # FFmpeg handles M4A/MP3 and other compressed formats.
            try:
                process = subprocess.run(
                    ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le",
                     "-acodec", "pcm_f32le", "-ac", "2", "-ar", str(SAMPLE_RATE), "-"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
                )
            except FileNotFoundError as exc:
                raise RuntimeError("FFmpeg is required to read this sound file. Install FFmpeg and put it on PATH.") from exc
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(f"Could not decode {path}: {exc.stderr.decode(errors='replace')}") from exc
            data = np.frombuffer(process.stdout, dtype="<f4").reshape(-1, 2).copy()
            rate = SAMPLE_RATE
        if len(data) == 0:
            raise ValueError(f"Empty sample file: {path}")
        if data.shape[1] == 1:
            data = np.repeat(data, 2, axis=1)
        elif data.shape[1] > 2:
            data = data[:, :2]
        if rate != SAMPLE_RATE:
            # Linear resampling needs no SciPy and works for short sound samples.
            positions = np.arange(max(1, round(len(data) * SAMPLE_RATE / rate))) * rate / SAMPLE_RATE
            positions = np.minimum(positions, len(data) - 1)
            data = interpolate_stereo(data, positions)
        cache[path] = data
    return cache[path]


def interpolate_stereo(data, positions):
    left = np.interp(positions, np.arange(len(data)), data[:, 0])
    right = np.interp(positions, np.arange(len(data)), data[:, 1])
    return np.column_stack((left, right)).astype(np.float32)


def extract_notes(midi):
    """Honor tempo changes, program changes, drum channel, and note-offs."""
    programs = [0] * 16
    active = defaultdict(list)
    notes = []
    seconds = 0.0
    for msg in midi:  # mido computes merged, tempo-aware times in seconds
        seconds += msg.time
        if msg.type == "program_change":
            programs[msg.channel] = msg.program
        elif msg.type == "note_on" and msg.velocity > 0:
            active[(msg.channel, msg.note)].append((seconds, msg.velocity, programs[msg.channel]))
        elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
            key = (msg.channel, msg.note)
            if active[key]:
                start, velocity, program = active[key].pop(0)
                notes.append((start, max(seconds - start, 0.01), msg.note, velocity, program, msg.channel == 9))
    for (channel, note), outstanding in active.items():
        for start, velocity, program in outstanding:
            notes.append((start, max(seconds - start, 0.1), note, velocity, program, channel == 9))
    return notes


def synth_note(sample, midi_note, velocity, root_note, duration, loop, drum):
    speed = 1.0 if drum else 2.0 ** ((midi_note - root_note) / 12.0)
    target_len = max(1, round(duration * SAMPLE_RATE))
    if drum:
        # Drum samples play once, independent of the MIDI note-off duration.
        positions = np.arange(len(sample), dtype=np.float64)
    elif loop:
        positions = (np.arange(target_len, dtype=np.float64) * speed) % len(sample)
    else:
        count = min(target_len, max(1, int(np.ceil(len(sample) / speed))))
        positions = np.arange(count, dtype=np.float64) * speed
        positions = np.minimum(positions, len(sample) - 1)
    if drum:
        clip = sample.copy()
    else:
        clip = interpolate_stereo(sample, positions)
    clip *= velocity / 127.0
    if not drum:
        # Short fades prevent abrupt starts and note-offs.
        fade = min(round(0.01 * SAMPLE_RATE), len(clip) // 2)
        if fade > 0:
            ramp = np.linspace(0.0, 1.0, fade, dtype=np.float32)
            clip[:fade] *= ramp[:, None]
            clip[-fade:] *= ramp[::-1, None]
    return clip


def render_file(midi_path, output_path, programs, drums, cache):
    midi = mido.MidiFile(str(midi_path))
    notes = extract_notes(midi)
    scheduled = []
    missing_programs, missing_drums = set(), set()
    for start, duration, note, velocity, program, is_drum in notes:
        if is_drum:
            config = drums.get(note)
            if config is None:
                missing_drums.add(note)
                continue
        else:
            config = programs.get(program)
            if config is None:
                missing_programs.add(program)
                continue
        sample = load_sample(config["file"], cache)
        clip = synth_note(sample, note, velocity, config.get("root_note", 60),
                          duration, config.get("loop", False), is_drum)
        scheduled.append((round(start * SAMPLE_RATE), clip))
    if not scheduled:
        print(f"SKIPPED {midi_path.name}: no notes match the mapping")
        return
    n_frames = max(begin + len(clip) for begin, clip in scheduled) + round(0.25 * SAMPLE_RATE)
    output = np.zeros((n_frames, 2), dtype=np.float32)
    for begin, clip in scheduled:
        output[begin:begin + len(clip)] += clip
    peak = float(np.max(np.abs(output)))
    if peak > 0.98:
        output *= 0.98 / peak
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, output, SAMPLE_RATE, subtype="PCM_16")
    print(f"CREATED {output_path} ({len(scheduled)} notes)")
    if missing_programs:
        print(f"  Unmapped programs (0-based): {sorted(missing_programs)}")
    if missing_drums:
        print(f"  Unmapped drum notes: {sorted(missing_drums)}")


def main():
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("midi_file", help="Path to exactly one .mid or .midi file (required)")
    parser.add_argument("--mapping", default="sound_map.json")
    parser.add_argument("--sounds", default="../Sounds")
    parser.add_argument("--output-dir", default="../Songs/Fermata_Songs")
    parser.add_argument("--output", help="Optional output WAV filename/path; defaults to <MIDI stem>.wav in --output-dir")
    args = parser.parse_args()

    midi_path = resolve_path(args.midi_file, script_dir)
    if not midi_path.is_file():
        parser.error(f"MIDI file not found: {midi_path}")
    if midi_path.suffix.lower() not in (".mid", ".midi"):
        parser.error("Input must be a .mid or .midi file")

    sounds_dir = resolve_path(args.sounds, script_dir)
    output_dir = resolve_path(args.output_dir, script_dir)
    mapping_path = resolve_path(args.mapping, script_dir)
    if not mapping_path.is_file():
        parser.error(f"Mapping file not found: {mapping_path}")
    output_path = resolve_path(args.output, output_dir) if args.output else output_dir / (midi_path.stem + ".wav")
    if output_path.suffix.lower() != ".wav":
        parser.error("Output filename must end in .wav")

    programs, drums = read_mapping(mapping_path, sounds_dir)
    render_file(midi_path, output_path, programs, drums, {})


if __name__ == "__main__":
    main()
