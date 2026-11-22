"""Single-process prototype worker API. Run with one uvicorn worker."""
import hmac
import json
import logging
import os
import shutil
import threading
import tempfile
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from pipeline import ROOT, apply_sounds, run_pipeline
from Apply_Sounds.yamnet_mapping import load_class_table
from Apply_Sounds.role_mapping import build_role_mapping, validate_sounds
from percussion_pipeline import run_percussion_pipeline
from supabase_sounds import classified_sounds, get_sound_store, sample_ids, SignedSounds

OUTPUTS = Path(os.getenv("MUSIC_OUTPUT_DIR", str(ROOT / "outputs"))).resolve()
POOL = ThreadPoolExecutor(max_workers=1)
SLOTS = threading.BoundedSemaphore(4)  # One running job and at most three waiting.
LOCK = threading.Lock()
SUBMISSION_LOCK = threading.Lock()
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


def validate_mapping(mapping, sounds_dir):
    """Validate mappings against this request's staged Supabase samples."""
    if mapping is None:
        return
    if set(mapping) - {"programs", "drums"}:
        raise HTTPException(422, "Mapping supports programs and drums")
    try:
        for section in mapping.values():
            for entry in section.values():
                name = entry if isinstance(entry, str) else entry["file"]
                sample = (sounds_dir / name).resolve()
                if not sample.is_relative_to(sounds_dir):
                    raise ValueError("Sample path must stay inside the staged sound directory")
        from Apply_Sounds.render_midi_sounds import parse_mapping
        parse_mapping(mapping, sounds_dir)
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
    job_id: UUID | None = None
    sample_sources: list[dict] | None = Field(default=None, min_length=1, max_length=4)
    prompt: str = Field(min_length=1, max_length=2000)
    duration: float = Field(default=10, ge=1, le=30)
    mapping: dict | None = None
    sounds: list[dict] | None = Field(default=None, min_length=1, max_length=1000)


class RenderRequest(BaseModel):
    source_job_id: str
    mapping: dict | None = None
    sounds: list[dict] | None = Field(default=None, min_length=1, max_length=1000)


class MappingRequest(BaseModel):
    sounds: list[dict] = Field(min_length=1, max_length=1000)
    source_job_id: str
    fallback: str = "nearest"


class PercussionRequest(BaseModel):
    prompt: str | None = Field(default=None, min_length=1, max_length=2000)
    source_job_id: str | None = None
    duration: float = Field(default=10, ge=1, le=30)
    mapping: dict | None = None
    sounds: list[dict] | None = Field(default=None, min_length=1, max_length=1000)
    drums_gain_db: float = Field(default=0, ge=-24, le=12, allow_inf_nan=False)
    accompaniment_gain_db: float = Field(default=0, ge=-24, le=12, allow_inf_nan=False)


def validate_percussion_request(request, sounds_dir):
    if (request.prompt is None) == (request.source_job_id is None):
        raise HTTPException(422, "Supply exactly one of prompt or source_job_id")
    if request.prompt is not None and not request.prompt.strip():
        raise HTTPException(422, "Prompt must not be blank")
    if (request.mapping is None) == (request.sounds is None):
        raise HTTPException(422, "Supply exactly one of mapping or classified sounds")
    if request.source_job_id is not None:
        source = read_job(request.source_job_id)
        if source["status"] not in {"completed", "failed"} or not (job_dir(request.source_job_id) / "generated.wav").is_file():
            raise HTTPException(409, "Source audio is not available yet")
    if request.mapping is not None:
        if request.mapping.get("programs") or not request.mapping.get("drums"):
            raise HTTPException(422, "Use a drums mapping without programs")
        validate_mapping(request.mapping, sounds_dir)
    else:
        try:
            validate_sounds(request.sounds)
            for sound in request.sounds:
                sample = (sounds_dir / sound["file"]).resolve()
                if not sample.is_relative_to(sounds_dir) or not sample.is_file():
                    raise ValueError("Every classified sample must be available from Supabase")
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc


@app.get("/music/yamnet/classes")
def get_yamnet_classes():
    return load_class_table()


@app.post("/music/mappings")
def create_mapping(request: MappingRequest, store=Depends(get_sound_store)):
    source = read_job(request.source_job_id)
    midi = job_dir(request.source_job_id) / "transcribed.mid"
    if source["status"] not in {"completed", "failed"} or not midi.is_file():
        raise HTTPException(409, "Source MIDI is not available yet")
    # Check every supplied sound, including ones not chosen by the mapper.
    ids = sample_ids(sounds=request.sounds)
    if store is None:
        raise HTTPException(401, "Supply X-Supabase-Authorization: Bearer <user access token>")
    with tempfile.TemporaryDirectory(prefix="music-sounds-") as temporary:
        records = store.download(ids, Path(temporary))
        try:
            result = build_role_mapping(classified_sounds(request.sounds, records), midi,
                                        fallback=request.fallback)
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc
        if any(result["mapping"].values()):
            validate_mapping(result["mapping"], Path(temporary).resolve())
    return result


