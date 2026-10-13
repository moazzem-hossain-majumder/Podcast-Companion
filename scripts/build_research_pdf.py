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
<title>AI Engineering Challenge: Research & Technical Report</title>
<style>
  @page {
    size: A4;
    margin: 18mm 16mm 18mm 16mm;
    @bottom-right {
      content: counter(page);
    }
  }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: #1e293b;
    line-height: 1.55;
    font-size: 10.5pt;
    margin: 0;
    padding: 0;
  }
  .header {
    border-bottom: 2px solid #0f766e;
    padding-bottom: 12px;
    margin-bottom: 24px;
  }
  .badge {
    display: inline-block;
    background: #0f766e;
    color: #ffffff;
    font-size: 8pt;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 3px 8px;
    border-radius: 4px;
    margin-bottom: 8px;
  }
  h1 {
    font-size: 20pt;
    color: #0f172a;
    margin: 4px 0 6px 0;
    font-weight: 800;
    letter-spacing: -0.02em;
  }
  .subtitle {
    font-size: 11pt;
    color: #475569;
    margin-bottom: 8px;
  }
  .meta-grid {
    display: flex;
    gap: 20px;
    font-size: 9pt;
    color: #64748b;
    margin-top: 8px;
  }
  .meta-grid strong {
    color: #334155;
  }
  h2 {
    font-size: 13pt;
    color: #0f766e;
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 4px;
    margin-top: 24px;
    margin-bottom: 10px;
    font-weight: 700;
    page-break-after: avoid;
  }
  h3 {
    font-size: 11pt;
    color: #1e293b;
    margin-top: 14px;
    margin-bottom: 6px;
    font-weight: 600;
    page-break-after: avoid;
  }
  p {
    margin: 0 0 10px 0;
  }
  ul, ol {
    margin: 0 0 10px 0;
    padding-left: 20px;
  }
  li {
    margin-bottom: 4px;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0 16px 0;
    font-size: 9pt;
    page-break-inside: avoid;
  }
  th, td {
    border: 1px solid #cbd5e1;
    padding: 6px 10px;
    text-align: left;
    vertical-align: top;
  }
  th {
    background-color: #f1f5f9;
    font-weight: 600;
    color: #0f172a;
  }
  tr:nth-child(even) td {
    background-color: #f8fafc;
  }
  .callout {
    background-color: #f0fdf4;
    border-left: 4px solid #0f766e;
    padding: 10px 14px;
    margin: 12px 0;
    font-size: 9.5pt;
    border-radius: 0 4px 4px 0;
    page-break-inside: avoid;
  }
  .callout-title {
    font-weight: 700;
    color: #0f766e;
    margin-bottom: 4px;
  }
  .code {
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
    font-size: 8.5pt;
    background: #f1f5f9;
    padding: 2px 4px;
    border-radius: 3px;
    color: #0f766e;
  }
  .page-break {
    page-break-before: always;
  }
</style>
</head>
<body>

<div class="header">
  <span class="badge">AI Engineering Challenge &bull; Technical Report</span>
  <h1>From Audio to Insight: AI Podcast Companion</h1>
  <div class="subtitle">Comprehensive Research, Technology Evaluation, and Engineering Architecture</div>
  <div class="meta-grid">
    <div><strong>Author:</strong> Moazzem Hossain Majumder</div>
    <div><strong>Studio:</strong> Thealon Animation Studios | Dhaka, Bangladesh</div>
    <div><strong>Deployment:</strong> Render Cloud (Live)</div>
    <div><strong>Date:</strong> October 2026</div>
  </div>
</div>

<h2>1. Research Context & Problem Statement</h2>
<p>According to <em>Edison Research's The UK Podcast Consumer 2025</em>, 71% of adults aged 16+ have listened to or watched podcasts, and over 51% consume podcasts monthly. While long-form spoken audio contains dense educational, philosophical, and technical narratives, it suffers from severe accessibility barriers:</p>
<ul>
  <li><strong>Information Inelasticity:</strong> Listeners cannot easily skim, search, or index spoken audio without linear playback.</li>
  <li><strong>Unreliable Memory & Recall:</strong> Critical insights, arguments, and book recommendations are easily forgotten without synthesized takeaways.</li>
  <li><strong>Verification Deficit:</strong> Generic LLM chat tools produce summaries that hallucinate facts or fail to point to exact audio cues where claims were made.</li>
