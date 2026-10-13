# Code tour and likely follow-up questions

Read this before the technical discussion. Each answer points to the code that proves it.

## 10-minute walkthrough order
1. `app/pipeline.py` (`Doc`, `make_*_validator`): the idea of the project. LLM proposes, code verifies.
2. `app/llm.py` (`LLMClient.complete_json`, `_try_entry`): fallback, cooldowns, repair loop.
3. `app/transcript.py`: segments, subtitle parsing, why timestamps are only used when structural.
4. `app/transcribe.py` (`transcribe_file`): sniff → probe → compress/split → Whisper → offsets.
5. `app/security.py` + `app/main.py`: limits, headers, error shaping, background jobs.
6. `app/static/app.js`: `api()`, `loadSection()` (generation *and* revision), `cite()`.

## Questions to be ready for (and where the answer lives)
- **How do you stop the model inventing timestamps?** It never outputs them; it outputs segment numbers, and `make_chapters_validator` looks times up from the segment table (`pipeline.py`). Test: `test_chapters_timestamps_come_from_segments_not_model`.
- **How do you know a quiz answer is grounded?** `Doc.quote_supported` normalises (casefold, strip punctuation, keep Unicode marks) and checks the quote near the cited segment, with a 3-gram tolerance. Unverified questions are dropped; too few → repair → fallback.
- **What if Gemini is rate limited / the model disappears?** `LLMClient` classifies errors (`classify_http_error`), cools down 429s, disables 401/403/404 entries, and tries the next chain entry. Chain is env config.
- **Why is revision cheap?** One section = one endpoint call with `instruction` + `previous`; the other sections' state is untouched in the browser (`loadSection` in `app.js`).
- **Why a job + polling for audio?** Long work shouldn't hold an HTTP request open; free proxies time out; it also lets the UI show stages.
- **How are large files handled?** >24 MB → `compress_and_split` (16 kHz mono 32 kbps MP3, 20-min chunks), chunk offsets from measured durations, `ChunkResult` merge.
- **Security?** Keys in env only; header auth to Gemini; `BodyLimitMiddleware` counts streamed bytes; `sniff_audio` ignores filenames; ffmpeg gets `-f <demuxer>` and no shell; CSP; `textContent`-only rendering; per-IP limiter.
- **Why not Vercel?** 4.5 MB request-body cap; audio is a core feature (`docs/RESEARCH.md`).
- **What would you change with more time?** The three items in `ENGINEERING.md §G`.
- **What's the weakest part?** Be candid: quote verification proves existence not reasoning; summary claims aren't individually verified; free-tier cold starts and tiny CPU; I couldn't live-test the provider calls in my build sandbox, so provider adapters are tested against mocked HTTP built from the documented formats and verified live with `scripts/check_providers.py` / `scripts/smoke_live.py`.

## Small changes an interviewer might ask for (and how)
- *Add a "true/false" question type:* extend `_Question` and `make_quiz_validator`, add a branch in `questionEl` (app.js).
- *Change chapter count:* `chapter_range` in `pipeline.py`.
- *Add a provider:* implement `Provider.complete` (see `OpenAICompatProvider`), register in `build_llm`, add `provider:model` to `LLM_CHAIN` and `KNOWN_PROVIDERS`.
- *Lower the upload limit:* `MAX_AUDIO_MB` env var; the UI reads it from `/api/health`.
