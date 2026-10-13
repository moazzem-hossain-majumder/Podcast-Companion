"""Turning raw text / subtitle files / Whisper output into numbered segments.

Everything downstream (chapters, citations, timestamps) refers to segments by ID. That is
the key reliability trick: the model only ever *points at* segments, and the server looks
up the real timestamps, so a timestamp can never be invented by the model.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

MAX_MERGED_CHARS = 600
MAX_MERGED_SECONDS = 45.0
SENTENCE_SPLIT = re.compile(r"(?<=[.!?।॥。！？])\s+")
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class TranscriptError(ValueError):
    """User-facing problem with the supplied transcript."""


@dataclass
class RawCue:
    text: str
    start: Optional[float] = None
    end: Optional[float] = None


# ------------------------------------------------------------------ helpers
def fmt_time(seconds: Optional[float]) -> str:
    if seconds is None:
        return ""
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def clean_text(text: str) -> str:
    text = text.lstrip("\ufeff")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = CONTROL_CHARS.sub("", text)
    return text.strip()


def _hms_to_seconds(h: Optional[str], m: str, s: str, frac: Optional[str] = None) -> float:
    total = int(h or 0) * 3600 + int(m) * 60 + int(s)
    if frac:
        total += float("0." + frac)
    return float(total)


# ------------------------------------------------------------------ Markdown
_MD_FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
_MD_HEADING = re.compile(r"^\s{0,3}#{1,6}\s+.*$", re.M)
_MD_RULE = re.compile(r"^\s{0,3}(?:[-*_]\s*){3,}$", re.M)
_MD_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
_MD_EMPHASIS = re.compile(r"(\*\*|__|\*|_|`)(?=\S)(.+?)(?<=\S)\1")
_MD_QUOTE_OR_BULLET = re.compile(r"^\s{0,3}(?:>\s?|[-*+]\s+|\d+[.)]\s+)", re.M)


def strip_markdown(text: str) -> str:
    """Reduce a Markdown transcript to its spoken text: headings, rules and front matter are not
    speech and are dropped; emphasis, links, quotes and bullets keep their words only."""
    text = _MD_FRONT_MATTER.sub("", text)
    text = _MD_HEADING.sub("", text)
    text = _MD_RULE.sub("", text)
    text = _MD_LINK.sub(r"\1", text)
    for _ in range(2):  # nested emphasis such as *a **b** c*
        text = _MD_EMPHASIS.sub(r"\2", text)
    text = _MD_QUOTE_OR_BULLET.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# ------------------------------------------------------------------ SRT / VTT
_CUE_TIME = re.compile(
    r"(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[.,](\d{1,3})\s*-->\s*(?:(\d{1,2}):)?(\d{1,2}):(\d{2})[.,](\d{1,3})"
)
_TAGS = re.compile(r"<[^>]+>|\{\\[^}]*\}")


def looks_like_subtitles(text: str) -> bool:
    return text.startswith("WEBVTT") or len(_CUE_TIME.findall(text)) >= 3


def parse_subtitles(text: str) -> list[RawCue]:
    cues: list[RawCue] = []
    for block in re.split(r"\n\s*\n", text):
        lines = [ln for ln in block.split("\n") if ln.strip()]
        for i, line in enumerate(lines):
            m = _CUE_TIME.search(line)
            if not m:
                continue
            g = m.groups()
            start = _hms_to_seconds(g[0], g[1], g[2], g[3])
            end = _hms_to_seconds(g[4], g[5], g[6], g[7])
            body = " ".join(_TAGS.sub("", ln).strip() for ln in lines[i + 1 :])
            body = re.sub(r"\s+", " ", body).strip()
            if body:
                cues.append(RawCue(body, start, end))
            break
    return cues


# ------------------------------------------------------------------ inline "[12:34] text" stamps
_STAMP = re.compile(
    r"^\s*[\[(]?(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?:[.,](\d{1,3}))?[\])]?\s*(?:[-–—:]\s*)?(.*)$"
)


def parse_inline_timestamps(text: str) -> Optional[list[RawCue]]:
    """Return cues only if timestamps are clearly a *structure* of the file, not incidental
    mentions like '3:30 pm we met'. Heuristic: most lines carry one and they never go backwards."""
    lines = [ln for ln in text.split("\n") if ln.strip()]
    if len(lines) < 3:
        return None
    parsed: list[tuple[Optional[float], str]] = []
    matches = 0
    for ln in lines:
        m = _STAMP.match(ln)
        if m and m.group(5).strip():
            h, mm, ss, frac, body = m.groups()
            parsed.append((_hms_to_seconds(h, mm, ss, frac), body.strip()))
            matches += 1
        else:
            parsed.append((None, ln.strip()))
    if matches < 3 or matches / len(lines) < 0.5:
        return None
    stamps = [t for t, _ in parsed if t is not None]
    non_decreasing = sum(1 for a, b in zip(stamps, stamps[1:]) if b >= a)
    if len(stamps) > 1 and non_decreasing / (len(stamps) - 1) < 0.9:
        return None
    cues: list[RawCue] = []
    for t, body in parsed:
        if t is not None:
            cues.append(RawCue(body, t, None))
        elif cues:  # continuation line without its own stamp
            cues[-1].text += " " + body
    for cur, nxt in zip(cues, cues[1:]):
        cur.end = nxt.start
    return cues


# ------------------------------------------------------------------ plain text
def split_plain(text: str) -> list[RawCue]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) == 1:
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        if len(lines) >= 5:
            paragraphs = lines
    pieces: list[str] = []
    for p in paragraphs:
        p = re.sub(r"\s+", " ", p)
        if len(p) <= MAX_MERGED_CHARS * 1.5:
            pieces.append(p)
            continue
        buf = ""
        for sent in SENTENCE_SPLIT.split(p):
            while len(sent) > MAX_MERGED_CHARS * 1.5:  # no punctuation at all: hard split on spaces
                cut = sent.rfind(" ", 0, MAX_MERGED_CHARS)
                cut = cut if cut > 0 else MAX_MERGED_CHARS
                pieces.append(sent[:cut].strip())
                sent = sent[cut:].strip()
            if buf and len(buf) + len(sent) + 1 > MAX_MERGED_CHARS:
                pieces.append(buf)
                buf = sent
            else:
                buf = f"{buf} {sent}".strip()
        if buf:
            pieces.append(buf)
    return [RawCue(p) for p in pieces if p]


# ------------------------------------------------------------------ merging
def merge_cues(cues: list[RawCue]) -> list[dict]:
    """Group tiny cues (2-5 s subtitle lines, short Whisper segments) into prompt-friendly segments."""
    merged: list[dict] = []
    cur: Optional[dict] = None
    for cue in cues:
        text = re.sub(r"\s+", " ", cue.text).strip()
        if not text:
            continue
        if cur is not None:
            too_long = len(cur["text"]) + len(text) + 1 > MAX_MERGED_CHARS
            too_slow = (
                cur["start"] is not None
                and cue.end is not None
                and cue.end - cur["start"] > MAX_MERGED_SECONDS
            )
            if too_long or too_slow:
                merged.append(cur)
                cur = None
        if cur is None:
            cur = {"start": cue.start, "end": cue.end, "text": text}
        else:
            cur["text"] += " " + text
            if cue.end is not None:
                cur["end"] = cue.end
    if cur is not None:
        merged.append(cur)
    out = []
    for i, seg in enumerate(merged):
        out.append({"id": i, "start": seg["start"], "end": seg["end"], "text": seg["text"]})
    return out


def build_transcript(
    cues: list[RawCue], *, source: str, language: Optional[str] = None, timestamps_reliable: bool = True
) -> dict:
    segments = merge_cues(cues)
    has_ts = timestamps_reliable and bool(segments) and all(s["start"] is not None for s in segments)
    if not has_ts:
        for s in segments:
            s["start"] = s["end"] = None
    else:  # make sure every segment has an end
        for s, nxt in zip(segments, segments[1:] + [None]):
            if s["end"] is None:
                s["end"] = nxt["start"] if nxt else s["start"]
    return {"segments": segments, "has_timestamps": has_ts, "source": source, "language": language}


def parse_transcript(text: str, *, min_chars: int, max_chars: int, filename: Optional[str] = None) -> dict:
    text = clean_text(text)
    if filename and filename.lower().endswith((".md", ".markdown")):
        text = strip_markdown(text)
    letters = sum(1 for ch in text if unicodedata.category(ch).startswith("L"))
    if len(text) < min_chars:
        raise TranscriptError(
            f"The transcript is too short ({len(text)} characters). Provide at least {min_chars} characters."
        )
    if len(text) > max_chars:
        raise TranscriptError(
            f"The transcript is too long ({len(text):,} characters). The limit is {max_chars:,} characters; "
            "split the episode and process it in parts."
        )
    if letters < len(text) * 0.4:
        raise TranscriptError("That doesn't look like a text transcript (too few letters). Check the file.")

    if looks_like_subtitles(text):
        cues = parse_subtitles(text)
        if len(cues) >= 2:
            return build_transcript(cues, source="text")
    inline = parse_inline_timestamps(text)
    if inline:
        return build_transcript(inline, source="text")
    cues = split_plain(text)
    if not cues:
        raise TranscriptError("No readable text found in the transcript.")
    return build_transcript(cues, source="text", timestamps_reliable=False)


# ------------------------------------------------------------------ prompt rendering
def render_for_prompt(segments: list[dict], has_timestamps: bool) -> str:
    lines = []
    for s in segments:
        stamp = f" | {fmt_time(s['start'])}" if has_timestamps and s.get("start") is not None else ""
        lines.append(f"[S{s['id']}{stamp}] {s['text']}")
    return "\n".join(lines)


_PUNCT_SYMBOL = re.compile(r"[\W_]+", re.UNICODE)


def normalize_for_match(text: str) -> str:
    """Casefold + strip punctuation, but keep combining marks so Bengali/Hindi etc. compare correctly."""
    text = unicodedata.normalize("NFKC", text).casefold()
    out = []
    for ch in text:
        cat = unicodedata.category(ch)
        out.append(" " if cat[0] in ("P", "S", "Z", "C") else ch)
    return re.sub(r"\s+", " ", "".join(out)).strip()
