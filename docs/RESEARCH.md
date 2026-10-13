# Research & Engineering Findings

A simple, easy-to-read summary of why we built Podcast Companion, the tools we tested, and what we learned.

---

## 1. Why We Built This (User Value)

Listening to long podcasts is great, but finding specific information later is hard. Most AI tools produce generic summaries that you cannot verify.

### Who Benefits:
- **Students & Learners:** Want to remember key ideas and test what they learned.
- **Busy People:** Want to see in 2 minutes whether a 90-minute episode is worth their time.
- **Readers & Accessibility:** People who understand better by reading than by listening.
- **Podcast Creators:** Want clean chapters and quiz questions to share with their listeners.

### The Core Problem Solved:
Instead of just summarizing, we answer: *"Where did the speaker actually say that, and can I trust it?"*  
Every takeaway, chapter, and quiz question connects directly to the exact words in the podcast transcript.

---

## 2. Technical Tools Compared

We tested multiple free tools to find the best combination for speed, reliability, and cost.

### A. AI Text Models (Summaries, Chapters, Quiz)

| Tool | Strengths | Limitations | Our Verdict |
|---|---|---|---|
| **Google Gemini Flash** | **Huge memory window:** Reads 10+ hours in one call. Native JSON support. Free tier available. | Free tier is sometimes slow during busy hours. | **Primary Model** (best for long podcasts). |
| **Groq (GPT-OSS-120B)** | **Super fast:** Answers in 1 to 2 seconds. | Free tier has an 8,000 token per minute budget; cannot fit very long episodes. | **Fast Backup & Comparison Model**. |
| **Hugging Face** | Access to many open-source models via a single API token. | Free accounts get small monthly credits that can run out. | **Secondary Fallback**. |
| **Local Models (Ollama)** | Private and free. | Needs a powerful GPU/computer. Cannot run on small free cloud servers. | **Not used for cloud deployment**. |

> **Real-World Finding:** AI models get retired quickly! While testing, Groq retired `llama-3.3-70b-versatile`. Because our system tests real API calls, we quickly caught this and upgraded to `openai/gpt-oss-120b`.

---

### B. Speech-to-Text (Audio Transcribers)

| Tool | Strengths | Limitations | Our Verdict |
|---|---|---|---|
| **Groq Whisper** | **Real timestamps:** Provides second-by-second timing. 200x faster than real-time. Supports 100+ languages. | 25 MB file upload limit on the free tier. | **Primary Choice** (we compress and split audio into chunks so any episode fits). |
| **Gemini Audio** | Good at understanding many languages. | Does not provide dependable second-by-second timestamps. | **Backup Choice** (used if Groq is down; drops timestamps honestly). |
| **OpenAI Whisper API** | Good quality reference model. | Requires a paid credit card account. | **Not used** (breaks the free-tier rule). |

---

### C. Cloud Hosting

| Platform | Strengths & Limits | Verdict |
|---|---|---|
| **Render (Free Tier)** | Runs Python and Docker smoothly. No credit card needed. No tiny file upload caps. | **Chosen Host.** (Deployed live at podcast-companion.onrender.com). |
| **Vercel** | Popular, but has a hard **4.5 MB request limit**. Real podcast audio files are 20 to 60 MB, so Vercel blocks them. | **Rejected** (cannot handle podcast audio). |
| **Hugging Face Spaces** | Free Docker spaces were removed for new accounts in mid-2026. | **Rejected** (requires paid plan). |

---

## 3. How We Keep Answers Trustworthy (Reliability)

Instead of hoping the AI tells the truth, our code checks everything:

1. **Numbered Passages:** The transcript is cut into numbered segments (`Passage 1`, `Passage 2`, etc.). The AI must cite these numbers.
2. **Quote Verification:** For quizzes and Q&A, the server searches the transcript to confirm the quote is real word-for-word. Ungrounded questions are thrown away.
3. **Honest Timestamps:** Timestamps come only from real audio transcription (Whisper) or subtitle files (`.srt`/`.vtt`). If plain text is uploaded, the app honestly says *"No timestamps available"* instead of inventing fake times.
4. **No Answer Bias:** AI models often put the correct quiz answer as option B. Our backend shuffles answers randomly to keep quizzes fair.
5. **Abstaining on Unknowns:** If you ask a question not mentioned in the podcast (like *"Who won the World Cup?"*), the system politely refuses instead of guessing.

---

## 4. Safety & Security (OWASP Top 10)

We followed standard security practices to protect users and the server:

- **File Header Checks (Magic Bytes):** We check the binary header of uploaded files. Renaming a virus or text file to `.mp3` is safely blocked before reaching the audio player.
- **Input Size Limits:** Enforces a minimum of 200 characters and a maximum of 150,000 characters to prevent server crashes.
- **Strict Privacy Notice:** We tell users upfront that free AI tiers may process their text, advising them not to submit confidential passwords or trade secrets.
- **Zero Hardcoded Secrets:** All API keys live safely in server environment variables and are never saved in GitHub.

---

## 5. Measured Test: Gemini vs. Groq in Our App

We tested both models on the exact same 11-minute podcast transcript (about 10,300 characters). Here are the measured results:

| Feature / Metric | Google Gemini Flash-Lite | Groq (GPT-OSS-120B) |
|---|---|---|
| **Overview Generation Speed** | 5.2 seconds | **1.5 seconds** (3x faster) |
| **Chapter Generation Speed** | 1.5 seconds | 1.8 seconds |
| **Quiz Generation Speed** | 5.8 seconds | **3.5 seconds** |
| **Quote Verification Rate** | **100% (All quotes verified)** | **100% (All quotes verified)** |
| **Off-Topic Refusal ("World Cup")** | Refused correctly | Refused correctly |
| **Maximum Episode Length** | **Huge (up to 10+ hours)** | Medium (limited by 8K tokens/min) |

### Key Takeaway:
- **Groq is the speed champion:** It generates answers in 1 to 2 seconds, making it feel instant.
- **Gemini is the capacity champion:** It easily handles long, multi-hour podcast marathons.
- **Our Recommendation:** Use **Auto Mode**. It uses Groq for speed when possible, and seamlessly relies on Gemini for long episodes.

---

## 6. Three Future Improvements (Next Steps)

1. **Automated Truthfulness Testing (Highest Priority):**  
   Build an automated benchmark tool that grades whether every generated summary sentence strictly matches the audio without hallucination.
2. **Saving & Sharing Links (Database Support):**  
   Add a lightweight database so listeners can save their favorite episodes and share a web link with friends.
3. **Word-by-Word Streaming (Faster Feel):**  
   Stream AI words as they are generated so users don't have to wait for the whole paragraph to finish before reading.
