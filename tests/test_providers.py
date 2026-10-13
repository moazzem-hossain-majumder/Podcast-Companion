"""Model selection (Gemini vs Groq), the comparison metadata, Markdown input and the built-in samples."""
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.llm import AllProvidersFailed, ChainEntry, GroundingError, RateLimited
from app.main import create_app
from app.security import sniff_audio
from app.transcribe import find_ffmpeg
from app.transcript import parse_transcript, strip_markdown
from tests.conftest import FakeProvider, make_client
from tests.test_api import good_overview

SAMPLES = Path(__file__).resolve().parent.parent / "app" / "static" / "samples"


def ok_validator(obj):
    if "x" not in obj:
        raise GroundingError("missing x")
    return obj


# ---------------------------------------------------------------- LLM client: pinning
async def test_pinned_provider_never_falls_back_to_the_other_provider():
    gem = FakeProvider("gemini", [RateLimited("429", retry_after=60)])
    groq = FakeProvider("groq", [{"x": 1}])
    with pytest.raises(AllProvidersFailed) as e:
        await make_client([gem, groq]).complete_json(system="s", user="u", validator=ok_validator, provider="gemini")
    assert groq.calls == [] and e.value.provider == "gemini"


async def test_pinned_provider_still_uses_its_own_backup_models():
    gem = FakeProvider("gemini", [RateLimited("429", retry_after=60), {"x": 1}])
    groq = FakeProvider("groq", [{"x": 2}])
    entries = [ChainEntry("gemini", "big"), ChainEntry("gemini", "lite"), ChainEntry("groq", "llama")]
    res, info = await make_client([gem, groq], entries).complete_json(
        system="s", user="u", validator=ok_validator, provider="gemini")
    assert res == {"x": 1} and info.model == "lite" and info.fallback_used and groq.calls == []


async def test_pinned_to_groq_uses_groq_even_when_gemini_is_first():
    gem = FakeProvider("gemini", [{"x": 1}])
    groq = FakeProvider("groq", [{"x": 2}])
    res, info = await make_client([gem, groq]).complete_json(system="s", user="u", validator=ok_validator, provider="groq")
    assert res == {"x": 2} and info.provider == "groq" and gem.calls == []


async def test_pinned_to_unconfigured_provider_reports_not_configured():
    gem = FakeProvider("gemini", [{"x": 1}])
    client = make_client([gem], [ChainEntry("gemini", "m"), ChainEntry("groq", "llama")])
    with pytest.raises(AllProvidersFailed) as e:
        await client.complete_json(system="s", user="u", validator=ok_validator, provider="groq")
    assert e.value.only_unconfigured and e.value.provider == "groq"


async def test_pinned_input_too_long_is_reported_as_such():
    groq = FakeProvider("groq", [{"x": 1}])
    client = make_client([groq], [ChainEntry("groq", "llama", max_input_chars=100)])
    with pytest.raises(AllProvidersFailed) as e:
        await client.complete_json(system="s", user="u" * 500, validator=ok_validator, provider="groq")
    assert e.value.too_long and not e.value.only_unconfigured and groq.calls == []


async def test_latency_is_measured():
    now = [100.0]

    class Slow(FakeProvider):
        async def complete(self, **kw):
            now[0] += 1.25
            return await super().complete(**kw)

    p = Slow("gemini", [{"x": 1}])
    _, info = await make_client([p], clock=lambda: now[0]).complete_json(system="s", user="u", validator=ok_validator)
    assert info.latency_ms == 1250


# ---------------------------------------------------------------- API
def two_provider_app(gem_script, groq_script, **kw):
    gem, groq = FakeProvider("gemini", gem_script), FakeProvider("groq", groq_script)
    s = Settings(gemini_api_key="G", groq_api_key="Q", rate_limit_per_minute=100,
                 llm_chain=(("gemini", "gem-model"), ("groq", "groq-model")), **kw)
    entries = [ChainEntry("gemini", "gem-model"), ChainEntry("groq", "groq-model", s.small_context_chars)]
    app = create_app(s, llm=make_client([gem, groq], entries))
    return TestClient(app), gem, groq


def test_health_lists_model_options_with_models():
    c, _, _ = two_provider_app([], [])
    body = c.get("/api/health").json()
    opts = {o["id"]: o for o in body["llm_options"]}
    assert set(opts) == {"auto", "gemini", "groq"} and all(o["ready"] for o in opts.values())
    assert opts["gemini"]["models"] == ["gem-model"] and opts["groq"]["models"] == ["groq-model"]
    assert {o["id"] for o in body["asr_options"]} == {"auto", "groq", "gemini"}
    assert body["small_context_chars"] == 24_000


