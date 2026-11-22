"""
Quick smoke test for the classify endpoint.

Usage:
    1. Start the server:  uvicorn classify_server:app --port 8000
    2. In another terminal: python test_endpoint.py
"""
import sys
import httpx

BASE = "http://localhost:8000"

def test_health():
    r = httpx.get(f"{BASE}/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    print("health check passed")

def test_classify_upload(path: str):
    with open(path, "rb") as f:
        r = httpx.post(f"{BASE}/classify", files={"file": (path, f, "audio/wav")}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    print(f"classify upload result:")
    print(f"  top role: {data['role_suggestions'][0]['role']}")
    print(f"  top 2:    {[s['role'] for s in data['role_suggestions'][:2]]}")
    print(f"  labels:   {data['sound_labels'][:3]}")
    return data

def test_classify_url(url: str):
    r = httpx.post(f"{BASE}/classify-url", json={"audio_url": url}, timeout=30)
    assert r.status_code == 200
    data = r.json()
    print(f"classify-url result:")
    print(f"  top role: {data['role_suggestions'][0]['role']}")
    return data

if __name__ == "__main__":
    test_health()
    if len(sys.argv) > 1:
        test_classify_upload(sys.argv[1])
    else:
        print("pass a .wav path to test classify: python test_endpoint.py some_clip.wav")
