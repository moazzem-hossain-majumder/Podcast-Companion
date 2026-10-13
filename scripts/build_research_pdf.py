import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Podcast Companion: Research & Engineering Findings</title>
<style>
  @page {
    size: A4;
    margin: 16mm 15mm 16mm 15mm;
    @bottom-right {
      content: counter(page);
    }
  }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #111827;
    line-height: 1.5;
    font-size: 10pt;
    margin: 0;
    padding: 0;
  }
  .header {
    border-bottom: 2px solid #111827;
    padding-bottom: 10px;
    margin-bottom: 18px;
  }
  .badge {
    display: inline-block;
    background: #111827;
    color: #ffffff;
    font-size: 8pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 3px 8px;
    border-radius: 3px;
    margin-bottom: 6px;
  }
  h1 {
    font-size: 18pt;
    color: #111827;
    margin: 4px 0 4px 0;
    font-weight: 800;
    letter-spacing: -0.02em;
  }
  .subtitle {
    font-size: 10.5pt;
    color: #4b5563;
    margin-bottom: 8px;
  }
  .meta-grid {
    display: flex;
    gap: 18px;
    font-size: 8.5pt;
    color: #4b5563;
    margin-top: 6px;
  }
  .meta-grid strong {
    color: #111827;
  }
  h2 {
    font-size: 12pt;
    color: #111827;
    border-bottom: 1.5px solid #111827;
    padding-bottom: 3px;
    margin-top: 18px;
    margin-bottom: 8px;
    font-weight: 700;
    page-break-after: avoid;
  }
  h3 {
    font-size: 10.5pt;
    color: #111827;
    margin-top: 12px;
    margin-bottom: 4px;
    font-weight: 600;
    page-break-after: avoid;
  }
  p {
    margin: 0 0 8px 0;
  }
  ul, ol {
    margin: 0 0 8px 0;
    padding-left: 18px;
  }
  li {
    margin-bottom: 3px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 12px 0;
    font-size: 9pt;
  }
  th, td {
    border: 1px solid #d1d5db;
    padding: 6px 8px;
    text-align: left;
    vertical-align: top;
  }
  th {
    background-color: #f3f4f6;
    font-weight: 700;
    color: #111827;
  }
  tr:nth-child(even) td {
    background-color: #fafafa;
  }
  .callout {
    background-color: #f9fafb;
    border: 1px solid #d1d5db;
    border-left: 4px solid #111827;
    padding: 8px 12px;
    margin: 8px 0 12px 0;
    font-size: 9pt;
    border-radius: 0 4px 4px 0;
  }
  .callout strong {
    color: #111827;
  }
  .highlight-box {
    background-color: #f9fafb;
    border: 1px solid #d1d5db;
    border-radius: 4px;
    padding: 10px 12px;
    margin: 8px 0 12px 0;
  }
  code {
    background-color: #f3f4f6;
    color: #111827;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 8.5pt;
    padding: 1px 4px;
    border-radius: 3px;
    border: 1px solid #e5e7eb;
  }
</style>
</head>
<body>

<div class="header">
  <span class="badge">AI Engineering Project</span>
  <h1>Podcast Companion: Research & Engineering Findings</h1>
  <div class="subtitle">A clear, practical review of technical choices, reliability mechanisms, and real-world benchmarks</div>
  <div class="meta-grid">
    <div><strong>Author:</strong> Moazzem Hossain Majumder</div>
    <div><strong>Date:</strong> October 2026</div>
    <div><strong>Live App:</strong> podcast-companion.onrender.com</div>
    <div><strong>Code:</strong> GitHub Public Repository</div>
  </div>
</div>

<h2>1. Why We Built This (User Value)</h2>
<p>
  Long podcasts are packed with valuable information, but remembering and finding specific points later is frustrating. Standard AI chatbots usually produce generic summaries that you cannot verify.
</p>

<div class="highlight-box">
  <p style="margin-bottom: 4px;"><strong>Who benefits most:</strong></p>
  <ul style="margin-bottom: 0;">
    <li><strong>Students & Learners:</strong> Want to quickly review core ideas and test what they learned.</li>
    <li><strong>Busy Listeners:</strong> Need to know in 2 minutes whether an 80-minute episode is worth hearing.</li>
    <li><strong>Readers & Accessibility:</strong> People who retain information better through text than audio.</li>
    <li><strong>Podcast Creators:</strong> Need chapter markers and quiz questions to engage their listeners.</li>
  </ul>
</div>

<p>
  <strong>The Core Problem Solved:</strong> Instead of guessing, we answer: <em>"Where did the speaker actually say that, and can I trust it?"</em> Every takeaway, chapter, and quiz answer links directly to the exact words in the podcast transcript.
</p>

<h2>2. Technical Tools Compared</h2>
<p>We tested multiple free tools to find the best combination for speed, reliability, and cost.</p>

