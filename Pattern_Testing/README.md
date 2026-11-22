# Everyday sounds music pipeline

**Prompt -> MusicGen Small -> YourMT3+ MIDI -> everyday-sound WAV.**

## Run locally (no worker/API needed)

Use Python 3.10-3.12, Git and Git LFS. From the repository root:

```powershell
cd pattern_testing
python -m venv .venv
.venv/Scripts/Activate.ps1
python -m pip install -r requirements.txt
python -m pip check
```

On Linux/macOS, activate with `source .venv/bin/activate` instead.
Everything uses this single environment. First inference downloads model weights.
For the tested NVIDIA GPU setup, install the matching CUDA builds:

```powershell
python -m pip install torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu128
```

Optional: reuse this project's local model cache (PowerShell):

```powershell
$env:HF_HOME = "outputs/.model_cache/huggingface"
$env:MT3_CHECKPOINT_DIR = "outputs/.model_cache/mt3"
```

Generate audio and transcribe it:

```powershell
python pipeline.py "{description here}" --duration 10 --output-dir outputs/local
```

This saves `generated.wav`, `transcribed.mid` and `result.json`.
Use a fresh output directory to keep each run. Duration must be 1-30 seconds.

To apply everyday sounds, create a MIDI-aware mapping and render it:

```powershell
python Apply_Sounds/yamnet_mapping.py Sounds/everyday_classifications.json --midi outputs/local/transcribed.mid --output outputs/local/mapping.json
python Apply_Sounds/render_midi_sounds.py "../outputs/local/transcribed.mid" --mapping "../outputs/local/mapping.json" --sounds "../Sounds" --output-dir "../outputs/local" --output rendered.wav
```

The final file is `outputs/local/rendered.wav`. The renderer CLI resolves paths
from `Apply_Sounds`; the other commands resolve paths from your working directory.
Replace the example classifications with your own sound filenames and trusted
YAMNet classes. A supplied `user_class` overrides the model class.
See [mapping details](Apply_Sounds/yamnet/README.md) for the input format.
Samples are smoothed and level-balanced before MIDI velocity is applied.

## Run the worker API

From `pattern_testing`, in the same environment:

```powershell
$env:MUSIC_API_KEY = "replace-with-a-long-random-secret"
python -m uvicorn api:app --host 127.0.0.1 --port 8000 --workers 1
# This could be subject to change depending on integration
```




### IMPORTANT FOR INTEGRATION WITH APP 
Every request requires `Authorization: Bearer <MUSIC_API_KEY>`.
Set environment variables in your shell/host; `.env.example` is not auto-loaded.

| Endpoint | Purpose |
| --- | --- |
| `POST /music/jobs` | Generate audio and transcribe MIDI. Body: `prompt`, optional `duration` (default 10), and optional `mapping` or `sounds` for rendering. Returns a job ID. |
| `POST /music/percussion-jobs` | Optional HDemucs drum replacement mixed with original accompaniment. Accepts a prompt or source job, plus a drum mapping or classified sounds. |
| `GET /music/jobs/{id}` | Poll progress, results and download links. |
| `GET /music/jobs/{id}/artifacts/audio` | Download the original generated WAV. |
| `GET /music/jobs/{id}/artifacts/midi` | Download the transcribed MIDI. |
| `GET /music/jobs/{id}/artifacts/rendered` | Download the sample-rendered WAV, if available. |
| `GET /music/yamnet/classes` | List all 521 YAMNet classes and their instrument assignments. |
| `POST /music/mappings` | Assign database-classified sounds to MIDI instruments. Body: `sounds`, required `source_job_id`, optional `fallback` (`nearest` or `omit`). |
| `POST /music/renders` | Render an existing job's MIDI. Body: `source_job_id` and either `mapping` or `sounds`. Returns a new job ID. |

For **replace percussion, keep the rest of the song**, see
[the optional percussion pipeline](PERCUSSION.md) for requests, local commands
and stem downloads. Its `rendered` artifact is the final combined mix.

Typical flow: create job -> poll until `completed` -> build a mapping with
its `source_job_id` -> submit that mapping to `/music/renders` -> poll and download.
Jobs return 202; a full queue returns 429. Failed jobs include an error.
A completed generation may include `render_error` while its original WAV and
MIDI remain available. API samples come from Supabase; see below.

### Supabase samples in API requests

Set `SUPABASE_URL` and `SUPABASE_ANON_KEY` on the worker (the existing
`VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` are accepted as fallbacks).
Use the publishable/anon key, not a service-role key. For requests containing
samples, forward the signed-in user's access token in a second header:

```text
Authorization: Bearer <MUSIC_API_KEY>
X-Supabase-Authorization: Bearer <user Supabase access token>
```

The `file` field now contains a canonical **sound UUID from `public.sounds`**,
not a local filename, storage path, or URL. For example, `/music/mappings` takes:

```json
{
  "source_job_id": "<completed-generation-job-uuid>",
  "sounds": [{"file": "11111111-1111-4111-8111-111111111111"}]
}
```

