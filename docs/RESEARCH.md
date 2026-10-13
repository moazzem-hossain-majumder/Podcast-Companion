# Research and comparison

Researched in October 2026 using official documentation first. Where I relied on a community or third-party source it is labelled. Constraints that drove everything: **free tiers only**, a **48 h / ~10 h** budget, and a working deployed app.

## 1. User value

**Who benefits.** (a) Learners who treat podcasts as study material and need to revisit specifics; (b) people short on time who want to decide if an episode is worth 90 minutes; (c) accessibility: people who prefer reading, or have trouble following long audio; (d) creators/teachers who want chapters and comprehension questions for their own episodes.

**The problem to solve particularly well:** *finding and verifying*. A listener's pain isn't "I need a summary" (any chatbot does that) but "where did they say that, and can I trust this?" So the product centres on **citations**: every takeaway, quiz answer and chat answer links to the exact passage. That is also what makes the output safe to rely on.

## 2. Technology choices (options compared)

### 2a. Text generation (summary, chapters, quiz, Q&A)

| Option | Strengths | Weaknesses / limits | Verdict |
|---|---|---|---|
| **Google Gemini Flash / Flash-Lite** (Gemini API) | ~1M-token context (a full episode fits in one call, so chapters see the whole story); native JSON output mode; free tier; prompts via a single REST call | Free tier has low RPM (sources I found range 5-15 RPM depending on model/date) and **free-tier prompts may be used to improve Google's products**; model IDs are retired quickly (see below) | **Primary** |
| **Groq** (`openai/gpt-oss-120b`, OpenAI-compatible) | Very fast (measured 1.6-4.9 s per section, §6); JSON mode; same key also gives Whisper | Free tier: **8K tokens/min, 30 requests/min, 200K tokens/day**, so one ~11-minute episode fits only 1-2 sections per minute; open-weight reasoning model needs output headroom for hidden reasoning | **Fallback #1** and the comparison model |
| **Hugging Face Inference Providers** (router, many open models) | One token, OpenAI-compatible endpoint, large model choice | Free accounts get a **small monthly credit**; exhausted credits return HTTP 402 (documented in the HF forum) | **Fallback #2** (treated as rate limit) |
| Local open-source (llama.cpp / Ollama) | Private, no quota | Needs RAM/GPU that free hosting doesn't have (512 MB) | Rejected for the deployed app |

**Lesson that shaped the architecture: vendor model dates move in both directions.** When I started, Google's deprecations page listed `gemini-2.5-flash` for shutdown on October 16, 2026, and forum users reported 404 "no longer available" errors from it in July, months *before* that date. By the page's 2026-10-09 update, Google lists 2.5 Flash as "not deprecated" and served "until further notice". Its newer models also move: `gemini-3.5-flash` requests are now automatically routed to `gemini-3.6-flash`, and `gemini-3.1-flash-lite` has an earliest shutdown of May 7, 2027. Hard-coding one model would have risked breaking the product during review. So the model chain is **configuration** (`LLM_CHAIN`), a 404 permanently disables that entry for the process and falls through, and `scripts/check_providers.py` lists the models a key can actually call. Defaults are `gemini-3.5-flash` then `gemini-3.1-flash-lite`.

Sources:
- Gemini deprecations: https://ai.google.dev/gemini-api/docs/deprecations
- Gemini rate limits (limits are per project and model; free tier restricted): https://ai.google.dev/gemini-api/docs/rate-limits
- Forum thread on early 2.5 Flash 404s (community): https://discuss.ai.google.dev/t/gemini-2-5-flash-deprecated-without-warning-earlier-than-shutdown-date/174217
- HF Inference Providers (OpenAI-compatible router, free monthly credits): https://huggingface.co/inference/get-started and https://huggingface.co/docs/inference-providers/guides/gpt-oss
- HF 402 "exceeded monthly credits" behaviour (community): https://discuss.huggingface.co/t/hugging-face-payment-error-402-youve-exceeded-monthly-quota/144968
- Groq rate limits (gpt-oss-120b: 30 RPM, 1K RPD, 8K TPM, 200K TPD): https://console.groq.com/docs/rate-limits
- Groq deprecations (`llama-3.3-70b-versatile` shut down 2026-08-16, replacement `openai/gpt-oss-120b`): https://console.groq.com/docs/deprecations