def execute(folder, request, samples):
    try:
        sounds_dir = Path(samples.name).resolve()
        if isinstance(request, PercussionRequest):
            source_audio = job_dir(request.source_job_id) / "generated.wav" if request.source_job_id else None
            result = run_percussion_pipeline(
                request.prompt, folder, source_audio=source_audio, duration=request.duration,
                mapping=request.mapping, sounds=request.sounds, sounds_dir=sounds_dir,
                mapping_builder=build_role_mapping,
                model=os.getenv("MUSICGEN_MODEL", "facebook/musicgen-small"),
                drums_gain_db=request.drums_gain_db, accompaniment_gain_db=request.accompaniment_gain_db,
                progress=lambda stage: update_job(folder, status=stage),
            )
        elif isinstance(request, GenerationRequest):
            result = run_pipeline(
                request.prompt, folder, duration=request.duration, mapping=request.mapping, sounds=request.sounds,
                sounds_dir=sounds_dir, model=os.getenv("MUSICGEN_MODEL", "facebook/musicgen-small"),
                progress=lambda stage: update_job(folder, status=stage),
            )
        else:
            update_job(folder, status="rendering")
            shutil.copyfile(job_dir(request.source_job_id) / "transcribed.mid", folder / "transcribed.mid")
            report = None
            mapping = request.mapping
            if request.sounds is not None:
                report = build_role_mapping(request.sounds, folder / "transcribed.mid")
                mapping = report["mapping"]
                if not any(mapping.values()):
                    raise ValueError("No selected sounds have roles compatible with the MIDI instruments")
            rendered = apply_sounds(folder / "transcribed.mid", mapping,
                                    folder / "rendered.wav", sounds_dir=sounds_dir)
            result = {"artifacts": {"midi": "transcribed.mid", "rendered": "rendered.wav"}, "render": rendered}
            if report is not None:
                result.update(mapping=mapping, mapping_report=report)
        update_job(folder, status="completed", result=result)
    except Exception:
        logging.exception("Music job %s failed", folder.name)
        # Keep subprocess details/paths in worker logs, away from API responses.
        update_job(folder, status="failed", error="Processing failed; inspect worker logs")
    finally:
        try:
            samples.cleanup()
        finally:
            SLOTS.release()


def submit(request, store=None):
    if isinstance(request, GenerationRequest) and request.sample_sources is not None:
        store = SignedSounds(request.sample_sources)
    if request.mapping is not None and request.sounds is not None:
        raise HTTPException(422, "Supply mapping or sounds, not both")
    if isinstance(request, RenderRequest) and request.mapping is None and request.sounds is None:
        raise HTTPException(422, "Supply mapping or sounds")
    ids = sample_ids(mapping=request.mapping, sounds=getattr(request, "sounds", None))
    if ids and store is None:
        raise HTTPException(401, "Supply X-Supabase-Authorization: Bearer <user access token>")
    if not SLOTS.acquire(blocking=False):
        raise HTTPException(429, "Worker queue is full; retry later")
    samples = None
    try:
        samples = tempfile.TemporaryDirectory(prefix="music-sounds-")
        sounds_dir = Path(samples.name).resolve()
        if ids:
            records = store.download(ids, sounds_dir)
            if request.sounds is not None:
                request = request.model_copy(update={"sounds": classified_sounds(request.sounds, records)})
                try:
                    validate_sounds(request.sounds)
                except ValueError as exc:
                    raise HTTPException(422, str(exc)) from exc
        if isinstance(request, PercussionRequest):
            validate_percussion_request(request, sounds_dir)
        else:
            validate_mapping(request.mapping, sounds_dir)
        folder = OUTPUTS / str(getattr(request, "job_id", None) or uuid4())
        folder.mkdir(parents=True)
        update_job(folder, id=folder.name, status="queued")
        POOL.submit(execute, folder, request, samples)
        return {"id": folder.name, "status": "queued", "status_url": f"/music/jobs/{folder.name}"}
    except Exception:
        try:
            if samples is not None:
                samples.cleanup()
        finally:
            SLOTS.release()
        raise


@app.post("/music/jobs", status_code=202)
def create_job(request: GenerationRequest, store=Depends(get_sound_store)):
    if not request.prompt.strip():
        raise HTTPException(422, "Prompt must not be blank")
    # Node uses the beat UUID as an idempotency key. A retry after a lost
    # response or API restart resumes the same job rather than generating again.
    with SUBMISSION_LOCK:
        if request.job_id is not None and (job_dir(str(request.job_id)) / "job.json").is_file():
            job = read_job(str(request.job_id))
            return {"id": job["id"], "status": job["status"], "status_url": f"/music/jobs/{job['id']}"}
        return submit(request, store)


@app.post("/music/percussion-jobs", status_code=202)
def create_percussion_job(request: PercussionRequest, store=Depends(get_sound_store)):
    return submit(request, store)


@app.post("/music/renders", status_code=202)
def create_render(request: RenderRequest, store=Depends(get_sound_store)):
    read_job(request.source_job_id)
    if not (job_dir(request.source_job_id) / "transcribed.mid").is_file():
        raise HTTPException(409, "Source MIDI is not available yet")
    return submit(request, store)


@app.get("/music/jobs/{job_id}")
def get_job(job_id: str):
    data = read_job(job_id)
    # A successfully transcribed MIDI can be downloaded even if a later stage failed.
    data["downloads"] = {kind: f"/music/jobs/{job_id}/artifacts/{kind}"
                         for kind, name in ARTIFACTS.items() if (job_dir(job_id) / name).is_file()
                         and data["status"] in {"completed", "failed"}}
    return data


ARTIFACTS = {"audio": "generated.wav", "midi": "transcribed.mid", "rendered": "rendered.wav",
             "drums": "drums.wav", "accompaniment": "accompaniment.wav",
             "percussion": "percussion.wav", "raw_midi": "raw_transcribed.mid"}


@app.get("/music/jobs/{job_id}/artifacts/{kind}")
def download(job_id: str, kind: str):
    data = read_job(job_id)
    if kind not in ARTIFACTS:
        raise HTTPException(404, "Artifact not found")
    path = job_dir(job_id) / ARTIFACTS[kind]
    if data["status"] not in {"completed", "failed"} or not path.is_file():
        raise HTTPException(404, "Artifact not available")
    return FileResponse(path, media_type="audio/midi" if path.suffix == ".mid" else "audio/wav", filename=path.name)
