"""Section generators and the grounding checks that make their output trustworthy.

Design: the LLM proposes, deterministic code disposes.
* Chapters: the model gives only *segment numbers*; timestamps are looked up from the real
  segment table, so a timestamp can never be invented.
* Quiz: every question must carry a verbatim quote that we verify against the transcript.
  Questions whose quote can't be found are dropped; answer options are shuffled server-side to
  remove the model's positional bias.
* Takeaways: must cite real segment numbers.
"""
from __future__ import annotations

import hashlib
import random
import re
from typing import Any, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from . import prompts
from .llm import CallInfo, GroundingError, LLMClient
from .schemas import GenerateRequest, TranscriptIn, coerce_segment_id
from .transcript import fmt_time, normalize_for_match, render_for_prompt


# ------------------------------------------------------------------ transcript helpers
class Doc:
    """Normalised, read-only view over the transcript supplied by the client."""

    def __init__(self, tr: TranscriptIn):
        # Re-index so ids are always 0..n-1 regardless of what the client sent.
        self.segments: list[dict] = []
        for i, s in enumerate(tr.segments):
            text = s.text.strip()
            if text:
                self.segments.append({"id": len(self.segments), "start": s.start, "end": s.end, "text": text})
        if not self.segments:
            raise GroundingError("transcript has no text")
        self.has_timestamps = tr.has_timestamps and all(s["start"] is not None for s in self.segments)
        self.n = len(self.segments)
        self.words = sum(len(s["text"].split()) for s in self.segments)
        self._norm = [normalize_for_match(s["text"]) for s in self.segments]
        self._full_norm = " ".join(self._norm)

    @property
    def prompt_text(self) -> str:
        return render_for_prompt(self.segments, self.has_timestamps)

    def valid_id(self, i: Optional[int]) -> bool:
        return i is not None and 0 <= i < self.n

    def time_of(self, seg_id: int) -> Optional[float]:
        return self.segments[seg_id]["start"] if self.has_timestamps else None

    # -- quote verification --
    def quote_supported(self, quote: str, seg_id: Optional[int]) -> bool:
        q = normalize_for_match(quote)
        if len(q.split()) < 4:
            return False
        if seg_id is not None and self.valid_id(seg_id):
            lo, hi = max(0, seg_id - 1), min(self.n, seg_id + 2)
            if q in " ".join(self._norm[lo:hi]):
                return True
        if q in self._full_norm:
            return True
        # Tolerate tiny deviations (a dropped filler word): require 90% of the quote's word
        # 3-grams to occur in the neighbourhood of the cited segment.
        if seg_id is not None and self.valid_id(seg_id):
            lo, hi = max(0, seg_id - 1), min(self.n, seg_id + 2)
            hay = " ".join(self._norm[lo:hi])
            words = q.split()
            grams = [" ".join(words[i : i + 3]) for i in range(len(words) - 2)]
            if grams and sum(1 for g in grams if g in hay) / len(grams) >= 0.9:
                return True
        return False


# ------------------------------------------------------------------ output shapes
class _Theme(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=600)


class _Takeaway(BaseModel):
    text: str = Field(min_length=3, max_length=600)
    evidence: list[Any] = Field(default_factory=list)