**Second lesson, found by running the app, not by reading:** this project was first built on Groq's `llama-3.3-70b-versatile`. In the live benchmark every Groq call failed within 0.2 s. The improved error message (section 6) reported `model_unavailable`, and Groq's deprecations page confirmed the model was shut down on 2026-08-16. Groq's *models* page still listed it as a production model, so reading one official page was not enough; only a live call told the truth. The default is now `openai/gpt-oss-120b`, Groq's named replacement.

### 2b. Speech to text

| Option | Strengths | Weaknesses / limits | Verdict |
|---|---|---|---|
| **Groq Whisper (`whisper-large-v3-turbo`, `whisper-large-v3`)** | Hosted Whisper, OpenAI-compatible endpoint; `verbose_json` returns **segment timestamps**; docs list ~216x real-time for turbo; 100+ languages | **25 MB upload limit** on the free tier; formats flac/mp3/mp4/mpeg/mpga/m4a/ogg/wav/webm; audio is downsampled to 16 kHz mono | **Primary** (turbo first, large-v3 second: separate model, better accuracy) |
| **Gemini audio understanding** | Handles audio natively, good multilingual transcription | Timestamps not dependable; inline audio capped near 20 MB per request | **Last-resort fallback, text only** (timestamps are then dropped and the UI says so) |
| OpenAI Whisper API (the brief's example) | Reference implementation | Paid; the brief forbids unapproved costs | Not used |
| Local `faster-whisper` / `whisper.cpp` | Free, private | CPU-bound; hopeless on a 0.1 vCPU free instance | Rejected for deployment; viable if self-hosted |

Groq's rate-limits page lists Whisper (turbo and large-v3) at 20 requests/min, 7,200 audio-seconds/hour and 28,800 audio-seconds/day, which is about 2 hours of audio per hour and 8 per day: plenty for a demo, and the reason the app runs one transcription at a time. Raw `.aac` is not in Groq's accepted formats, so the app converts it to MP3 with ffmpeg first.

What I learned from the Groq docs and acted on: the 25 MB limit and the recommendation to downsample to 16 kHz mono (they suggest `ffmpeg`) led to my **compress-and-split** step (16 kHz mono 32 kbps MP3, 20-minute chunks, about 14 MB per hour), which lets a typical 50 MB podcast MP3 work. Because `verbose_json` returns segment times, timestamps can be real. Chunk time offsets use each chunk's *measured* duration, not an assumed 20:00.

Sources:
- Groq speech-to-text docs (limits, formats, models, verbose_json): https://console.groq.com/docs/speech-to-text
- Brief-provided references: OpenAI audio transcription docs (https://platform.openai.com/docs/guides/speech-to-text) and OWASP API Security Project (https://owasp.org/www-project-api-security/). I used the latter as the checklist in section 5 below.

### 2c. Hosting

| Option | Finding | Verdict |
|---|---|---|
| **Vercel** (what I've used before) | Function request/response bodies are capped at **4.5 MB**, and streaming doesn't lift the request limit (Vercel docs + community). Real podcast files are 20-100 MB. Function duration limits also vary by plan and configuration, which complicates long audio jobs. | Fine for transcript-only; **rejected** because audio is a core feature |
| **Hugging Face Spaces (Docker)** | As of July 2026 HF docs and forum reports state Docker/Gradio Spaces on CPU Basic now **require a paid plan** for new accounts; only static Spaces are free | **Rejected** (would cost money) |
| **Render free web service** | Python/Docker, no card required, 512 MB RAM / 0.1 vCPU, sleeps after 15 min idle (~1 min wake), no small body cap | **Chosen** |
| Fly.io | Requires a card, no free tier for new users (per Render's comparison article, a vendor source) | Rejected |

Sources:
- Vercel function limits (4.5 MB body): https://examples.vercel.com/docs/functions/limitations and community confirmation https://community.vercel.com/t/413-payload-too-large/218
- HF Spaces overview (compute Spaces need a paid plan): https://huggingface.co/docs/hub/en/spaces-overview and forum report https://discuss.huggingface.co/t/docker-sdk-now-marked-as-paid-when-creating-a-new-space/177580
- Render free tier behaviour: https://render.com/articles/platforms-with-a-real-free-tier-for-developers-in-2026 (vendor article; spec corroborated by independent pricing trackers)

### 2d. Reliability approach

| Approach | Why / why not |
|---|---|
| **Segment citations + deterministic verification** (chosen) | Cheap, fast, auditable. The model must point at numbered passages and quote verbatim; code verifies. Timestamps are looked up, never generated. |
| RAG / embeddings | Overkill: an episode fits in one long-context call. Retrieval would hurt chapter segmentation, which needs the whole arc. |
| LLM-as-judge on every output | Doubles latency and burns the scarce free RPM; judges share the generator's blind spots. Kept as a next step for offline evaluation. |
| Constrained decoding / strict schemas only | Guarantees shape, not truth. I validate shape with Pydantic *and* truth with quote checks. |

## 3. Reliability measures (summary)
Numbered segments and citations; verbatim-quote verification; retry with the validator's exact complaint; provider fallback with cooldowns; server-side option shuffling to remove the "answer is always B" bias; prompt-injection framing (`<transcript>` is untrusted data); Whisper hallucination filtering on silence; abstention in "Ask the episode".

## 4. Practical constraints
- **Cost:** everything runs on free tiers, so operating cost is $0 (see [ENGINEERING.md](ENGINEERING.md) for estimates if it ever went paid).
- **Latency:** three parallel LLM calls (staggered by 350 ms to respect RPM) finish in roughly the time of the slowest single call; audio transcription is dominated by upload and compression, not Whisper.
- **Input limits:** 150k characters of text, 60 MB / 90 minutes of audio (all configurable and displayed in the UI).
- **Maintenance:** model IDs are config; the app degrades rather than fails when a provider disappears.

## 5. Responsible handling (OWASP API Security lens)
- *Unrestricted resource consumption:* per-IP rate limits, streaming body-size cap (works even without Content-Length), size/duration limits, one transcription at a time, job TTL and cap.
- *Security misconfiguration:* strict CSP and security headers, no docs/OpenAPI exposed, errors never leak internals or provider bodies.
- *Broken authentication / secrets:* keys only in environment; sent to Gemini via header, not URL; never logged; `.env` ignored; health endpoint reports provider *names* only.
- *Injection / unsafe consumption of APIs:* magic-byte file sniffing (filename ignored), ffmpeg invoked without a shell with the demuxer forced (an HLS playlist disguised as audio can't reach ffmpeg), language parameter regex-validated, model output rendered as text only, all model JSON validated.
- *Content permissions:* a plain-language notice before upload (third-party processing; free tiers may train on inputs; don't submit confidential material). Uploaded audio is deleted when the job ends; transcripts are not stored server-side.
- *Test content I'm allowed to process:* the built-in sample episode is my own script read by a synthetic voice (espeak-ng), so it carries no third-party rights. The suggested real-speech test files are public-domain LibriVox recordings. The benchmark above sent only this content to Google and Groq.
- *Third-party service requirements:* each provider's free tier is subject to its own terms, including use of submitted content to improve products on Gemini's free tier and per-organisation rate limits on Groq. The app sends only what the user submits, and only to the providers that have keys. Keys stay server-side, so a reviewer's requests use the deployer's quota, which the per-IP rate limit protects.

## 6. Measured comparison: Gemini vs Groq inside this app

**Setup (12 October 2026).** The app ran locally with real free-tier keys. Input: the built-in 11-minute sample episode (1,770 words, about 10,300 characters), as `.srt` (19 passages, real timestamps) and as plain `.txt` (23 passages). Each provider was **pinned** (`provider: "gemini"` or `"groq"`, no cross-fallback) and given identical prompts and validators. Latency is server-side and includes validation re-asks, rate-limit waits and any skipped backup entries. Raw data came from the Compare models tab / `/api/generate` meta.

| Metric | Google Gemini (chain: 3.5 Flash → 3.1 Flash-Lite) | Groq (`openai/gpt-oss-120b`) |
|---|---|---|
| Model that actually answered | `gemini-3.1-flash-lite` in 7 of 8 calls (primary `gemini-3.5-flash` failed first; see note) | `openai/gpt-oss-120b` every time |
| Overview time | 18.9-31.4 s | 1.6-4.9 s |
| Chapters time | 34.2-46.7 s | 1.7-4.3 s |
| Quiz time | 20.3-32.8 s | 17.4 s when run alongside the other sections (12 s of it waiting for the per-minute limit) |
| Summary length / themes / takeaways | 147-149 words / 3-4 / 5-6 | 100-137 words / 4-5 / 5-6 |
| Chapters (11-min episode) | 4, the last one covering cable faults and repair | 4-5. In one run the last chapter started at 5:23 and absorbed CDNs, last mile, faults *and* recap (coarser) |
| Verified quiz questions | 12 of 12 (1 validation re-ask in one run) | 12 of 12 |
| Ask, covered question ("What causes most undersea cable faults?") | Correct, 1 verified quote, 39 s | Correct, 1 verified quote, 1.0 s |
| Ask, uncovered question ("2022 World Cup winner?") | Correctly refused, 15 s | Correctly refused, 0.6 s |
| Free-tier failure mode | Primary model often unavailable or rate-limited, so a slower fallback answers | Per-minute token budget (8K TPM): the 2nd or 3rd section in the same minute gets 429 |

**What the numbers say.**
- **Grounding quality was equal.** Both providers passed every verbatim-quote check (24/24 quiz questions) and both abstained correctly. That is evidence the deterministic validation, not the model, carries the reliability, which was the design goal.
- **Groq is roughly 5-30x faster per call** (overview 6-12x, chapters 8-27x, Ask about 25-40x), but its free tier holds about 8K tokens per minute, and one section of this episode costs an estimated 4.5-5K tokens (prompt plus answer). The app generates three sections at once, so before the fix below, one or two of them failed.
- **Gemini handles length better.** Its free tier accepted all three sections at once and is the only option for long episodes. The Groq path is skipped above about 24K characters. On this free tier, however, Gemini was slow, because the primary model kept failing and every call paid for that failed attempt first.
- **Chapter granularity differed more than anything else.** Gemini's last chapter isolated "maintaining undersea cables". Groq once merged the second half into one chapter. Both are valid by the validator's rules (increasing, in range), so this is a quality difference the code can't catch, which is why an evaluation harness is next step #1.

**What I changed because of this measurement.**
1. **Errors name the cause.** The first run showed only "Groq is busy". It now says `model_unavailable` / `provider_auth` / `provider_rejected` / `providers_busy` with short `details` (chain entry plus reason, never provider bodies or keys).
2. **Groq model replaced** (`openai/gpt-oss-120b`, with 2× output headroom and `reasoning_effort: "low"`, because hidden reasoning tokens count toward `max_tokens`).
3. **Short rate-limit waits are absorbed.** If every usable entry is only cooling down (at most 30 s per wait, 60 s in total), the server waits and retries instead of failing the section. The section notes say "Waited N s for the provider's per-minute limit". Longer waits still fail fast with `Retry-After`.
4. **The reason for each fallback is now visible** (`meta.skipped`, shown in the Compare tab and section footers). Without it I could see *that* Gemini fell back, but not *why*. **Note:** the Gemini rows above were recorded before this field existed, so the exact reason the primary failed (rate limit vs. overload) isn't in this dataset; re-run Compare to see it.
5. **Recommendation.** Use Auto for real use: Gemini for long episodes, with Groq taking over when Gemini is down. Use Groq when speed matters on short or medium episodes. The comparison supports keeping both, not choosing one.
