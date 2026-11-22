"""Resolve sound IDs through RLS, then stage Storage audio for the renderer."""
import os
from pathlib import Path
from urllib.parse import quote, urlsplit
from uuid import UUID

import httpx
from fastapi import Header, HTTPException

BUCKETS = {"private": "sounds-private", "public": "sounds-public"}
MAX_SAMPLE_BYTES = 10 * 1024 * 1024


def sound_id(value):
    try:
        return str(UUID(str(value)))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(422, "Samples must reference a Supabase sound UUID") from None


def sample_ids(mapping=None, sounds=None):
    """Keep the renderer's file field, but use database IDs as its filenames."""
    ids = set()
    try:
        if mapping is not None:
            if not isinstance(mapping, dict) or set(mapping) - {"programs", "drums"}:
                raise ValueError()
            for section in mapping.values():
                for entry in section.values():
                    value = entry if isinstance(entry, str) else entry["file"]
                    canonical = sound_id(value)
                    if value != canonical:
                        raise ValueError()
                    ids.add(canonical)
        if sounds is not None:
            for sound in sounds:
                value = sound["file"]
                canonical = sound_id(value)
                if value != canonical:
                    raise ValueError()
                ids.add(canonical)
    except (ValueError, KeyError, TypeError, AttributeError):
        raise HTTPException(422, "Use canonical sound UUIDs in each sample's file field") from None
    return sorted(ids)


class SupabaseSounds:
    def __init__(self, token):
        self.url = (os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL", "")).rstrip("/")
        self.key = os.getenv("SUPABASE_ANON_KEY") or os.getenv("VITE_SUPABASE_ANON_KEY", "")
        if not self.url or not self.key:
            raise HTTPException(503, "Worker Supabase URL and publishable/anon key are not configured")
        self.headers = {"apikey": self.key, "Authorization": f"Bearer {token}"}

    @staticmethod
    def check(response):
        if response.status_code in {401, 403}:
            raise HTTPException(response.status_code, "Supabase denied access to the sound")
        if response.status_code == 404:
            raise HTTPException(404, "Sound audio not found")
        if not response.is_success:
            raise HTTPException(502, "Could not fetch sound from Supabase")

    def download(self, ids, destination):
        """No service key, arbitrary URLs, shared cache, or persisted user tokens."""
        records = {}
        try:
            with httpx.Client(headers=self.headers, timeout=30, follow_redirects=False) as client:
                for identifier in ids:
                    response = client.get(f"{self.url}/rest/v1/sounds", params={
                        "select": "id,visibility,storage_path,classification", "id": f"eq.{identifier}",
                    })
                    self.check(response)
                    rows = response.json()
                    if not rows:
                        raise HTTPException(404, "Sound not found or not accessible")
                    row = rows[0]
                    records[identifier] = row
                    bucket = BUCKETS.get(row["visibility"])
                    path = row["storage_path"]
                    if not bucket or not isinstance(path, str) or not path or any(
                        part in {"", ".", ".."} for part in path.split("/")
                    ):
                        raise HTTPException(502, "Invalid Supabase sound storage record")
                    url = f"{self.url}/storage/v1/object/authenticated/{bucket}/{quote(path, safe='/')}"
                    target = Path(destination) / identifier
                    with client.stream("GET", url) as audio:
                        self.check(audio)
                        total = 0
                        with target.open("wb") as output:
                            for chunk in audio.iter_bytes():
                                total += len(chunk)
                                if total > MAX_SAMPLE_BYTES:
                                    raise HTTPException(422, "Sound audio exceeds 10 MB")
                                output.write(chunk)
                        if total == 0:
                            raise HTTPException(422, "Sound audio is empty")
        except httpx.HTTPError:
            raise HTTPException(502, "Could not fetch sound from Supabase") from None
        return records


def classified_sounds(sounds, records):
    """Database roles are authoritative; only renderer controls come from requests."""
    return [{"file": sound["file"], "classification": records[sound["file"]].get("classification"),
             **{key: sound[key] for key in ("root_note", "loop") if key in sound}}
            for sound in sounds]


class SignedSounds:
    """Server-authorized manifest for background/guest jobs; no stored user JWT.

    Only callers holding MUSIC_API_KEY may submit this manifest. Node rechecks
    ownership/public visibility and issues short-lived Supabase signed links.
    """
    def __init__(self, sources):
        self.sources = sources

    def download(self, ids, destination):
        if len(self.sources) != len(ids) or {s.get("file") for s in self.sources} != set(ids):
            raise HTTPException(422, "Sample sources must match selected sound IDs exactly")
        base = urlsplit(os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL", ""))
        if not base.netloc:
            raise HTTPException(503, "Worker Supabase URL is not configured")
        records = {}
        try:
            with httpx.Client(timeout=30, follow_redirects=False) as client:
                for source in self.sources:
                    url = urlsplit(source.get("audio_url", ""))
                    if (url.scheme, url.netloc) != (base.scheme, base.netloc) or not any(
                        url.path.startswith(f"{base.path.rstrip('/')}/storage/v1/object/sign/{bucket}/")
                        for bucket in BUCKETS.values()
                    ):
                        raise HTTPException(422, "Sample URLs must be signed sound URLs from the configured Supabase project")
                    with client.stream("GET", source["audio_url"]) as response:
                        SupabaseSounds.check(response)
                        total = 0
                        with (Path(destination) / source["file"]).open("wb") as output:
                            for chunk in response.iter_bytes():
                                total += len(chunk)
                                if total > MAX_SAMPLE_BYTES:
                                    raise HTTPException(422, "Sound audio exceeds 10 MB")
                                output.write(chunk)
                        if not total:
                            raise HTTPException(422, "Sound audio is empty")
                    records[source["file"]] = {"classification": source.get("classification")}
        except httpx.HTTPError:
            raise HTTPException(502, "Could not fetch sound from Supabase") from None
        return records


def get_sound_store(x_supabase_authorization: str | None = Header(default=None)):
    # The primary Authorization header remains the server-to-worker secret.
    if x_supabase_authorization is None:
        return None
    scheme, _, token = x_supabase_authorization.partition(" ")
    if scheme != "Bearer" or not token or any(c.isspace() for c in token):
        raise HTTPException(401, "Invalid Supabase session header")
    return SupabaseSounds(token)
