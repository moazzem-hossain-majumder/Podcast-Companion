"""Runtime configuration, read from environment variables only.

Secrets (API keys) never live in code or in the repository. Locally they come from
a git-ignored `.env` file; in production from the host's secret store.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Mapping

# Model IDs and vendor shutdown dates change often (Gemini 2.5 Flash was announced for shutdown
# on 2026-10-16, then listed as "not deprecated" again by October 2026), so the chain is
# configuration, not code. Format: "provider:model,provider:model".
DEFAULT_LLM_CHAIN = (
    "gemini:gemini-3.5-flash,"
    "gemini:gemini-3.1-flash-lite,"
    "groq:openai/gpt-oss-120b,"
    "huggingface:meta-llama/Llama-3.3-70B-Instruct"
)
# Groq's and Hugging Face's free tiers have small tokens-per-minute budgets, so they
# are only used as fallbacks for shorter transcripts (see llm.py).
DEFAULT_SMALL_CONTEXT_CHARS = 24_000

KNOWN_PROVIDERS = ("gemini", "groq", "huggingface")

# Used when a provider has an API key but a custom LLM_CHAIN leaves it out, so it can still be
# chosen in the model picker (and compared). Appended at the end, so Auto's order is unchanged.
DEFAULT_MODEL_FOR = {
    "gemini": "gemini-3.5-flash",
    "groq": "openai/gpt-oss-120b",  # llama-3.3-70b-versatile was shut down by Groq on 2026-08-16
    "huggingface": "meta-llama/Llama-3.3-70B-Instruct",
}


def _int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:  # fail fast on a typo instead of silently ignoring it
        raise ValueError(f"Environment variable {name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"Environment variable {name} must be positive, got {value}")
    return value


def parse_chain(raw: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(f"LLM_CHAIN entry {item!r} must look like 'provider:model'")
        provider, model = item.split(":", 1)
        provider, model = provider.strip().lower(), model.strip()
        if provider not in KNOWN_PROVIDERS:
            raise ValueError(f"Unknown provider {provider!r} in LLM_CHAIN (known: {KNOWN_PROVIDERS})")
        if not model:
            raise ValueError(f"LLM_CHAIN entry {item!r} has an empty model name")
        entries.append((provider, model))
    if not entries:
        raise ValueError("LLM_CHAIN is empty")
    return entries


@dataclass(frozen=True)
class Settings:
    # --- secrets (optional individually; at least one LLM key is needed to generate) ---
    gemini_api_key: str = field(default="", repr=False)
    groq_api_key: str = field(default="", repr=False)
    hf_token: str = field(default="", repr=False)

    # --- model routing ---
    llm_chain: tuple[tuple[str, str], ...] = ()
    asr_models: tuple[str, ...] = ("whisper-large-v3-turbo", "whisper-large-v3")
    gemini_asr_model: str = "gemini-3.5-flash"
    small_context_chars: int = DEFAULT_SMALL_CONTEXT_CHARS

    # --- input limits (all surfaced to the UI through /api/health) ---
    max_transcript_chars: int = 150_000
    min_transcript_chars: int = 200
    max_audio_mb: int = 60
    max_audio_minutes: int = 90
    groq_direct_mb: int = 24  # Groq free tier accepts files up to 25 MB

    # --- protection of the free quotas ---
    rate_limit_per_minute: int = 20
    audio_jobs_per_10_min: int = 3
    max_concurrent_llm: int = 4
    llm_timeout_s: int = 60

    @property
    def max_json_body_bytes(self) -> int:
        return 3 * 1024 * 1024

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> "Settings":
        env = os.environ if env is None else env
        asr = tuple(m.strip() for m in env.get("ASR_MODELS", "").split(",") if m.strip())
        return cls(
            gemini_api_key=env.get("GEMINI_API_KEY", "").strip(),
            groq_api_key=env.get("GROQ_API_KEY", "").strip(),
            hf_token=env.get("HF_TOKEN", "").strip(),
            llm_chain=tuple(parse_chain(env.get("LLM_CHAIN", "") or DEFAULT_LLM_CHAIN)),
            asr_models=asr or cls.asr_models,
            gemini_asr_model=env.get("GEMINI_ASR_MODEL", "").strip() or cls.gemini_asr_model,
            small_context_chars=_int(env, "SMALL_CONTEXT_CHARS", DEFAULT_SMALL_CONTEXT_CHARS),
            max_transcript_chars=_int(env, "MAX_TRANSCRIPT_CHARS", 150_000),
            max_audio_mb=_int(env, "MAX_AUDIO_MB", 60),
            max_audio_minutes=_int(env, "MAX_AUDIO_MINUTES", 90),
            rate_limit_per_minute=_int(env, "RATE_LIMIT_PER_MINUTE", 20),
            audio_jobs_per_10_min=_int(env, "AUDIO_JOBS_PER_10_MIN", 3),
            max_concurrent_llm=_int(env, "MAX_CONCURRENT_LLM", 4),
            llm_timeout_s=_int(env, "LLM_TIMEOUT_S", 60),
        )

    def key_for(self, provider: str) -> str:
        return {"gemini": self.gemini_api_key, "groq": self.groq_api_key, "huggingface": self.hf_token}[provider]

    def configured_providers(self) -> list[str]:
        return [p for p in KNOWN_PROVIDERS if self.key_for(p)]