</ul>

<div class="callout">
  <div class="callout-title">Core Mission</div>
  Transform unstructured spoken audio into a deterministic, interactive companion featuring structured summaries, verifiable chapter bounds, comprehension quizzes, and honest question-answering with verbatim citations.
</div>

<h2>2. User Value Analysis</h2>
<p>We identified four primary user personas who benefit directly from this solution:</p>
<table>
  <thead>
    <tr>
      <th>User Persona</th>
      <th>Primary Need</th>
      <th>Companion Solution & Impact</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Active Learners & Students</strong></td>
      <td>Study tool for technical or philosophical lectures.</td>
      <td>Comprehension quizzes with instant feedback and direct links back to verbatim source passages.</td>
    </tr>
    <tr>
      <td><strong>Time-Constrained Listeners</strong></td>
      <td>Deciding whether a 90-minute recording is worth hearing.</td>
      <td>~150-word overview, key themes, and takeaways readable in under 60 seconds.</td>
    </tr>
    <tr>
      <td><strong>Accessibility & Reading-First Users</strong></td>
      <td>Struggling to track rapid or accented spoken dialogue.</td>
      <td>Clean transcript segmentation, responsive chapter timelines, and complete textual exploration.</td>
    </tr>
    <tr>
      <td><strong>Podcast Creators & Educators</strong></td>
      <td>Producing show notes, chapter markers, and engagement.</td>
      <td>One-click Markdown/JSON export formatted with exact timestamps for YouTube and podcast feeds.</td>
    </tr>
  </tbody>
</table>

<h2>3. Technology Choices & Comparative Evaluation</h2>

<h3>3.1 Large Language Models (Summary, Chapters, Quiz, Q&A)</h3>
<table>
  <thead>
    <tr>
      <th>Provider & Model</th>
      <th>Context & Features</th>
      <th>Latency & Constraints</th>
      <th>Evaluation Verdict</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Google Gemini 3.1 Flash-Lite / 3.5 Flash</strong></td>
      <td>~1M tokens context; native JSON schema enforcement; generous free tier.</td>
      <td>2.0s–5.0s per section; free tier may train on inputs (disclosed to user).</td>
      <td><strong>Primary Model:</strong> Accommodates full-length episodes in one prompt without chunking.</td>
    </tr>
    <tr>
      <td><strong>Groq (openai/gpt-oss-120b)</strong></td>
      <td>Open-weight reasoning model via Groq LPU; sub-second token generation.</td>
      <td>1.5s per section; strict 8K tokens/min free tier budget limits length.</td>
      <td><strong>Fallback #1 & Benchmark:</strong> Ultra-low latency for short/medium episodes (&lt;24k chars).</td>
    </tr>
    <tr>
      <td><strong>Hugging Face Inference Providers</strong></td>
      <td>Multi-provider router (Llama 3.3 70B); OpenAI-compatible client.</td>
      <td>HTTP 402 on credit exhaustion; latency varies by provider queue.</td>
      <td><strong>Fallback #2:</strong> Provides tertiary redundancy if Google and Groq are down.</td>
    </tr>
    <tr>
      <td><strong>Local Open-Source (llama.cpp)</strong></td>
      <td>Fully offline and private.</td>
      <td>Requires high GPU/RAM unavailable on free 512MB hosting instances.</td>
      <td><strong>Rejected</strong> for deployed web service.</td>
    </tr>
  </tbody>
</table>

<div class="page-break"></div>

