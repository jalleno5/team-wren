# Everyday sounds music pipeline

All code and examples here stay inside `pattern_testing` (Git may display the
existing directory as `Pattern_Testing` on Windows).

`prompt -> MusicGen WAV -> YourMT3+ MIDI -> optional sample-rendered WAV`

The MIDI is a separate downloadable artifact. Applying sounds creates an audio
file: MIDI itself stores notes/instruments, rather than the everyday sound clips.
Example MIDI files live in `MIDI_sequences`; existing audio examples are preserved
in `Songs/Music_Gen_Songs` and `Songs/Rendered_Examples`. Sample clips live in `Sounds`.

`Sounds` also includes ten synthetic everyday foley samples, each under 1.5
seconds. See [the sound pack guide](Sounds/README.md) for the list and use
`Apply_Sounds/everyday_sound_map.json` to try them on MIDI.

## Setup and run

Use Python 3.10–3.12 and install Git before installing dependencies. All commands
below run from `pattern_testing`, using one `.venv` and one `requirements.txt`
for generation, transcription, rendering and the API.

From the repository root:

```powershell
cd pattern_testing
```

Create the environment once (skip this command if `.venv` already exists):

```powershell
python -m venv .venv
```

Install or update its dependencies:

```powershell
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m pip check
```

These commands use the environment's Python directly; activation is optional.

MusicGen and YourMT3 share this environment and its dependencies. Each model
runs in a child process using the same Python interpreter so its GPU memory is
released before the next stage. A second virtual environment is unnecessary.
The declared dependency ranges overlap; full model inference still needs to be
verified on your worker hardware.

For a Linux worker/container, install this same `requirements.txt` and run
`python -m uvicorn api:app --host 0.0.0.0 --port 8000 --workers 1`.
An isolated container can use its system Python; an additional virtual
environment inside the container is optional. Keep one dependency set for both
local development and deployment.

First inference downloads weights. Install a CUDA-compatible PyTorch build for
your GPU when applicable. `musicgen-small` is the default; use `--model
facebook/musicgen-large` for the existing larger model. Outputs go to
`outputs/local/{generated.wav,transcribed.mid,result.json}`. Choose a fresh
`--output-dir` per CLI run to preserve earlier outputs. Generation is capped at
30 seconds. Model installation and actual inference need validation on your
chosen worker hardware; the lightweight tests do not download or run models.

Generate music and transcribe it to MIDI:

```powershell
.venv/Scripts/python pipeline.py "A sparse funky bass and drum groove" --duration 10 --output-dir outputs/first-song
```

To also render the MIDI with your sound mapping:

```powershell
.venv/Scripts/python pipeline.py "A sparse funky bass and drum groove" --duration 10 --output-dir outputs/mapped-song --mapping Apply_Sounds/sound_map.json --sounds Sounds
```

The output folder contains `generated.wav`, `transcribed.mid` and `result.json`,
plus `rendered.wav` when mapping succeeds.

## Apply sounds independently

Use an existing MIDI without running either model:

```powershell
.venv/Scripts/python Apply_Sounds/render_midi_sounds.py "../MIDI_sequences/jazz.mid" --mapping sound_map.json --output jazz_custom.wav
```

The renderer CLI resolves relative paths from `Apply_Sounds`, and writes this
example to `outputs/rendered/jazz_custom.wav`.
You can also call the renderer from Python using the same environment:

```python
from pathlib import Path
from Apply_Sounds.render_midi_sounds import apply_sounds

result = apply_sounds(
    Path("MIDI_sequences/popular.mid"),
    {"programs": {"0": {"file": "whoosh.wav", "root_note": 60, "loop": True}},
     "drums": {"36": "kick.wav", "38": "snare.wav", "42": "hi-hat.wav"}},
    Path("outputs/custom.wav"),
    sounds_dir=Path("Sounds"),
)
```