def test_health_marks_missing_provider_not_ready():
    app = create_app(Settings(gemini_api_key="G", llm_chain=(("gemini", "m"), ("groq", "l"))),
                     llm=make_client([FakeProvider("gemini", [])], [ChainEntry("gemini", "m"), ChainEntry("groq", "l")]))
    opts = {o["id"]: o["ready"] for o in TestClient(app).get("/api/health").json()["llm_options"]}
    assert opts == {"auto": True, "gemini": True, "groq": False}


def test_generate_with_each_provider_and_meta(sample_transcript):
    ov = good_overview(sample_transcript)
    c, gem, groq = two_provider_app([ov], [ov])
    r1 = c.post("/api/generate", json={"transcript": sample_transcript, "section": "overview", "provider": "gemini"}).json()
    r2 = c.post("/api/generate", json={"transcript": sample_transcript, "section": "overview", "provider": "groq"}).json()
    assert r1["meta"]["provider"] == "gemini" and r1["meta"]["requested"] == "gemini"
    assert r2["meta"]["provider"] == "groq" and r2["meta"]["model"] == "groq-model" and r2["meta"]["requested"] == "groq"
    for r in (r1, r2):
        assert isinstance(r["meta"]["latency_ms"], int) and r["meta"]["attempts"] == 1
    assert len(gem.calls) == 1 and len(groq.calls) == 1


def test_auto_is_the_default(sample_transcript):
    c, gem, groq = two_provider_app([good_overview(sample_transcript)], [])
    r = c.post("/api/generate", json={"transcript": sample_transcript, "section": "overview"}).json()
    assert r["meta"]["provider"] == "gemini" and r["meta"]["requested"] == "auto"


def test_invalid_provider_rejected(sample_transcript):
    c, _, _ = two_provider_app([], [])
    r = c.post("/api/generate", json={"transcript": sample_transcript, "section": "overview", "provider": "openai"})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_request"


def test_pinned_groq_without_key_says_so(sample_transcript):
    app = create_app(Settings(gemini_api_key="G", llm_chain=(("gemini", "m"), ("groq", "l"))),
                     llm=make_client([FakeProvider("gemini", [])], [ChainEntry("gemini", "m"), ChainEntry("groq", "l")]))
    r = TestClient(app).post("/api/generate", json={"transcript": sample_transcript, "section": "overview", "provider": "groq"})
    assert r.status_code == 503 and r.json()["error"]["code"] == "not_configured"
    assert "Groq" in r.json()["error"]["message"]


def test_pinned_groq_rate_limited_names_groq(sample_transcript):
    c, gem, _ = two_provider_app([], [RateLimited("429", retry_after=30)])
    r = c.post("/api/generate", json={"transcript": sample_transcript, "section": "overview", "provider": "groq"})
    assert r.status_code == 503 and r.json()["error"]["message"].startswith("Groq is busy") and gem.calls == []


def test_long_transcript_too_long_for_groq_gives_413_with_advice(sample_transcript):
    c, _, groq = two_provider_app([], [], small_context_chars=1000)
    r = c.post("/api/generate", json={"transcript": sample_transcript, "section": "overview", "provider": "groq"})
    assert r.status_code == 413 and r.json()["error"]["code"] == "too_long_for_provider"
    assert "Gemini" in r.json()["error"]["message"] and groq.calls == []


def test_ask_respects_provider(sample_transcript):
    ans = {"answerable": False, "answer": "Not covered.", "evidence": []}
    c, gem, groq = two_provider_app([], [ans])
    r = c.post("/api/ask", json={"transcript": sample_transcript, "question": "Who won?", "provider": "groq"})
    assert r.status_code == 200 and r.json()["meta"]["provider"] == "groq" and gem.calls == []


# ---------------------------------------------------------------- transcription engine choice
def test_transcribe_rejects_unknown_engine():
    c, _, _ = two_provider_app([], [])
    r = c.post("/api/transcribe", files={"file": ("a.wav", b"RIFF0000WAVEfmt ", "audio/wav")}, data={"asr_provider": "azure"})
    assert r.status_code == 422