<h3>3.2 Automated Speech-to-Text (ASR) Pipeline</h3>
<table>
  <thead>
    <tr>
      <th>Engine</th>
      <th>Capabilities</th>
      <th>Limitations</th>
      <th>Verdict</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Groq Whisper (whisper-large-v3-turbo)</strong></td>
      <td>~216x real-time speed; returns segment-level millisecond timestamps via <span class="code">verbose_json</span>.</td>
      <td>25 MB file limit per API call on free tier.</td>
      <td><strong>Primary ASR:</strong> Powers exact chapter timestamp generation.</td>
    </tr>
    <tr>
      <td><strong>Google Gemini Audio Ingestion</strong></td>
      <td>Direct audio processing without external transcription step.</td>
      <td>Does not provide reliable segment timecodes; inline upload capped at 20MB.</td>
      <td><strong>Text-Only Fallback:</strong> Used when Whisper is unavailable; UI honestly reports lack of times.</td>
    </tr>
    <tr>
      <td><strong>OpenAI Whisper API</strong></td>
      <td>Reference implementation.</td>
      <td>Paid service; challenge constraints forbid incurring unapproved costs.</td>
      <td><strong>Rejected</strong> to honor zero-cost constraint.</td>
    </tr>
  </tbody>
</table>

<h3>3.3 Hosting Platform Comparison</h3>
<ul>
  <li><strong>Vercel Serverless:</strong> Rejected due to a rigid <strong>4.5 MB request body cap</strong> that rejects real-world podcast files (20–100 MB).</li>
  <li><strong>Hugging Face Spaces:</strong> Docker compute Spaces now require paid subscriptions for new users.</li>
  <li><strong>Render Free Web Service:</strong> Selected. Provides native Docker/Python execution, up to 60 MB request streaming, and zero credit card requirement.</li>
</ul>

