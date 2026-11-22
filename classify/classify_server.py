"""
Encore classify endpoint.

Accepts an audio file (upload or URL) and returns YAMNet sound labels
plus 5-role musical role suggestions.

Run:
    pip install fastapi uvicorn python-multipart httpx
    uvicorn classify_server:app --host 0.0.0.0 --port 8000

"""
import os
import tempfile
from pathlib import Path

import httpx
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")

from encore_audio import classify_audio_file, warm_up  # noqa: E402

app = FastAPI(title="Encore Classify", version="0.1.0")

# allow the Node backend and frontend to call this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    warm_up()
    print("Encore classifier ready.")


# --- POST /classify (file upload) ---

@app.post("/classify")
async def classify_upload(file: UploadFile = File(...)):
    """Upload an audio file and get classification results."""
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        result = classify_audio_file(tmp_path)
    finally:
        os.unlink(tmp_path)
    return result


# --- POST /classify-url (audio from a URL, e.g. Supabase signed link) ---

class ClassifyUrlRequest(BaseModel):
    audio_url: str

@app.post("/classify-url")
async def classify_from_url(request: ClassifyUrlRequest):
    """Download audio from a URL (e.g. Supabase signed link) and classify it."""
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(request.audio_url)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(400, f"Could not download audio: {e}")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(resp.content)
        tmp_path = tmp.name
    try:
        result = classify_audio_file(tmp_path)
    finally:
        os.unlink(tmp_path)
    return result


# --- GET /health ---

@app.get("/health")
def health():
    return {"status": "ok", "service": "encore-classify"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
