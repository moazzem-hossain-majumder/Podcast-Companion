"""Audio -> timestamped transcript.

Pipeline: sniff -> probe duration -> (compress + split when large) -> Groq Whisper per chunk
(turbo, then large-v3, then Gemini as a text-only last resort) -> merge with exact time offsets.

Timestamps come from Whisper segment times plus the measured duration of every earlier chunk,
so they are real. If only the Gemini fallback could transcribe a chunk, timestamps are dropped
for the whole episode and the UI says so, rather than showing guesses.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import re
import secrets
import shutil
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

import httpx

from .config import Settings
from .llm import AuthError, BadRequest, MalformedOutput, ModelUnavailable, RateLimited, TransientError, classify_http_error
from .security import FFMPEG_DEMUXER, GROQ_DIRECT_KINDS, MIME_FOR, EXT_FOR
from .transcript import RawCue, build_transcript

log = logging.getLogger("podcast.transcribe")
GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models"
CHUNK_SECONDS = 1200  # 20 min -> ~4.8 MB at 32 kbps, well under every provider limit


class TranscribeError(Exception):
    """User-facing transcription failure (message is safe to show)."""

    def __init__(self, message: str, code: str = "transcription_failed", status: int = 502):
        super().__init__(message)
        self.code, self.status = code, status


# ------------------------------------------------------------------ jobs
@dataclass
class Job:
    id: str
    created: float
    status: str = "queued"  # queued | processing | done | error
    stage: str = "Waiting to start"
    progress: float = 0.0
    result: Optional[dict] = None
    error: Optional[dict] = None
    notes: list[str] = field(default_factory=list)

    def public(self) -> dict:
        return {
            "job_id": self.id, "status": self.status, "stage": self.stage,
            "progress": round(self.progress, 2), "transcript": self.result, "error": self.error, "notes": self.notes,
        }


class JobStore:
    def __init__(self, ttl_s: int = 1800, max_jobs: int = 50, clock: Callable[[], float] = time.time):
        self._jobs: dict[str, Job] = {}
        self.ttl_s, self.max_jobs, self._clock = ttl_s, max_jobs, clock

    def _gc(self) -> None:
        now = self._clock()
        for jid in [j for j, job in self._jobs.items() if now - job.created > self.ttl_s]:
            self._jobs.pop(jid, None)

    def create(self) -> Job:
        self._gc()
        if len(self._jobs) >= self.max_jobs:
            raise TranscribeError("The server is busy with other uploads. Try again in a few minutes.", "busy", 503)
        job = Job(id=secrets.token_urlsafe(16), created=self._clock())
        self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        self._gc()
        return self._jobs.get(job_id)


# ------------------------------------------------------------------ ffmpeg
def find_ffmpeg() -> Optional[str]:
    explicit = os.environ.get("FFMPEG_BIN")
    if explicit and Path(explicit).exists():
        return explicit
    try:
        import imageio_ffmpeg  # bundles a static ffmpeg binary, so no apt/brew step is needed

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return shutil.which("ffmpeg")


async def _run(args: list[str], timeout: float) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *args, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE
    )
    try:
        _, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TranscribeError("Compressing the audio took too long. Try a shorter or smaller file.", "timeout", 504)
    return proc.returncode or 0, err.decode("utf-8", "replace")


_DURATION = re.compile(r"Duration:\s*(\d+):(\d{2}):(\d{2}(?:\.\d+)?)")


async def probe_duration(ffmpeg: str, path: Path, kind: str) -> Optional[float]:
    _, err = await _run([ffmpeg, "-hide_banner", "-nostdin", "-f", FFMPEG_DEMUXER[kind], "-i", str(path)], 60)
    m = _DURATION.search(err)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else None


async def compress_and_split(ffmpeg: str, src: Path, kind: str, out_dir: Path, timeout: float) -> list[Path]:
    """16 kHz mono 32 kbps MP3 is what Whisper downsamples to anyway, and cuts a 1-hour episode to ~14 MB."""
    pattern = out_dir / "part_%03d.mp3"
    args = [
        ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
        "-f", FFMPEG_DEMUXER[kind], "-i", str(src),  # force the demuxer: no format auto-detection tricks
        "-vn", "-map", "0:a:0", "-ac", "1", "-ar", "16000", "-b:a", "32k", "-threads", "1",
        "-f", "segment", "-segment_time", str(CHUNK_SECONDS), "-reset_timestamps", "1", str(pattern),
    ]
    code, err = await _run(args, timeout)
    parts = sorted(out_dir.glob("part_*.mp3"))
    if code != 0 or not parts:
        log.warning("ffmpeg failed code=%s err=%s", code, err[-300:])
        raise TranscribeError("Couldn't read that audio file. It may be corrupted or contain no audio track.", "bad_audio", 422)
    return parts


# ------------------------------------------------------------------ providers
@dataclass
class ChunkResult:
    cues: list[RawCue]
    has_timestamps: bool
    language: Optional[str] = None
    model: str = ""


async def groq_whisper(client: httpx.AsyncClient, key: str, model: str, path: Path, kind: str, language: Optional[str]) -> ChunkResult:
    data: dict[str, Any] = {
        "model": model, "response_format": "verbose_json", "timestamp_granularities[]": "segment", "temperature": "0",
    }
    if language:
        data["language"] = language
    try:
        resp = await client.post(
            GROQ_STT_URL, headers={"Authorization": f"Bearer {key}"}, data=data,
            files={"file": (f"audio.{EXT_FOR[kind]}", path.read_bytes(), MIME_FOR[kind])},
        )
    except httpx.TimeoutException as exc:
        raise TransientError("timeout") from exc
    except httpx.HTTPError as exc:
        raise TransientError(f"network error: {type(exc).__name__}") from exc
    if resp.status_code != 200:
        raise classify_http_error(resp)
    try:
        body = resp.json()
        segments = body.get("segments") or []
    except ValueError as exc:
        raise MalformedOutput("non-JSON response") from exc
    cues: list[RawCue] = []
    for s in segments:
        text = str(s.get("text", "")).strip()
        # Whisper hallucinates on silence/music ("Thanks for watching!"). Drop segments it is itself unsure are speech.
        if not text or (s.get("no_speech_prob", 0) > 0.9 and s.get("avg_logprob", 0) < -1.0):
            continue
        cues.append(RawCue(text, float(s.get("start", 0)), float(s.get("end", 0))))
    if not cues and body.get("text", "").strip():  # no segment list: keep the text, lose the timestamps
        return ChunkResult([RawCue(body["text"].strip())], False, body.get("language"), model)
    return ChunkResult(cues, True, body.get("language"), model)


async def gemini_transcribe(client: httpx.AsyncClient, key: str, model: str, path: Path) -> ChunkResult:
    """Last resort. Gemini transcribes well but its timestamps are not dependable, so we ask for text only."""
    payload = {
        "contents": [{"role": "user", "parts": [
            {"text": "Transcribe this audio verbatim in its original language. Output plain text only, "
                     "with a blank line between paragraphs. Do not add timestamps, speaker names or commentary."},
            {"inline_data": {"mime_type": "audio/mp3", "data": base64.b64encode(path.read_bytes()).decode()}},
        ]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 16384},
    }
    try:
        resp = await client.post(f"{GEMINI_URL}/{model}:generateContent", json=payload, headers={"x-goog-api-key": key})
    except httpx.TimeoutException as exc:
        raise TransientError("timeout") from exc
    except httpx.HTTPError as exc:
        raise TransientError(f"network error: {type(exc).__name__}") from exc
    if resp.status_code != 200:
        raise classify_http_error(resp)
    try:
        parts = resp.json()["candidates"][0]["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise MalformedOutput("unexpected Gemini response") from exc
    if not text:
        raise MalformedOutput("empty transcription")
    cues = [RawCue(p.strip()) for p in re.split(r"\n\s*\n", text) if p.strip()]
    return ChunkResult(cues, False, None, model)


# ------------------------------------------------------------------ orchestration
async def transcribe_file(
    *, settings: Settings, client: httpx.AsyncClient, path: Path, kind: str, size: int,
    language: Optional[str], work_dir: Path, job: Job,
    sleep: Callable[[float], Any] = asyncio.sleep,
    asr_provider: str = "auto",
) -> dict:
    # asr_provider pins transcription to one engine ("groq" = Whisper, "gemini" = Gemini audio
    # understanding) so the two can be compared; "auto" keeps Whisper-first with Gemini as backup.
    use_groq = bool(settings.groq_api_key) and asr_provider in ("auto", "groq")
    use_gemini = bool(settings.gemini_api_key) and asr_provider in ("auto", "gemini")
    if not use_groq and not use_gemini:
        raise TranscribeError("Audio transcription isn't configured on this server (no Groq or Gemini key).", "not_configured", 503)

    ffmpeg = find_ffmpeg()
    duration: Optional[float] = None
    if ffmpeg:
        job.stage = "Checking the audio"
        duration = await probe_duration(ffmpeg, path, kind)
        if duration is not None and duration > settings.max_audio_minutes * 60:
            raise TranscribeError(
                f"This recording is {duration / 60:.0f} minutes long; the limit is {settings.max_audio_minutes} minutes.",
                "too_long", 413,
            )

    direct = size <= settings.groq_direct_mb * 1024 * 1024 and kind in GROQ_DIRECT_KINDS and use_groq
    if direct:
        chunks, kinds = [path], [kind]
    else:
        if not ffmpeg:
            raise TranscribeError("This file is too large to send directly and audio compression isn't available on the server.", "too_large", 413)
        job.stage = "Compressing audio (this can take a few minutes for long files)"
        job.progress = 0.1
        parts = await compress_and_split(ffmpeg, path, kind, work_dir, timeout=1500)
        chunks, kinds = parts, ["mp3"] * len(parts)

    offsets: list[float] = []
    acc = 0.0
    for chunk, ck in zip(chunks, kinds):
        offsets.append(acc)
        if len(chunks) > 1:
            d = await probe_duration(ffmpeg, chunk, ck) if ffmpeg else None
            acc += d if d is not None else CHUNK_SECONDS

    all_cues: list[RawCue] = []
    all_timestamped = True
    language_out: Optional[str] = None
    models_used: set[str] = set()
    for i, (chunk, ck, offset) in enumerate(zip(chunks, kinds, offsets)):
        job.stage = f"Transcribing{f' part {i + 1} of {len(chunks)}' if len(chunks) > 1 else ''}"
        job.progress = 0.2 + 0.7 * i / len(chunks)
        res = await _transcribe_chunk(settings, client, chunk, ck, language, ffmpeg, work_dir, job, sleep,
                                      use_groq=use_groq, use_gemini=use_gemini)
        models_used.add(res.model)
        language_out = language_out or res.language
        all_timestamped &= res.has_timestamps
        for c in res.cues:
            all_cues.append(RawCue(c.text, None if c.start is None else c.start + offset, None if c.end is None else c.end + offset))

    if not all_cues:
        raise TranscribeError("No speech was detected in this recording.", "no_speech", 422)
    if not all_timestamped:
        why = ("Gemini transcription doesn't provide reliable ones" if asr_provider == "gemini"
               else "the backup transcription service doesn't provide reliable ones")
        job.notes.append(f"Timestamps are unavailable for this recording because {why}.")
    transcript = build_transcript(all_cues, source="audio", language=language_out, timestamps_reliable=all_timestamped)
    if len("".join(s["text"] for s in transcript["segments"])) > settings.max_transcript_chars:
        raise TranscribeError("The transcript is longer than the supported limit. Try a shorter recording.", "too_long", 413)
    transcript["asr_models"] = sorted(models_used)
    return transcript


async def _transcribe_chunk(settings, client, chunk: Path, kind: str, language, ffmpeg, work_dir: Path, job: Job, sleep,
                            *, use_groq: bool = True, use_gemini: bool = True) -> ChunkResult:
    last_reasons: list[str] = []
    if use_groq and settings.groq_api_key:
        for model in settings.asr_models:
            for attempt in (1, 2):
                try:
                    return await groq_whisper(client, settings.groq_api_key, model, chunk, kind, language)
                except RateLimited as exc:
                    last_reasons.append(f"{model}: rate limited")
                    if attempt == 1 and exc.retry_after <= 20:
                        job.stage = f"Waiting for the transcription service ({exc.retry_after:.0f}s rate-limit pause)"
                        await sleep(exc.retry_after)
                        continue
                    break
                except TransientError as exc:
                    last_reasons.append(f"{model}: {exc}")
                    if attempt == 1:
                        await sleep(1.5)
                        continue
                    break
                except (AuthError, ModelUnavailable, BadRequest, MalformedOutput) as exc:
                    last_reasons.append(f"{model}: {exc.kind}")
                    break
    if use_gemini and settings.gemini_api_key and ffmpeg:
        try:
            gem_dir = work_dir / f"gem_{uuid.uuid4().hex[:6]}"
            gem_dir.mkdir()
            parts = [chunk] if (kind == "mp3" and chunk.stat().st_size < 12 * 1024 * 1024) else await compress_and_split(ffmpeg, chunk, kind, gem_dir, 1500)
            cues: list[RawCue] = []
            for p in parts:
                cues.extend((await gemini_transcribe(client, settings.gemini_api_key, settings.gemini_asr_model, p)).cues)
            return ChunkResult(cues, False, None, settings.gemini_asr_model)
        except (RateLimited, AuthError, ModelUnavailable, TransientError, BadRequest, MalformedOutput) as exc:
            last_reasons.append(f"gemini: {getattr(exc, 'kind', 'error')}")
    log.error("all ASR options failed: %s", last_reasons)
    if any("rate limited" in r for r in last_reasons):
        raise TranscribeError("The transcription services are rate-limited right now. Wait a minute and try again.", "rate_limited", 429)
    raise TranscribeError("Transcription failed on every available service. Please try again later.", "transcription_failed", 502)
