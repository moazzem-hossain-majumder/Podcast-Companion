import json
import time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.llm import RateLimited
from app.main import create_app
from app.pipeline import Doc
from app.schemas import TranscriptIn
from tests.conftest import FakeProvider, make_client


def settings(**kw):
    base = dict(gemini_api_key="SECRET-GEMINI-KEY-123", groq_api_key="SECRET-GROQ-KEY-456", llm_chain=(("gemini", "m"),), rate_limit_per_minute=50)
    base.update(kw)
    return Settings(**base)


def client_with(script, **kw):
    prov = FakeProvider("gemini", script)
    app = create_app(settings(**kw), llm=make_client([prov]))
    return TestClient(app), prov


def good_overview(tr):
    d = Doc(TranscriptIn(**tr))
    sid = next(s["id"] for s in d.segments if "Ebbinghaus" in s["text"])
    return {"title": "T", "one_line": "o", "summary": "A summary that is long enough to pass validation.",
            "themes": [{"name": "n", "description": "d"}],
            "takeaways": [{"text": f"point {i}", "evidence": [sid]} for i in range(3)]}


def test_health_reports_limits_but_no_secrets():
    c, _ = client_with([])
    body = c.get("/api/health").json()
    assert body["llm_ready"] and body["limits"]["max_audio_mb"] == 60
    assert "SECRET" not in json.dumps(body)  # key values never appear
    assert body["providers"] == ["gemini", "groq"]


def test_security_headers_and_json_404():
    c, _ = client_with([])
    r = c.get("/api/nope")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    r = c.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff" and "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert r.headers["cache-control"] == "no-store" and r.headers["x-request-id"]
    assert c.get("/").status_code == 200  # UI served


def test_parse_endpoint(sample_text):
    c, _ = client_with([])
    r = c.post("/api/transcript/parse", json={"text": sample_text})
    assert r.status_code == 200 and r.json()["segments"]
    r = c.post("/api/transcript/parse", json={"text": "short"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_transcript"
    r = c.post("/api/transcript/parse", content=b"not json", headers={"content-type": "application/json"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_request"


def test_generate_and_revise_roundtrip(sample_transcript):
    c, prov = client_with([good_overview(sample_transcript)] * 2)
    r = c.post("/api/generate", json={"transcript": sample_transcript, "section": "overview"})
    assert r.status_code == 200, r.text
    first = r.json()
    assert first["meta"]["provider"] == "gemini" and first["meta"]["revised"] is False
    r = c.post("/api/generate", json={"transcript": sample_transcript, "section": "overview",
                                      "instruction": "  Make   it shorter ", "previous": first["result"]})
    assert r.status_code == 200 and r.json()["meta"]["revised"] is True
    assert "Make it shorter" in prov.calls[1]["user"] and len(prov.calls) == 2


def test_generate_validation_errors(sample_transcript):
    c, _ = client_with([])
    assert c.post("/api/generate", json={"transcript": sample_transcript, "section": "poem"}).status_code == 422
    assert c.post("/api/generate", json={"transcript": {"segments": []}, "section": "quiz"}).status_code == 422
    r = c.post("/api/generate", json={"transcript": sample_transcript, "section": "overview", "instruction": "x" * 400})
    assert r.status_code == 422 and "instruction" in r.json()["error"]["message"]
    r = c.post("/api/generate", json={"transcript": sample_transcript, "section": "overview", "instruction": "shorter"})
    assert r.status_code == 502  # revision without previous output


def test_generate_rate_limited_providers_returns_503_with_retry_after(sample_transcript):
    c, _ = client_with([RateLimited("429", retry_after=45)])
    r = c.post("/api/generate", json={"transcript": sample_transcript, "section": "overview"})
    assert r.status_code == 503 and r.headers["retry-after"] == "45"
    assert r.json()["error"]["code"] == "providers_busy" and "45" in r.json()["error"]["message"]


def test_no_provider_configured(sample_transcript):
    app = create_app(Settings(llm_chain=(("gemini", "m"),)))
    r = TestClient(app).post("/api/generate", json={"transcript": sample_transcript, "section": "overview"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "not_configured"


def test_oversized_transcript_rejected(sample_transcript):
    c, _ = client_with([], max_transcript_chars=500)
    r = c.post("/api/generate", json={"transcript": sample_transcript, "section": "overview"})
    assert r.status_code == 413


def test_per_ip_rate_limit(sample_transcript):
    c, _ = client_with([RateLimited("429", retry_after=5)] * 10, rate_limit_per_minute=3)
    codes = [c.post("/api/generate", json={"transcript": sample_transcript, "section": "overview"}).status_code for _ in range(5)]
    assert codes[:3] == [503] * 3 and codes[3:] == [429, 429]
    r = c.post("/api/generate", json={"transcript": sample_transcript, "section": "overview"})
    assert "retry-after" in r.headers


def test_unexpected_exception_does_not_leak_details(sample_transcript, monkeypatch):
    c, _ = client_with([])
    import app.main as m

    async def boom(*a, **k):
        raise RuntimeError("secret internal path /etc/passwd")

    monkeypatch.setattr(m, "generate_section", boom)
    r = TestClient(c.app, raise_server_exceptions=False).post("/api/generate", json={"transcript": sample_transcript, "section": "overview"})
    assert r.status_code == 500 and "passwd" not in r.text


def test_json_body_limit_declared_and_streamed():
    c, _ = client_with([])
    big = b"x" * (3 * 1024 * 1024 + 10)
    assert c.post("/api/transcript/parse", content=big, headers={"content-type": "application/json"}).status_code == 413

    def gen():  # chunked transfer: no Content-Length header, so only the streaming check can catch it
        for _ in range(8):
            yield b"y" * (512 * 1024)

    r = c.post("/api/transcript/parse", content=gen(), headers={"content-type": "application/json"})
    assert r.status_code == 413 and r.json()["error"]["code"] == "too_large"


def test_ui_assets_served():
    c, _ = client_with([])
    for path in ("/", "/app.js", "/styles.css", "/sample.txt"):
        assert c.get(path).status_code == 200, path
