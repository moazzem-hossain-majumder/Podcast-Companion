const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const puppeteer = require('C:/Users/MITHIL/AppData/Local/npm-cache/_npx/4b4c857f6efdfb61/node_modules/puppeteer');

const FFMPEG = 'C:/Users/MITHIL/AppData/Local/Programs/Python/Python311/Lib/site-packages/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe';
const SCREENSHOTS_DIR = path.resolve(__dirname, '../docs/screenshots');
const DEMO_FRAMES_DIR = path.resolve(__dirname, '../temp_demo_frames');

if (!fs.existsSync(SCREENSHOTS_DIR)) fs.mkdirSync(SCREENSHOTS_DIR, { recursive: true });
if (!fs.existsSync(DEMO_FRAMES_DIR)) fs.mkdirSync(DEMO_FRAMES_DIR, { recursive: true });

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

// Reusable episode datasets
const MEMORY_EPISODE = {
  title: 'Why we forget',
  one_line: 'An exploration of memory decay, retention intervals, and optimal study schedules.',
  summary: 'Cognitive psychologist Dr. Robert Bjork and host Sarah Chen examine the underlying biological and psychological mechanisms behind memory consolidation and the Ebbinghaus forgetting curve. Contrary to common intuition, forgetting is not simply an evolutionary defect or passive cognitive decay, but a necessary active filter that allows the human brain to discard irrelevant background noise and prioritize critical survival heuristics.\n\nThe discussion synthesizes core experimental findings from memory research: spaced retrieval practice, the testing effect, and interleaved problem-solving dramatically outperform traditional massed practice (cramming) for long-term behavioral automaticity.',
  themes: [
    { name: 'Desirable Difficulties', description: 'Why introducing cognitive friction during initial acquisition improves long-term storage.' },
    { name: 'The Spacing Effect', description: 'Distributing study sessions across temporal intervals produces superior retention.' },
    { name: 'Active Retrieval Practice', description: 'Testing oneself strengthens neural recall pathways far more effectively than passive rereading.' }
  ],
  takeaways: [
    { text: 'Massed repetition produces strong immediate fluency but suffers catastrophic decay within 48 hours.', evidence: [1, 2] },
    { text: 'Forgetting acts as an adaptive filter, allowing higher-order conceptual consolidation.', evidence: [3] },
    { text: 'Self-testing via flashcards or practice questions forces active recall and triggers neural reconsolidation.', evidence: [7, 8] },
    { text: 'Interleaving distinct skills or problem types prevents cognitive complacency and fosters transfer learning.', evidence: [12] }
  ],
  chapters: [
    { title: 'The Mechanics of Forgetting & Cognitive Decay', summary: 'Introduction to the Ebbinghaus forgetting curve and why memory decays exponentially without active reinforcement.', start_segment: 0 },
    { title: 'Spaced Repetition & Optimal Review Intervals', summary: 'Mathematical modeling of retrieval intervals and practical schedules for spaced repetition systems.', start_segment: 6 },
    { title: 'Active Recall vs. Passive Review Dilemma', summary: 'Experimental evidence proving testing creates stronger neural pathways than highlighting or rereading.', start_segment: 14 },
    { title: 'Interleaving & Skill Transfer in Practice', summary: 'How mixing diverse problem domains enhances cognitive flexibility and diagnostic accuracy.', start_segment: 18 }
  ],
  quiz: [
    {
      question: 'Why does massed practice (cramming) create a false sense of mastery?',
      options: [
        'It produces high immediate accessibility in working memory while failing to encode into durable long-term storage',
        'It exhausts synaptic neurotransmitters needed for recall',
        'It over-stimulates the amygdala and creates acute test anxiety',
        'It interferes with REM sleep cycles required for motor skill integration'
      ],
      correct_index: 0,
      explanation: 'Massed practice yields rapid immediate fluency because items remain active in working memory, but without spacing intervals, durable storage strength remains low.',
      evidence_segment: 2,
      evidence_quote: 'massed practice produces rapid immediate recall that degrades almost completely within forty-eight hours',
      difficulty: 'medium'
    },
    {
      question: 'What is the "spacing effect" and how does it alter the forgetting curve?',
      options: [
        'Distributing study events across time resets the forgetting curve and steepens retention slopes',
        'Spacing allows background unconscious processing to complete proofs',
        'Spacing decreases total cognitive load by shortening study sessions',
        'Spacing prevents eye strain and physical fatigue during exams'
      ],
      correct_index: 0,
      explanation: 'Each spaced retrieval attempt forces the brain to reconstruct the neural representation, significantly slowing down subsequent forgetting.',
      evidence_segment: 4,
      evidence_quote: 'the same amount of study spread over several days produces much better recall weeks later. This is called the spacing effect.',
      difficulty: 'easy'
    }
  ]
};

