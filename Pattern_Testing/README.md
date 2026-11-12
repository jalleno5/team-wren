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
| `POST /music/jobs` | Generate audio and transcribe MIDI. Body: `prompt`, optional `duration` (default 10) and `mapping`. Returns a job ID. |
| `POST /music/percussion-jobs` | Optional HDemucs drum replacement mixed with original accompaniment. Accepts a prompt or source job, plus a drum mapping or classified sounds. |
| `GET /music/jobs/{id}` | Poll progress, results and download links. |
| `GET /music/jobs/{id}/artifacts/audio` | Download the original generated WAV. |
| `GET /music/jobs/{id}/artifacts/midi` | Download the transcribed MIDI. |
| `GET /music/jobs/{id}/artifacts/rendered` | Download the sample-rendered WAV, if available. |
| `GET /music/yamnet/classes` | List all 521 YAMNet classes and their instrument assignments. |
| `POST /music/mappings` | Build a sound mapping. Body: `sounds`, optional `source_job_id` and `fallback` (`nearest` or `omit`). |
| `POST /music/renders` | Render an existing job's MIDI. Body: `source_job_id` and `mapping`. Returns a new job ID. |

For **replace percussion, keep the rest of the song**, see
[the optional percussion pipeline](PERCUSSION.md) for requests, local commands
and stem downloads. Its `rendered` artifact is the final combined mix.

Typical flow: create job -> poll until `completed` -> build a mapping with
its `source_job_id` -> submit that mapping to `/music/renders` -> poll and download.
Jobs return 202; a full queue returns 429. Failed jobs include an error.
A completed generation may include `render_error` while its original WAV and
MIDI remain available. Samples must already exist in the worker's sound library.

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
