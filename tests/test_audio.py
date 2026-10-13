"""End-to-end audio tests: real files, real ffmpeg, mocked Groq/Gemini HTTP."""
import io
import math
import struct
import time
import wave

import httpx
import pytest
from fastapi.testclient import TestClient

import app.transcribe as tr
from app.config import Settings
from app.main import create_app
from app.security import sniff_audio
from app.transcribe import find_ffmpeg
from tests.conftest import FakeProvider, make_client

pytestmark = pytest.mark.skipif(find_ffmpeg() is None, reason="ffmpeg not available")


def make_wav(seconds: float, rate=16000) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
        n = int(seconds * rate)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 220 * i / rate))) for i in range(n)))
    return buf.getvalue()


def settings(**kw):
    base = dict(gemini_api_key="GEM", groq_api_key="GRQ", llm_chain=(("gemini", "m"),), audio_jobs_per_10_min=50)
    base.update(kw)
    return Settings(**base)


def app_with(handler, **kw):
    app = create_app(settings(**kw), llm=make_client([FakeProvider("gemini", [])]))
    app.state.asr_http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return app


def whisper_ok(counter=None, text="Hello and welcome to the show, today we talk about memory."):
    def handler(req: httpx.Request):
        if "groq.com" in str(req.url):
            if counter is not None:
                counter.append(req.read()[:2000])
            n = len(counter) if counter is not None else 1
            segs = [{"start": 0.0, "end": 4.0, "text": f" {text} Part {n}.", "avg_logprob": -0.2, "no_speech_prob": 0.01},
                    {"start": 4.0, "end": 9.0, "text": " Second sentence of the chunk goes here.", "avg_logprob": -0.2, "no_speech_prob": 0.01}]
            return httpx.Response(200, json={"text": "x", "language": "en", "segments": segs})
        raise AssertionError("unexpected URL " + str(req.url))
    return handler


def wait_job(c, job_id, timeout=60):
    end = time.time() + timeout
    while time.time() < end:
        j = c.get(f"/api/jobs/{job_id}").json()
        if j["status"] in ("done", "error"):
            return j
        time.sleep(0.1)
    raise AssertionError("job did not finish")


def upload(c, data, name="a.wav", **form):
    return c.post("/api/transcribe", files={"file": (name, data, "application/octet-stream")}, data=form)


def test_sniff():
    assert sniff_audio(make_wav(0.1)) == "wav"
    assert sniff_audio(b"ID3\x04\x00" + b"\x00" * 20) == "mp3"
    assert sniff_audio(b"\x00\x00\x00\x20ftypM4A " + b"\x00" * 8) == "mp4"
    assert sniff_audio(b"#!/bin/sh\nrm -rf / ...........") is None
    assert sniff_audio(b"#EXTM3U\n#EXT-X-VERSION:3\n") is None  # HLS playlist must never reach ffmpeg


def test_direct_path_wav_with_real_timestamps():
    calls = []
    with TestClient(app_with(whisper_ok(calls))) as c:
        r = upload(c, make_wav(3), language="en")
        assert r.status_code == 202
        job = wait_job(c, r.json()["job_id"])
    assert job["status"] == "done", job
    t = job["transcript"]
    assert t["has_timestamps"] and t["source"] == "audio" and t["segments"][0]["start"] == 0.0
    assert len(calls) == 1  # no compression needed for small files


def test_large_file_is_compressed_split_and_offsets_are_correct(monkeypatch):
    monkeypatch.setattr(tr, "CHUNK_SECONDS", 20)
    calls = []
    wav = make_wav(47)  # ~1.5 MB
    with TestClient(app_with(whisper_ok(calls), groq_direct_mb=1)) as c:
        job = wait_job(c, upload(c, wav).json()["job_id"])
    assert job["status"] == "done", job
    assert len(calls) == 3  # 47 s -> 20 + 20 + 7
    segs = job["transcript"]["segments"]
    starts = [s["start"] for s in segs]
    assert starts == sorted(starts)
    # Cues are merged across chunk borders, so check the *measured* offset of chunk 3 (~40 s) + its 2nd cue (4 s).
    assert 43.5 <= segs[-1]["start"] <= 45.0, starts
    assert segs[-1]["end"] == pytest.approx(segs[-1]["start"] + 5.0)
    assert "Part 1" in segs[0]["text"] and "Part 3" in segs[0]["text"]


def test_rejects_non_audio_with_415():
    with TestClient(app_with(whisper_ok())) as c:
        r = upload(c, b"This is just a text file pretending to be audio. " * 20, name="evil.mp3")
    assert r.status_code == 415 and r.json()["error"]["code"] == "unsupported_format"