<h3>A. AI Text Models (Summaries, Chapters, Quiz)</h3>
<table>
  <thead>
    <tr>
      <th style="width: 25%;">Model</th>
      <th style="width: 35%;">Key Strengths</th>
      <th style="width: 25%;">Limitations</th>
      <th style="width: 15%;">Our Verdict</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Google Gemini Flash</strong></td>
      <td><strong>Huge context window:</strong> Reads 10+ hours in one call. Native JSON support. Generous free tier.</td>
      <td>Free tier can experience queue delays during peak traffic hours.</td>
      <td><strong>Primary Choice</strong> (handles long episodes).</td>
    </tr>
    <tr>
      <td><strong>Groq (GPT-OSS-120B)</strong></td>
      <td><strong>Super fast:</strong> Answers in 1 to 2 seconds. Reliable JSON mode.</td>
      <td>Free tier has an 8,000 token per minute ceiling; cannot fit huge files.</td>
      <td><strong>Fast Backup</strong> & comparison model.</td>
    </tr>
    <tr>
      <td><strong>Hugging Face Router</strong></td>
      <td>Provides access to diverse open-source models with one API key.</td>
      <td>Free tier gives small monthly credits that can run out quickly.</td>
      <td><strong>Secondary Fallback</strong>.</td>
    </tr>
    <tr>
      <td><strong>Local Models (Ollama)</strong></td>
      <td>100% private with zero API rate limits.</td>
      <td>Needs a powerful computer/GPU. Cannot run on free cloud servers (512MB RAM).</td>
      <td><strong>Rejected</strong> for free cloud hosting.</td>
    </tr>
  </tbody>
</table>

<div class="callout">
  <strong>Real-World Finding:</strong> AI models retire quickly! While developing, Groq retired <code>llama-3.3-70b-versatile</code>. Because our system makes real API calls, we caught this immediately and upgraded to <code>openai/gpt-oss-120b</code>.
</div>

<h3>B. Speech-to-Text (Audio Transcribers)</h3>
<table>
  <thead>
    <tr>
      <th style="width: 25%;">Transcriber</th>
      <th style="width: 35%;">Key Strengths</th>
      <th style="width: 25%;">Limitations</th>
      <th style="width: 15%;">Our Verdict</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Groq Whisper</strong></td>
      <td><strong>Real timestamps:</strong> Second-by-second accuracy via <code>verbose_json</code>. Over 200x faster than real-time.</td>
      <td>25 MB file size limit on free tier.</td>
      <td><strong>Primary Choice</strong> (we compress and split audio into chunks).</td>
    </tr>
    <tr>
      <td><strong>Gemini Audio</strong></td>
      <td>Handles many spoken languages well natively.</td>
      <td>Timestamps are not dependable; inline audio capped at 20 MB.</td>
      <td><strong>Backup Choice</strong> (drops timestamps honestly).</td>
    </tr>
    <tr>
      <td><strong>OpenAI Whisper API</strong></td>
      <td>High quality reference implementation.</td>
      <td>Requires a paid credit card account.</td>
      <td><strong>Rejected</strong> (breaks free-tier rule).</td>
    </tr>
  </tbody>
</table>

<h3>C. Cloud Hosting Platforms</h3>
<table>
  <thead>
    <tr>
      <th style="width: 25%;">Platform</th>
      <th style="width: 55%;">Findings & Evaluation</th>
      <th style="width: 20%;">Our Verdict</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Render (Free Web Service)</strong></td>
      <td>Runs Python and Docker smoothly without credit cards. Allows audio uploads without small file ceilings. Sleeps after 15 min idle.</td>
      <td><strong>Chosen Host</strong> (Live on Render).</td>
    </tr>
    <tr>
      <td><strong>Vercel</strong></td>
      <td>Has a strict <strong>4.5 MB request body limit</strong>. Real podcast audio files are 20–60 MB, so Vercel blocks them.</td>
      <td><strong>Rejected</strong> (cannot upload audio).</td>
    </tr>
    <tr>
      <td><strong>Hugging Face Spaces</strong></td>
      <td>Free Docker compute spaces now require paid accounts for new users.</td>
      <td><strong>Rejected</strong> (requires paid plan).</td>
    </tr>
  </tbody>
</table>

