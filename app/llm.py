"""Multi-provider LLM client with fallback, cooldowns and defensive JSON handling.

Why this exists: free tiers rate-limit aggressively and model IDs get retired without much
warning. A single hard-coded model call would make the whole product fragile, so every call
walks a configurable chain (e.g. Gemini -> Gemini-lite -> Groq -> Hugging Face) and:

* classifies failures (rate limit / auth / model gone / transient / bad request / malformed),
* puts rate-limited entries on cooldown so later calls skip them instantly,
* permanently skips entries whose key is invalid or whose model no longer exists,
* repairs or re-asks when the model returns malformed or ungrounded JSON,
* never logs prompts, transcripts or keys.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional, Protocol, TypeVar

import httpx

log = logging.getLogger("podcast.llm")
T = TypeVar("T")


# ------------------------------------------------------------------ errors
class LLMError(Exception):
    """Base class. `kind` is a stable machine-readable label."""

    kind = "error"


class RateLimited(LLMError):
    kind = "rate_limited"

    def __init__(self, message: str = "rate limited", retry_after: float = 30.0):
        super().__init__(message)
        self.retry_after = retry_after


class AuthError(LLMError):
    kind = "auth"


class ModelUnavailable(LLMError):
    kind = "model_unavailable"


class TransientError(LLMError):
    kind = "transient"


class BadRequest(LLMError):
    kind = "bad_request"


class MalformedOutput(LLMError):
    kind = "malformed"


class AllProvidersFailed(LLMError):
    kind = "all_failed"

    def __init__(
        self,
        reasons: list[str],
        retry_after: Optional[float],
        only_unconfigured: bool = False,
        *,
        provider: Optional[str] = None,
        too_long: bool = False,
    ):
        super().__init__("; ".join(reasons) or "no provider available")
        self.reasons = reasons
        self.retry_after = retry_after
        self.only_unconfigured = only_unconfigured
        self.provider = provider  # set when the request was pinned to one provider
        self.too_long = too_long  # every usable entry was skipped because the input is too long


class GroundingError(ValueError):
    """Raised by a validator when output parses but is not supported by the transcript.
    The message is fed back to the model on the repair attempt."""


# ------------------------------------------------------------------ JSON extraction
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")


def extract_json(raw: str) -> Any:
    """Parse a JSON object out of model text, tolerating fences, chatter and trailing commas."""
    if not raw or not raw.strip():
        raise MalformedOutput("empty response")
    text = _FENCE.sub("", raw.strip()).strip()
    candidates = [text]
    first, last = text.find("{"), text.rfind("}")
    if first != -1 and last > first:
        candidates.append(text[first : last + 1])
    for cand in candidates:
        for variant in (cand, _TRAILING_COMMA.sub(r"\1", cand)):
            try:
                value = json.loads(variant)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
    if first != -1 and (last == -1 or last < first or text.count("{") > text.count("}")):
        raise MalformedOutput("response looks truncated (unbalanced braces)")
    raise MalformedOutput("response is not valid JSON")


# ------------------------------------------------------------------ providers
class Provider(Protocol):
    name: str

    async def complete(
        self, *, model: str, system: str, user: str, max_tokens: int, temperature: float
    ) -> str: ...


def _retry_after_from(resp: httpx.Response, body: str) -> float:
    header = resp.headers.get("retry-after")
    if header:
        try:
            return min(max(float(header), 1.0), 600.0)
        except ValueError:
            pass
    m = re.search(r'"retryDelay"\s*:\s*"(\d+(?:\.\d+)?)s"', body)  # Gemini style
    if m:
        return min(max(float(m.group(1)), 1.0), 600.0)
    return 30.0


def classify_http_error(resp: httpx.Response) -> LLMError:
    body = resp.text[:2000]
    status = resp.status_code
    lowered = body.lower()
    if status == 429:
        return RateLimited(f"HTTP 429: {body[:200]}", _retry_after_from(resp, body))
    if status == 402:  # Hugging Face: monthly free credits exhausted
        return RateLimited("HTTP 402: free credits exhausted", 3600.0)
    if status in (401, 403) or "api key not valid" in lowered or "api_key_invalid" in lowered:
        return AuthError(f"HTTP {status}: credentials rejected")
    if status == 404 or "no longer available" in lowered or "is not found" in lowered:
        return ModelUnavailable(f"HTTP {status}: model not available")
    if status in (408, 409, 425) or status >= 500:
        return TransientError(f"HTTP {status}")
    return BadRequest(f"HTTP {status}: {body[:200]}")


class GeminiProvider:
    name = "gemini"
    BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, client: httpx.AsyncClient):
        self._key, self._client = api_key, client

    async def complete(self, *, model: str, system: str, user: str, max_tokens: int, temperature: float) -> str:
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": temperature,
                # Thinking models count hidden reasoning tokens against this limit, so leave generous
                # headroom or the visible JSON gets truncated (finishReason=MAX_TOKENS).
                "maxOutputTokens": min(max_tokens * 4 + 4096, 32768),
                "responseMimeType": "application/json",
            },
        }
        try:
            # API key goes in a header, never in the URL (URLs end up in logs).
            resp = await self._client.post(
                f"{self.BASE}/{model}:generateContent", json=payload, headers={"x-goog-api-key": self._key}
            )
        except httpx.TimeoutException as exc:
            raise TransientError("timeout") from exc
        except httpx.HTTPError as exc:
            raise TransientError(f"network error: {type(exc).__name__}") from exc
        if resp.status_code != 200:
            raise classify_http_error(resp)
        try:
            data = resp.json()
        except ValueError as exc:
            raise MalformedOutput("provider returned non-JSON body") from exc
        return _gemini_text(data)


def _gemini_text(data: dict) -> str:
    block = (data.get("promptFeedback") or {}).get("blockReason")
    if block:
        raise BadRequest(f"prompt blocked by provider safety filter ({block})")
    candidates = data.get("candidates") or []
    if not candidates:
        raise MalformedOutput("no candidates in response")
    cand = candidates[0]
    parts = (cand.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought"))
    if cand.get("finishReason") == "MAX_TOKENS":
        raise MalformedOutput("output truncated (MAX_TOKENS)")
    if not text.strip():
        raise MalformedOutput(f"empty text (finishReason={cand.get('finishReason')})")
    return text


class OpenAICompatProvider:
    """Groq and Hugging Face Inference Providers both speak the OpenAI chat-completions dialect."""

    def __init__(self, name: str, base_url: str, api_key: str, client: httpx.AsyncClient, json_mode: bool):
        self.name, self._base, self._key, self._client, self._json_mode = name, base_url, api_key, client, json_mode

    async def complete(self, *, model: str, system: str, user: str, max_tokens: int, temperature: float) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if "gpt-oss" in model:
            # Reasoning model: hidden reasoning tokens count toward max_tokens, so leave headroom (or the
            # visible JSON is cut off, finish_reason=length) and keep reasoning short for speed and quota.
            payload["max_tokens"] = min(max_tokens * 2 + 2048, 32768)
            payload["reasoning_effort"] = "low"
        if self._json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            resp = await self._client.post(
                f"{self._base}/chat/completions", json=payload, headers={"Authorization": f"Bearer {self._key}"}
            )
        except httpx.TimeoutException as exc:
            raise TransientError("timeout") from exc
        except httpx.HTTPError as exc:
            raise TransientError(f"network error: {type(exc).__name__}") from exc
        if resp.status_code != 200:
            raise classify_http_error(resp)
        try:
            choice = resp.json()["choices"][0]
            text = choice["message"]["content"] or ""
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise MalformedOutput("unexpected response shape") from exc
        if choice.get("finish_reason") == "length":
            raise MalformedOutput("output truncated (length)")
        return text


# ------------------------------------------------------------------ the chain
@dataclass(frozen=True)
class ChainEntry:
    provider: str
    model: str
    max_input_chars: Optional[int] = None  # skip this entry for longer prompts

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.model}"


@dataclass
class CallInfo:
    provider: str
    model: str
    attempts: int
    skipped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    latency_ms: int = 0

    @property
    def fallback_used(self) -> bool:
        return bool(self.skipped)


class LLMClient:
    def __init__(
        self,
        entries: list[ChainEntry],
        providers: dict[str, Provider],
        *,
        timeout_s: float = 60,
        max_concurrent: int = 4,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        short_retry_s: float = 4.0,
        max_cooldown_wait_s: float = 30.0,
        max_total_wait_s: float = 60.0,
    ):
        self.entries, self.providers = entries, providers
        self.timeout_s, self._clock, self._sleep, self._short_retry_s = timeout_s, clock, sleep, short_retry_s
        # If every usable entry is only cooling down for a short while (a per-minute token budget, typical of
        # Groq's free tier when three sections are generated at once), waiting once beats failing the section.
        self._max_cooldown_wait_s, self._max_total_wait_s = max_cooldown_wait_s, max_total_wait_s
        self._sem = asyncio.Semaphore(max_concurrent)
        self._cooldown: dict[str, float] = {}
        self._disabled: dict[str, str] = {}

    # -- introspection (used by /api/health) --
    def available_entries(self, provider: Optional[str] = None) -> list[str]:
        return [
            e.key
            for e in self.entries
            if e.provider in self.providers and e.key not in self._disabled and (provider is None or e.provider == provider)
        ]

    def models_for(self, provider: str) -> list[str]:
        return [e.model for e in self.entries if e.provider == provider]

    # -- core --
    async def complete_json(
        self,
        *,
        system: str,
        user: str,
        validator: Callable[[dict], T],
        max_tokens: int = 4096,
        temperature: float = 0.2,
        provider: Optional[str] = None,
    ) -> tuple[T, CallInfo]:
        """Walk the chain. With `provider` set, only that provider's entries are tried (no
        cross-provider fallback), which is what a fair side-by-side comparison needs."""
        started = self._clock()
        waited = 0.0
        while True:
            try:
                result, info = await self._walk(system, user, validator, max_tokens, temperature, provider, started)
            except AllProvidersFailed as exc:
                wait = (exc.retry_after or 0) + 0.5
                if (exc.only_unconfigured or exc.too_long or not exc.retry_after
                        or exc.retry_after > self._max_cooldown_wait_s or waited + wait > self._max_total_wait_s):
                    raise
                if any(not ("rate limited" in r or "cooling down" in r) for r in exc.reasons):
                    raise  # something other than a short rate limit went wrong; don't hide it behind a wait
                await self._sleep(wait)
                waited += wait
                continue
            if waited:
                info.warnings.append(f"Waited {waited:.0f}s for the provider's per-minute limit.")
            return result, info

    async def _walk(self, system, user, validator, max_tokens, temperature, provider, started):
        reasons: list[str] = []
        skipped: list[str] = []
        soonest: Optional[float] = None
        usable = False
        tried = 0
        too_long_skips = 0
        for entry in self.entries:
            if provider is not None and entry.provider != provider:
                continue
            if entry.provider not in self.providers:
                continue
            usable = True
            if entry.key in self._disabled:
                skipped.append(f"{entry.key} (disabled: {self._disabled[entry.key]})")
                continue
            if entry.max_input_chars is not None and len(user) + len(system) > entry.max_input_chars:
                skipped.append(f"{entry.key} (input too long for this model's free tier)")
                too_long_skips += 1
                continue
            wait = self._cooldown.get(entry.key, 0) - self._clock()
            if wait > 0:
                skipped.append(f"{entry.key} (cooling down {wait:.0f}s)")
                soonest = wait if soonest is None else min(soonest, wait)
                continue
            tried += 1
            try:
                async with self._sem:
                    result, attempts, warnings = await self._try_entry(
                        entry, system, user, validator, max_tokens, temperature
                    )
                latency = int((self._clock() - started) * 1000)
                return result, CallInfo(entry.provider, entry.model, attempts, skipped, warnings, latency)
            except RateLimited as exc:
                self._cooldown[entry.key] = self._clock() + exc.retry_after
                soonest = exc.retry_after if soonest is None else min(soonest, exc.retry_after)
                reasons.append(f"{entry.key}: rate limited")
                skipped.append(f"{entry.key} (rate limited)")
            except (AuthError, ModelUnavailable) as exc:
                self._disabled[entry.key] = exc.kind
                log.error("chain entry disabled key=%s reason=%s", entry.key, exc.kind)
                reasons.append(f"{entry.key}: {exc.kind}")
                skipped.append(f"{entry.key} ({exc.kind})")
            except (TransientError, BadRequest, MalformedOutput, GroundingError) as exc:
                label = getattr(exc, "kind", "ungrounded")
                log.warning("chain entry failed key=%s kind=%s detail=%s", entry.key, label, str(exc)[:200])
                reasons.append(f"{entry.key}: {label}")
                skipped.append(f"{entry.key} ({label})")
        raise AllProvidersFailed(
            reasons or skipped,
            soonest,
            only_unconfigured=not usable,
            provider=provider,
            too_long=usable and tried == 0 and too_long_skips > 0 and soonest is None,
        )

    async def _try_entry(
        self, entry: ChainEntry, system: str, user: str, validator: Callable[[dict], T], max_tokens: int, temperature: float
    ) -> tuple[T, int, list[str]]:
        provider = self.providers[entry.provider]
        attempts = 0
        feedback = ""
        transient_retries = 0
        malformed_retries = 0
        while True:
            attempts += 1
            prompt = user if not feedback else f"{user}\n\n{feedback}"
            try:
                raw = await asyncio.wait_for(
                    provider.complete(
                        model=entry.model, system=system, user=prompt, max_tokens=max_tokens, temperature=temperature
                    ),
                    timeout=self.timeout_s,
                )
            except asyncio.TimeoutError as exc:
                raise TransientError("timeout") from exc
            except TransientError:
                if transient_retries >= 1:
                    raise
                transient_retries += 1
                await self._sleep(1.0)
                continue
            except RateLimited as exc:
                # A very short wait is worth it (RPM windows); a long one means "use the next entry".
                if exc.retry_after <= self._short_retry_s and transient_retries < 1:
                    transient_retries += 1
                    await self._sleep(exc.retry_after)
                    continue
                raise
            except MalformedOutput as exc:  # provider-level truncation / empty body
                if malformed_retries >= 1:
                    raise
                malformed_retries += 1
                feedback = f"Your previous reply was unusable ({exc}). Reply again with the complete JSON object only, and keep it concise."
                continue
            try:
                parsed = extract_json(raw)
                return validator(parsed), attempts, []
            except (MalformedOutput, GroundingError, ValueError) as exc:
                # pydantic.ValidationError subclasses ValueError, so schema problems land here too
                if malformed_retries >= 1:
                    if isinstance(exc, GroundingError):
                        raise
                    raise MalformedOutput(str(exc)[:300]) from exc
                malformed_retries += 1
                detail = str(exc)[:600]
                feedback = (
                    "Your previous reply was rejected by the validator:\n"
                    f"{detail}\n"
                    "Fix exactly these problems and return the complete JSON object again, nothing else."
                )