def test_rejects_oversized_upload_declared_and_chunked():
    wav = make_wav(70)  # ~2.2 MB
    with TestClient(app_with(whisper_ok(), max_audio_mb=1)) as c:
        assert upload(c, wav).status_code == 413

        def gen():
            yield wav[:1000]
            for i in range(1000, len(wav), 65536):
                yield wav[i : i + 65536]

        r = c.post("/api/transcribe", content=gen(), headers={"content-type": "multipart/form-data; boundary=x"})
        assert r.status_code in (413, 422)


def test_too_long_audio_rejected_before_spending_quota():
    calls = []
    with TestClient(app_with(whisper_ok(calls), max_audio_minutes=1)) as c:
        job = wait_job(c, upload(c, make_wav(75)).json()["job_id"])
    assert job["status"] == "error" and job["error"]["code"] == "too_long" and not calls


def test_whisper_turbo_rate_limited_falls_back_to_large_v3():
    models = []

    def handler(req):
        body = req.read()
        model = "turbo" if b"whisper-large-v3-turbo" in body else "v3"
        models.append(model)
        if model == "turbo":
            return httpx.Response(429, headers={"retry-after": "300"}, text="rate")
        return whisper_ok()(req)

    with TestClient(app_with(handler)) as c:
        job = wait_job(c, upload(c, make_wav(3)).json()["job_id"])
    assert job["status"] == "done" and models == ["turbo", "v3"] and job["transcript"]["asr_models"] == ["whisper-large-v3"]


def test_groq_down_uses_gemini_text_only_and_drops_timestamps():
    def handler(req):
        if "groq.com" in str(req.url):
            return httpx.Response(500, text="boom")
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "First paragraph of the episode talks about memory.\n\nSecond paragraph keeps going."}]}}]})

    async def fast(_):
        return None

    with TestClient(app_with(handler)) as c:
        job = wait_job(c, upload(c, make_wav(3)).json()["job_id"])
    assert job["status"] == "done", job
    assert job["transcript"]["has_timestamps"] is False
    assert any("Timestamps are unavailable" in n for n in job["notes"])


def test_all_asr_fail_gives_clean_error():
    with TestClient(app_with(lambda r: httpx.Response(500, text="x"), gemini_api_key="")) as c:
        job = wait_job(c, upload(c, make_wav(3)).json()["job_id"])
    assert job["status"] == "error" and job["error"]["code"] == "transcription_failed"
    assert "x" not in job["error"]["message"].replace("existing", "")  # no provider body leaked


def test_silence_hallucinations_are_filtered():
    def handler(req):
        segs = [{"start": 0, "end": 3, "text": " Real speech about the topic at hand.", "avg_logprob": -0.3, "no_speech_prob": 0.02},
                {"start": 3, "end": 6, "text": " Thanks for watching!", "avg_logprob": -1.8, "no_speech_prob": 0.97}]
        return httpx.Response(200, json={"text": "x", "segments": segs})

    with TestClient(app_with(handler)) as c:
        job = wait_job(c, upload(c, make_wav(3)).json()["job_id"])
    texts = " ".join(s["text"] for s in job["transcript"]["segments"])
    assert "Real speech" in texts and "Thanks for watching" not in texts


def test_corrupt_audio_with_valid_magic_bytes_fails_cleanly():
    import os
    bad = b"RIFF\x00\x00\x00\x00WAVE" + os.urandom(1_300_000)  # passes the sniff, has no fmt chunk, > 1 MB so ffmpeg is used
    with TestClient(app_with(whisper_ok(), groq_direct_mb=1)) as c:
        job = wait_job(c, upload(c, bad).json()["job_id"])
    assert job["status"] == "error" and job["error"]["code"] == "bad_audio"


def test_audio_upload_rate_limit_and_job_404():
    with TestClient(app_with(whisper_ok(), audio_jobs_per_10_min=1)) as c:
        assert upload(c, make_wav(1)).status_code == 202
        assert upload(c, make_wav(1)).status_code == 429
        assert c.get("/api/jobs/doesnotexist").status_code == 404


def test_bad_language_code_rejected():
    with TestClient(app_with(whisper_ok())) as c:
        assert upload(c, make_wav(1), language="english; rm -rf").status_code == 422


def test_temp_files_deleted_after_job():
    import glob, tempfile
    before = set(glob.glob(tempfile.gettempdir() + "/podcast_*"))
    with TestClient(app_with(whisper_ok())) as c:
        wait_job(c, upload(c, make_wav(2)).json()["job_id"])
        time.sleep(0.3)
    assert set(glob.glob(tempfile.gettempdir() + "/podcast_*")) <= before
