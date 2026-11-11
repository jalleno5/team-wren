# Everyday sound pack

These ten WAV files are synthetic foley, generated locally with NumPy/SciPy.
They imitate everyday sounds; they are not field recordings and use no
third-party audio samples. The existing instrument samples remain separate.

| File | Length |
| --- | --- |
| `door_knock.wav` | 0.70 s |
| `finger_snap.wav` | 0.18 s |
| `hand_clap.wav` | 0.38 s |
| `key_jingle.wav` | 1.15 s |
| `coin_drop.wav` | 0.95 s |
| `glass_clink.wav` | 1.20 s |
| `water_drop.wav` | 0.42 s |
| `paper_crumple.wav` | 1.10 s |
| `zipper_pull.wav` | 0.85 s |
| `switch_click.wav` | 0.23 s |

All are mono, 44.1 kHz, 16-bit PCM WAV, with edge fades and a peak of about
-1.4 dBFS. `everyday_manifest.json` contains descriptions and durations.
Only `glass_clink.wav` has an intentional musical root (C6, MIDI 84); the other
sounds are mostly unpitched and work best as percussion.

From `pattern_testing`, try the example mapping on an existing MIDI:

```powershell
.venv/Scripts/python Apply_Sounds/render_midi_sounds.py "../MIDI_sequences/jazz.mid" --mapping everyday_sound_map.json --output everyday_jazz.wav
```

Output: `outputs/rendered/everyday_jazz.wav`. The example mapping is generated
from `everyday_classifications.json` and the instruments used by `jazz.mid`.
Those labels are manually supplied examples, not model inference results.
See [YAMNet mapping](../Apply_Sounds/yamnet/README.md) to regenerate it for another
MIDI or use your actual YAMNet/user-corrected classes. The report explains any
fallbacks and unused sounds. Set `loop: false` for short foley hits.
Melodic notes pitch-shift the sample and can truncate it at note-off; drum notes
play the entire sample once. The 1.5-second cap applies to source files.

Regenerate this pack with the shared environment:

```powershell
.venv/Scripts/python Sounds/generate_everyday.py
```

This overwrites only the ten files listed above and their manifest.
