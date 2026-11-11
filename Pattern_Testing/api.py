"""Single-process prototype worker API. Run with one uvicorn worker."""
import hmac
import json
import logging
import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from pipeline import ROOT, apply_sounds, run_pipeline
from Apply_Sounds.yamnet_mapping import build_sound_mapping, load_class_table

OUTPUTS = Path(os.getenv("MUSIC_OUTPUT_DIR", str(ROOT / "outputs"))).resolve()
SOUNDS = Path(os.getenv("MUSIC_SOUNDS_DIR", str(ROOT / "Sounds"))).resolve()
POOL = ThreadPoolExecutor(max_workers=1)
SLOTS = threading.BoundedSemaphore(4)  # One running job and at most three waiting.
LOCK = threading.Lock()
AUTH = HTTPBearer(auto_error=False)


def authorize(credentials: HTTPAuthorizationCredentials = Depends(AUTH)):
    key = os.getenv("MUSIC_API_KEY", "")
    if not key:
        raise HTTPException(503, "Worker MUSIC_API_KEY is not configured")
    if credentials is None or not hmac.compare_digest(credentials.credentials, key):
        raise HTTPException(401, "Invalid worker credentials")


def job_dir(job_id: str) -> Path:
    try:
        return OUTPUTS / str(UUID(job_id))
    except ValueError:
        raise HTTPException(404, "Job not found")


def read_job(job_id):
    path = job_dir(job_id) / "job.json"
    with LOCK:
        if not path.is_file():
            raise HTTPException(404, "Job not found")
        return json.loads(path.read_text(encoding="utf-8"))


def update_job(folder, **changes):
    with LOCK:
        path = folder / "job.json"
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        data.update(changes)
        temporary = folder / "job.tmp"
        temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temporary.replace(path)


def validate_mapping(mapping):
    """API sample names are confined to the configured sound library."""
    if mapping is None:
        return
    if set(mapping) - {"programs", "drums"}:
        raise HTTPException(422, "Mapping supports programs and drums")
    try:
        for section in mapping.values():
            for entry in section.values():
                name = entry if isinstance(entry, str) else entry["file"]
                sample = (SOUNDS / name).resolve()
                if not sample.is_relative_to(SOUNDS):
                    raise ValueError("Sample path must stay inside the sound library")
        from Apply_Sounds.render_midi_sounds import parse_mapping
        parse_mapping(mapping, SOUNDS)
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@asynccontextmanager
async def lifespan(app):
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    for path in OUTPUTS.glob("*/job.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("status") not in {"completed", "failed"}:
            update_job(path.parent, status="failed", error="Worker restarted; submit a new job")
    yield
    POOL.shutdown(wait=True)


app = FastAPI(title="Everyday sound music worker", lifespan=lifespan,
              dependencies=[Depends(authorize)])


class GenerationRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    duration: float = Field(default=10, ge=1, le=30)
    mapping: dict | None = None


class RenderRequest(BaseModel):
    source_job_id: str
    mapping: dict


class MappingRequest(BaseModel):
    sounds: list[dict] = Field(min_length=1, max_length=1000)
    source_job_id: str | None = None
    fallback: str = "nearest"


@app.get("/music/yamnet/classes")
def get_yamnet_classes():
    return load_class_table()


@app.post("/music/mappings")
def create_mapping(request: MappingRequest):
    midi = None
    if request.source_job_id is not None:
        source = read_job(request.source_job_id)
        midi = job_dir(request.source_job_id) / "transcribed.mid"
        if source["status"] not in {"completed", "failed"} or not midi.is_file():
            raise HTTPException(409, "Source MIDI is not available yet")
    try:
        result = build_sound_mapping(request.sounds, midi, fallback=request.fallback)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    if any(result["mapping"].values()):
        validate_mapping(result["mapping"])
    return result


def execute(folder, request):
    try:
        if isinstance(request, GenerationRequest):
            result = run_pipeline(
                request.prompt, folder, duration=request.duration, mapping=request.mapping,
                sounds_dir=SOUNDS, model=os.getenv("MUSICGEN_MODEL", "facebook/musicgen-small"),
                progress=lambda stage: update_job(folder, status=stage),
            )
        else:
            update_job(folder, status="rendering")
            shutil.copyfile(job_dir(request.source_job_id) / "transcribed.mid", folder / "transcribed.mid")
            rendered = apply_sounds(folder / "transcribed.mid", request.mapping,
                                    folder / "rendered.wav", sounds_dir=SOUNDS)
            result = {"artifacts": {"midi": "transcribed.mid", "rendered": "rendered.wav"}, "render": rendered}
        update_job(folder, status="completed", result=result)
    except Exception:
        logging.exception("Music job %s failed", folder.name)
        # Keep subprocess details/paths in worker logs, away from API responses.
        update_job(folder, status="failed", error="Processing failed; inspect worker logs")
    finally:
        SLOTS.release()


def submit(request):
    validate_mapping(request.mapping)
    if not SLOTS.acquire(blocking=False):
        raise HTTPException(429, "Worker queue is full; retry later")
    try:
        folder = OUTPUTS / str(uuid4())
        folder.mkdir(parents=True)
        update_job(folder, id=folder.name, status="queued")
        POOL.submit(execute, folder, request)
        return {"id": folder.name, "status": "queued", "status_url": f"/music/jobs/{folder.name}"}
    except Exception:
        SLOTS.release()
        raise


@app.post("/music/jobs", status_code=202)
def create_job(request: GenerationRequest):
    if not request.prompt.strip():
        raise HTTPException(422, "Prompt must not be blank")
    return submit(request)


@app.post("/music/renders", status_code=202)
def create_render(request: RenderRequest):
    read_job(request.source_job_id)
    if not (job_dir(request.source_job_id) / "transcribed.mid").is_file():
        raise HTTPException(409, "Source MIDI is not available yet")
    return submit(request)


@app.get("/music/jobs/{job_id}")
def get_job(job_id: str):
    data = read_job(job_id)
    # A successfully transcribed MIDI can be downloaded even if a later stage failed.
    data["downloads"] = {kind: f"/music/jobs/{job_id}/artifacts/{kind}"
                         for kind, name in ARTIFACTS.items() if (job_dir(job_id) / name).is_file()
                         and data["status"] in {"completed", "failed"}}
    return data


ARTIFACTS = {"audio": "generated.wav", "midi": "transcribed.mid", "rendered": "rendered.wav"}


@app.get("/music/jobs/{job_id}/artifacts/{kind}")
def download(job_id: str, kind: str):
    data = read_job(job_id)
    if kind not in ARTIFACTS:
        raise HTTPException(404, "Artifact not found")
    path = job_dir(job_id) / ARTIFACTS[kind]
    if data["status"] not in {"completed", "failed"} or not path.is_file():
        raise HTTPException(404, "Artifact not available")
    return FileResponse(path, media_type="audio/midi" if kind == "midi" else "audio/wav", filename=path.name)
