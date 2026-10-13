import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402
from app.llm import ChainEntry, LLMClient  # noqa: E402
from app.transcript import parse_transcript  # noqa: E402

SAMPLE = (Path(__file__).resolve().parent.parent / "app" / "static" / "sample.txt").read_text()


@pytest.fixture(scope="session")
def sample_text() -> str:
    return SAMPLE


@pytest.fixture()
def sample_transcript() -> dict:
    return parse_transcript(SAMPLE, min_chars=200, max_chars=150_000)


class FakeProvider:
    """Scriptable provider: each call pops the next item (a string to return or an Exception to raise)."""

    def __init__(self, name, script):
        self.name, self.script, self.calls = name, list(script), []

    async def complete(self, *, model, system, user, max_tokens, temperature):
        self.calls.append({"model": model, "user": user})
        item = self.script.pop(0) if self.script else RuntimeError("script exhausted")
        if isinstance(item, Exception):
            raise item
        return item if isinstance(item, str) else json.dumps(item)


def make_client(providers, entries=None, **kw):
    entries = entries or [ChainEntry(p.name, f"{p.name}-model") for p in providers]

    async def no_sleep(_):
        return None

    return LLMClient(entries, {p.name: p for p in providers}, sleep=no_sleep, **kw)
