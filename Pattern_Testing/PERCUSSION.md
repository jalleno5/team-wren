# Optional percussion replacement

`MusicGen WAV -> HDemucs -> drums + accompaniment -> drum MIDI -> your sounds -> final mix`

Only the drum stem is transcribed and replaced. The separated bass, vocals and
other accompaniment are retained as audio, so lost melodic MIDI predictions do
not remove those parts from the final song. The normal `/music/jobs` path remains
the full-transcription path.

## Worker endpoint

`POST /music/percussion-jobs` uses the same bearer authentication, job queue,
polling and download routes as other music jobs. It returns 202 with a job ID.

Generate a new song and replace its percussion:

```json
{
  "prompt": "A simple trap beat with bass and a bell melody",
  "duration": 10,
  "mapping": {
    "drums": {
      "36": "door_knock.wav",
      "38": "hand_clap.wav",
      "42": "finger_snap.wav"
    }
  },
  "drums_gain_db": -3,
  "accompaniment_gain_db": 0
}
```

Or reuse a completed/failed job whose original audio is available, avoiding
another MusicGen run. Supply trusted classifications to build a MIDI-aware
mapping automatically:

```json
{
  "source_job_id": "original-job-uuid",
  "sounds": [
    {"file": "door_knock.wav", "yamnet_class": "Knock"},
    {"file": "hand_clap.wav", "yamnet_class": "Clapping"},
    {"file": "finger_snap.wav", "yamnet_class": "Finger snapping"}
  ]
}
```

Supply exactly one of `prompt` or `source_job_id`, and exactly one of `mapping`
or `sounds`. Explicit mappings use drum pitches only; `programs` must be empty
or omitted. Unmapped drum notes in a manual mapping are reported and skipped.
The automatic mapping covers the transcribed drum pitches, reusing samples if
necessary. User-corrected classes are accepted as in the standard mapping path.
All sample files must already exist inside `MUSIC_SOUNDS_DIR`.

Poll `GET /music/jobs/{id}`. The stages are `generating` (or `copying_audio`),
`separating`, `transcribing_drums`, `rendering_percussion`, `mixing`, then
`completed` or `failed`.

Download with `GET /music/jobs/{id}/artifacts/{kind}`:

| Kind | Contents |
| --- | --- |
| `audio` | Original full song |
| `drums` | HDemucs drum stem |
| `accompaniment` | Sum of separated bass, vocals and other stems |
| `raw_midi` | Unfiltered transcription of the drum stem, for diagnosis |
| `midi` | Drum-channel notes only, preserving timing and tempo |
| `percussion` | Your samples playing the drum MIDI, before remix level matching |
| `rendered` | **Final mix: replacement percussion + retained accompaniment** |

Mix gains default to 0 dB and accept -24 to +12 dB. Replacement percussion is
first level-matched toward the original drum stem using active-frame RMS;
upward gain is capped at 12 dB. The final mix is attenuated together if needed
to keep peaks below 0.98. Its duration matches the accompaniment; replacement
tails beyond the song are cropped with a short fade. No time stretching or
automatic grid quantization is applied.

If no drum notes are recovered, the job fails rather than synthesizing melodic
leakage as percussion. Available original/stem files remain downloadable. Stem
separation is approximate: some percussion may remain in the accompaniment.

## Local use without the API

Use the same environment and requirements as the main README. No separate
Demucs installation is needed. TorchAudio 2.8 supplies the pretrained
[`HDEMUCS_HIGH_MUSDB_PLUS` model](https://docs.pytorch.org/audio/2.8.0/generated/torchaudio.pipelines.HDEMUCS_HIGH_MUSDB_PLUS.html).
Its checkpoint downloads on first use to `outputs/.model_cache/torch`, unless
`TORCH_HOME` is set. Model stages use separate processes to release GPU memory.

From `pattern_testing`:

```powershell
python percussion_pipeline.py --prompt "A simple trap beat with bass and bells" --duration 10 --classifications Sounds/everyday_classifications.json --output-dir outputs/percussion_local
```

To test an existing WAV instead:

```powershell
python percussion_pipeline.py --audio outputs/local/generated.wav --classifications Sounds/everyday_classifications.json --output-dir outputs/percussion_local
```

Use `--mapping mapping.json` instead of `--classifications` for an explicit
drum mapping. Optional `--sounds`, `--drums-gain-db` and
`--accompaniment-gain-db` control the sample library and blend. The output
contains all files listed above, `mapping.json`, and `result.json`.

The Vercel helper `createPercussionJob(options)` submits this optional path.
Your server must check ownership of any `source_job_id` before forwarding it.
