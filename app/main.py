"""FastAPI application: routes, middleware and error handling.

The server is stateless apart from short-lived audio-transcription jobs (in memory, 30 min TTL).
Transcripts and results live in the browser, so nothing a user uploads is stored server-side.
"""
from __future__ import annotations

import asyncio
import logging
import math
import re
import shutil
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import DEFAULT_MODEL_FOR, Settings
from .llm import AllProvidersFailed, ChainEntry, GeminiProvider, GroundingError, LLMClient, OpenAICompatProvider
from .pipeline import answer_question, generate_section
from .schemas import AskRequest, GenerateRequest, ParseRequest
from .security import SECURITY_HEADERS, BodyLimitMiddleware, SlidingWindowLimiter, sniff_audio, EXT_FOR
from .transcribe import JobStore, TranscribeError, transcribe_file
from .transcript import TranscriptError, parse_transcript

log = logging.getLogger("podcast.api")
STATIC_DIR = Path(__file__).parent / "static"
MB = 1024 * 1024
PROVIDER_LABELS = {"gemini": "Google Gemini", "groq": "Groq"}


def error_response(code: str, message: str, status: int, headers: Optional[dict] = None,
                   details: Optional[list[str]] = None) -> JSONResponse:
    err = {"code": code, "message": message}
    if details:
        err["details"] = details[:6]  # short machine labels like "groq:openai/gpt-oss-120b: auth", never provider bodies
    return JSONResponse({"error": err}, status_code=status, headers=headers)


def build_llm(settings: Settings, client: httpx.AsyncClient) -> LLMClient:
    providers = {}
    if settings.gemini_api_key:
        providers["gemini"] = GeminiProvider(settings.gemini_api_key, client)
    if settings.groq_api_key:
        providers["groq"] = OpenAICompatProvider("groq", "https://api.groq.com/openai/v1", settings.groq_api_key, client, True)
    if settings.hf_token:
        # Not every routed model supports response_format, so JSON is requested via the prompt only.
        providers["huggingface"] = OpenAICompatProvider("huggingface", "https://router.huggingface.co/v1", settings.hf_token, client, False)
    chain = list(settings.llm_chain)
    # A key without a chain entry would leave that provider unusable ("not configured") even though
    # it is set up; append its default model so it can still be picked and compared.
    for p in providers:
        if not any(cp == p for cp, _ in chain):
            chain.append((p, DEFAULT_MODEL_FOR[p]))
    entries = [
        ChainEntry(p, m, settings.small_context_chars if p in ("groq", "huggingface") else None)
        for p, m in chain
    ]
    return LLMClient(entries, providers, timeout_s=settings.llm_timeout_s, max_concurrent=settings.max_concurrent_llm)


