"""Pydantic models: API request bodies and the shapes we accept from LLMs."""
from __future__ import annotations

import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

Section = Literal["overview", "chapters", "quiz"]
# "auto" walks the whole fallback chain; a named provider pins the request to that provider's
# models only, so two providers can be compared on identical input.
ProviderChoice = Literal["auto", "gemini", "groq"]

MAX_SEGMENTS = 3000
MAX_SEGMENT_CHARS = 4000
MAX_INSTRUCTION_CHARS = 300


class Segment(BaseModel):
    id: int
    start: Optional[float] = None
    end: Optional[float] = None
    text: str = Field(max_length=MAX_SEGMENT_CHARS)


class TranscriptIn(BaseModel):
    """The transcript as the browser holds it. The server is stateless and re-validates it."""

    segments: list[Segment] = Field(min_length=1, max_length=MAX_SEGMENTS)
    has_timestamps: bool = False
    source: Literal["text", "audio"] = "text"
    language: Optional[str] = Field(default=None, max_length=16)


class ParseRequest(BaseModel):
    text: str = Field(max_length=2_000_000)
    filename: Optional[str] = Field(default=None, max_length=255)


class GenerateOptions(BaseModel):
    num_questions: int = Field(default=6, ge=3, le=12)


class GenerateRequest(BaseModel):
    transcript: TranscriptIn
    section: Section
    options: GenerateOptions = GenerateOptions()
    # Revision: the user's change request and the output it applies to.
    instruction: Optional[str] = Field(default=None, max_length=MAX_INSTRUCTION_CHARS)
    previous: Optional[dict[str, Any]] = None
    provider: ProviderChoice = "auto"

    @field_validator("instruction")
    @classmethod
    def _strip_instruction(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = re.sub(r"\s+", " ", v).strip()
        return v or None


class AskRequest(BaseModel):
    transcript: TranscriptIn
    question: str = Field(min_length=3, max_length=300)
    provider: ProviderChoice = "auto"


# ---------------------------------------------------------------- LLM output shapes
def coerce_segment_id(value: Any) -> Optional[int]:
    """Accept 12, "12", "S12", "[S12]", 12.0 -- models are inconsistent about this."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if float(value).is_integer() else None
    if isinstance(value, str):
        m = re.search(r"\d+", value)
        return int(m.group()) if m else None
    return None