<h2>3. How We Keep Answers Trustworthy (Reliability)</h2>
<p>Instead of hoping the AI doesn't hallucinate, our Python backend strictly checks everything:</p>
<ul>
  <li><strong>Numbered Passages:</strong> The transcript is cut into numbered segments (Passage 1, Passage 2...). The AI must cite these numbers.</li>
  <li><strong>Verbatim Quote Checks:</strong> For quizzes and Q&amp;A, the server searches the transcript to confirm the quote is real word-for-word. Ungrounded questions are discarded.</li>
  <li><strong>Honest Timestamps:</strong> Timestamps come only from Whisper or subtitle files (<code>.srt</code>/<code>.vtt</code>). If plain text is uploaded, the app honestly displays <em>"No timestamps available"</em> instead of making up fake times.</li>
  <li><strong>Server-Side Option Shuffling:</strong> AI models often put the right quiz answer as Option B. We randomize answer positions on the server to prevent bias.</li>
  <li><strong>Abstaining on Out-of-Domain Questions:</strong> If a user asks something not in the podcast (like <em>"Who won the World Cup?"</em>), the system politely refuses instead of guessing.</li>
</ul>

<h2>4. Safety & Security (OWASP Top 10 API Security)</h2>
<ul>
  <li><strong>File Header Checks (Magic Bytes):</strong> We inspect the binary header of uploaded files. Renaming a text or malicious file to <code>.mp3</code> is safely caught and rejected before reaching ffmpeg.</li>
  <li><strong>Input Guardrails:</strong> Transcripts under 200 characters or over 150,000 characters are safely rejected with clear HTTP error codes.</li>
  <li><strong>Privacy Notice:</strong> Users are informed upfront that free AI tiers may process their inputs, advising against submitting private passwords or confidential records.</li>
  <li><strong>Secret Hygiene:</strong> Zero credentials are saved in code or GitHub; all API keys load securely from environment variables.</li>
</ul>

<h2>5. Measured Benchmark: Gemini vs. Groq Inside Our App</h2>
<p>We ran both models head-to-head on the exact same 11-minute podcast transcript (about 10,300 characters). Both models were pinned with no hidden fallback:</p>

<table>
  <thead>
    <tr>
      <th style="width: 35%;">Benchmark Metric</th>
      <th style="width: 32%;">Google Gemini Flash-Lite</th>
      <th style="width: 33%;">Groq (GPT-OSS-120B)</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Overview Generation Time</strong></td>
      <td>5.2 seconds</td>
      <td><strong>1.5 seconds</strong> (over 3x faster)</td>
    </tr>
    <tr>
      <td><strong>Chapters Generation Time</strong></td>
      <td>1.5 seconds</td>
      <td>1.8 seconds</td>
    </tr>
    <tr>
      <td><strong>Quiz Generation Time</strong></td>
      <td>5.8 seconds</td>
      <td><strong>3.5 seconds</strong></td>
    </tr>
    <tr>
      <td><strong>Verbatim Quote Check</strong></td>
      <td><strong>100% Verified</strong> (3 of 3 questions)</td>
      <td><strong>100% Verified</strong> (3 of 3 questions)</td>
    </tr>
    <tr>
      <td><strong>Off-Topic Question Refusal</strong></td>
      <td>Refused correctly (no guess)</td>
      <td>Refused correctly (no guess)</td>
    </tr>
    <tr>
      <td><strong>Maximum Episode Length</strong></td>
      <td><strong>Huge</strong> (handles 10+ hour audio)</td>
      <td>Medium (limited by 8K tokens/min)</td>
    </tr>
  </tbody>
</table>

<p>
  <strong>Takeaway:</strong> Groq is unmatched for speed (1.5 seconds), while Gemini is unmatched for episode length. Our <strong>Auto mode</strong> uses Groq for speed when possible, and smoothly relies on Gemini for long marathons.
</p>

<h2>6. Three Future Improvements (Next Steps)</h2>
<ol>
  <li><strong>Automated Truthfulness Testing (Highest Priority):</strong> An automated benchmark harness that checks if every summary claim strictly matches the podcast audio without any subtle drift.</li>
  <li><strong>Durable Database & Shareable Links:</strong> Storing episode companions in a lightweight database so users can share permanent links with friends.</li>
  <li><strong>Word-by-Word Streaming:</strong> Streaming tokens over Server-Sent Events (SSE) so users see summary sentences appear instantly as they are generated.</li>
</ol>

</body>
</html>
"""

def generate_pdf():
    print("Generating monochrome/grayscale Research PDF...")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        page.set_content(HTML_TEMPLATE, wait_until="networkidle")
        
        pdf_path_docs = DOCS / "RESEARCH.pdf"
        pdf_path_root = ROOT / "RESEARCH.pdf"
        
        page.pdf(
            path=str(pdf_path_docs),
            format="A4",
            margin={"top": "14mm", "bottom": "14mm", "left": "14mm", "right": "14mm"},
            print_background=True,
        )
        print(f"Created: {pdf_path_docs}")
        
        # Also save to root for easy reviewer access
        page.pdf(
            path=str(pdf_path_root),
            format="A4",
            margin={"top": "14mm", "bottom": "14mm", "left": "14mm", "right": "14mm"},
            print_background=True,
        )
        print(f"Created: {pdf_path_root}")
        browser.close()

if __name__ == "__main__":
    generate_pdf()