def create_app(settings: Optional[Settings] = None, llm: Optional[LLMClient] = None) -> FastAPI:
    load_dotenv()  # local development only; harmless if there is no .env file
    settings = settings or Settings.from_env()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        await app.state.http.aclose()
        await app.state.asr_http.aclose()

    app = FastAPI(title="Podcast Companion", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.settings = settings
    app.state.limiter = SlidingWindowLimiter()
    app.state.jobs = JobStore()
    app.state.asr_sem = asyncio.Semaphore(1)  # one transcription at a time protects RAM and Whisper quota
    app.state.tasks = set()
    app.state.http = httpx.AsyncClient(timeout=httpx.Timeout(settings.llm_timeout_s, connect=10))
    app.state.asr_http = httpx.AsyncClient(timeout=httpx.Timeout(300, connect=10))
    app.state.llm = llm or build_llm(settings, app.state.http)

    # ------------------------------------------------------------ middleware
    def limit_for(path: str) -> int:
        return settings.max_audio_mb * MB + MB if path == "/api/transcribe" else settings.max_json_body_bytes

    app.add_middleware(BodyLimitMiddleware, limit_for=limit_for)

    @app.middleware("http")
    async def common(request: Request, call_next):
        rid = uuid.uuid4().hex[:8]
        started = time.perf_counter()
        response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers[k] = v
        response.headers["X-Request-ID"] = rid
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            log.info("rid=%s %s %s -> %s %.0fms", rid, request.method, request.url.path, response.status_code,
                     (time.perf_counter() - started) * 1000)
        return response

    # ------------------------------------------------------------ errors
    @app.exception_handler(StarletteHTTPException)
    async def http_exc(_: Request, exc: StarletteHTTPException):
        codes = {404: "not_found", 405: "method_not_allowed", 413: "too_large"}
        msg = "That upload is too large." if exc.status_code == 413 else (str(exc.detail) or "Request failed")
        return error_response(codes.get(exc.status_code, "http_error"), msg, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exc(_: Request, exc: RequestValidationError):
        first = exc.errors()[0] if exc.errors() else {}
        where = ".".join(str(x) for x in first.get("loc", []) if x != "body")
        return error_response("invalid_request", f"Invalid request ({where}): {first.get('msg', 'bad input')}", 422)

    @app.exception_handler(Exception)
    async def unexpected(_: Request, exc: Exception):
        log.exception("unhandled error")
        return error_response("internal", "Something went wrong on the server. Please try again.", 500)

    # ------------------------------------------------------------ helpers
    def throttle(request: Request, bucket: str, limit: int, window_s: float) -> Optional[JSONResponse]:
        ip = request.client.host if request.client else "unknown"
        ok, wait = app.state.limiter.check(f"{bucket}:{ip}", limit, window_s)
        if ok:
            return None
        return error_response("rate_limited", f"Too many requests. Please wait {math.ceil(wait)} seconds.", 429,
                              {"Retry-After": str(math.ceil(wait))})

    def check_size(tr) -> Optional[JSONResponse]:
        if sum(len(s.text) for s in tr.segments) > settings.max_transcript_chars:
            return error_response("too_large", f"The transcript exceeds {settings.max_transcript_chars:,} characters.", 413)
        return None

    def llm_failure(exc: AllProvidersFailed) -> JSONResponse:
        label = PROVIDER_LABELS.get(exc.provider or "", "")
        if exc.only_unconfigured:
            if label:
                return error_response("not_configured", f"{label} isn't configured on this server (its API key is missing).", 503)
            return error_response("not_configured", "No AI provider is configured on this server.", 503)
        if exc.too_long and label:
            return error_response(
                "too_long_for_provider",
                f"This transcript is too long for {label}'s free tier (about {settings.small_context_chars:,} characters). "
                "Use a shorter transcript, or choose Gemini or Auto.",
                413,
            )
        # Name the real cause: "busy" for everything hid a rejected key or an over-budget request.
        kinds = {r.rsplit(": ", 1)[-1].replace("disabled: ", "").strip("()") for r in exc.reasons}
        who = label or "The AI service"
        env = {"gemini": "GEMINI_API_KEY", "groq": "GROQ_API_KEY"}.get(exc.provider or "", "the API key")
        if kinds and kinds <= {"auth"}:
            return error_response("provider_auth", f"{who} rejected the API key. Check {env} in .env (or the host's settings) "
                                  "and restart the server.", 502, details=exc.reasons)
        if kinds and kinds <= {"model_unavailable", "auth"}:
            return error_response("model_unavailable", f"{who}'s configured model isn't available any more. Run "
                                  "scripts/check_providers.py and update LLM_CHAIN.", 502, details=exc.reasons)
        if "bad_request" in kinds and not kinds & {"rate limited", "transient"}:
            return error_response("provider_rejected", f"{who} rejected the request. On free tiers this usually means the "
                                  "transcript is too large for the per-minute token budget; try a shorter transcript or another model.",
                                  502, details=exc.reasons)
        if kinds and kinds <= {"malformed", "ungrounded"}:
            return error_response("generation_failed", f"{who} answered, but its output failed verification twice. "
                                  "Try again or choose another model.", 502, details=exc.reasons)
        wait = math.ceil(exc.retry_after) if exc.retry_after else 30
        return error_response(
            "providers_busy",
            (f"{label} is busy or rate-limited right now" if label else "The AI services are busy or rate-limited right now")
            + f". Please retry in about {wait} seconds.",
            503, {"Retry-After": str(wait)}, details=exc.reasons,
        )

    def llm_options() -> list[dict]:
        llm: LLMClient = app.state.llm
        opts = [{"id": "auto", "label": "Auto (best available, with fallback)", "ready": bool(llm.available_entries()),
                 "models": [e.key for e in llm.entries]}]
        for pid in ("gemini", "groq"):
            opts.append({"id": pid, "label": PROVIDER_LABELS[pid], "ready": bool(llm.available_entries(pid)),
                         "models": llm.models_for(pid)})
        return opts

    def asr_options() -> list[dict]:
        return [
            {"id": "auto", "label": "Auto (Groq Whisper, Gemini as backup)",
             "ready": bool(settings.groq_api_key or settings.gemini_api_key)},
            {"id": "groq", "label": "Groq Whisper (real timestamps)", "ready": bool(settings.groq_api_key),
             "models": list(settings.asr_models)},
            {"id": "gemini", "label": "Gemini (no timestamps)", "ready": bool(settings.gemini_api_key),
             "models": [settings.gemini_asr_model]},
        ]

    # ------------------------------------------------------------ routes
    @app.get("/api/health")
    async def health():
        return {
            "status": "ok",
            "llm_ready": bool(app.state.llm.available_entries()),
            "transcription_ready": bool(settings.groq_api_key or settings.gemini_api_key),
            "providers": settings.configured_providers(),
            "llm_options": llm_options(),
            "asr_options": asr_options(),
            "small_context_chars": settings.small_context_chars,
            "limits": {
                "max_transcript_chars": settings.max_transcript_chars,
                "min_transcript_chars": settings.min_transcript_chars,
                "max_audio_mb": settings.max_audio_mb,
                "max_audio_minutes": settings.max_audio_minutes,
                "audio_formats": ["mp3", "m4a/mp4", "wav", "ogg", "flac", "webm", "aac"],
                "text_formats": [".txt", ".md", ".srt", ".vtt"],
            },
        }

    @app.post("/api/transcript/parse")
    async def parse(req: ParseRequest, request: Request):
        if (r := throttle(request, "parse", settings.rate_limit_per_minute * 2, 60)):
            return r
        try:
            return parse_transcript(req.text, min_chars=settings.min_transcript_chars, max_chars=settings.max_transcript_chars,
                                    filename=req.filename)
        except TranscriptError as exc:
            return error_response("invalid_transcript", str(exc), 422)

    @app.post("/api/generate")
    async def generate(req: GenerateRequest, request: Request):
        if (r := throttle(request, "llm", settings.rate_limit_per_minute, 60)) or (r := check_size(req.transcript)):
            return r
        try:
            result, info = await generate_section(app.state.llm, req)
        except GroundingError as exc:
            return error_response("generation_failed", f"Couldn't produce a verified result: {str(exc)[:200]}", 502)
        except AllProvidersFailed as exc:
            log.warning("generate failed section=%s reasons=%s", req.section, exc.reasons)
            return llm_failure(exc)
        return {
            "section": req.section,
            "result": result,
            "meta": {"provider": info.provider, "model": info.model, "fallback_used": info.fallback_used,
                     "warnings": info.warnings, "revised": bool(req.instruction), "requested": req.provider,
                     "latency_ms": info.latency_ms, "attempts": info.attempts,
                     # e.g. ["gemini:gemini-3.5-flash (rate limited)"]: why a backup model answered
                     "skipped": info.skipped},
        }

    @app.post("/api/ask")
    async def ask(req: AskRequest, request: Request):
        if (r := throttle(request, "llm", settings.rate_limit_per_minute, 60)) or (r := check_size(req.transcript)):
            return r
        try:
            result, info = await answer_question(app.state.llm, req.transcript, req.question, req.provider)
        except GroundingError as exc:
            return error_response("generation_failed", f"Couldn't produce a verified answer: {str(exc)[:200]}", 502)
        except AllProvidersFailed as exc:
            return llm_failure(exc)
        return {"result": result, "meta": {"provider": info.provider, "model": info.model, "requested": req.provider,
                                           "latency_ms": info.latency_ms}}

    @app.post("/api/transcribe", status_code=202)
    async def transcribe(
        request: Request,
        file: UploadFile = File(...),
        language: Optional[str] = Form(default=None),
        asr_provider: str = Form(default="auto"),
    ):
        if (r := throttle(request, "audio", settings.audio_jobs_per_10_min, 600)):
            return r
        asr_provider = (asr_provider or "auto").strip().lower()
        if asr_provider not in ("auto", "groq", "gemini"):
            return error_response("invalid_request", "Transcription engine must be 'auto', 'groq' or 'gemini'.", 422)
        if asr_provider != "auto" and not settings.key_for(asr_provider):
            return error_response("not_configured",
                                  f"{PROVIDER_LABELS[asr_provider]} isn't configured on this server (its API key is missing).", 503)
        if language is not None:
            language = language.strip().lower()
            if language in ("", "auto"):
                language = None
            elif not re.fullmatch(r"[a-z]{2,3}", language):
                return error_response("invalid_request", "Language must be a 2-3 letter ISO code such as 'en' or 'bn'.", 422)

        head = await file.read(16)
        kind = sniff_audio(head)
        if kind is None:
            return error_response("unsupported_format",
                                  "That doesn't look like a supported audio file. Use mp3, m4a, wav, ogg, flac, webm or aac.", 415)

        work_dir = Path(tempfile.mkdtemp(prefix="podcast_"))
        src = work_dir / f"input.{EXT_FOR[kind]}"
        size = 0
        try:
            with src.open("wb") as out:
                out.write(head)
                size = len(head)
                while chunk := await file.read(MB):
                    size += len(chunk)
                    if size > settings.max_audio_mb * MB:
                        raise TranscribeError(f"The file is larger than {settings.max_audio_mb} MB.", "too_large", 413)
                    out.write(chunk)
            job = app.state.jobs.create()
        except TranscribeError as exc:
            shutil.rmtree(work_dir, ignore_errors=True)
            return error_response(exc.code, str(exc), exc.status)
        except Exception:
            shutil.rmtree(work_dir, ignore_errors=True)
            raise

        task = asyncio.create_task(run_job(app, job, src, kind, size, language, work_dir, asr_provider))
        app.state.tasks.add(task)  # keep a reference so the task isn't garbage-collected mid-run
        task.add_done_callback(app.state.tasks.discard)
        return {"job_id": job.id}

    @app.get("/api/jobs/{job_id}")
    async def job_status(job_id: str):
        job = app.state.jobs.get(job_id)
        if job is None:
            return error_response("not_found", "That transcription job doesn't exist or has expired.", 404)
        return job.public()

    # The UI. Mounted last so it never shadows /api/*.
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
    return app


async def run_job(
    app: FastAPI, job, src: Path, kind: str, size: int, language: Optional[str], work_dir: Path, asr_provider: str = "auto"
) -> None:
    settings: Settings = app.state.settings
    try:
        async with app.state.asr_sem:
            job.status, job.stage = "processing", "Starting"
            transcript = await asyncio.wait_for(
                transcribe_file(settings=settings, client=app.state.asr_http, path=src, kind=kind, size=size,
                                language=language, work_dir=work_dir, job=job, asr_provider=asr_provider),
                timeout=40 * 60,
            )
        job.result, job.status, job.stage, job.progress = transcript, "done", "Done", 1.0
    except TranscribeError as exc:
        job.status, job.error = "error", {"code": exc.code, "message": str(exc)}
    except asyncio.TimeoutError:
        job.status, job.error = "error", {"code": "timeout", "message": "Transcription took too long and was stopped."}
    except Exception:
        log.exception("transcription job crashed")
        job.status, job.error = "error", {"code": "internal", "message": "Transcription failed unexpectedly."}
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)  # uploaded audio is deleted as soon as the job ends


app = create_app()