<h2>4. Grounding & Reliability Architecture</h2>
<p>To eliminate hallucination and guarantee that all generated content is faithful to the source material, the system enforces a strict <strong>deterministic verification layer</strong> written in Python:</p>
<ul>
  <li><strong>Segment-Indexed Grounding:</strong> The transcript is tokenized into numbered passages (<span class="code">#1, #2, ...</span>). LLM outputs cite passage IDs rather than raw times. Real timestamps are resolved by Python lookups.</li>
  <li><strong>Verbatim Quote Verification:</strong> Every quiz question and Ask response must contain an exact transcript quote. The server normalizes punctuation and whitespace to verify that the quote appears verbatim near the cited passage. Questions failing verification are purged.</li>
  <li><strong>Server-Side Option Shuffling:</strong> Answer choices are shuffled programmatically to neutralize LLM positional biases (such as favoritism toward option B).</li>
  <li><strong>Refusal Guardrail:</strong> In the Ask Q&A feature, questions that cannot be supported by the transcript are explicitly refused rather than hallucinated (verified in Test 18).</li>
</ul>

<h2>5. Measured Empirical Benchmark: Gemini vs. Groq</h2>
<p>A live head-to-head evaluation was conducted on an identical 11-minute podcast transcript (1,770 words, 10,300 characters):</p>
<table>
  <thead>
    <tr>
      <th>Benchmark Metric</th>
      <th>Google Gemini (gemini-3.1-flash-lite)</th>
      <th>Groq (openai/gpt-oss-120b)</th>
      <th>Analysis & Takeaway</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>Overview Latency</strong></td>
      <td>5.2 seconds</td>
      <td>1.5 seconds</td>
      <td>Groq LPU achieves 3.4x faster time-to-completion.</td>
    </tr>
    <tr>
      <td><strong>Chapters Latency</strong></td>
      <td>1.5 seconds</td>
      <td>1.8 seconds</td>
      <td>Comparable latency on structured chapter segmentation.</td>
    </tr>
    <tr>
      <td><strong>Quiz Latency</strong></td>
      <td>5.8 seconds</td>
      <td>3.5 seconds</td>
      <td>Groq was 1.6x faster on complex multi-choice extraction.</td>
    </tr>
    <tr>
      <td><strong>Validation Re-asks</strong></td>
      <td>0 re-asks (100% first-pass pass)</td>
      <td>0 re-asks (100% first-pass pass)</td>
      <td>Both models strictly adhered to Pydantic JSON schemas.</td>
    </tr>
    <tr>
      <td><strong>Verified Quiz Questions</strong></td>
      <td>6 of 6 verified</td>
      <td>6 of 6 verified</td>
      <td>100% of quotes matched transcript verbatim.</td>
    </tr>
    <tr>
      <td><strong>Context Capacity</strong></td>
      <td>150,000+ characters</td>
      <td>&le; 24,000 characters</td>
      <td>Gemini handles full episodes; Groq throttled on TPM budget.</td>
    </tr>
  </tbody>
</table>

<div class="page-break"></div>

<h2>6. Responsible AI Handling (OWASP API Security Lens)</h2>
<ul>
  <li><strong>API Security & Secrets:</strong> Zero credentials exist in client-side code or public git history. All API keys are loaded via environment variables and injected as HTTP headers.</li>
  <li><strong>Magic-Byte Sniffing:</strong> Uploaded audio files are inspected for binary magic bytes (<span class="code">ID3</span>, <span class="code">RIFF/WAVE</span>, <span class="code">fLaC</span>, <span class="code">OggS</span>, <span class="code">ftyp</span>) rather than trusting client MIME types or file extensions.</li>
  <li><strong>Ephemeral Data Lifecycle:</strong> Audio chunks are transcoded in temporary scratch directories and immediately deleted post-transcription. No user transcripts are stored server-side.</li>
  <li><strong>Resource Throttling:</strong> Per-IP sliding-window rate limiters and body streaming guards protect free-tier quotas against denial-of-service or quota exhaustion.</li>
</ul>

<h2>7. Real-World Debugging Case Studies</h2>
<ol>
  <li><strong>CSP Inline Style Suppression:</strong> A strict Content-Security-Policy (<span class="code">style-src 'self'</span>) silently blocked <span class="code">setAttribute('style')</span>, rendering chapter bars as uniform blocks without error. <em>Fix:</em> Refactored DOM helper to assign <span class="code">el.style.cssText</span> via the CSSOM and added automated spy tests.</li>
  <li><strong>Model Picker Event Detachment:</strong> Clicking the custom model picker destroyed and recreated the DOM button during the same event loop, causing <span class="code">event.target</span> to become detached and closing the menu instantly. <em>Fix:</em> Migrated to <span class="code">event.composedPath().includes(root)</span> and scoped re-renders to the menu only.</li>
  <li><strong>Vendor Deprecation & Cooldown Backoff:</strong> Groq retired <span class="code">llama-3.3-70b-versatile</span> on 2026-08-16 without updating models documentation, causing immediate 500 errors. <em>Fix:</em> Upgraded default to <span class="code">openai/gpt-oss-120b</span>, added automated provider capability probing (<span class="code">scripts/check_providers.py</span>), and built short cooldown absorption for 8K TPM rate limits.</li>
</ol>

<h2>8. Technical References & Official Documentation</h2>
<ul>
  <li><strong>Google Gemini API:</strong> Model Deprecations (<a href="https://ai.google.dev/gemini-api/docs/deprecations">ai.google.dev/gemini-api/docs/deprecations</a>) & Rate Limits (<a href="https://ai.google.dev/gemini-api/docs/rate-limits">ai.google.dev/gemini-api/docs/rate-limits</a>)</li>
  <li><strong>Groq Cloud Documentation:</strong> Speech-to-Text Whisper (<a href="https://console.groq.com/docs/speech-to-text">console.groq.com/docs/speech-to-text</a>) & Model Limits (<a href="https://console.groq.com/docs/rate-limits">console.groq.com/docs/rate-limits</a>)</li>
  <li><strong>OWASP Foundation:</strong> API Security Top 10 Project (<a href="https://owasp.org/www-project-api-security/">owasp.org/www-project-api-security</a>)</li>
  <li><strong>Edison Research:</strong> The UK Podcast Consumer 2025 (<a href="https://www.edisonresearch.com/">edisonresearch.com</a>)</li>
</ul>

</body>
</html>
"""

def generate_pdf():
    print("Generating Research PDF...")
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page()
        page.set_content(HTML_TEMPLATE, wait_until="networkidle")
        
        pdf_path_docs = DOCS / "RESEARCH.pdf"
        pdf_path_root = ROOT / "RESEARCH.pdf"
        
        page.pdf(
            path=str(pdf_path_docs),
            format="A4",
            margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"},
            print_background=True,
        )
        print(f"Created: {pdf_path_docs}")
        
        # Also save to root for easy reviewer access
        page.pdf(
            path=str(pdf_path_root),
            format="A4",
            margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"},
            print_background=True,
        )
        print(f"Created: {pdf_path_root}")
        browser.close()

if __name__ == "__main__":
    generate_pdf()