def test_transcribe_engine_without_key_is_503():
    app = create_app(Settings(gemini_api_key="G", llm_chain=(("gemini", "m"),)), llm=make_client([FakeProvider("gemini", [])]))
    r = TestClient(app).post("/api/transcribe", files={"file": ("a.wav", b"RIFF0000WAVEfmt ", "audio/wav")},
                             data={"asr_provider": "groq"})
    assert r.status_code == 503 and "Groq" in r.json()["error"]["message"]


@pytest.mark.skipif(find_ffmpeg() is None, reason="ffmpeg not available")
def test_transcribe_pinned_to_gemini_never_calls_groq():
    from tests.test_audio import make_wav, wait_job

    def handler(req: httpx.Request):
        if "groq.com" in str(req.url):
            raise AssertionError("Groq must not be called when Gemini is chosen")
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [
            {"text": "Hello and welcome to the show about memory.\n\nToday we talk about forgetting and how to fix it."}]}}]})

    s = Settings(gemini_api_key="G", groq_api_key="Q", llm_chain=(("gemini", "m"),), audio_jobs_per_10_min=50)
    app = create_app(s, llm=make_client([FakeProvider("gemini", [])]))
    app.state.asr_http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with TestClient(app) as c:
        r = c.post("/api/transcribe", files={"file": ("a.wav", make_wav(1.5), "audio/wav")}, data={"asr_provider": "gemini"})
        assert r.status_code == 202, r.text
        job = wait_job(c, r.json()["job_id"])
    assert job["status"] == "done", job
    assert job["transcript"]["has_timestamps"] is False
    assert any("Gemini" in n for n in job["notes"])


# ---------------------------------------------------------------- Markdown
def test_strip_markdown_keeps_words_drops_structure():
    md = "---\ntitle: x\n---\n# Title\n\n## Part one\n\n**Nadia:** Hello *there*, see [the docs](http://x).\n\n- point one\n> quoted line\n\n---\n"
    out = strip_markdown(md)
    assert "Title" not in out and "Part one" not in out and "#" not in out and "**" not in out and "http" not in out
    assert "Nadia: Hello there, see the docs." in out and "point one" in out and "quoted line" in out


def test_parse_endpoint_strips_markdown_only_for_md_files():
    c, _, _ = two_provider_app([], [])
    text = (SAMPLES / "episode.md").read_text()
    md = c.post("/api/transcript/parse", json={"text": text, "filename": "episode.md"}).json()
    raw = c.post("/api/transcript/parse", json={"text": text}).json()
    assert not any("**" in s["text"] or s["text"].startswith("#") for s in md["segments"])
    assert any("**" in s["text"] for s in raw["segments"])


# ---------------------------------------------------------------- built-in samples
TEXT_SAMPLES = {
    "episode.txt": False, "episode-timestamped.txt": True, "episode.md": False, "episode.srt": True, "episode.vtt": True,
}
AUDIO_SAMPLES = {"episode.mp3": "mp3", "episode.m4a": "mp4", "episode.mp4": "mp4", "episode.wav": "wav", "episode.ogg": "ogg",
                 "episode.flac": "flac", "episode.webm": "webm", "episode.aac": "aac"}


@pytest.mark.parametrize("name,timestamps", TEXT_SAMPLES.items())
def test_text_samples_parse_and_are_long(name, timestamps):
    t = parse_transcript((SAMPLES / name).read_text(encoding="utf-8"), min_chars=200, max_chars=150_000, filename=name)
    chars = sum(len(s["text"]) for s in t["segments"])
    assert t["has_timestamps"] is timestamps
    assert 9_000 < chars < 24_000  # long enough to be realistic, short enough for Groq's free tier
    if timestamps:
        assert t["segments"][-1]["start"] > 9 * 60  # the episode runs about 11 minutes


@pytest.mark.parametrize("name,kind", AUDIO_SAMPLES.items())
def test_audio_samples_are_detected_and_under_direct_upload_limit(name, kind):
    data = (SAMPLES / name).read_bytes()
    assert sniff_audio(data[:16]) == kind
    assert len(data) < 24 * 1024 * 1024  # small enough for Groq's direct path (no slow compression on Render)


def test_samples_are_served():
    c, _, _ = two_provider_app([], [])
    for name in [*TEXT_SAMPLES, *AUDIO_SAMPLES]:
        r = c.get(f"/samples/{name}")
        assert r.status_code == 200 and len(r.content) > 1000, name


