# Demo video script (target: 3-4 minutes, screen recording)

Record the **deployed** URL. For audio, use **Audio file → Try a sample → .mp3** (built in), or a public-domain LibriVox clip from [TESTING.md](TESTING.md).

1. **(0:00) Context, 15 s.** "This turns a podcast into a companion: overview, chapters, quiz, with every claim linked to the source."
2. **(0:15) Input & limits, 20 s.** Show the three input options, the limits line and the **Try a sample** buttons in each tab (every supported format). Open the **Model ⌄** menu: Auto, Google Gemini, Groq. Mention the privacy notice.
3. **(0:35) Audio path, 60 s.** Upload the clip → show the progress stages → results appear. Point out: the title, the **chapter strip** (hover for names), and that chapter cards show **real timestamps**.
4. **(1:35) Grounding, 40 s.** Quiz tab: answer one right and one wrong; show explanation and the **source quote**; click the citation to jump to the highlighted transcript passage.
5. **(2:15) Revision, 40 s.** Overview → click **Shorter** → show only that section changes (quiz untouched) and the "Revised" note → **Undo**. Then Quiz → **More challenging**.
6. **(2:55) Honesty features, 30 s.** Ask tab: ask something covered ("what about sleep?") and something not covered; show the refusal. Paste the sample text to show the "no timestamps" notice on chapters.
7. **(3:25) Export, 15 s.** Copy all / Download .md.
7b. **(optional, 40 s) Model comparison.** Open **Compare models** → **Run comparison**: Gemini and Groq side by side on the same transcript (time, verified questions, outputs). Mention that each is pinned so there is no hidden fallback.
8. **(3:40) Close, 10 s.** "Fallback chain across Gemini, Groq, Hugging Face; in-app Gemini vs Groq comparison; 126 automated tests; limitations and next steps are in the README."

Tip: do a throwaway run first so the free instance is awake (cold start can take a minute), and keep the browser console closed.
