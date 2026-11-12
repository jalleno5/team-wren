"""Optional HDemucs -> drum MIDI -> sample replacement + retained accompaniment."""
import argparse
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

import mido
import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from pipeline import ROOT, generate_music, transcribe_audio, inspect_midi
from Apply_Sounds.render_midi_sounds import apply_sounds, active_rms, SAMPLE_RATE
from Apply_Sounds.yamnet_mapping import build_sound_mapping


def keep_drum_notes(source, destination):
    """Retain channel 10 and all meta timing; discard melodic note predictions."""
    original = mido.MidiFile(str(source))
    if original.type == 2:
        raise ValueError("Asynchronous type-2 MIDI is not supported")
    midi = mido.MidiFile(type=original.type, ticks_per_beat=original.ticks_per_beat)
    count = 0
    for source_track in original.tracks:
        track = mido.MidiTrack()
        midi.tracks.append(track)
        tick = previous = 0
        for message in source_track:
            tick += message.time
            if message.type == "end_of_track":
                continue
            if message.is_meta or getattr(message, "channel", None) == 9:
                track.append(message.copy(time=tick-previous))
                previous = tick
                count += message.type == "note_on" and message.velocity > 0
        track.append(mido.MetaMessage("end_of_track", time=tick-previous))
    if not count:
        raise ValueError("YourMT3 recovered no drum-channel notes; accompaniment was not remixed")
    midi.save(str(destination))
    return count


def read_stereo(path):
    data, rate = sf.read(path, dtype="float32", always_2d=True)
    if not len(data) or not np.isfinite(data).all():
        raise ValueError("Mix inputs must contain finite, nonempty audio")
    if data.shape[1] == 1:
        data = np.repeat(data, 2, axis=1)
    if data.shape[1] != 2:
        raise ValueError("Mix inputs must be mono or stereo")
    if rate != SAMPLE_RATE:
        divisor = math.gcd(rate, SAMPLE_RATE)
        data = resample_poly(data, SAMPLE_RATE // divisor, rate // divisor)
    return data


def mix_tracks(accompaniment, percussion, reference_drums, output, *,
               drums_gain_db=0, accompaniment_gain_db=0):
    for value in [drums_gain_db, accompaniment_gain_db]:
        if not math.isfinite(value) or not -24 <= value <= 12:
            raise ValueError("Mix gains must be between -24 and +12 dB")
    backing = read_stereo(accompaniment)
    hits = read_stereo(percussion)
    reference = read_stereo(reference_drums)
    # Keep sample timing at zero offset; pad/crop to the accompaniment duration.
    cropped = len(hits) > len(backing)
    hits = np.pad(hits, ((0, max(0, len(backing)-len(hits))), (0, 0)))[:len(backing)]
    if cropped:
        fade = min(round(.010 * SAMPLE_RATE), len(hits))
        hits[-fade:] *= np.linspace(1, 0, fade)[:, None]
    reference_level, hit_level = active_rms(reference), active_rms(hits)
    if hit_level < 1e-7 or reference_level < 1e-7:
        raise ValueError("Original/replacement percussion is silent; no remix created")
    level_gain = min(reference_level / hit_level, 10 ** (12 / 20))
    mixed = backing * 10 ** (accompaniment_gain_db / 20) + hits * level_gain * 10 ** (drums_gain_db / 20)
    peak = float(np.abs(mixed).max())
    master_gain = min(1, .98 / max(peak, 1e-12))
    mixed *= master_gain
    sf.write(output, mixed, SAMPLE_RATE, subtype="PCM_16")
    return {"drums_gain_db": drums_gain_db, "accompaniment_gain_db": accompaniment_gain_db,
            "percussion_level_match_db": round(20 * math.log10(level_gain), 3),
            "master_gain_db": round(20 * math.log10(master_gain), 3),
            "duration_seconds": len(backing) / SAMPLE_RATE}


def run_percussion_pipeline(prompt, output_dir, *, source_audio=None, duration=10,
                            mapping=None, sounds=None, sounds_dir=None,
                            model="facebook/musicgen-small", drums_gain_db=0,
                            accompaniment_gain_db=0, progress=lambda stage: None):
    if (mapping is None) == (sounds is None):
        raise ValueError("Supply exactly one of mapping or classified sounds")
    if (source_audio is None) == (prompt is None):
        raise ValueError("Supply exactly one of prompt or source_audio")
    if mapping is not None:
        if isinstance(mapping, (str, Path)):
            mapping = json.loads(Path(mapping).read_text(encoding="utf-8"))
        if mapping.get("programs") or not mapping.get("drums"):
            raise ValueError("Percussion replacement requires a drums mapping without programs")
    for gain in [drums_gain_db, accompaniment_gain_db]:
        if not math.isfinite(gain) or not -24 <= gain <= 12:
            raise ValueError("Mix gains must be between -24 and +12 dB")
    folder = Path(output_dir).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    audio = folder / "generated.wav"
    if source_audio is not None:
        progress("copying_audio")
        if Path(source_audio).resolve() != audio:
            shutil.copyfile(source_audio, audio)
    else:
        progress("generating")
        generate_music(prompt, audio, duration=duration, model=model)
    progress("separating")
    subprocess.run([sys.executable, str(ROOT / "separate_audio.py"), str(audio),
                    "--output-dir", str(folder)], check=True)
    progress("transcribing_drums")
    raw = transcribe_audio(folder / "drums.wav", folder / "raw_transcribed.mid")
    midi = folder / "transcribed.mid"
    keep_drum_notes(raw, midi)
    mapping_report = None
    if sounds is not None:
        mapping_report = build_sound_mapping(sounds, midi)
        mapping = mapping_report["mapping"]
    (folder / "mapping.json").write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    progress("rendering_percussion")
    render = apply_sounds(midi, mapping, folder / "percussion.wav", sounds_dir=sounds_dir)
    render["path"] = "percussion.wav"
    progress("mixing")
    mix = mix_tracks(folder / "accompaniment.wav", folder / "percussion.wav", folder / "drums.wav",
                     folder / "rendered.wav", drums_gain_db=drums_gain_db,
                     accompaniment_gain_db=accompaniment_gain_db)
    result = {"pipeline": "percussion_replacement", "separator": "HDEMUCS_HIGH_MUSDB_PLUS",
              "artifacts": {"audio": "generated.wav", "drums": "drums.wav",
                            "accompaniment": "accompaniment.wav", "midi": "transcribed.mid",
                            "raw_midi": "raw_transcribed.mid", "percussion": "percussion.wav",
                            "rendered": "rendered.wav"},
              "midi": inspect_midi(midi), "mapping": mapping, "render": render, "mix": mix}
    if mapping_report is not None:
        result["mapping_report"] = mapping_report
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--prompt")
    source.add_argument("--audio", type=Path)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--mapping", type=Path)
    selection.add_argument("--classifications", type=Path)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/percussion_local")
    parser.add_argument("--sounds", type=Path, default=ROOT / "Sounds")
    parser.add_argument("--duration", type=float, default=10)
    parser.add_argument("--drums-gain-db", type=float, default=0)
    parser.add_argument("--accompaniment-gain-db", type=float, default=0)
    args = parser.parse_args()
    sounds = json.loads(args.classifications.read_text(encoding="utf-8")) if args.classifications else None
    result = run_percussion_pipeline(args.prompt, args.output_dir, source_audio=args.audio, duration=args.duration,
                                     mapping=args.mapping, sounds=sounds, sounds_dir=args.sounds,
                                     drums_gain_db=args.drums_gain_db, accompaniment_gain_db=args.accompaniment_gain_db,
                                     progress=print)
    (args.output_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