class _Overview(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    one_line: str = Field(default="", max_length=400)
    summary: str = Field(min_length=20, max_length=6000)
    themes: list[_Theme] = Field(min_length=1, max_length=10)
    takeaways: list[_Takeaway] = Field(min_length=1, max_length=12)


class _Chapter(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(default="", max_length=800)
    start_segment: Any


class _Chapters(BaseModel):
    chapters: list[_Chapter] = Field(min_length=1, max_length=40)


class _Question(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    options: list[str] = Field(min_length=2, max_length=8)
    correct_index: Any
    explanation: str = Field(default="", max_length=800)
    evidence_segment: Any = None
    evidence_quote: str = Field(default="", max_length=600)
    difficulty: str = "medium"

    @field_validator("options", mode="before")
    @classmethod
    def _opts(cls, v):
        if isinstance(v, list):
            return [re.sub(r"^\s*(?:[A-Da-d][\).:]|\(?[A-Da-d]\))\s+", "", str(o)).strip() for o in v]
        return v


class _Quiz(BaseModel):
    questions: list[_Question] = Field(min_length=1, max_length=30)


def _parse(model: type[BaseModel], obj: dict):
    try:
        return model.model_validate(obj)
    except ValidationError as exc:
        # Compact, model-readable description for the repair attempt.
        parts = [f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in exc.errors()[:6]]
        raise GroundingError("JSON does not match the required shape -> " + "; ".join(parts)) from exc


# ------------------------------------------------------------------ validators
def make_overview_validator(doc: Doc):
    def validate(obj: dict) -> dict:
        ov = _parse(_Overview, obj)
        takeaways, dropped = [], 0
        for t in ov.takeaways:
            ids = []
            for raw in t.evidence:
                sid = coerce_segment_id(raw)
                if doc.valid_id(sid) and sid not in ids:
                    ids.append(sid)
            if not ids:
                dropped += 1
                continue
            takeaways.append({"text": t.text.strip(), "evidence": ids[:3]})
        if len(takeaways) < min(3, len(ov.takeaways)):
            raise GroundingError(
                "Too many takeaways cite no valid segment numbers. Every takeaway needs 1-3 existing segment numbers "
                f"(valid range 0-{doc.n - 1})."
            )
        out = {
            "title": ov.title.strip(),
            "one_line": ov.one_line.strip(),
            "summary": ov.summary.strip(),
            "themes": [{"name": t.name.strip(), "description": t.description.strip()} for t in ov.themes[:6]],
            "takeaways": takeaways[:7],
        }
        if dropped:
            out["_warnings"] = [f"{dropped} takeaway(s) removed because they cited no valid transcript segment."]
        return out

    return validate


def chapter_range(doc: Doc) -> tuple[int, int]:
    target = max(3, min(12, round(doc.words / 700)))
    lo, hi = max(2, target - 1), min(14, target + 2)
    if doc.n < 6:
        lo, hi = 1, 2
    return lo, min(hi, max(1, doc.n))


def make_chapters_validator(doc: Doc, lo: int, hi: int):
    def validate(obj: dict) -> dict:
        ch = _parse(_Chapters, obj)
        seen: dict[int, _Chapter] = {}
        for c in ch.chapters:
            sid = coerce_segment_id(c.start_segment)
            if doc.valid_id(sid) and sid not in seen:
                seen[sid] = c
        starts = sorted(seen)
        if not starts:
            raise GroundingError(f"No chapter has a valid start_segment (valid range 0-{doc.n - 1}).")
        if starts[0] != 0:  # the first chapter always starts at the beginning
            seen[0] = seen.pop(starts[0])
            starts[0] = 0
        starts = starts[:20]
        if len(starts) < lo:
            raise GroundingError(
                f"Only {len(starts)} chapters had valid, strictly increasing start_segment values; return at least {lo}."
            )
        chapters = []
        for i, s in enumerate(starts):
            end = (starts[i + 1] - 1) if i + 1 < len(starts) else doc.n - 1
            c = seen[s]
            chapters.append(
                {
                    "title": c.title.strip(),
                    "summary": c.summary.strip(),
                    "start_segment": s,
                    "end_segment": end,
                    # Looked up, never model-generated:
                    "start_time": doc.segments[s]["start"] if doc.has_timestamps else None,
                    "end_time": doc.segments[end]["end"] if doc.has_timestamps else None,
                }
            )
        return {"chapters": chapters, "has_timestamps": doc.has_timestamps}

    return validate


def make_quiz_validator(doc: Doc, requested: int):
    minimum = max(2, min(requested, 3))

    def validate(obj: dict) -> dict:
        quiz = _parse(_Quiz, obj)
        good, problems, seen_q = [], [], set()
        for i, q in enumerate(quiz.questions):
            opts = [o for o in q.options if o]
            ci = coerce_segment_id(q.correct_index)
            if len(set(o.casefold() for o in opts)) != len(opts) or len(opts) < 3:
                problems.append(f"Q{i + 1}: needs distinct options (3-4)")
                continue
            if ci is None or not (0 <= ci < len(opts)):
                problems.append(f"Q{i + 1}: correct_index out of range")
                continue
            sid = coerce_segment_id(q.evidence_segment)
            if not doc.quote_supported(q.evidence_quote, sid):
                problems.append(f"Q{i + 1}: evidence_quote not found verbatim near segment {sid}")
                continue
            key = normalize_for_match(q.question)
            if key in seen_q:
                continue
            seen_q.add(key)
            correct_text = opts[ci]
            # Shuffle deterministically (stable across re-validation) to avoid "answer is always B".
            rng = random.Random(hashlib.sha1(q.question.encode("utf-8")).hexdigest())
            rng.shuffle(opts)
            diff = q.difficulty.strip().lower()
            good.append(
                {
                    "question": q.question.strip(),
                    "options": opts,
                    "correct_index": opts.index(correct_text),
                    "explanation": q.explanation.strip(),
                    "difficulty": diff if diff in ("easy", "medium", "hard") else "medium",
                    "evidence_segment": sid if doc.valid_id(sid) else None,
                    "evidence_quote": q.evidence_quote.strip(),
                    "evidence_time": doc.time_of(sid) if doc.valid_id(sid) else None,
                    "verified": True,
                }
            )
        if len(good) < minimum:
            raise GroundingError(
                f"Only {len(good)} of {len(quiz.questions)} questions passed verification (need at least {minimum}). "
                "Problems: " + "; ".join(problems[:6]) + ". Copy evidence_quote exactly from the cited segment."
            )
        out: dict[str, Any] = {"questions": good[: max(requested, minimum)]}
        if problems:
            out["_warnings"] = [
                f"{len(problems)} generated question(s) were discarded because their source quote could not be "
                "verified in the transcript."
            ]
        return out

    return validate


def make_ask_validator(doc: Doc):
    def validate(obj: dict) -> dict:
        answerable = bool(obj.get("answerable"))
        answer = str(obj.get("answer", "")).strip()[:1200]
        if not answer:
            raise GroundingError("answer is empty")
        evidence = []
        if answerable:
            for e in (obj.get("evidence") or [])[:4]:
                if not isinstance(e, dict):
                    continue
                sid = coerce_segment_id(e.get("segment"))
                quote = str(e.get("quote", "")).strip()
                if doc.valid_id(sid) and doc.quote_supported(quote, sid):
                    evidence.append({"segment": sid, "quote": quote, "time": doc.time_of(sid)})
            if not evidence:
                # An answer we cannot back with a verifiable quote is treated as unsupported.
                return {
                    "answerable": False,
                    "answer": "I couldn't find a passage in the transcript that clearly answers this, so I won't guess.",
                    "evidence": [],
                    "downgraded": True,
                }
        return {"answerable": answerable, "answer": answer, "evidence": evidence}

    return validate


# ------------------------------------------------------------------ orchestration
async def generate_section(llm: LLMClient, req: GenerateRequest) -> tuple[dict, CallInfo]:
    doc = Doc(req.transcript)
    instr, prev = req.instruction, req.previous
    if instr and not prev:
        raise GroundingError("A revision needs the previous output.")
    text = doc.prompt_text
    if req.section == "overview":
        user = prompts.overview_prompt(text, instr, prev)
        validator, max_tokens = make_overview_validator(doc), 3000
    elif req.section == "chapters":
        lo, hi = chapter_range(doc)
        if instr:  # "fewer, broader" / "more granular" must be able to move the count either way
            lo, hi = (2 if doc.n >= 6 else 1), 14
        user = prompts.chapters_prompt(text, lo, hi, instr, prev)
        validator, max_tokens = make_chapters_validator(doc, lo, hi), 3500
    else:
        n = req.options.num_questions
        user = prompts.quiz_prompt(text, n, instr, prev)
        validator, max_tokens = make_quiz_validator(doc, n), 6000
    result, info = await llm.complete_json(
        system=prompts.SYSTEM, user=user, validator=validator, max_tokens=max_tokens, temperature=0.2,
        provider=None if req.provider == "auto" else req.provider,
    )
    warnings = result.pop("_warnings", [])
    info.warnings.extend(warnings)
    return result, info


async def answer_question(
    llm: LLMClient, tr: TranscriptIn, question: str, provider: str = "auto"
) -> tuple[dict, CallInfo]:
    doc = Doc(tr)
    result, info = await llm.complete_json(
        system=prompts.SYSTEM,
        user=prompts.ask_prompt(doc.prompt_text, question),
        validator=make_ask_validator(doc),
        max_tokens=1500,
        temperature=0.1,
        provider=None if provider == "auto" else provider,
    )
    return result, info
