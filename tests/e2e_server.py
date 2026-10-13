"""Local server with a deterministic fake LLM, used by the browser-level (jsdom) test.
It reads the numbered segments out of the prompt and returns schema-valid, verbatim-grounded JSON,
so the whole UI can be exercised without any API key or network."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import uvicorn  # noqa: E402

from app.config import Settings  # noqa: E402
from app.llm import ChainEntry, LLMClient  # noqa: E402
from app.main import create_app  # noqa: E402


class FakeLLM:
    fail_next_quiz = False

    def __init__(self, name: str = "gemini"):
        self.name = name

    async def complete(self, *, model, system, user, max_tokens, temperature):
        segs = [(int(m.group(1)), m.group(2)) for m in re.finditer(r"^\[S(\d+)[^\]]*\] (.*)$", user, re.M)]
        n = len(segs)
        revised = "REVISION MODE" in user
        if "write an episode overview" in user:
            return json.dumps({
                "title": ('<img src=x onerror="window.__xss=1">' if "XSSMARK" in user else "Why we forget") + (" (shorter)" if revised else "")
                + (" [groq]" if self.name == "groq" else ""), "one_line": "Fake one-liner.",
                "summary": "First paragraph of the fake summary text.\n\nSecond paragraph here." + ("" if revised else " More words."),
                "themes": [{"name": "Memory", "description": "How memory fades."}, {"name": "Study", "description": "Techniques."}],
                "takeaways": [{"text": f"Takeaway {i}", "evidence": [segs[i * 2 % n][0]]} for i in range(4)]})
        if "divide the episode" in user:
            return json.dumps({"chapters": [{"title": f"Chapter {i + 1}", "summary": "About something.", "start_segment": i * n // 3} for i in range(3)]})
        if "multiple-choice quiz" in user:
            if FakeLLM.fail_next_quiz:
                FakeLLM.fail_next_quiz = False
                raise RuntimeError  # not an LLMError -> would be 500; use rate limit instead below
            qs = []
            for i in range(6):
                sid, text = segs[(i * 3) % n]
                words = text.split()[:12]
                qs.append({"question": f"Fake question {i + 1} about passage {sid}?", "options": [f"Right {i}", f"Wrong a{i}", f"Wrong b{i}", f"Wrong c{i}"],
                           "correct_index": 0, "explanation": "Because the passage says so.", "evidence_segment": sid,
                           "evidence_quote": " ".join(words), "difficulty": "hard" if revised else "easy"})
            return json.dumps({"questions": qs})
        if "answer the listener" in user:
            q = re.search(r"<question>(.*?)</question>", user, re.S).group(1)
            if "sleep" in q.lower():
                sid, text = next((s for s in segs if "sleep" in s[1].lower()), segs[0])
                return json.dumps({"answerable": True, "answer": "Sleep consolidates memories.", "evidence": [{"segment": sid, "quote": " ".join(text.split()[:10])}]})
            return json.dumps({"answerable": False, "answer": "The episode does not cover this.", "evidence": []})
        return "{}"


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    s = Settings(gemini_api_key="fake", groq_api_key="fake", rate_limit_per_minute=500,
                 llm_chain=(("gemini", "fake-gemini"), ("groq", "fake-groq")))
    entries = [ChainEntry("gemini", "fake-gemini"), ChainEntry("groq", "fake-groq")]
    app = create_app(s, llm=LLMClient(entries, {"gemini": FakeLLM("gemini"), "groq": FakeLLM("groq")}))
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
