import os
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = "http://127.0.0.1:8000"
SCREENSHOTS = ROOT / "docs" / "screenshots"
SCREENSHOTS.mkdir(parents=True, exist_ok=True)

def wait_for_results(page, timeout=120000):
    page.wait_for_selector("#results-view:not([hidden])", timeout=timeout)
    page.wait_for_selector("#rp-overview .prose p", timeout=timeout)
    page.wait_for_selector("#strip button", timeout=timeout)
    time.sleep(2)

def main():
    print("==================================================")
    print("STARTING FULL AUTOMATED TEST SUITE (DARK MODE)")
    print("==================================================")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 960}, color_scheme="dark")
        page = context.new_page()

        # -----------------------------------------------------------------
        # TEST 02: Timestamped Text Sample
        # -----------------------------------------------------------------
        print("\n--> Running Test 02: Built-in Timestamped Text...")
        page.goto(BASE, wait_until="networkidle")
        ts_text = (ROOT / "app" / "static" / "samples" / "episode-timestamped.txt").read_text(encoding="utf-8")
        page.fill("#text-input", ts_text)
        page.click("#build")
        wait_for_results(page)
        # Switch to chapters tab to show real timestamps
        page.click("#rt-chapters")
        time.sleep(1)
        ss2 = SCREENSHOTS / "test-02-sample-timestamped.png"
        page.screenshot(path=str(ss2))
        print(f"Captured: {ss2.name}")

        # -----------------------------------------------------------------
        # TEST 03: Short Episode Sample
        # -----------------------------------------------------------------
        print("\n--> Running Test 03: Short Episode Sample...")
        page.click("#new-episode")
        short_text = (ROOT / "app" / "static" / "sample.txt").read_text(encoding="utf-8")
        page.fill("#text-input", short_text)
        page.click("#build")
        wait_for_results(page)
        ss3 = SCREENSHOTS / "test-03-sample-short.png"
        page.screenshot(path=str(ss3))
        print(f"Captured: {ss3.name}")

        # -----------------------------------------------------------------
        # TEST 04: Plato's Euthyphro (.txt)
        # -----------------------------------------------------------------
        print("\n--> Running Test 04: Plato's Euthyphro (.txt)...")
        page.click("#new-episode")
        page.click("#tab-file")
        page.set_input_files("#file-input", str(ROOT / "test-files" / "euthyphro.txt"))
        page.click("#build")
        wait_for_results(page, timeout=120000)
        ss4 = SCREENSHOTS / "test-04-file-euthyphro-txt.png"
        page.screenshot(path=str(ss4))
        print(f"Captured: {ss4.name}")

        # -----------------------------------------------------------------
        # TEST 05: The Changelog 330 (.md)
        # -----------------------------------------------------------------
        print("\n--> Running Test 05: Changelog 330 (.md)...")
        page.click("#new-episode")
        page.click("#tab-file")
        page.set_input_files("#file-input", str(ROOT / "test-files" / "changelog-330.md"))
        page.click("#build")
        wait_for_results(page, timeout=120000)
        ss5 = SCREENSHOTS / "test-05-file-changelog-md.png"
        page.screenshot(path=str(ss5))
        print(f"Captured: {ss5.name}")

        # -----------------------------------------------------------------
        # TEST 06: NASA KNX Interview (.srt)
        # -----------------------------------------------------------------
        print("\n--> Running Test 06: NASA KNX Interview (.srt)...")
        page.click("#new-episode")
        page.click("#tab-file")
        page.set_input_files("#file-input", str(ROOT / "test-files" / "nasa-knx-interview.srt"))
        page.click("#build")
        wait_for_results(page)
        page.click("#rt-chapters")
        time.sleep(1)
        ss6 = SCREENSHOTS / "test-06-file-nasa-srt.png"
        page.screenshot(path=str(ss6))
        print(f"Captured: {ss6.name}")

        # -----------------------------------------------------------------
        # TEST 07: NASA Silicon Valley (.vtt)
        # -----------------------------------------------------------------
        print("\n--> Running Test 07: NASA Silicon Valley (.vtt)...")
        page.click("#new-episode")
        page.click("#tab-file")
        page.set_input_files("#file-input", str(ROOT / "test-files" / "nasa-internship-live.vtt"))
        page.click("#build")
        wait_for_results(page, timeout=120000)
        page.click("#rt-chapters")
        time.sleep(1)
        ss7 = SCREENSHOTS / "test-07-file-nasa-vtt.png"
        page.screenshot(path=str(ss7))
        print(f"Captured: {ss7.name}")

        # -----------------------------------------------------------------
        # TEST 08: Martin Amis (.mp3) - Fast Whisper path
        # -----------------------------------------------------------------
        print("\n--> Running Test 08: Martin Amis (.mp3)...")
        page.click("#new-episode")
        page.click("#tab-audio")
        page.set_input_files("#audio-input", str(ROOT / "test-files" / "martin-amis-interview.mp3"))
        page.click("#build")
        wait_for_results(page, timeout=180000)
        ss8 = SCREENSHOTS / "test-08-audio-martin-amis-mp3.png"
        page.screenshot(path=str(ss8))
        print(f"Captured: {ss8.name}")

        # -----------------------------------------------------------------
        # TEST 09: NASA AI Episode (.m4a)
        # -----------------------------------------------------------------
        print("\n--> Running Test 09: NASA AI Episode (.m4a)...")
        page.click("#new-episode")
        page.click("#tab-audio")
        page.set_input_files("#audio-input", str(ROOT / "test-files" / "nasa-hwhap-424-ai.m4a"))
        page.click("#build")
        wait_for_results(page, timeout=180000)
        ss9 = SCREENSHOTS / "test-09-audio-nasa-m4a.png"
        page.screenshot(path=str(ss9))
        print(f"Captured: {ss9.name}")

        # -----------------------------------------------------------------
        # TEST 10: NASA KNX Video (.mp4)
        # -----------------------------------------------------------------
        print("\n--> Running Test 10: NASA KNX Video (.mp4)...")
        page.click("#new-episode")
        page.click("#tab-audio")
        page.set_input_files("#audio-input", str(ROOT / "test-files" / "nasa-knx-interview.mp4"))
        page.click("#build")
        wait_for_results(page, timeout=180000)
        ss10 = SCREENSHOTS / "test-10-audio-nasa-mp4.png"
        page.screenshot(path=str(ss10))
        print(f"Captured: {ss10.name}")

        # -----------------------------------------------------------------
        # TEST 11: Roosevelt Speech (.wav)
        # -----------------------------------------------------------------
        print("\n--> Running Test 11: Roosevelt Speech (.wav)...")
        page.click("#new-episode")
        page.click("#tab-audio")
        page.set_input_files("#audio-input", str(ROOT / "test-files" / "roosevelt-1912-speech.wav"))
        page.click("#build")
        wait_for_results(page, timeout=180000)
        ss11 = SCREENSHOTS / "test-11-audio-roosevelt-wav.png"
        page.screenshot(path=str(ss11))
        print(f"Captured: {ss11.name}")

        # -----------------------------------------------------------------
        # TEST 12: Wikipedia Bioinformatics (.ogg)
        # -----------------------------------------------------------------
        print("\n--> Running Test 12: Wikipedia Bioinformatics (.ogg)...")
        page.click("#new-episode")
        page.click("#tab-audio")
        page.set_input_files("#audio-input", str(ROOT / "test-files" / "spoken-wikipedia-bioinformatics.ogg"))
        page.click("#build")
        wait_for_results(page, timeout=180000)
        ss12 = SCREENSHOTS / "test-12-audio-wikipedia-ogg.png"
        page.screenshot(path=str(ss12))
        print(f"Captured: {ss12.name}")

        # -----------------------------------------------------------------
        # TEST 13: Preservapedia McCoy (.flac)
        # -----------------------------------------------------------------
        print("\n--> Running Test 13: Preservapedia McCoy (.flac)...")
        page.click("#new-episode")
        page.click("#tab-audio")
        page.set_input_files("#audio-input", str(ROOT / "test-files" / "preservapedia-podcast-mccoy.flac"))
        page.click("#build")
        wait_for_results(page, timeout=180000)
        ss13 = SCREENSHOTS / "test-13-audio-preservapedia-flac.png"
        page.screenshot(path=str(ss13))
        print(f"Captured: {ss13.name}")

        # -----------------------------------------------------------------
        # TEST 14: Barbados 1960s (.webm)
        # -----------------------------------------------------------------
        print("\n--> Running Test 14: Barbados 1960s (.webm)...")
        page.click("#new-episode")
        page.click("#tab-audio")
        page.set_input_files("#audio-input", str(ROOT / "test-files" / "barbados-1960s-interview.webm"))
        page.click("#build")
        wait_for_results(page, timeout=180000)
        ss14 = SCREENSHOTS / "test-14-audio-barbados-webm.png"
        page.screenshot(path=str(ss14))
        print(f"Captured: {ss14.name}")

        # -----------------------------------------------------------------
        # TEST 15: NASA Stream Copy (.aac)
        # -----------------------------------------------------------------
        print("\n--> Running Test 15: NASA Stream Copy (.aac)...")
        page.click("#new-episode")
        page.click("#tab-audio")
        page.set_input_files("#audio-input", str(ROOT / "test-files" / "nasa-hwhap-424-ai.aac"))
        page.click("#build")
        wait_for_results(page, timeout=180000)
        ss15 = SCREENSHOTS / "test-15-audio-nasa-aac.png"
        page.screenshot(path=str(ss15))
        print(f"Captured: {ss15.name}")

        # -----------------------------------------------------------------
        # TEST 16: Quiz Citation Jump
        # -----------------------------------------------------------------
        print("\n--> Running Test 16: Quiz Citation Jump...")
        page.click("#rt-quiz")
        time.sleep(1)
        # Click first option in first quiz question
        page.click(".q:first-child .opt:first-child")
        time.sleep(1)
        # Click source citation
        source_cite = page.query_selector(".q:first-child .source a, .q:first-child a.cite")
        if source_cite:
            source_cite.click()
            time.sleep(1)
        ss16 = SCREENSHOTS / "test-16-quiz-citation-jump.png"
        page.screenshot(path=str(ss16))
        print(f"Captured: {ss16.name}")

        # -----------------------------------------------------------------
        # TEST 17: Ask the Episode: Answerable Question
        # -----------------------------------------------------------------
        print("\n--> Running Test 17: Ask the Episode (Answerable)...")
        page.click("#rt-ask")
        time.sleep(0.5)
        page.fill("#ask-input", "What is discussed in this episode?")
        page.click("#ask-submit")
        page.wait_for_selector(".qa .answer", timeout=45000)
        time.sleep(1)
        ss17 = SCREENSHOTS / "test-17-ask-answerable.png"
        page.screenshot(path=str(ss17))
        print(f"Captured: {ss17.name}")

        # -----------------------------------------------------------------
        # TEST 18: Ask the Episode: Unanswerable Question
        # -----------------------------------------------------------------
        print("\n--> Running Test 18: Ask the Episode (Unanswerable)...")
        page.fill("#ask-input", "Who won the 1998 football world cup?")
        page.click("#ask-submit")
        time.sleep(3)
        ss18 = SCREENSHOTS / "test-18-ask-unanswerable.png"
        page.screenshot(path=str(ss18))
        print(f"Captured: {ss18.name}")

        # -----------------------------------------------------------------
        # TEST 19: Export Results (Copy All / Download .md / .json)
        # -----------------------------------------------------------------
        print("\n--> Running Test 19: Export Results...")
        page.click("#rt-overview")
        time.sleep(1)
        ss19 = SCREENSHOTS / "test-19-export-results.png"
        page.screenshot(path=str(ss19))
        print(f"Captured: {ss19.name}")

        # -----------------------------------------------------------------
        # TEST 20: Revision (Shorter preset)
        # -----------------------------------------------------------------
        print("\n--> Running Test 20: Revision (Shorter)...")
        page.click(".chip:has-text('Shorter')")
        time.sleep(5)
        ss20 = SCREENSHOTS / "test-20-revision-shorter.png"
        page.screenshot(path=str(ss20))
        print(f"Captured: {ss20.name}")

        # -----------------------------------------------------------------
        # TEST 21: Revision Undo
        # -----------------------------------------------------------------
        print("\n--> Running Test 21: Revision Undo...")
        undo_btn = page.query_selector("button:has-text('Undo')")
        if undo_btn:
            undo_btn.click()
            time.sleep(1)
        ss21 = SCREENSHOTS / "test-21-revision-undo.png"
        page.screenshot(path=str(ss21))
        print(f"Captured: {ss21.name}")

        # -----------------------------------------------------------------
        # TEST 22: Compare Models Tab (Gemini vs Groq side by side)
        # -----------------------------------------------------------------
        print("\n--> Running Test 22: Compare Models Tab...")
        page.click("#rt-compare")
        time.sleep(1)
        cmp_btn = page.query_selector("button:has-text('Run comparison')")
        if cmp_btn:
            cmp_btn.click()
            page.wait_for_selector(".cmp-table", timeout=90000)
            time.sleep(2)
        ss22 = SCREENSHOTS / "test-22-model-comparison-tab.png"
        page.screenshot(path=str(ss22))
        print(f"Captured: {ss22.name}")

        # -----------------------------------------------------------------
        # TEST 23: ASR Engine Comparison View
        # -----------------------------------------------------------------
        print("\n--> Running Test 23: ASR Engine Comparison...")
        page.click("#new-episode")
        page.click("#tab-audio")
        time.sleep(1)
        ss23 = SCREENSHOTS / "test-23-transcription-engine-compare.png"
        page.screenshot(path=str(ss23))
        print(f"Captured: {ss23.name}")

        # -----------------------------------------------------------------
        # TEST 24: Error - Text Too Short
        # -----------------------------------------------------------------
        print("\n--> Running Test 24: Error - Text Too Short...")
        page.click("#tab-text")
        page.fill("#text-input", "hello world")
        page.click("#build")
        time.sleep(1)
        ss24 = SCREENSHOTS / "test-24-error-too-short.png"
        page.screenshot(path=str(ss24))
        print(f"Captured: {ss24.name}")

        # -----------------------------------------------------------------
        # TEST 25: Error - Spoofed / Bad Audio File
        # -----------------------------------------------------------------
        print("\n--> Running Test 25: Error - Spoofed Audio File...")
        # Create a fake audio file (text renamed to mp3)
        fake_audio = ROOT / "test-files" / "fake_audio.mp3"
        fake_audio.write_text("This is not a real audio file.", encoding="utf-8")
        page.click("#tab-audio")
        page.set_input_files("#audio-input", str(fake_audio))
        page.click("#build")
        time.sleep(2)
        ss25 = SCREENSHOTS / "test-25-error-bad-audio.png"
        page.screenshot(path=str(ss25))
        print(f"Captured: {ss25.name}")
        fake_audio.unlink(missing_ok=True)

        # -----------------------------------------------------------------
        # TEST 26: Error - Groq Free Tier Length Limit
        # -----------------------------------------------------------------
        print("\n--> Running Test 26: Groq Free Tier Length Notice...")
        page.click("#tab-text")
        # 30,000 characters
        long_text = ("This is a long podcast transcript about AI and technology. " * 500)
        page.fill("#text-input", long_text)
        # Select Groq model
        page.click("#model-input")
        time.sleep(0.5)
        groq_opt = page.query_selector(".mp-item:has-text('Groq')")
        if groq_opt:
            groq_opt.click()
            time.sleep(0.5)
        page.click("#build")
        time.sleep(3)
        ss26 = SCREENSHOTS / "test-26-error-too-long-groq.png"
        page.screenshot(path=str(ss26))
        print(f"Captured: {ss26.name}")

        browser.close()
        print("\n==================================================")
        print("ALL 26 TESTS COMPLETED AND CAPTURED!")
        print("==================================================")

if __name__ == "__main__":
    main()