Mappings returned by this endpoint retain those UUIDs in their `file` fields.
Pass them unchanged to `/music/renders` or `/music/jobs`, forwarding the user
token again. `/music/percussion-jobs` supports the same UUIDs in `sounds` or
`mapping`. In a manual mapping, a string value is also a sound UUID:
`{"drums": {"36": "11111111-1111-4111-8111-111111111111"}}`.

The worker looks up each sound's `visibility` and `storage_path` under the
user's RLS permissions, then downloads from `sounds-private` or `sounds-public`.
Samples are staged before queuing so the queued job does not retain a user
token. Temporary files are isolated per request and removed on completion or
failure. Missing/inaccessible sounds fail before a job is accepted; downloads
are limited to 10 MB per sample. Requests without samples need only the worker
key. Compressed recordings such as WebM require FFmpeg on the worker's PATH.

The Node background worker uses `integration/worker-client.js` to submit jobs
and retrieve results. It sends `job_id` equal to the beat UUID for idempotent
retries and `sample_sources` containing short-lived Supabase signed URLs and
persisted per-beat classifications. This trusted server path requires the
worker key and does not require a user JWT. Direct user-scoped worker requests
can continue using `X-Supabase-Authorization` as described above. See
[application setup](../docs/integration.md#real-generation-after-the-background-worker-merge).

Local CLI commands still accept sample filenames and `--sounds`; only the
HTTP API uses Supabase IDs.

### Automatic assignment from database roles

The worker reads `sounds.classification` from Supabase: `Percussion`, `Rhythmic`,
`Melodic`, `Ambient`, or `Transition`. Request-supplied classifications,
`yamnet_class`, and `user_class` do not override this database role. Sounds
without a valid classification are rejected before an automatic job is queued.
Explicit manual mappings can still use unclassified sounds.

The trusted Node background service additionally supports a `sample_sources`
manifest: these roles come from persisted `sounds_beats.category`, falling back
to the sound's global classification. This preserves the merged frontend's
per-beat role choices. Only the backend holding `MUSIC_API_KEY` may submit
these scoped, signed sample URLs.

To generate and automatically render in one job, send `POST /music/jobs`:

```json
{
  "prompt": "A relaxed house beat",
  "duration": 10,
  "sounds": [
    {"file": "11111111-1111-4111-8111-111111111111"},
    {"file": "22222222-2222-4222-8222-222222222222"}
  ]
}
```

Assignment runs after transcription and uses only instruments with playable
notes. `Apply_Sounds/role_mapping.py` contains the editable compatibility policy:

| MIDI instrument | Preferred role | Compatible fallback |
| --- | --- | --- |
| Most drum pitches | Percussion | Rhythmic |
| Hats, shakers, scrapes | Rhythmic | Percussion |
| Crash/effect cymbals | Transition | Percussion |
| Pitched programs, including bass, keys, strings, leads | Melodic | None |
| Synth pads (programs 88–95) | Ambient | None |
| Synth effects (96–103) | Ambient | Transition |
| Percussive programs (112–119) | Percussion | Rhythmic, Melodic |
| Sound effects (120–127) | Transition | None |

Programs are zero-based. Within the best matching role, the mapper distributes
instruments across samples in request order and reuses samples if necessary.
Instruments without a compatible sound are omitted and reported; surplus
samples are reported as unused. It does not invent instruments or alter MIDI
timing. A transition sample follows its assigned MIDI notes; phrase-boundary
scheduling is not added by this mapper.

`mapping_report` contains assignments, reuse flags, unused samples and unmapped
instruments. Generation retains its original WAV and MIDI with `render_error`
if no compatible mapping can be rendered. For an existing MIDI, use
`/music/mappings` to inspect the report before rendering, or pass `sounds`
directly to `/music/renders` to assign and render in one job. Supply `mapping`
or `sounds`, not both. `fallback=omit` on `/music/mappings` restricts assignment
to preferred roles; `nearest` also permits the compatible roles in the table.

Optional `root_note` and `loop` are playback controls, not classification
overrides. Root note defaults to MIDI 60; pitch detection is not performed.
Ambient samples loop by default; other roles play without looping.
The local YAMNet CLI mapper remains available for the bundled demonstrations.

For deployment, Vercel forwards authenticated requests to this separate Python
worker; Supabase stores finished files. Keep the worker key server-side and
check user ownership before forwarding job requests. The server-side helpers in
`integration/worker-client.js` are examples, not installed Vercel routes.
Use one worker process/replica with persistent output storage; its queue has
four slots and interrupted jobs fail after restart. This is a prototype queue.

## Examples and checks

- [Listening examples and results](outputs/README.md)
- [Sound samples](Sounds/README.md)
- Tests: `python -m unittest discover -s tests -v`

Transcription can miss instruments and notes. A BPM or instrument in the prompt
is guidance, not a guarantee. HDemucs separation is available only through the
optional percussion path.
Model caches, virtual environments, logs and runtime output folders are ignored;
curated listening examples under `outputs` are included for review.
