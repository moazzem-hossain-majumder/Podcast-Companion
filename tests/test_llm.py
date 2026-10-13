import httpx
import pytest

from app.llm import (
    AllProvidersFailed, AuthError, ChainEntry, GeminiProvider, GroundingError, LLMClient, MalformedOutput,
    ModelUnavailable, OpenAICompatProvider, RateLimited, TransientError, classify_http_error, extract_json,
)
from tests.conftest import FakeProvider, make_client


def ok_validator(obj):
    if "x" not in obj:
        raise GroundingError("missing x")
    return obj


# ---------------------------------------------------------------- JSON extraction
@pytest.mark.parametrize("raw", [
    '{"x": 1}', '```json\n{"x": 1}\n```', 'Sure! Here you go:\n{"x": 1}\nHope that helps', '{"x": 1,}', '{"x": [1,2,],}',
])
def test_extract_json_tolerates_common_mess(raw):
    assert extract_json(raw)["x"] in (1, [1, 2])


@pytest.mark.parametrize("raw", ["", "   ", "no json here", '{"x": [1, 2', "[1,2,3]"])
def test_extract_json_rejects_garbage(raw):
    with pytest.raises(MalformedOutput):
        extract_json(raw)


# ---------------------------------------------------------------- chain behaviour
async def test_fallback_on_rate_limit_then_success():
    a = FakeProvider("gemini", [RateLimited("429", retry_after=60)])
    b = FakeProvider("groq", [{"x": 1}])
    res, info = await make_client([a, b]).complete_json(system="s", user="u", validator=ok_validator)
    assert res == {"x": 1} and info.provider == "groq" and info.fallback_used


async def test_rate_limited_entry_is_skipped_during_cooldown():
    a = FakeProvider("gemini", [RateLimited("429", retry_after=60), {"x": 1}])
    b = FakeProvider("groq", [{"x": 1}, {"x": 1}])
    client = make_client([a, b])
    await client.complete_json(system="s", user="u", validator=ok_validator)
    await client.complete_json(system="s", user="u", validator=ok_validator)
    assert len(a.calls) == 1 and len(b.calls) == 2  # gemini not hit again while cooling down


async def test_cooldown_expires():
    now = [0.0]
    a = FakeProvider("gemini", [RateLimited("429", retry_after=10), {"x": 1}])
    b = FakeProvider("groq", [{"x": 1}])
    client = make_client([a, b], clock=lambda: now[0])
    await client.complete_json(system="s", user="u", validator=ok_validator)
    now[0] = 11
    _, info = await client.complete_json(system="s", user="u", validator=ok_validator)
    assert info.provider == "gemini"


async def test_short_rate_limit_is_retried_in_place():
    a = FakeProvider("gemini", [RateLimited("429", retry_after=2), {"x": 1}])
    _, info = await make_client([a]).complete_json(system="s", user="u", validator=ok_validator)
    assert info.provider == "gemini" and info.attempts == 2


@pytest.mark.parametrize("exc", [AuthError("bad key"), ModelUnavailable("gone")])
async def test_auth_and_missing_model_disable_entry_permanently(exc):
    a = FakeProvider("gemini", [exc, {"x": 1}])
    b = FakeProvider("groq", [{"x": 1}, {"x": 1}])
    client = make_client([a, b])
    await client.complete_json(system="s", user="u", validator=ok_validator)
    await client.complete_json(system="s", user="u", validator=ok_validator)
    assert len(a.calls) == 1
    assert "gemini:gemini-model" not in client.available_entries()


async def test_transient_error_retried_once_then_next_provider():
    a = FakeProvider("gemini", [TransientError("503"), TransientError("503")])
    b = FakeProvider("groq", [{"x": 1}])
    _, info = await make_client([a, b]).complete_json(system="s", user="u", validator=ok_validator)
    assert len(a.calls) == 2 and info.provider == "groq"


async def test_malformed_json_gets_repair_attempt_with_feedback():
    a = FakeProvider("gemini", ['{"x": [1, 2', {"x": 1}])
    res, info = await make_client([a]).complete_json(system="s", user="u", validator=ok_validator)
    assert res == {"x": 1} and info.attempts == 2
    assert "rejected by the validator" in a.calls[1]["user"]


async def test_grounding_failure_feedback_reaches_model_then_falls_back():
    a = FakeProvider("gemini", [{"nope": 1}, {"nope": 2}])
    b = FakeProvider("groq", [{"x": 1}])
    res, info = await make_client([a, b]).complete_json(system="s", user="u", validator=ok_validator)
    assert info.provider == "groq" and "missing x" in a.calls[1]["user"]


async def test_all_fail_reports_retry_after():
    # both waits are longer than the client's max cooldown wait (30 s), so it reports instead of waiting
    a = FakeProvider("gemini", [RateLimited("429", retry_after=42)])
    b = FakeProvider("groq", [RateLimited("429", retry_after=35)])
    with pytest.raises(AllProvidersFailed) as e:
        await make_client([a, b]).complete_json(system="s", user="u", validator=ok_validator)
    assert e.value.retry_after == 35 and not e.value.only_unconfigured


