# Testing guide: inputs, model comparison and how to verify results yourself

This guide covers three things: where to get a test input in **every supported format**, how to **compare Gemini and Groq**, and how to **check the output yourself**, without trusting the app (or the AI).

---

## 1. Start the app locally (Windows PowerShell)

```powershell
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
python scripts\check_providers.py      # must show OK for at least one Gemini model and one Groq model
python -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000>. Both `GEMINI_API_KEY` and `GROQ_API_KEY` must be set in `.env` to compare the two models. You can confirm with <http://127.0.0.1:8000/api/health>: `llm_options` should list `gemini` and `groq` with `"ready": true`.

On macOS/Linux, use `source .venv/bin/activate` and forward slashes.

---

## 2. Test inputs for every format

### 2a. Built-in samples (one episode, every supported format)

The same 11-minute episode, *Wired Planet, Episode 12: How the Internet Actually Reaches You* (two speakers, about 1,770 words, about 10,300 characters), is provided in every format. Because the content is identical, you can compare formats with each other, and Gemini with Groq, on the same material. The text is short enough for Groq's free tier, which takes up to about 24,000 characters.

**Fastest way:** every input tab has a **Try a sample** row with one button per format that tab accepts:
- **Paste text:** Plain transcript, With [mm:ss] times, Short episode
- **Transcript file:** .txt, .md, .srt, .vtt
- **Audio file:** .mp3, .m4a, .mp4, .wav, .ogg, .flac, .webm, .aac

Click one, then **Build my companion**. After loading, a **Download** link appears, so you can also test the real upload path by dragging the file in yourself.

Links work locally and on the live site. On the live site, replace `http://127.0.0.1:8000` with your Render URL.

