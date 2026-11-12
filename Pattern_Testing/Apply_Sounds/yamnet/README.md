# YAMNet classes to musical instruments

`class_instruments.csv` contains an explicit assignment for **all 521 official
YAMNet classes**. Edit this file to change the app's musical policy. Each row
includes the official index, AudioSet MID, display name, target kind (`program`
or `drum`), target number, instrument name, musical role and enabled flag.

Class names/indices come from TensorFlow's
[official YAMNet class map](https://github.com/tensorflow/models/blob/master/research/audioset/yamnet/yamnet_class_map.csv),
copied locally as `yamnet_class_map.csv`. The source project uses the
[Apache 2.0 license](https://github.com/tensorflow/models/blob/master/LICENSE).
The instrument assignments are this app's creative defaults, not predictions
or recommendations supplied by TensorFlow. Broad classes such as Music,
Noise and Field recording have explicit defaults too. Silence has a Pad target
but is disabled: it is reported as skipped and never used for rendering.

Examples of defaults:

| YAMNet class | Musical target |
| --- | --- |
| Knock | Hi Wood Block, drum 76 |
| Thump, thud | Bass Drum 1, drum 36 |
| Clapping | Hand Clap, drum 39 |
| Finger snapping | Side Stick, drum 37 |
| Keys jangling | Tambourine, drum 54 |
| Coin (dropping) | Ride Cymbal 1, drum 51 |
| Chink, clink | Glockenspiel, program 9 |
| Drip | Marimba, program 12 |
| Crumpling, crinkling | Closed Hi-Hat, drum 42 |
| Zipper (clothing) | Long Guiro, drum 74 |
| Clicking | Side Stick, drum 37 |
| Bass guitar | Electric Bass (finger), program 33 |

Program numbers are **zero-based**; drum numbers are MIDI pitches on channel
10 (channel index 9). An instrument assignment describes how to use a sample;
it does not convert that recording into an instrument or identify its pitch.

## Input and user corrections

```json
[
  {"file": "door_knock.wav", "yamnet_class": "Knock"},
  {"file": "glass_clink.wav", "yamnet_class": 436, "root_note": 84},
  {"file": "hand_clap.wav", "yamnet_class": "Speech", "user_class": "Clapping", "priority": 2}
]
```

Use full official class names (case-insensitive), integer indices, numeric
index strings, or AudioSet MIDs such as `/m/0l15bq` for Clapping. `user_class`
overrides `yamnet_class` when supplied. The selected class is trusted, without
confidence thresholds, audio analysis or reclassification. Unknown classes are
rejected. Pass one final class per sound; resolve top-k predictions in your
classification/user-selection UI before calling this function.

`file` points to a sample in the renderer's sound library. Optional `root_note`
defaults to 60 and must be supplied if you know the sample's actual pitch.
Classification alone cannot establish that pitch. `loop` defaults to false for
short one-shot sounds. Higher `priority` wins between equally suitable samples;
otherwise the first input wins. No randomness or confidence weighting is used.

## Generate a renderer mapping

Run from `pattern_testing` with the shared environment:

```powershell
.venv/Scripts/python Apply_Sounds/yamnet_mapping.py Sounds/everyday_classifications.json --midi outputs/local/transcribed.mid --output outputs/local/mapping.json --report outputs/local/mapping_report.json
.venv/Scripts/python Apply_Sounds/render_midi_sounds.py "../outputs/local/transcribed.mid" --mapping "../outputs/local/mapping.json" --output-dir "../outputs/local" --output rendered.wav
```

`Sounds/everyday_classifications.json` contains manually assigned example
labels for the synthetic sound pack. They are not results of running YAMNet.
Use your actual classifier/user selections for production inputs.

With `--midi`, the mapper inspects every used program and drum pitch. It ranks
samples by exact target, same GM program family, same musical role within the
same kind, any sample of the same kind, then a sample of the other kind.
Higher priority and input order break ties within each rank. The last two are
broad fallbacks, not claims of acoustic similarity. A sample can be reused for
several MIDI parts; some sounds may remain unused. `nearest` is the default
policy and covers all notes when at least one usable sound is supplied.
Choose `--fallback omit` to allow only exact target matches and report the rest
as unmapped. Without `--midi`, only preferred targets from the table are emitted.

The output JSON is directly compatible with `apply_sounds()` and the existing
job/render endpoints. The report contains assignments and reasons, user
corrections, skipped classes, unused sounds and unmapped MIDI parts.

Callable equivalent:

```python
from Apply_Sounds.yamnet_mapping import build_sound_mapping
from Apply_Sounds.render_midi_sounds import apply_sounds

report = build_sound_mapping(classified_sounds, "outputs/local/transcribed.mid")
apply_sounds("outputs/local/transcribed.mid", report["mapping"], "outputs/classified.wav",
             sounds_dir="Sounds")
```

## Worker API

All requests use the existing worker bearer authentication.

- `GET /music/yamnet/classes` returns the complete editable class/instrument
  catalog for a class-selection UI.
- `POST /music/mappings` accepts `{"sounds": [...], "source_job_id": "...",
  "fallback": "nearest"}` and returns the mapping plus its assignment report.
  Omit `source_job_id` to emit only preferred targets before a MIDI exists.
- Pass the returned `mapping` to `POST /music/renders` with the same
  `source_job_id` to render the MIDI with those sounds. A preferred-target
  mapping can also be passed to `POST /music/jobs`, but may not cover instruments
  discovered later; generate a MIDI-aware mapping after transcription for coverage.

Samples must already exist in `MUSIC_SOUNDS_DIR`. The mapping endpoint validates
sample paths and availability, and does not upload audio. Your Vercel route must
check ownership of the source job before forwarding this request.

## Maintaining the table

`build_instrument_table.py` records the initial curated defaults and can rebuild
the table from the official class map. Running it overwrites manual CSV edits.
Runtime code reads the CSV directly, so editing the CSV is sufficient to change
the assignments on the next request.