async def test_no_configured_provider():
    client = LLMClient([ChainEntry("gemini", "m")], {})
    with pytest.raises(AllProvidersFailed) as e:
        await client.complete_json(system="s", user="u", validator=ok_validator)
    assert e.value.only_unconfigured


async def test_long_prompts_skip_small_context_models():
    small = FakeProvider("groq", [{"x": 1}])
    big = FakeProvider("gemini", [{"x": 1}])
    entries = [ChainEntry("groq", "m", max_input_chars=100), ChainEntry("gemini", "m")]
    _, info = await make_client([small, big], entries=entries).complete_json(system="s", user="u" * 500, validator=ok_validator)
    assert info.provider == "gemini" and not small.calls


async def test_timeout_is_treated_as_transient():
    import asyncio

    class Slow:
        name = "gemini"

        async def complete(self, **kw):
            await asyncio.sleep(5)

    ok = FakeProvider("groq", [{"x": 1}])
    client = LLMClient([ChainEntry("gemini", "m"), ChainEntry("groq", "m")], {"gemini": Slow(), "groq": ok}, timeout_s=0.05)
    _, info = await client.complete_json(system="s", user="u", validator=ok_validator)
    assert info.provider == "groq"


# ---------------------------------------------------------------- real provider code via mocked HTTP
def gemini_with(handler):
    return GeminiProvider("KEY", httpx.AsyncClient(transport=httpx.MockTransport(handler)))


async def test_gemini_happy_path_and_header_auth():
    seen = {}

    def handler(req):
        seen["key"] = req.headers.get("x-goog-api-key")
        seen["url"] = str(req.url)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"x": 1}'}]}, "finishReason": "STOP"}]})

    out = await gemini_with(handler).complete(model="gm", system="s", user="u", max_tokens=10, temperature=0)
    assert out == '{"x": 1}' and seen["key"] == "KEY" and "KEY" not in seen["url"]


async def test_gemini_thought_parts_ignored():
    h = lambda r: httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "thinking", "thought": True}, {"text": "{}"}]}}]})
    assert await gemini_with(h).complete(model="m", system="", user="", max_tokens=1, temperature=0) == "{}"


@pytest.mark.parametrize("status,body,exc", [
    (429, {"error": {"details": [{"retryDelay": "34s"}]}}, RateLimited),
    (403, {"error": {"message": "denied"}}, AuthError),
    (400, {"error": {"message": "API key not valid"}}, AuthError),
    (404, {"error": {"message": "models/x is no longer available"}}, ModelUnavailable),
    (503, {}, TransientError),
])
async def test_gemini_status_mapping(status, body, exc):
    with pytest.raises(exc):
        await gemini_with(lambda r: httpx.Response(status, json=body)).complete(model="m", system="", user="", max_tokens=1, temperature=0)


async def test_gemini_retry_delay_parsed():
    with pytest.raises(RateLimited) as e:
        await gemini_with(lambda r: httpx.Response(429, text='{"retryDelay": "34s"}')).complete(model="m", system="", user="", max_tokens=1, temperature=0)
    assert e.value.retry_after == 34


async def test_gemini_truncation_and_block_detected():
    trunc = lambda r: httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": '{"a'}]}, "finishReason": "MAX_TOKENS"}]})
    with pytest.raises(MalformedOutput):
        await gemini_with(trunc).complete(model="m", system="", user="", max_tokens=1, temperature=0)
    blocked = lambda r: httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}})
    with pytest.raises(Exception) as e:
        await gemini_with(blocked).complete(model="m", system="", user="", max_tokens=1, temperature=0)
    assert e.value.kind == "bad_request"


async def test_gemini_network_error_and_timeout():
    def boom(req):
        raise httpx.ConnectError("down")

    with pytest.raises(TransientError):
        await gemini_with(boom).complete(model="m", system="", user="", max_tokens=1, temperature=0)

    def slow(req):
        raise httpx.ReadTimeout("slow")

    with pytest.raises(TransientError):
        await gemini_with(slow).complete(model="m", system="", user="", max_tokens=1, temperature=0)


async def test_openai_compat_json_mode_and_402():
    sent = {}

    def handler(req):
        import json
        sent.update(json.loads(req.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"x":1}'}, "finish_reason": "stop"}]})

    p = OpenAICompatProvider("groq", "https://x/v1", "K", httpx.AsyncClient(transport=httpx.MockTransport(handler)), True)
    assert await p.complete(model="m", system="s", user="u", max_tokens=5, temperature=0) == '{"x":1}'
    assert sent["response_format"] == {"type": "json_object"}

    p2 = OpenAICompatProvider("huggingface", "https://x/v1", "K", httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(402, text="credits"))), False)
    with pytest.raises(RateLimited):
        await p2.complete(model="m", system="s", user="u", max_tokens=5, temperature=0)


def test_classify_retry_after_header():
    r = httpx.Response(429, headers={"retry-after": "7"}, text="x")
    assert classify_http_error(r).retry_after == 7


async def test_gemini_gets_headroom_for_thinking_tokens():
    sent = {}

    def handler(req):
        import json
        sent.update(json.loads(req.content))
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "{}"}]}}]})

    await gemini_with(handler).complete(model="m", system="s", user="u", max_tokens=3000, temperature=0)
    assert sent["generationConfig"]["maxOutputTokens"] >= 12000