| Format | Link | Input path | What you should see |
|---|---|---|---|
| Pasted text | [episode.txt](http://127.0.0.1:8000/samples/episode.txt) (copy, then paste) | Paste text tab | 23 passages, **no timestamps**; chapters show "Part 1" with a passage range instead of a time |
| Pasted text with `[mm:ss]` | [episode-timestamped.txt](http://127.0.0.1:8000/samples/episode-timestamped.txt) | Paste text tab | **Real timestamps** read from the `[00:06]` markers (last one about 10:38) |
| `.txt` file | [episode.txt](http://127.0.0.1:8000/samples/episode.txt) | Transcript file tab | Same as pasted text |
| `.md` file | [episode.md](http://127.0.0.1:8000/samples/episode.md) | Transcript file tab | Headings and `**bold**` removed; Transcript tab shows no `#` or `**` |
| `.srt` subtitles | [episode.srt](http://127.0.0.1:8000/samples/episode.srt) | Transcript file tab | 134 cues merged into 19 passages, **real timestamps** (0:00 to about 10:29) |
| `.vtt` subtitles | [episode.vtt](http://127.0.0.1:8000/samples/episode.vtt) | Transcript file tab | Same timings as the .srt |
| `.mp3` | [episode.mp3](http://127.0.0.1:8000/samples/episode.mp3) (3.8 MB) | Audio file tab | Transcribed by Groq Whisper with real timestamps |
| `.m4a` | [episode.m4a](http://127.0.0.1:8000/samples/episode.m4a) (4.0 MB) | Audio file tab | Same |
| `.mp4` | [episode.mp4](http://127.0.0.1:8000/samples/episode.mp4) (4.0 MB) | Audio file tab | Same (AAC audio in an MP4 container) |
| `.wav` | [episode.wav](http://127.0.0.1:8000/samples/episode.wav) (20 MB) | Audio file tab | Same; largest file, still under Groq's 25 MB direct limit |
| `.ogg` | [episode.ogg](http://127.0.0.1:8000/samples/episode.ogg) (3.0 MB) | Audio file tab | Same |
| `.flac` | [episode.flac](http://127.0.0.1:8000/samples/episode.flac) (11.7 MB) | Audio file tab | Same |
| `.webm` (Opus) | [episode.webm](http://127.0.0.1:8000/samples/episode.webm) (2.6 MB) | Audio file tab | Same |
| `.aac` (raw ADTS) | [episode.aac](http://127.0.0.1:8000/samples/episode.aac) (4.0 MB) | Audio file tab | Same |
| Short sample | [sample.txt](http://127.0.0.1:8000/sample.txt) | Paste text tab | The original 5-minute "Study Hall" episode |

The audio uses a synthetic voice (espeak-ng), which sounds robotic but is clear speech, so Whisper transcribes it well. The `.srt`/`.vtt` times were measured from that same audio, so you can play `episode.mp3` and check that a subtitle line is spoken at the time it claims. To rebuild every sample: `python scripts/make_samples.py` (needs `espeak-ng` and `ffmpeg`).

### 2b. Real recordings from the internet, for every format

**[TEST_FILES.md](../TEST_FILES.md)** lists a checked, openly licensed, real-world file for every input type, from NASA, Wikimedia Commons, Project Gutenberg and the Changelog podcast. It also includes error cases (a file that's too big, a text that's too long, non-English audio). `scripts\download_test_files.ps1` downloads all of them into `test-files\` with the correct extensions.

### 2c. More real human speech (public domain, from LibriVox on archive.org)

Use these to test with a natural human voice instead of the synthetic sample. They are public domain, so they are safe to send to the AI services.

| Format | Link | Length / size |
|---|---|---|
| MP3 | [shortstory036_baroness_rsc.mp3](https://archive.org/download/short_story_036_0904_librivox/shortstory036_baroness_rsc.mp3) | about 10.6 min, 10 MB |
| Ogg Vorbis | [shortstory036_baroness_rsc.ogg](https://archive.org/download/short_story_036_0904_librivox/shortstory036_baroness_rsc.ogg) | about 10.6 min, 5.6 MB |
| Long MP3 (64 kbps) | [shortstory036_attwilight_sbs_64kb.mp3](https://archive.org/download/short_story_036_0904_librivox/shortstory036_attwilight_sbs_64kb.mp3) | about 32 min, 15 MB |

Collection page: <https://archive.org/details/short_story_036_0904_librivox>.

Note that the 32-minute file's transcript (roughly 4,500+ words) will very likely exceed Groq's free-tier text limit (about 24,000 characters). That makes it a good test of the "too long for Groq" message: Gemini works, Groq is refused with a clear explanation.

To get the other audio formats from a real recording, convert the MP3 with ffmpeg:

```powershell
ffmpeg -i shortstory036_baroness_rsc.mp3 -ac 1 -ar 16000 baroness.wav
ffmpeg -i shortstory036_baroness_rsc.mp3 baroness.flac
ffmpeg -i shortstory036_baroness_rsc.mp3 -c:a aac -b:a 64k baroness.m4a
ffmpeg -i shortstory036_baroness_rsc.mp3 -c:a libopus -b:a 32k baroness.webm
```

(`python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"` prints the path of the ffmpeg binary that came with the project, if you don't have ffmpeg installed.)

---

## 3. Comparing Gemini and Groq

There are three ways, from quickest to most thorough:

1. **Compare models tab (recommended).** Build any sample, open **Compare models**, and click **Run comparison**. The overview, chapters and quiz are generated by Gemini and by Groq using the same transcript and the same prompts. Each request is pinned to one provider, so there is no silent fallback to the other model, and both go through the same verification. The table shows:
   - **Time** per section, measured on the server and including any validation re-asks
   - **Re-asks after validation**: how often the model's first answer failed a check (a bad citation or an unverifiable quote) and had to be corrected
   - **Verified quiz questions**: how many of the 6 requested questions passed the verbatim-quote check. Fewer than 6 means some were dropped as unsupported.
   - **Summary length**, the number of themes and takeaways, the number of chapters, and any warnings

   **Download .md / .json** saves the comparison, which you can put in your research notes. **Use Groq's results in the other tabs** opens that model's output in the normal tabs, so you can take its quiz.
2. **Model picker on the home page.** Choose *Google Gemini* or *Groq* before building. Every section, revision and "Ask" answer then uses only that model. The footer of each tab says which model wrote it and how long it took.
3. **Model switch on the results page.** Changing **Model** regenerates all sections with the other provider on the same transcript.

**Transcription comparison (audio only).** The Audio tab has a **Transcription engine** option: *Groq Whisper* returns real timestamps, while *Google Gemini* returns text only, so chapters have no times. Run the same `episode.mp3` through both and compare the Transcript tabs.

Suggested comparison runs for your write-up: `episode.srt` (timestamps), `episode.txt` (no timestamps), and the 32-minute LibriVox file (shows Groq's free-tier length limit).

---

## 4. Verify the results yourself

The app's rule is that the model proposes and the code verifies. Here is how to check it by hand.

| What to check | How | Pass if |
|---|---|---|
| **Quiz answers are grounded** | Quiz tab: answer a question, then click **source** under the quote | The Transcript tab highlights a passage that contains the quoted words, and that passage really supports the correct answer |
| **Quiz answers are correct** | Answer all 6 using only the transcript (Ctrl+F in the Transcript tab) | Your answers match the app's "Correct answer" |
| **Takeaways cite real passages** | Overview: click each **source** link next to a takeaway | Each linked passage talks about that takeaway |
| **Timestamps are real** | Build `episode.srt`, open Chapters, note a start time (for example 3:32). Play `episode.mp3` at that time | The audio at that moment matches the chapter's opening passage (within a few seconds) |
| **No invented timestamps** | Build `episode.txt` (plain text) | Chapters show "Part 1 · passages…", with no `mm:ss` anywhere |
| **"Ask" refuses unsupported questions** | Ask "Who won the 2022 World Cup?" | The answer says the episode doesn't cover it, with no quote |
| **"Ask" answers supported questions** | Ask "What causes most undersea cable faults?" | Fishing gear and ship anchors, with a quote you can click |
| **Revision changes only one section** | Overview → **Shorter** | The summary gets shorter, the quiz and chapters are unchanged, and **Undo** restores the old version |
| **Facts in the sample** | Built-in episode answer key: first transatlantic telegraph cable 1858 (failed after about 3 weeks); TCP/IP described by Vint Cerf and Bob Kahn in 1974; DNS introduced 1983; light in fibre about 200,000 km/s (about 2/3 of vacuum speed); 2008 YouTube route leak from Pakistan; most cable faults come from fishing gear and anchors | Quiz questions and the summary agree with these |

### Error handling (deliberate failures)

| Try this | Expected |
|---|---|
| Click **Build** with an empty text box | "Paste a transcript first, or load a sample episode." |
| Paste `hello` | "The transcript is too short…" |
| Rename `episode.txt` to `fake.mp3` and upload it as audio | "That doesn't look like a supported audio file…" (checked by file content, not by the extension) |
| Choose **Groq**, paste `episode.txt` three times (about 31,000 characters), then build | Each section shows "This transcript is too long for Groq's free tier… choose Gemini or Auto." |
| Remove `GROQ_API_KEY` from `.env` and restart | The Groq option is greyed out ("not configured on this server") |
| Run **Compare** twice quickly | If a free tier rate-limits, that column shows "Groq is busy or rate-limited… retry in N seconds" instead of crashing |

---

## 5. Automated tests

```powershell
pip install -r requirements-dev.txt
python -m pytest -q
```

This runs 126 tests. They cover parsing (including Markdown), grounding checks, the fallback chain, **provider pinning** (Gemini-only never calls Groq and vice versa), the "too long for Groq" and "not configured" errors, latency metadata, choosing a transcription engine, and the built-in samples: every file parses or is detected as the right audio type, is long enough, and is under the upload limits.

Browser-level UI test (no API keys needed; it uses a fake Gemini and a fake Groq):

```powershell
cd tests\e2e; npm init -y; npm i jsdom; cd ..\..
Start-Process python -ArgumentList "tests\e2e_server.py 8765"
$env:BASE="http://127.0.0.1:8765"; node tests\e2e\ui.test.mjs
```

This runs 21 UI steps, including the sample picker for every format, the Groq-only run, the model switch and the Compare tab.

Live deployment check (real API calls, prints real latencies):

```powershell
python scripts\smoke_live.py https://<your-render-url>
```
