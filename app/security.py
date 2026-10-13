"""Small, dependency-free security helpers (OWASP API Security Top 10 oriented)."""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable, Optional

from starlette.exceptions import HTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send


# ------------------------------------------------------------------ rate limiting
class SlidingWindowLimiter:
    """In-memory per-key limiter. Protects the shared free-tier quotas from a single noisy client.
    (Single process only -- documented; a multi-instance deployment would need Redis.)"""

    def __init__(self, clock: Callable[[], float] = time.monotonic):
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._clock = clock

    def check(self, key: str, limit: int, window_s: float) -> tuple[bool, float]:
        now = self._clock()
        q = self._hits[key]
        while q and now - q[0] >= window_s:
            q.popleft()
        if len(q) >= limit:
            return False, max(1.0, window_s - (now - q[0]))
        q.append(now)
        if len(self._hits) > 5000:  # crude memory bound
            for k in [k for k, v in self._hits.items() if not v][:1000]:
                self._hits.pop(k, None)
        return True, 0.0


# ------------------------------------------------------------------ file sniffing
# magic bytes -> (canonical kind, ffmpeg demuxer name, Groq-accepted?)
def sniff_audio(head: bytes) -> Optional[str]:
    """Identify the container from the first bytes. We never trust the filename or Content-Type."""
    if len(head) < 12:
        return None
    if head[:3] == b"ID3":
        return "mp3"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head[:4] == b"OggS":
        return "ogg"
    if head[:4] == b"fLaC":
        return "flac"
    if head[4:8] == b"ftyp":
        return "mp4"  # m4a / mp4 / mov family
    if head[:4] == b"\x1a\x45\xdf\xa3":
        return "webm"  # matroska / webm
    if head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
        return "aac" if (head[1] & 0xF6) == 0xF0 else "mp3"
    return None


FFMPEG_DEMUXER = {
    "mp3": "mp3",
    "wav": "wav",
    "ogg": "ogg",
    "flac": "flac",
    "mp4": "mov,mp4,m4a,3gp,3g2,mj2",
    "webm": "matroska,webm",
    "aac": "aac",
}
GROQ_DIRECT_KINDS = {"mp3", "wav", "ogg", "flac", "mp4", "webm"}
MIME_FOR = {
    "mp3": "audio/mpeg", "wav": "audio/wav", "ogg": "audio/ogg", "flac": "audio/flac",
    "mp4": "audio/mp4", "webm": "audio/webm", "aac": "audio/aac",
}
EXT_FOR = {"mp3": "mp3", "wav": "wav", "ogg": "ogg", "flac": "flac", "mp4": "m4a", "webm": "webm", "aac": "aac"}


# ------------------------------------------------------------------ ASGI: request body size limit
class BodyLimitMiddleware:
    """Reject oversized bodies *while streaming*, so a client that omits or lies about
    Content-Length cannot fill the disk or memory before our handlers run."""

    def __init__(self, app: ASGIApp, limit_for: Callable[[str], int]):
        self.app, self.limit_for = app, limit_for

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in ("GET", "HEAD", "OPTIONS"):
            await self.app(scope, receive, send)
            return
        limit = self.limit_for(scope["path"])
        declared = dict(scope["headers"]).get(b"content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            await self._reject(scope, receive, send, limit)
            return
        seen = 0

        async def limited_receive() -> Message:
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > limit:
                    raise HTTPException(status_code=413, detail="request body too large")
            return message

        await self.app(scope, limited_receive, send)

    async def _reject(self, scope: Scope, receive: Receive, send: Send, limit: int) -> None:
        body = (
            b'{"error":{"code":"too_large","message":"The upload is larger than the allowed '
            + str(limit // (1024 * 1024)).encode()
            + b' MB."}}'
        )
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
        await send({"type": "http.response.body", "body": body})


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; "
        "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
    ),
}
