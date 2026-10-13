"""Generate the built-in sample inputs in every supported format.

    python scripts/make_samples.py            # writes app/static/samples/*

Needs `espeak-ng` (speech synthesis) and `ffmpeg` on PATH. The generated files are committed,
so this only has to be re-run if scripts/sample_episode.py changes.

How the timestamps stay honest: every sentence is synthesised separately, its real duration is
measured from the WAV header, and the .srt / .vtt / [mm:ss] files are written from those
measurements. The audio files are the concatenation of exactly those sentence clips, so the
subtitle times line up with the audio.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from sample_episode import SCRIPT, SHOW, TITLE  # noqa: E402

OUT = ROOT / "app" / "static" / "samples"
VOICES = {"Nadia": ("en-us+f3", 165, 52), "Omar": ("en-gb+m3", 160, 44)}  # voice, words/min, pitch
SENTENCE_GAP_S = 0.22
TURN_GAP_S = 0.55
SENT = re.compile(r"(?<=[.!?])\s+")


def ts(sec: float, sep: str) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def mmss(sec: float) -> str:
    sec = int(sec)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def synth(text: str, speaker: str, path: Path) -> None:
    voice, wpm, pitch = VOICES[speaker]
    subprocess.run(["espeak-ng", "-v", voice, "-s", str(wpm), "-p", str(pitch), "-w", str(path), text], check=True)


def main() -> None:
    for tool in ("espeak-ng", "ffmpeg"):
        if not shutil.which(tool):
            sys.exit(f"{tool} is required (apt install espeak-ng ffmpeg)")
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="samples_"))

    frames: list[bytes] = []
    params = None
    t = 0.0
    cues: list[tuple[float, float, str]] = []  # (start, end, text) per sentence
    turns: list[tuple[float, str, str]] = []  # (start, speaker, paragraph)

    def silence(seconds: float) -> None:
        nonlocal t
        n = int(params.framerate * seconds)
        frames.append(b"\x00\x00" * n)
        t += n / params.framerate

    for ti, (speaker, para) in enumerate(SCRIPT):
        if ti:
            silence(TURN_GAP_S)
        turns.append((t, speaker, para))
        sentences = [s for s in SENT.split(para) if s.strip()]
        for si, sentence in enumerate(sentences):
            if si:
                silence(SENTENCE_GAP_S)
            clip = tmp / f"{ti:03d}_{si:02d}.wav"
            synth(sentence, speaker, clip)
            with wave.open(str(clip)) as w:
                p = w.getparams()
                if params is None:
                    params = p
                assert (p.nchannels, p.sampwidth, p.framerate) == (params.nchannels, params.sampwidth, params.framerate)
                data = w.readframes(p.nframes)
            start = t
            frames.append(data)
            t += p.nframes / p.framerate
            cues.append((start, t, f"{speaker}: {sentence}" if si == 0 else sentence))

    master = tmp / "master.wav"
    with wave.open(str(master), "wb") as w:
        w.setparams(params)
        w.writeframes(b"".join(frames))

    # ---------------- text formats
    plain = f"{TITLE}\n\n" + "\n\n".join(f"{sp}: {para}" for sp, para in SCRIPT) + "\n"
    (OUT / "episode.txt").write_text(plain, encoding="utf-8")

    stamped = "\n".join(f"[{mmss(start)}] {sp}: {para}" for start, sp, para in turns) + "\n"
    (OUT / "episode-timestamped.txt").write_text(stamped, encoding="utf-8")

    sections = {
        0: "Introduction", 5: "A short history", 9: "Inside a fibre optic cable", 17: "Packets and TCP/IP",
        23: "Finding the address: DNS", 29: "Choosing a route: BGP", 35: "Content delivery networks",
        39: "The last mile", 43: "When cables break", 49: "Recap",
    }
    md = [f"# {TITLE}", "", f"*A transcript from **{SHOW}**. Speakers: Nadia (host) and Omar (co-host).*", ""]
    for i, (sp, para) in enumerate(SCRIPT):
        if i in sections:
            md += [f"## {sections[i]}", ""]
        md += [f"**{sp}:** {para}", ""]
    (OUT / "episode.md").write_text("\n".join(md), encoding="utf-8")

    srt = []
    for n, (a, b, text) in enumerate(cues, 1):
        srt += [str(n), f"{ts(a, ',')} --> {ts(b, ',')}", text, ""]
    (OUT / "episode.srt").write_text("\n".join(srt), encoding="utf-8")

    vtt = ["WEBVTT", "", f"NOTE {TITLE}", ""]
    for a, b, text in cues:
        vtt += [f"{ts(a, '.')} --> {ts(b, '.')}", text, ""]
    (OUT / "episode.vtt").write_text("\n".join(vtt), encoding="utf-8")

    # ---------------- audio formats (16 kHz mono is what speech recognisers use internally)
    base = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(master), "-ac", "1"]
    meta = ["-metadata", f"title={TITLE}", "-metadata", f"artist={SHOW} (synthetic voices)"]
    encodes = {
        "episode.mp3": ["-ar", "22050", "-c:a", "libmp3lame", "-b:a", "48k", *meta],
        "episode.m4a": ["-ar", "22050", "-c:a", "aac", "-b:a", "48k", *meta],
        "episode.mp4": ["-ar", "22050", "-c:a", "aac", "-b:a", "48k", "-f", "mp4", "-brand", "isom", *meta],
        "episode.aac": ["-ar", "22050", "-c:a", "aac", "-b:a", "48k", "-f", "adts"],
        "episode.wav": ["-ar", "16000", "-c:a", "pcm_s16le"],
        "episode.flac": ["-ar", "16000", "-c:a", "flac", "-write_id3v2", "0", *meta],
        "episode.ogg": ["-ar", "22050", "-c:a", "libvorbis", "-q:a", "2", *meta],
        "episode.webm": ["-ar", "48000", "-c:a", "libopus", "-b:a", "32k"],
    }
    for name, args in encodes.items():
        subprocess.run([*base, *args, str(OUT / name)], check=True)

    shutil.rmtree(tmp, ignore_errors=True)
    words = sum(len(p.split()) for _, p in SCRIPT)
    print(f"{len(SCRIPT)} turns, {len(cues)} cues, {words} words, {t / 60:.1f} min of audio")
    for f in sorted(OUT.iterdir()):
        print(f"  {f.name:28s} {f.stat().st_size / 1024:8.0f} KB")


if __name__ == "__main__":
    main()