`mapping` also accepts a JSON file path. Program numbers and drum pitches are
0–127; programs use zero-based General MIDI numbering. Program mappings shift
sample pitch relative to `root_note`; drums play once without pitch shifting.
Pitch shifting uses resampling and changes timbre/playback speed. This renderer
handles tempo changes, velocity, overlapping notes and program changes; it does
not implement sustain pedals or the full MIDI controller specification. Unmapped
notes are reported and skipped; zero matching notes raises an error. Inspect
`result.json`'s MIDI inventory before selecting mappings. Existing
`Apply_Sounds/new_sound_map.py` can create a template for a MIDI file.

## Worker API

To derive mappings from trusted YAMNet labels or user-corrected classes, see
[YAMNet mapping](Apply_Sounds/yamnet/README.md). It covers all 521 classes and
can adapt the selection to the instruments present in a MIDI.

```powershell
$env:MUSIC_API_KEY = "your-long-random-secret"
.venv/Scripts/python -m uvicorn api:app --host 127.0.0.1 --port 8000 --workers 1
```

Every route needs `Authorization: Bearer <MUSIC_API_KEY>`. HTTPS should be
provided by your deployment host. See `.env.example` for settings. Environment
files are examples and are not automatically loaded.

| Request | Result |
| --- | --- |
| `POST /music/jobs` with `{"prompt":"funk groove","duration":10}` | 202 with `id` and `status_url` |
| `GET /music/jobs/{id}` | Status, results, available download routes |
| `GET /music/jobs/{id}/artifacts/midi` | Downloadable `.mid` |
| `GET /music/jobs/{id}/artifacts/audio` | Original generated WAV |
| `GET /music/jobs/{id}/artifacts/rendered` | Sample-rendered WAV, when requested |
| `POST /music/renders` with `{"source_job_id":"...","mapping":{...}}` | New render job using existing MIDI |
| `GET /music/yamnet/classes` | All 521 classes and their instrument assignments |
| `POST /music/mappings` with `{"sounds":[...],"source_job_id":"..."}` | Renderer mapping and selection report from classified sounds |

`POST /music/jobs` optionally accepts `mapping`. API sample paths must stay within
`MUSIC_SOUNDS_DIR`. The API currently uses the worker's sound library; arbitrary
user uploads need to be staged from Supabase into that library before rendering.
No remote URLs or arbitrary commands are accepted. Poll every few seconds until
`completed` or `failed`. A render error can accompany a completed generation job:
its MIDI and original WAV are still available.

This prototype has one serial model worker and a four-job admission limit
(429 when full). Manifests persist on disk; interrupted jobs become failed after
restart. Use **one process/replica**, persistent storage, and a retention policy.
It does not provide durable retries, cancellation, distributed queues or
per-user authorization. For multiple replicas, replace the in-process executor
with a durable queue and store job state in Supabase.

## Vite + Supabase + Vercel handoff

1. Vite calls your authenticated Vercel routes to create jobs and poll status.
2. Vercel verifies the Supabase session, stores `{user_id, worker_job_id}`, and
   checks ownership before forwarding any status, render or download request.
3. Vercel submits a short request to this separately hosted Python worker.
   Model inference continues there while Vercel returns the job ID immediately.
4. Once complete, copy artifacts to a private Supabase Storage bucket under
   `{user_id}/{job_id}/...`; return signed URLs for playback/download.

`integration/worker-client.js` provides server-side submission, polling and
MIDI-to-Supabase helpers. These are integration examples, not installed routes.
The worker key and Supabase service credentials stay in server environment
variables. Never expose them with a `VITE_` prefix. Configure Storage ownership
policies for browser access, or have your authenticated server issue signed
URLs after ownership checks. No cloud resources or database changes are applied
by these files.

References: [MusicGen API](https://huggingface.co/docs/transformers/model_doc/musicgen),
[MT3-Infer YourMT3 adapter and installation](https://github.com/openmirlab/mt3-infer),
[Vercel function limits](https://vercel.com/docs/functions/limitations),
[Supabase Storage access control](https://supabase.com/docs/guides/storage/security/access-control).
The transcription dependency tracks upstream Git; pin a tested commit before
production deployment. Review model weight licenses before commercial use.

## Checks

```powershell
.venv/Scripts/python -m unittest discover -s tests -v
```

Tests exercise real MIDI/sample rendering plus pipeline orchestration and worker
validation without downloading weights.
