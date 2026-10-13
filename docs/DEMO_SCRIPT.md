# Podcast Companion — Live Recording Teleprompter & Master Demo Guide

> **Target Duration:** 4.5 to 5.0 Minutes  
> **Presenter:** Moazzem Hossain Majumder  
> **How to use this guide:** Put this file on your second monitor or on half of your screen. Look directly at each Cue Card while recording. Perform the **👉 DO THIS** action and speak the **🗣️ SAY THIS** text.

---

## 📋 PRE-RECORDING CHECKLIST (Do this 2 minutes before starting)

1. **Wake up the app:** Open [https://podcast-companion.onrender.com](https://podcast-companion.onrender.com) so the server is warm.
2. **Open 3 Browser Tabs in ONE window:**
   - **Tab 1:** Live Website (`https://podcast-companion.onrender.com`) in Dark Mode
   - **Tab 2:** GitHub `README.md` scrolled to `## Test Execution Log & Visual Verification`
   - **Tab 3:** `RESEARCH.pdf` opened in browser viewer
3. **Screen Setup:** Full screen 1080p (1920x1080), browser address bar visible, DevTools closed, notifications muted.

---

## 🎬 THE LIVE RECORDING TELEPROMPTER

---

### 🟢 CUE 1 of 8 — [0:00 - 0:45] Look of the Website, Inputs & Outputs
**📍 SCREEN:** Tab 1 (`https://podcast-companion.onrender.com` Home Page)

👉 **DO THIS (Mouse Actions):**
1. Keep the home page on screen.
2. Hover your mouse over the title: **Podcast Companion**.
3. Slowly hover across the three input tabs:
   - Hover on **Paste text**
   - Hover on **Upload document**
   - Hover on **Audio file**
4. Click the **Model ⌄** dropdown in the top right. Show *Auto*, *Google Gemini*, and *Groq*. Click it again to close.
5. Hover over the grey limits text: *Max 150,000 characters · Audio up to 60 MB / 90 min*.

🗣️ **SAY THIS (Speak clearly):**
> "Hello everyone! My name is Moazzem Hossain Majumder, and this is **Podcast Companion**, deployed live on Render for the Thealon AI Engineering Challenge.
>
> Let's look at how the website is set up.
>
> The interface has a clean dark design that is very easy to navigate. At the top, there are three ways to provide input:
> First, you can paste plain text or transcripts with timestamps.
> Second, you can upload documents like text files, markdown, or subtitle files.
> Third, you can upload audio files in eight different formats.
>
> In the top corner, you can choose between Google Gemini, Groq, or let Auto pick the best model.
>
> Within seconds, the app gives you five useful outputs:
> A structured summary and key takeaways,
> A clickable chapter timeline with exact timestamps,
> An interactive quiz with instant scoring,
> An 'Ask the Episode' question box,
> And easy download buttons for Markdown and JSON.
>
> Best of all, every single takeaway and quiz answer comes with a real quote from the episode, so you always know where it came from."

---

### 🟢 CUE 2 of 8 — [0:45 - 1:30] Audio Ingestion & Format Tests (Tests 08–15)
**📍 SCREEN:** Tab 1 (`Audio file` Tab)

👉 **DO THIS (Mouse Actions):**
1. Click the **Audio file** tab.
2. Hover your mouse slowly across the **Try a sample:** row, pointing to each button:
   `.mp3` · `.m4a` · `.mp4` · `.wav` · `.ogg` · `.flac` · `.webm` · `.aac`
3. Click the **.mp3** button. Notice how `episode.mp3` appears in the box.
4. Hover over the privacy note at the bottom: *Privacy: Content is processed by Google Gemini and Groq...*
5. Click the purple **Generate Companion** button.
6. Watch the live progress box update: *Validating file → Transcribing with Groq Whisper → Creating sections*.

🗣️ **SAY THIS (Speak clearly):**
> "Now let's try it with real audio.
>
> Look at this 'Try a sample' row. In our testing suite—Tests 8 through 15—we verified that all eight audio formats work smoothly, including extracting audio from an MP4 video file.
>
> I will click on **.mp3**. This loads an 11-minute educational podcast about Undersea Internet Cables.
>
> Down here, there is a clear privacy note letting users know how their data is handled.
>
> Now I click **Generate Companion**.
>
> Behind the scenes, the server checks the audio file header to block fake files, uses Groq Whisper to transcribe speech into text with second-by-second timestamps, and passes it to our AI pipeline. Everything updates live on screen."

---

### 🟢 CUE 3 of 8 — [1:30 - 2:15] Overview, Citations & Chapters (Tests 01, 02, 06, 12, 13)
**📍 SCREEN:** Tab 1 (Results View — Overview & Chapters)

👉 **DO THIS (Mouse Actions):**
1. Hover over the top metadata badge: `22 passages · from audio · with real timestamps · model: Auto`.
2. Scroll down slowly through the **Episode Overview**:
   - Show the Title and the One-Sentence summary.
   - Show the 150-word summary paragraph.
3. Hover your mouse directly over one of the takeaway citation chips (e.g., `source passage 3`).
4. Switch to the **Chapters** tab (or look at the chapter strip at the top).
5. Hover slowly across each colored block in the **Chapter Timeline Strip**:
   - Point out how each block has a different width depending on how long that topic lasted.
   - Show the tooltip showing the chapter title and start time.
6. Click on Chapter 3 (*Deep Sea Faults & Cable Ships*).
7. Watch the page smoothly scroll down and highlight that exact sentence in the full transcript!

🗣️ **SAY THIS (Speak clearly):**
> "And here are our results!
>
> This top badge confirms: 22 passages were found with real timestamps from audio.
>
> In the Overview, we get a title, a one-sentence summary, a 150-word overview, and key takeaways.
>
> Look at these small citation tags next to each takeaway. In Tests 1 and 2, we verified that every takeaway must link to a real passage in the transcript. If the AI invents something without a citation, our code throws it away.
>
> Now look at this chapter timeline bar at the top.
>
> As I hover over each block, you can see the chapter title and start time. The block widths match the actual time length of each topic.
>
> These timestamps are 100% real from Whisper. When I click Chapter 3, watch—it jumps straight to that exact moment in the transcript and highlights it!"

---

### 🟢 CUE 4 of 8 — [2:15 - 3:00] Quiz & "Ask the Episode" (Tests 14, 15, 16, 17, 18)
**📍 SCREEN:** Tab 1 (`Quiz` Tab & `Ask the episode` Tab)

👉 **DO THIS (Mouse Actions):**
1. Click the **Quiz** tab.
2. Hover over the 4 choices on Question 1.
3. Click the **correct** answer. Show it turn green, the score update to `Score: 1/3`, and the explanation appear.
4. Hover over the **Source quote** box beneath the explanation.
5. Click the blue quote link. Watch the transcript scroll down and highlight the source sentence! (**This is Test 16**).
6. Scroll down to Question 2. Click an **incorrect** answer. Show it turn red with the explanation.
7. Click the **Ask the episode** tab.
8. Type: *"What causes most undersea cable damage?"* → Click **Ask**. Show the answer with a verified quote (**Test 17**).
9. Type: *"Who won the 2022 World Cup?"* → Click **Ask**. Show the polite refusal: *"I won't answer because this is not mentioned in the episode."* (**Test 18**).

🗣️ **SAY THIS (Speak clearly):**
> "Now let's check out the Interactive Quiz.
>
> Here are multiple-choice questions to test your understanding.
>
> Let's click the right answer on Question 1. It turns green right away, explains the answer, and updates our score.
>
> Even better: look at this 'Source quote' box. In Test 16, we proved this feature: every question must have a real quote from the episode. When I click this quote link, the app scrolls right to where the speaker said it in the transcript!
>
> If I click a wrong answer on Question 2, it turns red and gently explains the correct answer.
>
> Next is 'Ask the Episode'. When I ask what causes cable damage, it gives an accurate answer with a verified quote.
>
> But when I ask an off-topic question—like 'Who won the 2022 World Cup?'—it politely refuses because the podcast doesn't cover it. It never guesses or hallucinates."

---

### 🟢 CUE 5 of 8 — [3:00 - 3:35] Isolated Revisions & Instant Undo (Tests 19, 20, 21)
**📍 SCREEN:** Tab 1 (`Overview` Tab — Bottom Revision Card)

👉 **DO THIS (Mouse Actions):**
1. Click back to the **Overview** tab.
2. Scroll to the bottom card: **Revise this section**.
3. Hover over the preset chips: **Shorter**, **Simpler language**, **More detail**.
4. Click the **Shorter** preset chip.
5. Click the purple **Revise overview** button.
6. Show the spinner appear **only** inside the overview card.
7. Show the new shorter overview appear with the yellow badge: `Revised: "Make the summary much shorter...". Only this section was regenerated.` (**Test 20**).
8. Click the Quiz and Chapters tabs for 2 seconds to show they are **completely untouched**.
9. Click back to Overview. Hover over the **Undo last change** button.
10. Click **Undo last change**. Watch the previous full-length summary instantly restore with the notification: *Reverted to the previous version*! (**Test 21**).

🗣️ **SAY THIS (Speak clearly):**
> "Another key requirement is making meaningful revisions.
>
> Most AI tools force you to start over and re-generate everything. But in Podcast Companion, revisions are strictly isolated.
>
> Down here, we have quick preset buttons: 'Shorter', 'Simpler language', or 'More detail'.
>
> Watch: I click 'Shorter' and hit Revise. Only the Overview section is updated. In Test 20, we proved that the chapters and quiz stay completely untouched, saving time and tokens.
>
> And if you want the previous version back? In Test 21, we proved our Undo feature: just click 'Undo last change'. Instantly, our previous full-length summary is restored without making another slow web call."

---

### 🟢 CUE 6 of 8 — [3:35 - 4:10] Live Model Benchmark: Gemini vs Groq (Tests 22, 23)
**📍 SCREEN:** Tab 1 (`Compare models` Tab)

👉 **DO THIS (Mouse Actions):**
1. Click the **Compare models** tab in the main navigation.
2. Hover across the side-by-side comparison table:
   - Column 1: **Google Gemini** (`gemini-3.1-flash-lite`).
   - Column 2: **Groq** (`openai/gpt-oss-120b`).
3. Hover over the latency rows:
   - Overview Time: `5.2 s` vs `1.5 s`
   - Quiz Time: `5.8 s` vs `3.5 s`
4. Hover over **Verified quiz questions**: `3 / 3` for both models.
5. Hover over the download buttons: **Export comparison (.md)** and **Export comparison (.json)**.

🗣️ **SAY THIS (Speak clearly):**
> "The challenge also asked us to compare at least two technical options.
>
> Instead of just writing about it in a paper, we built a live model comparison tab directly into the product.
>
> In Test 22, we benchmarked Google Gemini and Groq on the exact same podcast transcript with pinned models, meaning there is zero hidden switching.
>
> Look at the numbers: Groq is lightning fast, generating answers in just 1.5 seconds. Meanwhile, Google Gemini has a massive context window that can easily fit 10-hour podcast marathons.
>
> Most importantly, both models scored 100% on our quote verification check, showing that our verification system works reliably with any modern LLM."

---

### 🟢 CUE 7 of 8 — [4:10 - 4:45] Tour of 26 Tests & Safety Guardrails (Tests 01–26 & 24, 25)
**📍 SCREEN:** Tab 2 (GitHub `README.md`) → then back to Tab 1 (Live App)

👉 **DO THIS (Mouse Actions):**
1. Switch smoothly to **Tab 2** (GitHub `README.md` at `## Test Execution Log & Visual Verification`).
2. Scroll slowly down through the 7 test categories showing the dark-mode screenshots:
   - Point to **Group 1 (Tests 01–03):** Plain text vs timestamped samples.
   - Point to **Group 2 (Tests 04–07):** Documents: Plato's `.txt`, Changelog `.md`, NASA `.srt`.
   - Point to **Group 3 (Tests 08–15):** All 8 audio formats: MP3, WAV, MP4 video demux, FLAC, M4A, etc.
   - Point to **Group 7 (Tests 24–26):** Error guardrail screenshots.
3. Switch back to **Tab 1** (Live app) to show a live error guardrail:
   - Click **Paste text** tab.
   - Type just two words: *"Hello test"*.
   - Click **Build my companion**.
   - Point to the red error banner: *The transcript is too short (10 characters). Provide at least 200 characters.* (**Test 24**).
   - Mention **Test 25**: Magic-byte checking blocks fake `.mp3` files before ffmpeg touches them.

🗣️ **SAY THIS (Speak clearly):**
> "To prove this application is truly production-ready, we ran and documented **26 separate tests** with high-resolution dark-mode screenshots in our README.
>
> As you can see, we tested every scenario: from reading Plato's classical philosophy and NASA astronaut subtitles, to extracting audio from video files, all the way to testing eight different audio formats.
>
> We also engineered strict safety guardrails. Watch this live: if someone submits a tiny two-word snippet, the app immediately catches it with an informative error in Test 24 before wasting any AI budget.
>
> And in Test 25, we verified that if someone renames a text file to .mp3, our server checks the real file header and safely rejects it before ffmpeg or Whisper even touch it."

---

### 🟢 CUE 8 of 8 — [4:45 - 5:00] Research PDF & Wrap Up
**📍 SCREEN:** Tab 3 (`RESEARCH.pdf`) → then back to Tab 1

👉 **DO THIS (Mouse Actions):**
1. Switch to **Tab 3** (`RESEARCH.pdf`).
2. Scroll through the clean, monochrome title page, the comparison tables, and next steps.
3. Switch back to **Tab 1** (the live app).
4. Rest mouse cleanly in the center of the screen.

🗣️ **SAY THIS (Speak clearly):**
> "Finally, we compiled our research into a clean, easy-to-read PDF, and our complete code with 135 passing automated tests is available on GitHub.
>
> Thank you so much for your time, and I look forward to your feedback!"

---

## 📌 MASTER REFERENCE: ALL 26 TESTS AT A GLANCE

If you ever need to quickly check which test does what while recording, here is the complete map:

| Group | Test # | Name / Input File | Exact Feature Verified |
|---|---|---|---|
| **1. Text Samples** | **01** | `episode.txt` | Plain text parsing; honest "no timestamps" notice |
| | **02** | `episode-timestamped.txt` | Inline `[mm:ss]` markers parsed into real chapter times |
| | **03** | `sample.txt` ("Study Hall") | Fast 5-minute concise episode extraction |
| **2. Documents & Subtitles** | **04** | Plato's `euthyphro.txt` | Large literary text parsing (138 passages, 71 KB) |
| | **05** | `changelog-330.md` | Technical podcast markdown; AST/SQL code jargon |
| | **06** | `nasa-knx-interview.srt` | Real SRT subtitle cues parsed into millisecond timestamps |
| | **07** | `librivox-vtt.vtt` | WebVTT format parsing and monotonic time bounds |
| **3. Audio Formats** | **08** | `martin-amis.mp3` | MP3 audio upload and Whisper transcription |
| | **09** | `nasa-interview.m4a` | M4A container handling |
| | **10** | `nasa-interview.mp4` | Video demuxing: extracts audio stream from MP4 video |
| | **11** | `roosevelt.wav` | Lossless WAV audio transcoding |
| | **12** | `wikipedia.ogg` | OGG Vorbis audio format |
| | **13** | `preservapedia.flac` | Lossless FLAC container |
| | **14** | `barbados.webm` | WebM container transcoding |
| | **15** | `nasa.aac` | Raw AAC conversion to MP3 |
| **4. Quiz & Citations** | **16** | Verbatim Quote Jump | Clicking blue quote scrolls & highlights transcript passage |
| | **17** | Ask (Covered Question) | Answers cable damage question with verified quote |
| | **18** | Ask (Uncovered Question) | Refuses "World Cup" off-topic question without guessing |
| **5. Revisions & Undo** | **19** | Copy & Export | Single-click Markdown & JSON download |
| | **20** | Section Revision ("Shorter") | Regenerates *only* the overview; chapters/quiz untouched |
| | **21** | Non-Destructive Undo | Instantly restores previous version without network call |
| **6. Model Comparison** | **22** | Live Comparison Table | Pinned Gemini vs Groq side-by-side benchmark |
| | **23** | Engine Picker | Selecting Whisper vs Gemini ASR and language codes |
| **7. Safety Guardrails** | **24** | Short Text Rejection | Rejects input under 200 characters with HTTP 422 |
| | **25** | Spoofed Audio Detection | Magic-byte sniffer rejects fake `.mp3` with HTTP 415 |
| | **26** | Groq Token Budget Limit | Rejects transcripts over 24k chars on Groq with HTTP 413 |