def test_provider_with_key_but_missing_from_llm_chain_is_still_selectable():
    # Real-world case: a custom LLM_CHAIN listing only Gemini models while GROQ_API_KEY is set.
    from app.main import build_llm
    import httpx as _h
    s = Settings(gemini_api_key="G", groq_api_key="Q", llm_chain=(("gemini", "gemini-3.5-flash"),))
    llm = build_llm(s, _h.AsyncClient())
    assert [e.key for e in llm.entries] == ["gemini:gemini-3.5-flash", "groq:openai/gpt-oss-120b"]  # Auto order kept
    assert llm.available_entries("groq") == ["groq:openai/gpt-oss-120b"]
    assert llm.entries[1].max_input_chars == s.small_context_chars


def test_provider_without_key_is_not_added():
    from app.main import build_llm
    import httpx as _h
    llm = build_llm(Settings(gemini_api_key="G", llm_chain=(("gemini", "m"),)), _h.AsyncClient())
    assert [e.key for e in llm.entries] == ["gemini:m"]


@pytest.mark.parametrize("exc,code,word", [
    ("auth", "provider_auth", "API key"),
    ("model", "model_unavailable", "check_providers"),
    ("bad", "provider_rejected", "rejected the request"),
])
def test_pinned_failure_names_the_real_cause(sample_transcript, exc, code, word):
    from app.llm import AuthError, BadRequest, ModelUnavailable
    err = {"auth": AuthError("HTTP 401"), "model": ModelUnavailable("HTTP 404"), "bad": BadRequest("HTTP 413")}[exc]
    c, gem, _ = two_provider_app([], [err, err])
    r = c.post("/api/generate", json={"transcript": sample_transcript, "section": "overview", "provider": "groq"})
    body = r.json()["error"]
    assert r.status_code == 502 and body["code"] == code and word in body["message"] and "Groq" in body["message"]
    assert body["details"] and all("groq:" in d for d in body["details"]) and gem.calls == []
    assert "Q" not in " ".join(body["details"]).replace("groq", "")  # key value never echoed


async def test_short_cooldown_is_waited_out_once_instead_of_failing():
    slept = []
    groq = FakeProvider("groq", [RateLimited("429", retry_after=12), {"x": 1}])

    async def fake_sleep(s):
        slept.append(s)

    from app.llm import LLMClient
    client = LLMClient([ChainEntry("groq", "m")], {"groq": groq}, sleep=fake_sleep)
    # the cooldown clock must advance past the wait for the retry to be allowed
    t = [0.0]
    client._clock = lambda: t[0]

    async def sleeping(s):
        slept.append(s); t[0] += s

    client._sleep = sleeping
    res, info = await client.complete_json(system="s", user="u", validator=ok_validator, provider="groq")
    assert res == {"x": 1} and slept and slept[-1] >= 12 and any("Waited" in w for w in info.warnings)


async def test_long_cooldown_still_fails_fast():
    groq = FakeProvider("groq", [RateLimited("429", retry_after=120), {"x": 1}])
    with pytest.raises(AllProvidersFailed):
        await make_client([groq]).complete_json(system="s", user="u", validator=ok_validator, provider="groq")
    assert len(groq.calls) == 1


async def test_two_short_waits_then_success_but_total_wait_is_capped():
    t = [0.0]
    slept = []

    async def sleeping(s):
        slept.append(s); t[0] += s

    from app.llm import LLMClient
    groq = FakeProvider("groq", [RateLimited("429", retry_after=10), RateLimited("429", retry_after=27), {"x": 1}])
    client = LLMClient([ChainEntry("groq", "m")], {"groq": groq}, sleep=sleeping, clock=lambda: t[0])
    res, info = await client.complete_json(system="s", user="u", validator=ok_validator, provider="groq")
    assert res == {"x": 1} and len(slept) == 2 and "Waited 38s" in info.warnings[-1]

    groq2 = FakeProvider("groq", [RateLimited("429", retry_after=29), RateLimited("429", retry_after=29), RateLimited("429", retry_after=29)])
    client2 = LLMClient([ChainEntry("groq", "m")], {"groq": groq2}, sleep=sleeping, clock=lambda: t[0])
    with pytest.raises(AllProvidersFailed):
        await client2.complete_json(system="s", user="u", validator=ok_validator, provider="groq")
    assert len(groq2.calls) == 3  # third wait would exceed the 60 s total, so it reports instead