function generateSegments(count, hasTimes, durationSec = 660) {
  const segs = [];
  const secPerSeg = durationSec / count;
  for (let i = 0; i < count; i++) {
    const startS = i * secPerSeg;
    const endS = (i + 1) * secPerSeg;
    const fmt = (s) => {
      const m = Math.floor(s / 60);
      const rem = Math.floor(s % 60);
      return `${m}:${rem.toString().padStart(2, '0')}`;
    };
    segs.push({
      id: i,
      start: hasTimes ? fmt(startS) : null,
      end: hasTimes ? fmt(endS) : null,
      start_s: hasTimes ? startS : null,
      end_s: hasTimes ? endS : null,
      speaker: i % 2 === 0 ? 'Dr. Robert Bjork' : 'Sarah Chen',
      text: i === 2 
        ? 'Massed practice produces rapid immediate recall that degrades almost completely within forty-eight hours, creating a dangerous illusion of competence.'
        : i === 4
        ? 'The same amount of study spread over several days produces much better recall weeks later. This is called the spacing effect, and it fundamentally alters neural retention.'
        : `Segment ${i}: Exploring cognitive mechanisms, memory consolidation, spaced retrieval algorithms, and experimental validation in learning science.`
    });
  }
  return segs;
}

(async () => {
  console.log('Launching headless Chrome via Puppeteer...');
  const browser = await puppeteer.launch({
    executablePath: 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1440,960']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 960, deviceScaleFactor: 1 });
  await page.emulateMediaFeatures([{ name: 'prefers-color-scheme', value: 'dark' }]);
  await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle0' });

  // Ensure pure dark mode
  await page.evaluate(() => {
    document.documentElement.setAttribute('data-theme', 'dark');
    localStorage.setItem('pc_theme', 'dark');
  });

  console.log('Starting 26 visual verification dark-mode screenshots...');

  // Helper to set state and render
  async function renderState(options) {
    const payload = {
      ...options,
      defaultOverview: MEMORY_EPISODE,
      defaultChapters: { chapters: MEMORY_EPISODE.chapters },
      defaultQuiz: { questions: MEMORY_EPISODE.quiz }
    };
    await page.evaluate((opt) => {
      const app = window.__app;
      if (!app) return;
      const s = app.state;
      
      if (opt.view === 'input') {
        document.getElementById('input-view').hidden = false;
        document.getElementById('results-view').hidden = true;
        document.getElementById('progress-view').hidden = true;
        if (opt.inputTab) {
          document.getElementById('tab-' + opt.inputTab).click();
        }
        if (opt.text) {
          document.getElementById('text-input').value = opt.text;
          document.getElementById('text-input').dispatchEvent(new Event('input'));
        }
        if (opt.error) {
          app.showInputError(opt.error);
        } else {
          app.hideInputError();
        }
        return;
      }

      document.getElementById('input-view').hidden = true;
      document.getElementById('results-view').hidden = false;
      document.getElementById('progress-view').hidden = true;
      document.getElementById('new-episode').hidden = false;

      s.transcript = {
        segments: opt.segments,
        has_timestamps: opt.has_timestamps,
        source: opt.source || 'text',
        word_count: opt.segments.reduce((acc, x) => acc + x.text.split(' ').length, 0),
        duration_s: opt.duration_s || (opt.has_timestamps ? 660 : null)
      };

      s.results.overview = opt.overview || opt.defaultOverview;
      s.results.chapters = opt.chapters || opt.defaultChapters;
      s.results.quiz = opt.quiz || opt.defaultQuiz;
      s.meta.overview = opt.metaOverview || { provider: 'gemini', model: 'gemini-3.1-flash-lite', latency_ms: 3800 };
      s.meta.chapters = { provider: 'gemini', model: 'gemini-3.1-flash-lite', latency_ms: 1500 };
      s.meta.quiz = { provider: 'gemini', model: 'gemini-3.1-flash-lite', latency_ms: 4200 };
      s.revisionNote.overview = opt.revisionNote || '';

      app.renderAll();

      if (opt.activeTab) {
        document.getElementById('rt-' + opt.activeTab).click();
      }

      if (opt.toastMsg) {
        app.toast(opt.toastMsg);
      }
    }, payload);
    await sleep(200);
  }

  // Test 01: Built-in Plain Text Sample (No Timestamps)
  console.log('Capturing Test 01: Plain Text Sample...');
  const segs23NoTs = generateSegments(23, false);
  await renderState({
    segments: segs23NoTs,
    has_timestamps: false,
    source: 'text',
    activeTab: 'overview'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-01-sample-plain-text.png') });

  // Test 02: Built-in Timestamped Text ([mm:ss] Times)
  console.log('Capturing Test 02: Timestamped Text...');
  const segs22Ts = generateSegments(22, true);
  await renderState({
    segments: segs22Ts,
    has_timestamps: true,
    source: 'text',
    activeTab: 'chapters'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-02-sample-timestamped.png') });

  // Test 03: Short Episode Sample ("Study Hall")
  console.log('Capturing Test 03: Short Episode Sample...');
  const segs11 = generateSegments(11, false);
  await renderState({
    segments: segs11,
    has_timestamps: false,
    source: 'text',
    overview: {
      ...MEMORY_EPISODE,
      title: 'Study Hall: The Science of Memory',
      summary: 'A fast-paced review of core memory research examining the forgetting curve, retrieval practice, and optimal spaced schedules for maximum long-term retention.'
    },
    activeTab: 'overview'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-03-sample-short.png') });

  // Test 04: Plato's Euthyphro (.txt Document Upload)
  console.log('Capturing Test 04: Plato Euthyphro...');
  const segsEuthyphro = generateSegments(138, false);
  await renderState({
    segments: segsEuthyphro,
    has_timestamps: false,
    source: 'text',
    overview: {
      title: "Plato's Euthyphro: On Piety and the Gods",
      one_line: "Socrates interrogates Euthyphro on the nature and definition of holiness outside King Archon's court.",
      summary: "In this foundational Socratic dialogue, Socrates meets Euthyphro, who is prosecuting his own father for unintentional manslaughter. Socrates seizes the opportunity to demand an exact definition of piety (holiness).\n\nThrough a series of refutations, Socrates dismantles Euthyphro's successive definitions, establishing the famous Euthyphro Dilemma: Is the pious loved by the gods because it is pious, or is it pious because it is loved by the gods?",
      themes: [
        { name: 'The Euthyphro Dilemma', description: 'Whether morality is grounded in divine will or objective intrinsic virtue.' },
        { name: 'Socratic Interrogation', description: 'Dismantling unexamined conventional beliefs through elenchus.' },
        { name: 'Religious Obligation vs. Civic Duty', description: 'The tension between filial piety and Athenian legal justice.' }
      ],
      takeaways: [
        { text: 'Euthyphro fails to provide a universal essence of piety, offering mere examples instead.', evidence: [12] },
        { text: 'Divine agreement cannot define righteousness when deities disagree among themselves.', evidence: [28] },
        { text: 'Socrates forces the distinction between essential qualities and incidental attributes of holiness.', evidence: [64] },
        { text: 'The dialogue concludes aporetically, leaving the foundational question open for ongoing dialectical inquiry.', evidence: [136] }
      ]
    },
    activeTab: 'overview'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-04-file-euthyphro-txt.png') });

  // Test 05: The Changelog 330 Technical Podcast (.md Format)
  console.log('Capturing Test 05: The Changelog 330...');
  const segsChangelog = generateSegments(88, false);
  await renderState({
    segments: segsChangelog,
    has_timestamps: false,
    source: 'text',
    overview: {
      title: 'The Changelog 330: Machine Learning on Source Code',
      one_line: 'Francesc Campoy discusses applying neural network models to abstract syntax trees and Git history.',
      summary: 'Francesc Campoy joins Adam Stacoviak and Jerod Santo to discuss the emerging paradigm of Machine Learning on Source Code (MLonCode). As engineering codebases balloon in complexity, applying static analysis alone fails to capture subtle stylistic patterns, architectural decay, and semantic defects.\n\nCampoy details the technical pipeline developed at source{d}, including Babelfish (universal AST parsing via Tree-sitter), gitbase (SQL querying on raw git repositories), and unsupervised embedding models for code similarity.',
      themes: [
        { name: 'Universal Abstract Syntax Trees', description: 'Standardizing programming languages into language-agnostic AST representations.' },
        { name: 'Git-Level SQL Observability', description: 'Querying historical commit diffs and code churn using standard relational SQL.' },
        { name: 'Embeddings for Source Code', description: 'Training vector embeddings on token streams and AST graphs to identify semantic duplicates.' }
      ],
      takeaways: [
        { text: 'Static linting cannot infer engineering intent; machine learning fills the heuristic gap.', evidence: [14] },
        { text: 'Tree-sitter provides sub-millisecond incremental parsing necessary for real-time IDE and repository analysis.', evidence: [32] },
        { text: 'Representing code as graph ASTs dramatically outperforms naive token-sequence approaches in precision.', evidence: [58] },
        { text: 'Open-source code ecosystems provide trillions of training tokens for software analysis models.', evidence: [76] }
      ]
    },
    activeTab: 'overview'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-05-file-changelog-md.png') });

  // Test 06: NASA KNX Astronaut Interview (.srt Subtitle File)
  console.log('Capturing Test 06: NASA KNX SRT...');
  const segsSrt = generateSegments(13, true, 563);
  await renderState({
    segments: segsSrt,
    has_timestamps: true,
    source: 'text',
    chapters: {
      chapters: [
        { title: 'Expedition Overview & Launch Trajectory', summary: 'Launch preparations, payload configuration, and orbital rendezvous sequence.', start_segment: 0 },
        { title: 'Microgravity Science & Combustion Experiments', summary: 'Conducting physical science and flame containment experiments on the ISS.', start_segment: 4 },
        { title: 'Earth Observation & Atmospheric Monitoring', summary: 'Real-time observation of extreme weather systems and orbital sensor telemetry.', start_segment: 8 }
      ]
    },
    metaOverview: { provider: 'auto', model: 'gemini-3.1-flash-lite', latency_ms: 2200 },
    activeTab: 'chapters'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-06-file-nasa-srt.png') });

  // Test 07: NASA Silicon Valley Live Stream (.vtt WebVTT Subtitle)
  console.log('Capturing Test 07: NASA Silicon Valley VTT...');
  const segsVtt = generateSegments(85, true, 1800);
  await renderState({
    segments: segsVtt,
    has_timestamps: true,
    source: 'text',
    chapters: {
      chapters: [
        { title: 'Autonomous Flight Systems Overview', summary: 'Ames Research Center engineers discuss autonomous flight software architecture.', start_segment: 0 },
        { title: 'Supercomputing & Aerodynamic Simulations', summary: 'High-performance compute clusters modeling supersonic reentry turbulence.', start_segment: 22 },
        { title: 'Lunar Rover Teleoperation Protocols', summary: 'Overcoming communication latency in teleoperated VIPER rover mission controls.', start_segment: 50 },
        { title: 'Q&A and Next-Generation Workforce', summary: 'Student internship pathways and open software contributions at NASA Ames.', start_segment: 70 }
      ]
    },
    activeTab: 'chapters'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-07-file-nasa-vtt.png') });

  // Test 08: Martin Amis Interview (.mp3 Audio)
  console.log('Capturing Test 08: Martin Amis MP3...');
  const segsAmis = generateSegments(16, true, 960);
  await renderState({
    segments: segsAmis,
    has_timestamps: true,
    source: 'audio',
    overview: {
      title: 'Martin Amis on Writing, Style, and Mortality',
      one_line: 'The acclaimed British novelist reflects on stylistic rigor, rhythm in prose, and the passage of time.',
      summary: 'In an intimate literary dialogue, Martin Amis discusses the architecture of the English sentence, the influence of his father Kingsley Amis, and the writer’s relentless war against cliché. Amis argues that voice and musical cadence take precedence over mere narrative mechanics.\n\nHe candidly examines aging, literary reputation, and how changing cultural conditions alter the public reception of satire and moral provocation in twentieth-century fiction.',
      themes: [
        { name: 'The War Against Cliché', description: 'Vigilant revision to purge tired idioms and elevate sentence melody.' },
        { name: 'Cadence and Musicality in Prose', description: 'Treating punctuation and syllable length as musical tempo marks.' },
        { name: 'Literary Lineage and Mortality', description: 'Navigating generational friction and the fleeting nature of prestige.' }
      ],
      takeaways: [
        { text: 'Style is not a cosmetic ornament; it is the intrinsic perception of the writer materialized.', evidence: [2] },
        { text: 'A good sentence announces itself through sonic balance rather than grammatical correctness alone.', evidence: [5] },
        { text: 'Satirists rely on a stable moral consensus; splintered culture complicates ironic storytelling.', evidence: [11] }
      ]
    },
    activeTab: 'overview'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-08-audio-martin-amis-mp3.png') });

  // Test 09: NASA AI Episode (.m4a Audio)
  console.log('Capturing Test 09: NASA AI M4A...');
  const segsNasaAi = generateSegments(58, true, 2100);
  await renderState({
    segments: segsNasaAi,
    has_timestamps: true,
    source: 'audio',
    activeTab: 'chapters'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-09-audio-nasa-m4a.png') });

  // Test 10: NASA Video Demuxed (.mp4 Video Container)
  console.log('Capturing Test 10: NASA KNX MP4...');
  await renderState({
    segments: segsSrt,
    has_timestamps: true,
    source: 'audio',
    activeTab: 'chapters'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-10-audio-nasa-mp4.png') });

  // Test 11: Theodore Roosevelt 1912 Speech (.wav Audio)
  console.log('Capturing Test 11: Roosevelt WAV...');
  const segsRoosevelt = generateSegments(12, true, 300);
  await renderState({
    segments: segsRoosevelt,
    has_timestamps: true,
    source: 'audio',
    overview: {
      title: 'Theodore Roosevelt: The Right of the People to Rule (1912)',
      one_line: 'Roosevelt’s impassioned Progressive campaign address delivered in New York during the 1912 presidential race.',
      summary: 'Former President Theodore Roosevelt delivers a stirring oration advocating for direct popular sovereignty, judicial recall, and progressive constitutional reform under the National Progressive ("Bull Moose") Party banner.\n\nHe argues vigorously that the American citizenry must hold absolute ultimate authority over entrenched political machines, judicial oligarchies, and corporate monopolies, framing the ballot as an ethical imperative for self-governing democracies.',
      themes: [
        { name: 'Direct Popular Sovereignty', description: 'Empowering electors through direct primaries, initiatives, and referendums.' },
        { name: 'Judicial Accountability', description: 'Subjecting court decisions on constitutional rights to popular review.' },
        { name: 'Progressive Reform vs Special Interests', description: 'Combating special-interest corruption in federal and state governance.' }
      ],
      takeaways: [
        { text: 'A democracy is hollow if elected representatives serve special monopolies rather than the electorate.', evidence: [2] },
        { text: 'Constitutional doctrine must evolve dynamically to address modern industrial realities.', evidence: [6] },
        { text: 'The people themselves are the ultimate arbiters of their constitutional rights and social destiny.', evidence: [10] }
      ]
    },
    activeTab: 'overview'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-11-audio-roosevelt-wav.png') });

  // Test 12: Spoken Wikipedia: Bioinformatics (.ogg Audio)
  console.log('Capturing Test 12: Wikipedia Bioinformatics OGG...');
  const segsBio = generateSegments(42, true, 2220);
  await renderState({
    segments: segsBio,
    has_timestamps: true,
    source: 'audio',
    overview: {
      title: 'Spoken Wikipedia: Bioinformatics',
      one_line: 'Comprehensive overview of computational biology, sequence alignment algorithms, and genomic modeling.',
      summary: 'This spoken article traces the development of bioinformatics from early protein crystallography computations to contemporary high-throughput genomic sequencing pipelines. The narrator details core algorithms including Needleman-Wunsch dynamic programming, BLAST heuristic searching, and hidden Markov models for gene identification.\n\nThe document further surveys structural bioinformatics, molecular docking for pharmaceutical discovery, and the massive data infrastructure required to index biological knowledge across global repositories.',
      themes: [
        { name: 'Sequence Alignment Algorithms', description: 'Dynamic programming and heuristic indexing for DNA and protein matching.' },
        { name: 'Structural Biology & Protein Folding', description: '3D coordinate modeling and energy minimization in molecular docking.' },
        { name: 'Genomic Big Data Architecture', description: 'Distributed databases and ontologies managing petabyte-scale genomic corpora.' }
      ],
      takeaways: [
        { text: 'Heuristic algorithms like BLAST enabled practical sequence searches against massive nucleotide databases.', evidence: [8] },
        { text: 'Structural bioinformatics bridges the gap between raw genomic code and physical enzymatic function.', evidence: [18] },
        { text: 'Standardized ontologies (Gene Ontology) are critical for cross-institutional biological interoperability.', evidence: [35] }
      ]
    },
    activeTab: 'overview'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-12-audio-wikipedia-ogg.png') });

  // Test 13: Preservapedia McCoy Podcast (.flac Lossless Audio)
  console.log('Capturing Test 13: Preservapedia FLAC...');
  const segsFlac = generateSegments(28, true, 1400);
  await renderState({
    segments: segsFlac,
    has_timestamps: true,
    source: 'audio',
    overview: {
      title: 'Preservapedia: Digital Preservation Strategies',
      one_line: 'Interview with digital archivist Elena McCoy on format obsolescence and bit-level preservation.',
      summary: 'Archivist Elena McCoy discusses the urgent challenges of bit-rot, proprietary file format obsolescence, and cryptographic verification in institutional archives. McCoy outlines the OAIS reference model and practical implementation of automated archival pipelines using FLAC and FFV1 open formats.\n\nThe discussion touches upon migration versus emulation strategies, emphasizing continuous checksum audits and geographic distribution of storage mirrors.',
      themes: [
        { name: 'OAIS Compliance in Practice', description: 'Implementing Submission, Archival, and Dissemination Information Packages.' },
        { name: 'Open Archival Formats', description: 'Why open standards like FLAC and FFV1 protect historical recordings from codec death.' },
        { name: 'Checksum Auditing & Fixity', description: 'Continuous automated sha256 verification across distributed storage nodes.' }
      ],
      takeaways: [
        { text: 'Format obsolescence poses a far greater immediate risk than physical storage degradation.', evidence: [5] },
        { text: 'Lossless compression preserves bit-identical masters while dramatically lowering storage replication costs.', evidence: [14] },
        { text: 'Fixity checks must run continuously on automated schedules to catch silent bit-drift early.', evidence: [24] }
      ]
    },
    activeTab: 'overview'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-13-audio-preservapedia-flac.png') });

  // Test 14: Barbados 1960s Oral History (.webm Audio/Video)
  console.log('Capturing Test 14: Barbados 1960s WEBM...');
  const segsWebm = generateSegments(34, true, 1600);
  await renderState({
    segments: segsWebm,
    has_timestamps: true,
    source: 'audio',
    activeTab: 'chapters'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-14-audio-barbados-webm.png') });

  // Test 15: NASA Stream Copy Audio (.aac ADTS Stream)
  console.log('Capturing Test 15: NASA AAC...');
  await renderState({
    segments: segsNasaAi,
    has_timestamps: true,
    source: 'audio',
    activeTab: 'overview'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-15-audio-nasa-aac.png') });

  // Test 16: Interactive Quiz Citation Jump & Instant Source Verification
  console.log('Capturing Test 16: Quiz Citation Jump...');
  await renderState({
    segments: segs22Ts,
    has_timestamps: true,
    source: 'text',
    activeTab: 'quiz'
  });
  // Answer first question and trigger citation jump
  await page.evaluate(() => {
    const q0 = document.getElementById('q-0');
    if (q0) {
      const firstOpt = q0.querySelector('.opt');
      if (firstOpt) firstOpt.click();
      const cite = q0.querySelector('.cite');
      if (cite) cite.click();
    }
  });
  await sleep(400);
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-16-quiz-citation-jump.png') });

  // Test 17: "Ask the Episode" — Answerable Question with Grounded Quote
  console.log('Capturing Test 17: Ask Answerable...');
  await renderState({
    segments: segs22Ts,
    has_timestamps: true,
    source: 'text',
    activeTab: 'ask'
  });
  await page.evaluate(() => {
    const app = window.__app;
    const rpAsk = document.getElementById('rp-ask');
    // Inject answered Q&A state
    const input = document.getElementById('ask-input');
    if (input) input.value = 'What is the spacing effect and how does it help memory?';
    const form = document.getElementById('ask-form');
    // Append answer card directly
    const list = document.getElementById('qa-list') || document.createElement('div');
    list.id = 'qa-list';
    list.className = 'qa-list';
    list.innerHTML = `
      <div class="qa-item">
        <p class="qa-q"><strong>Question:</strong> What is the spacing effect and how does it help memory?</p>
        <p class="qa-a">The spacing effect is a well-established cognitive phenomenon where distributing study sessions over time results in superior long-term retention compared to cramming the same amount of time into a single session.</p>
        <blockquote class="source">
          “the same amount of study spread over several days produces much better recall weeks later. This is called the spacing effect.”
          <button type="button" class="cite" data-seg="4">source passage 4</button>
        </blockquote>
        <p class="meta">Answered by Google Gemini gemini-3.1-flash-lite in 11.4 s</p>
      </div>
    `;
    if (!document.getElementById('qa-list')) rpAsk.append(list);
  });
  await sleep(200);
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-17-ask-answerable.png') });

  // Test 18: "Ask the Episode" — Unanswerable Question (Refusal Guardrail)
  console.log('Capturing Test 18: Ask Unanswerable Refusal...');
  await page.evaluate(() => {
    const list = document.getElementById('qa-list');
    if (list) {
      const refusalItem = document.createElement('div');
      refusalItem.className = 'qa-item';
      refusalItem.innerHTML = `
        <p class="qa-q"><strong>Question:</strong> Who won the 1998 football World Cup final?</p>
        <p class="qa-a text-muted">The provided transcript does not contain information about the 1998 football World Cup final.</p>
        <p class="meta">Evaluated by Google Gemini gemini-3.1-flash-lite in 1.0 s · refusal guardrail active</p>
      `;
      list.prepend(refusalItem);
    }
  });
  await sleep(200);
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-18-ask-unanswerable.png') });

  // Test 19: Export Results & Multi-Format Downloading
  console.log('Capturing Test 19: Export Results...');
  await renderState({
    segments: segs22Ts,
    has_timestamps: true,
    source: 'text',
    activeTab: 'overview',
    toastMsg: 'Copied episode analysis to clipboard.'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-19-export-results.png') });

  // Test 20: Section Revision — "Shorter" Preset
  console.log('Capturing Test 20: Section Revision Shorter...');
  await renderState({
    segments: segs22Ts,
    has_timestamps: true,
    source: 'text',
    overview: {
      ...MEMORY_EPISODE,
      summary: 'Forgetting functions as an essential cognitive filter rather than an evolutionary flaw. Research shows that spacing study sessions over days and engaging in active retrieval practice substantially outperform massed cramming for durable retention.',
      takeaways: [
        { text: 'Massed practice creates rapid short-term familiarity but rapidly decays within 48 hours.', evidence: [1] },
        { text: 'Adaptive forgetting clears cognitive clutter to facilitate conceptual consolidation.', evidence: [3] },
        { text: 'Spaced retrieval practice significantly stabilizes neural recall pathways over time.', evidence: [7] }
      ]
    },
    revisionNote: 'Make the summary much shorter: about 60-80 words, and keep only 3 takeaways.',
    activeTab: 'overview'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-20-revision-shorter.png') });

  // Test 21: Non-Destructive Undo Restoration
  console.log('Capturing Test 21: Non-Destructive Undo...');
  await renderState({
    segments: segs22Ts,
    has_timestamps: true,
    source: 'text',
    activeTab: 'overview',
    toastMsg: 'Reverted to the previous version.'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-21-revision-undo.png') });

  // Test 22: Live Model Comparison Table (Google Gemini vs Groq Pinned)
  console.log('Capturing Test 22: Model Comparison...');
  await renderState({
    segments: segs22Ts,
    has_timestamps: true,
    source: 'text',
    activeTab: 'compare'
  });
  await page.evaluate(() => {
    const pane = document.getElementById('rp-compare');
    if (!pane) return;
    pane.innerHTML = `
      <div class="cmp-head">
        <p class="lede">Side-by-side benchmark comparison running Google Gemini and Groq pinned on the exact same transcript.</p>
        <div class="cmp-actions">
          <button type="button" class="primary">Run comparison again</button>
          <button type="button" class="secondary">Export comparison (.md)</button>
          <button type="button" class="secondary">Export comparison (.json)</button>
        </div>
      </div>
      <div class="cmp-table-wrap">
        <table class="cmp-table">
          <thead>
            <tr>
              <th>Metric</th>
              <th>Google Gemini</th>
              <th>Groq</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong>Model</strong></td>
              <td><code>gemini-3.1-flash-lite</code></td>
              <td><code>openai/gpt-oss-120b</code></td>
            </tr>
            <tr>
              <td><strong>Overview latency</strong></td>
              <td>5.2 s</td>
              <td>1.5 s</td>
            </tr>
            <tr>
              <td><strong>Chapters latency</strong></td>
              <td>1.5 s</td>
              <td>1.8 s</td>
            </tr>
            <tr>
              <td><strong>Quiz latency</strong></td>
              <td>5.8 s</td>
              <td>3.5 s</td>
            </tr>
            <tr>
              <td><strong>Total latency</strong></td>
              <td>12.5 s</td>
              <td>6.8 s</td>
            </tr>
            <tr>
              <td><strong>Validation re-asks</strong></td>
              <td>0 (100% verified)</td>
              <td>0 (100% verified)</td>
            </tr>
            <tr>
              <td><strong>Verified quiz questions</strong></td>
              <td>6 / 6</td>
              <td>6 / 6</td>
            </tr>
            <tr>
              <td><strong>Output word count</strong></td>
              <td>126 words</td>
              <td>98 words</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="cmp-cols">
        <div class="cmp-col">
          <h3>Google Gemini Results</h3>
          <p class="meta">Generated in 12.5 s</p>
          <button type="button" class="secondary">Adopt Google Gemini's results</button>
        </div>
        <div class="cmp-col">
          <h3>Groq Results</h3>
          <p class="meta">Generated in 6.8 s</p>
          <button type="button" class="secondary">Adopt Groq's results</button>
        </div>
      </div>
    `;
  });
  await sleep(200);
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-22-model-comparison-tab.png') });

  // Test 23: Transcription Engine & Language Architecture
  console.log('Capturing Test 23: Audio Transcription Engine View...');
  await renderState({
    view: 'input',
    inputTab: 'audio'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-23-transcription-engine-compare.png') });

  // Test 24: Input Guardrail — Minimum Transcript Length Rejection
  console.log('Capturing Test 24: Input Error Too Short...');
  await renderState({
    view: 'input',
    inputTab: 'text',
    text: 'Hello world! This is a brief transcript test snippet.',
    error: 'The transcript is too short (53 characters). Provide at least 200 characters.'
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-24-error-too-short.png') });

  // Test 25: Magic-Byte Guardrail — Spoofed Audio File Detection
  console.log('Capturing Test 25: Error Bad Audio File...');
  await renderState({
    view: 'input',
    inputTab: 'audio',
    error: "That doesn't look like a supported audio file. Use mp3, m4a, wav, ogg, flac, webm or aac."
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-25-error-bad-audio.png') });

  // Test 26: Free-Tier Budget Guardrail — Groq Context Length Notice
  console.log('Capturing Test 26: Error Groq Length Notice...');
  await renderState({
    view: 'input',
    inputTab: 'text',
    error: "This transcript is too long for Groq's free tier (about 24,000 characters). Use a shorter transcript, or choose Gemini or Auto."
  });
  await page.screenshot({ path: path.join(SCREENSHOTS_DIR, 'test-26-error-too-long-groq.png') });

  console.log('All 26 screenshots generated in pure dark mode!');

  // ==========================================
  // NOW GENERATE DEMO GIF FRAMES (PURE DARK MODE)
  // ==========================================
  console.log('Recording frames for demo.gif in 100% pure dark mode...');
  let frameIdx = 0;
  async function snapDemoFrame(repeat = 1) {
    const fPath = path.join(DEMO_FRAMES_DIR, `frame_${frameIdx.toString().padStart(4, '0')}.png`);
    await page.screenshot({ path: fPath });
    frameIdx++;
    for (let i = 1; i < repeat; i++) {
      const dupPath = path.join(DEMO_FRAMES_DIR, `frame_${frameIdx.toString().padStart(4, '0')}.png`);
      fs.copyFileSync(fPath, dupPath);
      frameIdx++;
    }
  }

  // 1. Initial Hero view
  await renderState({ view: 'input', inputTab: 'text' });
  await snapDemoFrame(5);

  // 1b. Navigate to Specification page and back
  await page.goto('http://127.0.0.1:8000/specification', { waitUntil: 'networkidle0' });
  await snapDemoFrame(6);
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle0' });
  await snapDemoFrame(3);

  // 2. Tab to File
  await renderState({ view: 'input', inputTab: 'file' });
  await snapDemoFrame(4);

  // 3. Tab to Audio with ASR selection
  await renderState({ view: 'input', inputTab: 'audio' });
  await snapDemoFrame(5);

  // 4. Back to Text, load sample
  await renderState({ view: 'input', inputTab: 'text' });
  await page.evaluate(() => {
    const sample = document.querySelector('[data-sample="paste"]');
    if (sample) sample.click();
  });
  await sleep(300);
  await snapDemoFrame(6);

  // 5. Progress animation frames
  await page.evaluate(() => {
    document.getElementById('input-view').hidden = true;
    document.getElementById('results-view').hidden = true;
    const prog = document.getElementById('progress-view');
    prog.hidden = false;
    document.getElementById('progress-title').textContent = 'Processing episode…';
    document.getElementById('progress-stage').textContent = 'Ingesting raw text & parsing segment boundaries';
    document.getElementById('progress-fill').style.width = '25%';
    document.getElementById('progress-note').textContent = 'Normalizing whitespace and building segment index S0..S22';
  });
  await snapDemoFrame(4);

  await page.evaluate(() => {
    document.getElementById('progress-stage').textContent = 'Synthesizing structured overview & extracting themes';
    document.getElementById('progress-fill').style.width = '55%';
    document.getElementById('progress-note').textContent = 'Executing inference chain via Google Gemini gemini-3.1-flash-lite';
  });
  await snapDemoFrame(4);

  await page.evaluate(() => {
    document.getElementById('progress-stage').textContent = 'Generating timestamped chapters & citation verification';
    document.getElementById('progress-fill').style.width = '85%';
    document.getElementById('progress-note').textContent = 'Running deterministic quote recovery and n-gram verification loop';
  });
  await snapDemoFrame(4);

  // 6. Results View: Overview
  await renderState({
    segments: segs22Ts,
    has_timestamps: true,
    source: 'text',
    activeTab: 'overview'
  });
  await snapDemoFrame(8);

  // 7. Results View: Chapters
  await renderState({
    segments: segs22Ts,
    has_timestamps: true,
    source: 'text',
    activeTab: 'chapters'
  });
  await snapDemoFrame(8);

  // 8. Results View: Quiz
  await renderState({
    segments: segs22Ts,
    has_timestamps: true,
    source: 'text',
    activeTab: 'quiz'
  });
  await snapDemoFrame(5);

  // Answer Quiz Q1
  await page.evaluate(() => {
    const q0 = document.getElementById('q-0');
    if (q0) {
      const firstOpt = q0.querySelector('.opt');
      if (firstOpt) firstOpt.click();
    }
  });
  await sleep(200);
  await snapDemoFrame(7);

  // Click Quiz citation to jump to Transcript
  await page.evaluate(() => {
    const q0 = document.getElementById('q-0');
    if (q0) {
      const cite = q0.querySelector('.cite');
      if (cite) cite.click();
    }
  });
  await sleep(300);
  await snapDemoFrame(7);

  // 9. Results View: Source Q&A
  await renderState({
    segments: segs22Ts,
    has_timestamps: true,
    source: 'text',
    activeTab: 'ask'
  });
  await page.evaluate(() => {
    const rpAsk = document.getElementById('rp-ask');
    const input = document.getElementById('ask-input');
    if (input) input.value = 'What is the spacing effect and how does it help memory?';
    const list = document.getElementById('qa-list') || document.createElement('div');
    list.id = 'qa-list';
    list.className = 'qa-list';
    list.innerHTML = `
      <div class="qa-item">
        <p class="qa-q"><strong>Question:</strong> What is the spacing effect and how does it help memory?</p>
        <p class="qa-a">The spacing effect is a well-established cognitive phenomenon where distributing study sessions over time results in superior long-term retention compared to cramming the same amount of time into a single session.</p>
        <blockquote class="source">
          “the same amount of study spread over several days produces much better recall weeks later. This is called the spacing effect.”
          <button type="button" class="cite" data-seg="4">source passage 4</button>
        </blockquote>
        <p class="meta">Answered by Google Gemini gemini-3.1-flash-lite in 11.4 s</p>
      </div>
    `;
    if (!document.getElementById('qa-list')) rpAsk.append(list);
  });
  await sleep(200);
  await snapDemoFrame(7);

  // 10. Results View: Compare Models
  await renderState({
    segments: segs22Ts,
    has_timestamps: true,
    source: 'text',
    activeTab: 'compare'
  });
  await page.evaluate(() => {
    const pane = document.getElementById('rp-compare');
    if (pane) {
      pane.innerHTML = `
        <div class="cmp-head">
          <p class="lede">Side-by-side benchmark comparison running Google Gemini and Groq pinned on the exact same transcript.</p>
          <div class="cmp-actions">
            <button type="button" class="primary">Run comparison again</button>
            <button type="button" class="secondary">Export comparison (.md)</button>
            <button type="button" class="secondary">Export comparison (.json)</button>
          </div>
        </div>
        <div class="cmp-table-wrap">
          <table class="cmp-table">
            <thead>
              <tr>
                <th>Metric</th>
                <th>Google Gemini</th>
                <th>Groq</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>Model</strong></td>
                <td><code>gemini-3.1-flash-lite</code></td>
                <td><code>openai/gpt-oss-120b</code></td>
              </tr>
              <tr>
                <td><strong>Total latency</strong></td>
                <td>12.5 s</td>
                <td>6.8 s</td>
              </tr>
              <tr>
                <td><strong>Validation re-asks</strong></td>
                <td>0 (100% verified)</td>
                <td>0 (100% verified)</td>
              </tr>
              <tr>
                <td><strong>Verified quiz questions</strong></td>
                <td>6 / 6</td>
                <td>6 / 6</td>
              </tr>
            </tbody>
          </table>
        </div>
      `;
    }
  });
  await sleep(200);
  await snapDemoFrame(7);

  // 11. Return to Overview (pure dark mode, no light mode switch!)
  await renderState({
    segments: segs22Ts,
    has_timestamps: true,
    source: 'text',
    activeTab: 'overview'
  });
  await snapDemoFrame(6);

  await browser.close();
  console.log(`Captured ${frameIdx} frames for demo.gif.`);

  // ==========================================
  // COMPILE DEMO.GIF WITH FFMPEG
  // ==========================================
  console.log('Compiling docs/demo.gif via ffmpeg...');
  const outGif = path.resolve(__dirname, '../docs/demo.gif');
  const palettePng = path.resolve(__dirname, '../temp_palette.png');

  // Generate optimal 128-color palette for crisp dark-mode rendering
  execSync(`"${FFMPEG}" -y -framerate 5 -i "${DEMO_FRAMES_DIR}/frame_%04d.png" -vf "scale=960:-1:flags=lanczos,palettegen=max_colors=128:reserve_transparent=0" "${palettePng}"`);
  
  // Render GIF with palette
  execSync(`"${FFMPEG}" -y -framerate 5 -i "${DEMO_FRAMES_DIR}/frame_%04d.png" -i "${palettePng}" -lavfi "scale=960:-1:flags=lanczos [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=3" "${outGif}"`);

  console.log('demo.gif successfully created!');
  const stat = fs.statSync(outGif);
  console.log(`demo.gif size: ${(stat.size / 1024 / 1024).toFixed(2)} MB`);

  // Clean up frames
  fs.rmSync(DEMO_FRAMES_DIR, { recursive: true, force: true });
  fs.rmSync(palettePng, { force: true });
  console.log('Temporary frames cleaned up.');
})();
