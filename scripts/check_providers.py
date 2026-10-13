"""Verify your keys and model IDs with REAL calls. Run this before deploying and whenever a model is retired.

    python scripts/check_providers.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from app.config import Settings  # noqa: E402
from app.main import build_llm  # noqa: E402


async def main() -> int:
    load_dotenv()
    s = Settings.from_env()
    print("Configured providers:", ", ".join(s.configured_providers()) or "NONE")
    if not s.configured_providers():
        print("Add at least one key to .env (see .env.example).")
        return 1
    failures = 0
    async with httpx.AsyncClient(timeout=60) as client:
        llm = build_llm(s, client)
        print("\nLLM chain (one tiny call each):")
        for entry in llm.entries:
            prov = llm.providers.get(entry.provider)
            if prov is None:
                print(f"  SKIP  {entry.key}  (no key for {entry.provider})")
                continue
            try:
                out = await prov.complete(model=entry.model, system="Reply with JSON only.", user='Return {"ok": true}', max_tokens=50, temperature=0)
                print(f"  OK    {entry.key}  -> {out.strip()[:60]!r}")
            except Exception as exc:  # report, don't crash: the point is to see every entry's status
                failures += 1
                print(f"  FAIL  {entry.key}  -> {type(exc).__name__}: {str(exc)[:140]}")
        if s.gemini_api_key:
            r = await client.get("https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", headers={"x-goog-api-key": s.gemini_api_key})
            if r.status_code == 200:
                names = sorted(m["name"].removeprefix("models/") for m in r.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", []))
                print("\nGemini models your key can call (pick from these for LLM_CHAIN):\n  " + "\n  ".join(n for n in names if "flash" in n))
        if s.groq_api_key:
            r = await client.get("https://api.groq.com/openai/v1/models", headers={"Authorization": f"Bearer {s.groq_api_key}"})
            ids = sorted(m["id"] for m in r.json().get("data", [])) if r.status_code == 200 else []
            print(f"\nGroq key: HTTP {r.status_code}; whisper models available: {[i for i in ids if 'whisper' in i]}")
    return 1 if failures == len(llm.entries) else 0


sys.exit(asyncio.run(main()))
