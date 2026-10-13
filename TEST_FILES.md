# Test files: real internet links for every input type

Every link below was checked on **12 October 2026**. Each one loaded and played in a browser, or returned its full text, and its duration, size and licence were read from the source. The one exception is marked in its row. All files are public domain or openly licensed, so they are safe to send to Gemini and Groq.

**Quickest way to get them all:** run the download script. It saves every file into `test-files\` with the correct extension and also creates the `.aac` file:

```powershell
cd C:\Users\Lenovo\Downloads\podcast-companion\podcast-companion
powershell -ExecutionPolicy Bypass -File scripts\download_test_files.ps1
```

Then, in the app, open the matching tab (**Paste text**, **Transcript file** or **Audio file**), drag in a file and click **Build my companion**.

> **Saving text files by hand?** The app checks the extension (`.txt`, `.md`, `.srt`, `.vtt`). Links that end in `.php` or `api.php` open as text in the browser. Press **Ctrl+S** and save with the extension shown in the "Save as" column.

Limits to keep in mind: text **200 to 150,000 characters**; audio **max 60 MB and 90 minutes**. Files **over 24 MB** are compressed on the server first, which is slower. **Groq** only accepts transcripts up to about **24,000 characters**; longer ones need Gemini or Auto.

---

## 1. Transcript text

| Type | File (click to open / download) | Save as | Length | Licence / source | What to expect |
|---|---|---|---|---|---|
| `.txt` | [Plato, *Euthyphro* (Project Gutenberg)](https://www.gutenberg.org/cache/epub/1642/pg1642.txt) | `euthyphro.txt` | 69,700 chars, two speakers (`SOCRATES:` / `EUTHYPHRO:`) | Public domain | No timestamps; chapters show passage ranges. Includes Gutenberg's licence header, which the summary should ignore. Too long for Groq; use Gemini or Auto |
| `.txt` (long) | [Plato, *Apology*](https://www.gutenberg.org/cache/epub/1656/pg1656.txt) | `apology.txt` | 106,900 chars, one long speech | Public domain | Works with Gemini; tests a long single-speaker input |
| `.md` | [The Changelog #330 transcript](https://raw.githubusercontent.com/thechangelog/transcripts/master/podcast/the-changelog-330.md) | `changelog-330.md` | about 45,000 chars, full interview episode | CC BY-SA 4.0, Changelog Media | Markdown (`**Speaker:**`, links) is stripped. Too long for Groq |
| `.md` (short) | [Changelog News, 17 June 2024](https://raw.githubusercontent.com/thechangelog/transcripts/master/news/changelog-news-99.md) | `changelog-news-99.md` | about 8,000 chars | CC BY-SA 4.0 | **Fits Groq**, so use it for a Gemini vs Groq comparison on Markdown |
| `.srt` | [NASA KNX Radio interview with Chris Cassidy: captions](https://images-assets.nasa.gov/video/iss063m261631434_Expedition_63_KNX_Radio_and_Chris_Cassidy_200611/iss063m261631434_Expedition_63_KNX_Radio_and_Chris_Cassidy_200611.srt) | `nasa-knx-interview.srt` | 15,900 chars, 11 min | Public domain (NASA) | **Real timestamps** (0:00 to about 11:00). **Fits Groq.** It is the same interview as the `.mp4` below, so you can compare captions with transcription |
| `.srt` (long) | [NASA in Silicon Valley Live: How to Get an Internship at NASA (captions)](https://commons.wikimedia.org/w/index.php?title=TimedText%3ANASA%20in%20Silicon%20Valley%20Live%3B%20How%20to%20Get%20an%20Internship%20at%20NASA.webm.en.srt&action=raw) | `nasa-internship-live.srt` | 103,000 chars, 58-min live show | Public domain (NASA), via Wikimedia Commons | Real timestamps across a full hour. Gemini only |
| `.srt` (medium) | [NASA live interviews with Jeanette Epps (captions)](https://images-assets.nasa.gov/video/iss061m2627771232_Live_Interviews_Jeanette_Epps_191004/iss061m2627771232_Live_Interviews_Jeanette_Epps_191004.srt) | `nasa-epps-interviews.srt` | 38,000 chars, 19 min | Public domain (NASA) | Several back-to-back interviews, which makes a good chapter test |
| `.vtt` | [NASA in Silicon Valley Live: same show, WebVTT](https://commons.wikimedia.org/w/api.php?action=timedtext&title=File%3ANASA%20in%20Silicon%20Valley%20Live%3B%20How%20to%20Get%20an%20Internship%20at%20NASA.webm&lang=en&trackformat=vtt) | `nasa-internship-live.vtt` | 103,000 chars, 58 min | Public domain (NASA), via Wikimedia Commons | Should give the **same passages and times as the long `.srt`**, which is a direct format-parity check |

**Pasted text:** open any `.txt` or `.md` link, select all (Ctrl+A), copy, and paste it into the **Paste text** tab. To test pasted `[mm:ss]` timestamps, use the built-in **With [mm:ss] times** sample button.

---

## 2. Audio

| Type | File (click to download) | Length / size | Licence / source | What to expect |
|---|---|---|---|---|
| `.mp3` | [Martin Amis on creative writing (interview, 1990)](https://upload.wikimedia.org/wikipedia/commons/6/61/Martin_Amis_and_creative_writing_%28Interview_1990%29.mp3) | 11.1 min · 20.3 MB | CC BY-SA 4.0, Wikimedia Commons | Under 24 MB, so it goes straight to Groq Whisper. Real timestamps, two speakers |
| `.mp3` (long) | [NASA *Houston We Have a Podcast* Ep. 424: AI at NASA (128k)](https://images-assets.nasa.gov/audio/Ep424_AI_at_NASA/Ep424_AI_at_NASA~128k.mp3) | 34.4 min · 31.5 MB | Public domain (NASA) | Over 24 MB, so it is **compressed and split** first; watch the progress stages |
| `.m4a` | [NASA *Houston We Have a Podcast* Ep. 424: AI at NASA (64k)](https://images-assets.nasa.gov/audio/Ep424_AI_at_NASA/Ep424_AI_at_NASA~64k.m4a) | 33.9 min · 15.7 MB | Public domain (NASA) | A real podcast episode in M4A. Same episode as the long `.mp3`, so the results should match |
| `.m4a` (alt.) | [NASA *Houston We Have a Podcast* Ep. 391: Mars Is Hard (64k)](https://images-assets.nasa.gov/audio/Ep391_Mars_Is_Hard/Ep391_Mars_Is_Hard~64k.m4a) | 45.3 min · 21.0 MB | Public domain (NASA) | Longer episode, still under 24 MB |
| `.mp4` | [NASA: Chris Cassidy's in-flight interview with KNX Radio (video)](https://images-assets.nasa.gov/video/iss063m261631434_Expedition_63_KNX_Radio_and_Chris_Cassidy_200611/iss063m261631434_Expedition_63_KNX_Radio_and_Chris_Cassidy_200611~mobile.mp4) | 11.0 min · 26.0 MB | Public domain (NASA) | A video file; the app uses only its audio. Over 24 MB, so it is compressed first. **Compare its chapters with the `.srt` above** |
| `.wav` | [Theodore Roosevelt, "The Right of the People to Rule" (1912)](https://upload.wikimedia.org/wikipedia/commons/a/ab/The_Right_of_the_People_to_Rule_%28Speech_by_Theodore_Roosevelt%29.wav) | 4.1 min · 41.6 MB | Public domain | Large uncompressed file, so it is compressed first. **Old, noisy recording**: a hard transcription test |
| `.ogg` | [Spoken Wikipedia: "Bioinformatics"](https://upload.wikimedia.org/wikipedia/commons/4/43/En-Bioinformatics.ogg) | 37.0 min · 17.9 MB | CC BY-SA 3.0, Wikimedia Commons | A single narrator reading a long article; tests chapters on dense, technical content |
| `.flac` | [*Preservapedia Podcast*: Richard McCoy](https://upload.wikimedia.org/wikipedia/commons/1/10/Preservapedia_Podcast_Richard_McCoy.flac) | 9.7 min · 35.9 MB | CC BY-SA 3.0, Wikimedia Commons | A real podcast interview. Lossless and over 24 MB, so it is compressed first |
| `.webm` | ["What Barbados was like in the 1960s" (interview)](https://upload.wikimedia.org/wikipedia/commons/8/85/What_Barbados_was_like_in_the_1960%27s-N0d4O18lXqs.webm) | 18.3 min · 15.9 MB | CC BY 3.0, Wikimedia Commons | WebM/Opus audio, the format browsers record in |
| `.aac` | **Made by the download script** from the NASA `.m4a` above (lossless stream copy, no re-encoding) | 33.9 min · about 15.7 MB | Public domain (NASA) | Raw AAC isn't accepted by Groq directly, so the app converts it with ffmpeg first. No stable public raw-AAC speech file exists (Wikimedia doesn't accept `.aac`), so converting a real podcast is the honest option |

To make the `.aac` by hand instead of with the script:

```powershell
$ffmpeg = & .venv\Scripts\python.exe -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"
& $ffmpeg -i "test-files\nasa-hwhap-424-ai.m4a" -vn -c:a copy "test-files\nasa-hwhap-424-ai.aac"
```

---

## 3. Error and edge cases (these should fail cleanly or behave specially)

| Test | File | What should happen |
|---|---|---|
| Audio over 60 MB | [*Houston We Have a Podcast* 01-345: The Lost Universe](https://upload.wikimedia.org/wikipedia/commons/7/74/Houston_We_Have_a_Podcast_01-345_-_The_Lost_Universe.mp3) (77.5 MB) | The browser refuses it before uploading: "That file is 78 MB; the limit is 60 MB." |
| Text over 150,000 characters | [Plato, *Phaedrus*](https://www.gutenberg.org/cache/epub/1636/pg1636.txt) (235,000 chars) | "The transcript is too long (…) The limit is 150,000 characters." |
| Long text with **Groq** selected | *Euthyphro* `.txt` above, with **Model → Groq** | Each section says it is too long for Groq's free tier and suggests Gemini or Auto |
| Non-English audio | [Spanish Wikipedia article read aloud: "Big Bang"](https://upload.wikimedia.org/wikipedia/commons/c/ca/Big_bang_introduction_article_wikipedia_spanish.flac) (10.2 min · 44.5 MB, CC0; size and duration from Wikimedia's file record, not play-tested) | Set **Spoken language → Spanish**. The transcript should be in Spanish, and the summary should be in Spanish too |
| Wrong file type | Rename any `.txt` to `.mp3` and upload it as audio | "That doesn't look like a supported audio file…" (the app checks the file's content, not its name) |
| Gemini-only transcription | Any audio above, with **Transcription engine → Google Gemini** | The transcript has no timestamps, and the app says why |

---

## 4. The built-in samples (same content in every format)

The app's own sample episode (11 minutes, 1,770 words) is in every format under `/samples/`, and each tab has **Try a sample** buttons for them. Once the repository is pushed, the same files are also online:

`https://raw.githubusercontent.com/moazzem-hossain-majumder/Podcast-Companion/main/app/static/samples/episode.<ext>`

where `<ext>` is one of `txt`, `md`, `srt`, `vtt`, `mp3`, `m4a`, `mp4`, `wav`, `ogg`, `flac`, `webm`, `aac` (plus `episode-timestamped.txt`). Locally: `http://127.0.0.1:8000/samples/episode.<ext>`.

How to check results by hand (citations, timestamps, quiz answers, revision) is covered in [docs/TESTING.md](docs/TESTING.md).

---

### Credits

Wikimedia Commons files are by their respective authors under the licences shown, with each file's page at `https://commons.wikimedia.org/wiki/File:<name>`. NASA media is public domain ([NASA media guidelines](https://www.nasa.gov/nasa-brand-center/images-and-media/)). Changelog transcripts are © Changelog Media LLC, CC BY-SA 4.0 ([repository](https://github.com/thechangelog/transcripts)). Project Gutenberg texts are public domain in the US ([gutenberg.org](https://www.gutenberg.org)).
