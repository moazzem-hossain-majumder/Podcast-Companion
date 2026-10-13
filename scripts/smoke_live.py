"""End-to-end check of a RUNNING deployment, with timings you can quote in your write-up.

    python scripts/smoke_live.py https://your-app.onrender.com
"""
import json
import sys
import time
import urllib.error
import urllib.request

base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")


def call(path, body=None, timeout=180):
    req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r), time.time() - t
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}"), time.time() - t
    except (urllib.error.URLError, TimeoutError) as e:
        sys.exit(f"Could not reach {base}{path}: {getattr(e, 'reason', e)}. Is the server running / the URL correct?")


def check(name, ok, secs, detail=""):
    print(f"{'PASS' if ok else 'FAIL'}  {name:<34} {secs:6.1f}s  {detail}")
    return ok


all_ok = True
health, t = call("/api/health", timeout=120)  # first call may wake a sleeping free instance
all_ok &= check("health (cold start included)", health.get("llm_ready", False), t, f"providers={health.get('providers')}")
sample = urllib.request.urlopen(base + "/sample.txt").read().decode()
tr, t = call("/api/transcript/parse", {"text": sample})
all_ok &= check("parse sample transcript", bool(tr.get("segments")), t, f"{len(tr.get('segments', []))} segments")
results = {}
for section in ("overview", "chapters", "quiz"):
    res, t = call("/api/generate", {"transcript": tr, "section": section})
    ok = "result" in res
    results[section] = res.get("result")
    all_ok &= check(f"generate {section}", ok, t, (res.get("meta", {}).get("model", "") if ok else res.get("error", {}).get("message", "")))
if results["quiz"]:
    q = results["quiz"]["questions"]
    all_ok &= check("quiz questions grounded", all(x["verified"] for x in q), 0, f"{len(q)} questions verified")
if results["overview"]:
    res, t = call("/api/generate", {"transcript": tr, "section": "overview", "instruction": "Make it much shorter", "previous": results["overview"]})
    ok = "result" in res
    shorter = ok and len(res["result"]["summary"]) < len(results["overview"]["summary"])
    all_ok &= check("revise overview (shorter)", ok, t, f"summary {len(results['overview']['summary'])} -> {len(res['result']['summary']) if ok else '?'} chars, shorter={shorter}")
res, t = call("/api/ask", {"transcript": tr, "question": "Who won the 1998 football world cup?"})
all_ok &= check("ask: unanswerable is refused", res.get("result", {}).get("answerable") is False, t, res.get("result", {}).get("answer", "")[:70])
res, t = call("/api/ask", {"transcript": tr, "question": "What does the episode say about sleep?"})
all_ok &= check("ask: answerable has evidence", bool(res.get("result", {}).get("evidence")), t)
print("\nALL CHECKS PASSED" if all_ok else "\nSOME CHECKS FAILED")
sys.exit(0 if all_ok else 1)
