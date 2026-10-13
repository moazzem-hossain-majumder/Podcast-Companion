# Podcast Companion — Master Video Demonstration Script & Teleprompter

> **Target Duration:** 11 to 14 Minutes  
> **Presenter:** Moazzem Hossain Majumder  
> **Walkthrough Video:** [https://youtu.be/EvU0fI3n5sA](https://youtu.be/EvU0fI3n5sA)  
> **Project:** AI Engineering Project (From Audio to Insight)  
> **Live URL:** [https://podcast-companion.onrender.com](https://podcast-companion.onrender.com)  
> **Local URL:** [http://127.0.0.1:8000](http://127.0.0.1:8000)  
>
> **How to use this guide:**  
> Keep this document open on half your screen or on a secondary monitor while screen recording. For each scene, follow the **📍 WHERE TO GO**, execute the **👉 DO THIS** mouse actions, speak the **🗣️ SAY THIS** script in clear, simple English, and use the **⚠️ WHAT CAN GO WRONG & WHY** section to explain failure modes and limitations directly to the reviewer.

---

## 📋 PRE-RECORDING CHECKLIST (Complete 2 Minutes Before Recording)

1. **Wake up the Live Deployment:**  
   Open [https://podcast-companion.onrender.com](https://podcast-companion.onrender.com) in your browser 1–2 minutes beforehand so the Render free tier instance is warm.
2. **Open Windows File Explorer:**  
   Open the folder `D:\podcast-companion\Podcast-Companion\test-files\` side-by-side with your browser window. This allows you to drag-and-drop real downloaded files effortlessly during the live recording.
3. **Open 3 Browser Tabs in ONE Window:**  
   * **Tab 1:** Live Website (`https://podcast-companion.onrender.com`) in Dark Mode.
   * **Tab 2:** GitHub Repository (`README.md` scrolled to Test Execution Log).
   * **Tab 3:** [`RESEARCH.pdf`](RESEARCH.pdf) opened in browser viewer.
4. **Recording Setup:**  
   Resolution: 1080p (1920x1080). Close background messengers and mute system notifications.

---

## 🎬 MASTER TELEPROMPTER & STEP-BY-STEP SCENE BREAKDOWN

---

### 🟢 SCENE 1 [0:00 – 1:15] — Introduction & Project Overview

**📍 WHERE TO GO:** Tab 1 (`https://podcast-companion.onrender.com` Home Page)

👉 **DO THIS (Mouse Actions):**
1. Keep the home page centered on screen in Dark Mode.
2. Slowly hover over the top title: **Podcast Companion**.
3. Slowly hover across the three primary input tabs:
   * **Paste text**
   * **Transcript file**
   * **Audio file**
4. Hover over the grey limit badges at the bottom: *200 to 150,000 characters · Audio up to 60 MB / 90 minutes*.

🗣️ **SAY THIS (Speak clearly and naturally):**
> "Hello everyone! My name is Moazzem Hossain Majumder, and welcome to the full walkthrough of **Podcast Companion**.
>
> This application was engineered as an AI Engineering Project.
>
> The problem we are addressing is familiar to anyone who listens to podcasts: long-form episodes contain great insights, but finding specific information, verifying whether a claim was actually said, or quickly testing your retention is difficult.
>
> Podcast Companion transforms any audio recording or transcript into a reliable, interactive companion:
> - A structured overview with verified takeaways,
> - Navigable chapters with honest timestamps,
> - An interactive quiz that quotes the source directly,
> - An 'Ask the Episode' assistant that refuses to invent answers, and
> - Isolated single-section revisions.
>
> Everything is deployed live on Render and running right here. Let's walk through how it works, what happens under the hood, what can go wrong, and our key engineering decisions."

---

### 🟢 SCENE 2 [1:15 – 2:30] — Model Selection, Fallback Chains & What Can Go Wrong

**📍 WHERE TO GO:** Tab 1 — Top navigation bar, **Model ⌄** dropdown

👉 **DO THIS (Mouse Actions):**
1. Click the **Model ⌄** dropdown in the top right header.
2. Hover over the options:
   * **Auto (best available, with fallback)**
   * **Google Gemini** (`gemini-3.1-flash-lite`, `gemini-3.5-flash`)
   * **Groq** (`openai/gpt-oss-120b`)
3. Click on **Google Gemini**, then click back to **Auto**.

🗣️ **SAY THIS (Speak clearly):**
> "Let's start with how we handle AI models and reliability.
>
> In the top right, we have our Model Selector: you can choose Google Gemini, Groq, or let Auto manage it.
>
> **Now, what can go wrong here and why?**
> In real-world AI engineering, hard-coding a single model is very fragile. For example:
> 1. AI vendors retire model IDs with little notice.
> 2. Free tiers have aggressive rate limits.
> 3. During our live testing, Google's `gemini-3.5-flash` returned temporary HTTP 503 Service Unavailable errors due to high demand spikes.
>
> To solve this, we built an automated **Fallback Chain**:
> When a call to Gemini experiences an HTTP 503 or 429 rate limit, our backend catches the error, respects the Retry-After header, and immediately falls back to Gemini Flash-Lite, and then to Groq.
>
> Another issue is token limits: Groq's free tier has an 8,000 tokens-per-minute ceiling. If you upload a long transcript, Groq would fail. So our system automatically skips Groq for inputs over 24,000 characters and routes directly to Gemini, which supports up to 1 million tokens.
>
> The result? The user gets an unbroken experience with zero crashes."

---

### 🟢 SCENE 3 [2:30 – 3:30] — Sample Inputs vs. Testing with Real User Files

**📍 WHERE TO GO:** Tab 1 — Look at the input tabs and the **Try a sample:** row

👉 **DO THIS (Mouse Actions):**
1. Click on the **Paste text** tab. Show the *Try a sample* buttons: `Plain transcript`, `With [mm:ss] times`, `Short episode`.
2. Click on the **Transcript file** tab. Show: `.txt`, `.md`, `.srt`, `.vtt`.
3. Click on the **Audio file** tab. Show: `.mp3`, `.m4a`, `.mp4`, `.wav`, `.ogg`, `.flac`, `.webm`, `.aac`.
4. Open your Windows File Explorer window next to the browser, showing the `test-files\` folder with real files.

🗣️ **SAY THIS (Speak clearly):**
> "Now let's examine inputs.
>
> For reviewers who want a quick one-click check, we built in a full suite of sample buttons across every tab. Each button loads our standard 11-minute educational episode in that format.
>
> But today, to properly test the system according to the challenge requirements, I am not just going to click the built-in samples.
>
> Instead, I am going to test the app using real, external files downloaded to my computer—from Project Gutenberg, NASA, Wikimedia Commons, and real open podcasts—spanning four document types and eight audio formats."

---

### 🟢 SCENE 4 [3:30 – 5:45] — Testing Real Documents & Subtitles (User Files)

**📍 WHERE TO GO:** Tab 1 — **Transcript file** Tab & Windows File Explorer (`test-files\`)

👉 **DO THIS (Mouse Actions):**
1. Select the **Transcript file** tab.
2. **Test Plato's Philosophy (.txt)**:
   * Drag `euthyphro.txt` from your `test-files\` folder and drop it into the upload box.
   * Point to the file badge: *euthyphro.txt (71 KB)*.
   * Click **Build my companion**.
   * Wait 8–10 seconds for results.
   * Point out the metadata badge: *138 passages · no timestamps (plain text)*.
   * Show that the app displays passage numbers instead of inventing fake timestamps!
3. Click **New episode** in the top left.
4. **Test Real Subtitles (.srt / .vtt)**:
   * Select **Transcript file** tab.
   * Drag `nasa-knx-interview.srt` from `test-files\` and drop it into the upload box.
   * Click **Build my companion**.
   * Switch to the **Chapters** tab.
   * Point out the real timestamps: `00:00`, `02:15`, `05:40` extracted directly from the NASA astronaut interview captions!

🗣️ **SAY THIS (Speak clearly):**
> "Let's test our first real document: Plato's *Euthyphro*, a 71-kilobyte text file from Project Gutenberg with over 69,000 characters.
>
> I drag and drop `euthyphro.txt` into the upload zone and click **Build my companion**.
>
> The server parses the text into 138 structured passages.
>
> **Now, what can go wrong with plain text?**
> A common flaw in AI products is that models will invent fake timestamps like '04:12' out of thin air when given plain text.
>
> Requirement 3 of the challenge strictly forbids this: if timestamps cannot be reliably supported, the app must explain the limitation rather than presenting invented ones.
>
> Look at this badge: *'no timestamps (plain text)'*. The app explains why timestamps are absent and shows passage ranges like 'Passages 1 to 24'.
>
> Next, let's test a subtitle file. I click New Episode, select Transcript file, and drag in `nasa-knx-interview.srt`—real captions from astronaut Chris Cassidy on the ISS.
>
> Here, because subtitle cues contain real millisecond timings, the app extracts authentic timestamps and populates the chapter timeline accurately.
>
> We also verified Markdown files (`.md`), where the parser automatically strips code headers and formatting without losing spoken dialogue."

---

### 🟢 SCENE 5 [5:45 – 8:00] — Testing Real Audio & Video Demuxing (User Audio Files)

**📍 WHERE TO GO:** Tab 1 — **Audio file** Tab & Windows File Explorer (`test-files\`)

👉 **DO THIS (Mouse Actions):**
1. Click **New episode**, then click the **Audio file** tab.
2. In Windows File Explorer, point to the audio test files:
   `martin-amis-interview.mp3`, `nasa-hwhap-424-ai.m4a`, `nasa-knx-interview.mp4` (video!), `roosevelt-1912-speech.wav`, `spoken-wikipedia-bioinformatics.ogg`, `preservapedia-podcast-mccoy.flac`, `barbados-1960s-interview.webm`, `nasa-hwhap-424-ai.aac`.
3. Drag `martin-amis-interview.mp3` (or `nasa-knx-interview.mp4`) into the dropzone.
4. Click **Generate companion**.
5. Point to the live progress stages:
   * *Inspecting audio header*
   * *Transcribing audio with Groq Whisper*
   * *Generating overview, chapters, and quiz*
6. Show the resulting companion with real Whisper timestamps.

🗣️ **SAY THIS (Speak clearly):**
> "Now let's examine audio ingestion.
>
> We support **eight audio formats**: MP3, M4A, MP4 video, WAV, OGG, FLAC, WebM, and raw AAC streams.
>
> I'll drag in `martin-amis-interview.mp3`—a real 20-megabyte recording from Wikimedia Commons—and click **Generate companion**.
>
> **What can go wrong during audio ingestion, and how do we handle it?**
> 1. **Spoofed or corrupted files:** If a user renames an `.exe` or a text file to `.mp3`, running a transcriber on it could crash the server. Our backend performs binary magic-byte inspection and rejects fake audio immediately with an HTTP 415 error.
> 2. **File size and rate limits:** Groq's free Whisper API has a strict 25 MB limit. If a user uploads a 41 MB uncompressed WAV file or a 26 MB MP4 video, it would normally be rejected.
> To prevent this, our backend uses a bundled static `ffmpeg` pipeline that automatically extracts the audio stream from video, transcodes it to 16 kHz mono, and splits it into 20-minute chunks if necessary.
> 3. **Whisper hallucinations:** During long silences, Whisper can hallucinate repetitive text like 'Thank you for watching'. Our parser filters out segments with high silence probability.
>
> And here are the results: transcribed with second-level timestamps and rendered into chapters."

---

### 🟢 SCENE 6 [8:00 – 9:45] — Deep Dive on Generated Outputs & Deterministic Verification

**📍 WHERE TO GO:** Tab 1 — Results View (`Overview`, `Chapters`, `Quiz`, `Ask the episode`)

👉 **DO THIS (Mouse Actions):**
1. **Overview Tab:**
   * Scroll down through the Title, One-line summary, and 150-word synthesis.
   * Point to the **Key Takeaways** and hover over a citation chip like `[source passage 4]`.
2. **Chapters Tab:**
   * Hover over the interactive timeline strip blocks at the top (show different widths for duration).
   * Click on Chapter 2 or Chapter 3. Show smooth scrolling.
3. **Quiz Tab:**
   * Click the **Quiz** tab.
   * Click the correct option on Question 1 (turns green, updates score to `1/3`).
   * Point to the **Source quote** box underneath.
   * Click the blue quote link. Watch the page scroll down and highlight the verbatim sentence in the transcript!
   * Click an incorrect option on Question 2 (turns red).
4. **Ask the Episode Tab:**
   * Click **Ask the episode**.
   * Type: *"What does the speaker say about writing?"* &rarr; Click **Ask**. Show the answer with verified evidence.
   * Type: *"Who won the 1998 FIFA World Cup?"* &rarr; Click **Ask**. Show the refusal: *"The provided transcript does not contain information about the 1998 football world cup."*

🗣️ **SAY THIS (Speak clearly):**
> "Let's review the generated outputs against Requirements 2, 3, and 4 of the challenge PDF.
>
> First, the **Episode Overview**: We get a concise title, an executive one-liner, a 150-word summary, and core themes. Notice these Key Takeaways: each one cites an exact passage.
>
> **What can go wrong here?** Models love to invent plausible-sounding takeaways that were never actually said. Our server-side code checks every takeaway citation against the transcript segments. If a takeaway cites a non-existent passage, our code drops it.
>
> Second, the **Navigable Chapters**: This timeline bar at the top represents the entire episode. The block widths are proportional to the actual duration of each topic. Clicking any chapter card scrolls directly to that part of the episode.
>
> Third, the **Interactive Quiz**: When I select an option, it gives instant feedback and explanations.
>
> Most importantly: look at this **Source Quote**. Every single question requires a verbatim quote. When I click this blue quote link, the app scrolls to the exact sentence in the transcript. If the model generates a question with an invented quote, our deterministic validator discards the question or re-asks the model.
>
> Fourth, **Ask the Episode**: When asked an on-topic question, it answers with quoted evidence. But when asked an off-topic question—like 'Who won the 1998 World Cup?'—it politely refuses to answer. It never hallucinates."

---

### 🟢 SCENE 7 [9:45 – 10:45] — Isolated Revisions & Non-Destructive Undo

**📍 WHERE TO GO:** Tab 1 — **Overview** tab, bottom card (**Revise this section**)

👉 **DO THIS (Mouse Actions):**
1. Switch back to the **Overview** tab.
2. Scroll to the bottom card: **Revise this section**.
3. Point out the preset chips: `Shorter`, `Simpler language`, `More detail`.
4. Click the **Shorter** preset chip.
5. Click **Revise overview**.
6. Notice that a loading spinner appears **only** on the Overview card.
7. Show the revised shorter summary appear with the badge: *Revised: "Make the summary much shorter...". Only this section was regenerated.*
8. Click over to **Chapters** and **Quiz** tabs to demonstrate they were **not** regenerated or touched!
9. Return to **Overview** and click **Undo last change**.
10. Watch the original full-length overview instantly restore!

🗣️ **SAY THIS (Speak clearly):**
> "Requirement 5 of the PDF specifies supporting at least one meaningful revision without unnecessarily regenerating the entire application workflow.
>
> **What can go wrong in typical AI revision workflows?**
> In most applications, requesting a shorter summary re-runs the entire pipeline—wasting API tokens, adding latency, and wiping out any quiz answers the user already completed.
>
> In Podcast Companion, revisions are strictly **isolated**.
>
> I select the preset chip 'Shorter' and click **Revise overview**.
>
> Notice that only this card reloads. The chapters and quiz remain completely untouched.
>
> And what if the user dislikes the revision? We built a client-side history stack. I click **Undo last change**, and the previous summary is restored instantly from memory without making a network call."

---

### 🟢 SCENE 8 [10:45 – 11:30] — Live Model Comparison Tab (Gemini vs. Groq Benchmark)

**📍 WHERE TO GO:** Tab 1 — **Compare models** tab

👉 **DO THIS (Mouse Actions):**
1. Click the **Compare models** tab in the main navigation.
2. Point your mouse to the side-by-side columns:
   * Left Column: **Google Gemini**
   * Right Column: **Groq**
3. Hover over the benchmark metrics:
   * Latency per section (Overview, Chapters, Quiz)
   * Validation re-asks (0 re-asks = valid JSON and grounded quotes on first attempt)
   * Verified quiz questions (6 / 6)
4. Hover over the export buttons: **Export comparison (.md)** and **Export comparison (.json)**.

🗣️ **SAY THIS (Speak clearly):**
> "Section 05 of the challenge asks candidates to research and compare at least two AI models.
>
> We built an interactive **Model Comparison Tab** directly into the product.
>
> Here, we run Google Gemini and Groq side-by-side on the exact same transcript, with both models pinned so there is no hidden cross-fallback.
>
> **What did we learn from comparing them?**
> Groq is fast—generating sections in under 2 seconds—making it ideal for quick interactive revisions. However, its free tier has a strict 8,000 TPM limit.
>
> Google Gemini Flash-Lite is slightly slower at 5 to 7 seconds, but its 1-million-token context window can easily swallow multi-hour podcast marathons without failing.
>
> Both models achieved a 100% pass rate on our deterministic quote verifier."

---

### 🟢 SCENE 9 [11:30 – 12:45] — Deliberate Failure Tests & Safety Guardrails

**📍 WHERE TO GO:** Tab 1 — Home / Input View

👉 **DO THIS (Mouse Actions):**
1. Click **New episode**.
2. **Deliberate Failure 1: Short Text Rejection**:
   * On **Paste text**, type: *"Too short"*.
   * Click **Build my companion**.
   * Show the red error alert: *The transcript is too short (9 characters). Provide at least 200 characters.*
3. **Deliberate Failure 2: Oversized File Protection**:
   * Explain the 60 MB audio cap and 150,000 character transcript limit, rejected client-side before wasting server bandwidth.
4. **Deliberate Failure 3: Renamed Audio Files**:
   * Explain how renaming a text file to `.mp3` is caught by our magic-byte validator with `HTTP 415 Unsupported Media Type`.
5. Point to the **Copy** and **Download** buttons (Markdown `.md` and JSON `.json`) at the top right of any result view.

🗣️ **SAY THIS (Speak clearly):**
> "Section 05.C of the challenge asks for authentic debugging and failure scenarios that were deliberately tested.
>
> Here are three failure modes we engineered defenses for:
>
> 1. **Accidental tiny inputs:** If a user submits just two words, the app immediately catches it in Test 24 with a helpful error explaining that at least 200 characters are required, avoiding wasted AI tokens.
> 2. **Excessive payload size:** Transcripts exceeding 150,000 characters or audio over 60 MB are rejected client-side before uploading, protecting server memory.
> 3. **Malicious or renamed files:** If someone uploads an executable or script disguised as an MP3, our server inspects the binary file signature before running ffmpeg, safely rejecting it with an HTTP 415 error."

---

### 🟢 SCENE 10 [12:45 – 13:45] — Honest Limitations of the Project & Models (PDF Section 05.D)

**📍 WHERE TO GO:** Tab 1 (stay on screen) or Tab 2 (`README.md`)

👉 **DO THIS (Mouse Actions):**
1. Keep the browser open in Dark Mode.
2. Speak directly to the camera/microphone with honest, transparent engineering ownership.

🗣️ **SAY THIS (Speak clearly):**
> "Section 05.D of the challenge asks for an honest discussion of the **limitations of our approach**. In production AI engineering, being transparent about limitations is essential:
>
> 1. **Free Tier Hosting Sleep (Cold Starts):** On Render's free tier, the web service spins down after 15 minutes of inactivity. The first request after a pause can take 30 to 45 seconds to wake the instance up.
> 2. **Stateless Architecture & No Database Persistence:** Currently, all jobs run in memory. If a user refreshes their browser tab, their results are cleared unless they exported them to Markdown or JSON. In production, we would add a Postgres database with durable job IDs.
> 3. **Fallback Model Context Limits:** Because Groq's free tier has an 8K token budget, Groq fallback is only possible for transcripts under 24,000 characters. For 2-hour podcasts, the system relies exclusively on Gemini.
> 4. **Quote Verification vs. Deep Semantic Truth:** Our verifier deterministically guarantees that quotes exist verbatim near the cited segment. However, quote existence does not guarantee that the speaker wasn't being sarcastic or expressing an unverified opinion.
> 5. **Segment-Level vs. Word-Level Timestamps:** We currently extract timestamps at the chapter and passage level rather than word-level alignment.
> 6. **Data Privacy on Free AI Tiers:** Free-tier AI endpoints may retain prompts for model training. As stated in our pre-upload disclaimer, confidential or proprietary recordings should not be submitted on free tiers."

---

### 🟢 SCENE 11 [13:45 – 14:30] — Three Prioritized Next Steps, Research PDF & Wrap Up

**📍 WHERE TO GO:** Tab 2 (GitHub `README.md`) &rarr; Tab 3 (`RESEARCH.pdf`) &rarr; Tab 1

👉 **DO THIS (Mouse Actions):**
1. Switch to **Tab 2** (GitHub `README.md`). Show the 135 passing pytest tests.
2. Switch to **Tab 3** ([`RESEARCH.pdf`](RESEARCH.pdf)). Scroll through the styled pages.
3. Switch back to **Tab 1** (Live app).

🗣️ **SAY THIS (Speak clearly):**
> "Finally, Section 06 asks for the **three most important future improvements**:
> 1. **Automated Faithfulness Harness:** Build a golden test set of 10 episodes to quantitatively benchmark chapter agreement and semantic entailment whenever models are updated.
> 2. **Durable Persistence & Background Job Queue:** Add a database (SQLite to PostgreSQL) with Redis/Celery job queues so audio uploads can be resumed and results shared via persistent URLs.
> 3. **Hierarchical Map-Reduce Summarization & SSE Streaming:** Implement chunked summarization so small-context models can handle 3-hour episodes, and stream tokens via Server-Sent Events so the summary appears word-by-word.
>
> All research is documented in our standalone `RESEARCH.pdf`, and the complete codebase with 135 passing tests is available on GitHub.
>
> Thank you for reviewing this project! I look forward to your questions and discussion!"

---

## 📌 MASTER REFERENCE: TEST CASE MAPPING FOR LIVE DEMO

| Test Case | What You Show | Key Talking Point |
|---|---|---|
| **Test 01 & 04** | `euthyphro.txt` (Plato) | Plain text input; honest "no timestamps" policy; passage citations. |
| **Test 05** | `changelog-330.md` | Stripping markdown syntax while preserving spoken interview content. |
| **Test 06 & 07** | `nasa-knx-interview.srt` / `.vtt` | Real timestamps extracted directly from subtitle cues. |
| **Test 08** | `martin-amis-interview.mp3` | Direct Whisper audio transcription path under 24 MB. |
| **Test 10** | `nasa-knx-interview.mp4` | Video demuxing: extracting audio from MP4 video container. |
| **Test 11 & 13** | `roosevelt-1912-speech.wav` / `flac` | Server-side ffmpeg transcoding and compression for large audio files. |
| **Test 16** | Quiz Source Quote Click | Instant jump and highlight of verbatim quote in transcript. |
| **Test 17 & 18** | "Ask the Episode" | Grounded answers with citations; polite refusal for off-topic questions. |
| **Test 20 & 21** | Section Revision & Undo | Isolated single-section regeneration; instant non-destructive undo. |
| **Test 22** | Compare Models Tab | Side-by-side benchmark of Gemini vs. Groq with measured latencies. |
| **Test 24 & 25** | Input Guardrails | Rejection of input under 200 chars and binary magic-byte detection. |
