"""Use short source hits with the unchanged recovered MIDI; no model calls."""
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs"))
from artifact_paths import write_report
import mido
import numpy as np
import soundfile as sf
from Apply_Sounds.render_midi_sounds import apply_sounds, extract_notes


def main():
    library = OUT / "one_shots"
    library.mkdir(exist_ok=True)
    sources = []
    for name, duration in {"door_knock.wav": .16, "finger_snap.wav": .18,
                           "hand_clap.wav": .24, "switch_click.wav": .10}.items():
        path = ROOT / "Sounds" / name
        original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        samples, rate = sf.read(path, always_2d=True)
        clip = samples[:round(duration * rate)].copy()
        fade = min(round(.005 * rate), len(clip) // 2)
        clip[-fade:] *= np.linspace(1, 0, fade)[:, None]
        sf.write(library / name, clip, rate, subtype="PCM_16")
        assert hashlib.sha256(path.read_bytes()).hexdigest() == original_hash
        sources.append({"file": name, "source_sha256": original_hash, "seconds": len(clip)/rate})
    write_report(library / "sources.json", {"source_library": "../Sounds", "source_files_unchanged": True,
                                            "operation": "Leading one-shot crop and 5 ms tail fade", "samples": sources})
    folder = OUT / "take_501"
    mapping = json.loads((folder / "everyday_mapping.json").read_text())
    result = apply_sounds(folder / "transcribed.mid", mapping, folder / "everyday_tight.wav", sounds_dir=library)
    data, rate = sf.read(folder / "everyday_tight.wav", always_2d=True)
    notes = extract_notes(mido.MidiFile(folder / "transcribed.mid"))
    start = max(0, round((min(n[0] for n in notes) - .01) * rate))
    preview = data[start:].copy()
    fade = min(round(.010 * rate), len(preview) // 2)
    preview[-fade:] *= np.linspace(1, 0, fade)[:, None]
    assert np.isfinite(preview).all() and np.abs(preview).max() > 0
    sf.write(OUT / "listen.wav", preview, rate, subtype="PCM_16")
    result.update(preview="simple_trap_retry/listen.wav", preview_seconds=round(len(preview)/rate, 3),
                  leading_silence_removed_seconds=round(start/rate, 3),
                  midi_modified=False, selected_take=501,
                  selection_reason="Note onsets span 9 of 12 seconds versus 5 of 12 in the other take; not an auditory quality rating",
                  limitations="Only drum notes survived transcription; bass/melody were not invented or added")
    write_report(OUT / "preview.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
