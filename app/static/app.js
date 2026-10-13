/* Podcast Companion front end. Plain JS, no build step.
 * Security note: all model- and user-derived text is inserted with textContent / createTextNode
 * (via h()), never innerHTML, so generated content cannot inject markup. */
(() => {
  'use strict';

  // ------------------------------------------------------------------ tiny helpers
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

  function h(tag, attrs = {}, ...children) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === false || v == null) continue;
      if (k === 'class') el.className = v;
      else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
      else if (k === 'style') el.style.cssText = v; // CSSOM is allowed by our CSP; setAttribute('style') is not
      else if (k === 'text') el.textContent = v;
      else el.setAttribute(k, v === true ? '' : v);
    }
    for (const c of children.flat()) {
      if (c == null || c === false) continue;
      el.append(c.nodeType ? c : document.createTextNode(String(c)));
    }
    return el;
  }
  const clear = (el) => { while (el.firstChild) el.removeChild(el.firstChild); return el; };

  function fmtTime(sec) {
    if (sec == null) return '';
    sec = Math.max(0, Math.floor(sec));
    const hh = Math.floor(sec / 3600), mm = Math.floor((sec % 3600) / 60), ss = sec % 60;
    return hh ? `${hh}:${String(mm).padStart(2, '0')}:${String(ss).padStart(2, '0')}` : `${mm}:${String(ss).padStart(2, '0')}`;
  }

  let toastTimer;
  function toast(msg) {
    const t = $('#toast');
    t.textContent = msg; t.classList.add('show');
    clearTimeout(toastTimer); toastTimer = setTimeout(() => t.classList.remove('show'), 2200);
  }

  async function copyText(text) {
    try { await navigator.clipboard.writeText(text); toast('Copied to clipboard'); }
    catch {
      const ta = h('textarea', { 'aria-hidden': 'true', style: 'position:fixed;opacity:0' }); ta.value = text;
      document.body.append(ta); ta.select();
      try { document.execCommand('copy'); toast('Copied to clipboard'); } catch { toast('Copy failed. Select the text manually.'); }
      ta.remove();
    }
  }

  function download(filename, text, type) {
    const url = URL.createObjectURL(new Blob([text], { type }));
    const a = h('a', { href: url, download: filename }); document.body.append(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  // ------------------------------------------------------------------ API layer
  class ApiError extends Error {
    constructor(message, code, status, retryAfter) { super(message); this.code = code; this.status = status; this.retryAfter = retryAfter; }
  }

  async function api(path, { method = 'GET', body, form, timeoutMs = 120000 } = {}) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    try {
      const res = await fetch(path, {
        method, signal: ctrl.signal,
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : form,
      });
      const raw = await res.text();
      let data = null;
      try { data = JSON.parse(raw); } catch { /* non-JSON error page from a proxy */ }
      if (!res.ok) {
        const retry = Number(res.headers.get('Retry-After')) || null;
        throw new ApiError(data?.error?.message || `The server returned an error (${res.status}).`, data?.error?.code || 'http_error', res.status, retry);
      }
      if (data == null) throw new ApiError('The server sent an unreadable response.', 'bad_response', res.status);
      return data;
    } catch (e) {
      if (e instanceof ApiError) throw e;
      if (e.name === 'AbortError') throw new ApiError('The request took too long. Please try again.', 'timeout', 0);
      throw new ApiError('Could not reach the server. Check your connection and try again.', 'network', 0);
    } finally { clearTimeout(timer); }
  }

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

  // ------------------------------------------------------------------ state
  const SECTIONS = ['overview', 'chapters', 'quiz'];
  let chosenProvider = 'auto'; // set by the model picker
  const state = fresh();
  function fresh() {
    return {
      health: null, transcript: null, notes: [],
      results: { overview: null, chapters: null, quiz: null },
      meta: { overview: null, chapters: null, quiz: null },
      history: { overview: [], chapters: [], quiz: [] },
      revisionNote: { overview: '', chapters: '', quiz: '' },
      loading: { overview: false, chapters: false, quiz: false },
      errors: { overview: null, chapters: null, quiz: null },
      numQuestions: 6, answers: {}, qa: [], busyAsk: false, activeTab: 'overview',
      provider: currentProvider(),
      compare: { running: false, done: false, runs: {} },
    };
  }
  // Which AI provider the user picked on the input page ("auto" | "gemini" | "groq").
  function currentProvider() { return chosenProvider; }
  const PROVIDER_NAMES = { auto: 'Auto', gemini: 'Google Gemini', groq: 'Groq' };

  // Built-in sample inputs, one per supported format. All files live in /samples/ and contain the
  // same ~11-minute episode, so results can be compared across formats and across models.
  const SAMPLES = [
    { id: 'paste', chip: 'Plain transcript', group: 'Text', label: 'Pasted text (no timestamps)', file: 'episode.txt', mode: 'paste',
      desc: 'Plain transcript with speaker labels, pasted into the text box. Chapters show passage ranges, not times.' },
    { id: 'paste-ts', chip: 'With [mm:ss] times', group: 'Text', label: 'Pasted text with [mm:ss] timestamps', file: 'episode-timestamped.txt', mode: 'paste',
      desc: 'Plain text where each line starts with a [mm:ss] time. The app reads these as real timestamps.' },
    { id: 'txt', chip: '.txt', group: 'Text', label: 'Text file (.txt)', file: 'episode.txt', mode: 'file', mime: 'text/plain',
      desc: 'Uploads the transcript as a .txt file through the Transcript file tab.' },
    { id: 'md', chip: '.md', group: 'Text', label: 'Markdown file (.md)', file: 'episode.md', mode: 'file', mime: 'text/markdown',
      desc: 'Markdown with a title, headings and bold speaker names. Formatting is stripped before processing.' },
    { id: 'srt', chip: '.srt', group: 'Subtitles', label: 'SubRip subtitles (.srt)', file: 'episode.srt', mode: 'file', mime: 'application/x-subrip',
      desc: 'Subtitle file with real cue times. Chapters and citations get real timestamps.' },
    { id: 'vtt', chip: '.vtt', group: 'Subtitles', label: 'WebVTT subtitles (.vtt)', file: 'episode.vtt', mode: 'file', mime: 'text/vtt',
      desc: 'WebVTT captions with real cue times, the format used by web video players.' },
    { id: 'mp3', chip: '.mp3', group: 'Audio', label: 'MP3 audio (.mp3)', file: 'episode.mp3', mode: 'audio', mime: 'audio/mpeg', desc: 'Synthetic-voice recording of the episode, transcribed on the server.' },
    { id: 'm4a', chip: '.m4a', group: 'Audio', label: 'M4A / AAC-in-MP4 audio (.m4a)', file: 'episode.m4a', mode: 'audio', mime: 'audio/mp4', desc: 'Same recording in an MP4 container, as exported by phones and Apple apps.' },
    { id: 'mp4', chip: '.mp4', group: 'Audio', label: 'MP4 audio (.mp4)', file: 'episode.mp4', mode: 'audio', mime: 'audio/mp4', desc: 'AAC audio in an .mp4 container, the extension many video tools export.' },
    { id: 'wav', chip: '.wav', group: 'Audio', label: 'WAV audio (.wav)', file: 'episode.wav', mode: 'audio', mime: 'audio/wav', desc: 'Uncompressed recording (largest file, about 20 MB).' },
    { id: 'ogg', chip: '.ogg', group: 'Audio', label: 'Ogg Vorbis audio (.ogg)', file: 'episode.ogg', mode: 'audio', mime: 'audio/ogg', desc: 'Open-source Ogg Vorbis format.' },
    { id: 'flac', chip: '.flac', group: 'Audio', label: 'FLAC audio (.flac)', file: 'episode.flac', mode: 'audio', mime: 'audio/flac', desc: 'Lossless compressed audio.' },
    { id: 'webm', chip: '.webm', group: 'Audio', label: 'WebM / Opus audio (.webm)', file: 'episode.webm', mode: 'audio', mime: 'audio/webm', desc: 'The format browsers record in (MediaRecorder).' },
    { id: 'aac', chip: '.aac', group: 'Audio', label: 'Raw AAC audio (.aac)', file: 'episode.aac', mode: 'audio', mime: 'audio/aac', desc: 'AAC stream without a container (ADTS).' },
    { id: 'short', chip: 'Short episode (5 min)', group: 'Short sample', label: 'Short episode (pasted, ~5 min)', file: 'sample.txt', path: '/sample.txt', mode: 'paste',
      desc: 'The original short "Study Hall" episode about forgetting. Fast to process.' },
  ];
  const sampleUrl = (smp) => smp.path || `/samples/${smp.file}`;
  let inputMode = 'text';
  let pickedTextFile = null, pickedAudio = null;

  // ------------------------------------------------------------------ tabs (shared by input + results)
  function wireTabs(listEl, onChange) {
    const tabs = $$('[role="tab"]', listEl);
    const select = (tab, focus) => {
      tabs.forEach((t) => {
        const on = t === tab;
        t.setAttribute('aria-selected', on);
        t.tabIndex = on ? 0 : -1;
        const panel = document.getElementById(t.getAttribute('aria-controls'));
        if (panel) panel.hidden = !on;
      });
      if (focus) tab.focus();
      onChange(tab.id);
    };
    tabs.forEach((t, i) => {
      t.addEventListener('click', () => select(t));
      t.addEventListener('keydown', (e) => {
        const dir = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
        if (dir) { e.preventDefault(); select(tabs[(i + dir + tabs.length) % tabs.length], true); }
        if (e.key === 'Home') { e.preventDefault(); select(tabs[0], true); }
        if (e.key === 'End') { e.preventDefault(); select(tabs[tabs.length - 1], true); }
      });
    });
    return { select: (id) => select(document.getElementById(id)) };
  }

  // ------------------------------------------------------------------ startup / health
  async function init() {
    const wakeTimer = setTimeout(() => showBanner('Waking the server. Free hosting sleeps when idle, so the first request can take up to a minute.'), 2500);
    try {
      state.health = await api('/api/health', { timeoutMs: 90000 });
      clearTimeout(wakeTimer); hideBanner();
      applyHealth();
    } catch (e) {
      clearTimeout(wakeTimer);
      showBanner('The server is not responding right now. Reload in a moment.', true);
      $('#limits').textContent = '';
    }
  }
  function showBanner(msg, warn = false) { const b = $('#banner'); b.textContent = msg; b.className = 'banner' + (warn ? ' warn' : ''); b.hidden = false; }
  function hideBanner() { $('#banner').hidden = true; }

  function applyHealth() {
    const l = state.health.limits;
    $('#limits').textContent =
      `Text: paste it or upload ${l.text_formats.join(', ')} (${l.min_transcript_chars}–${l.max_transcript_chars.toLocaleString()} characters). ` +
      `Audio: ${l.audio_formats.join(', ')}, up to ${l.max_audio_mb} MB and ${l.max_audio_minutes} minutes. ` +
      'Only audio and subtitle files carry real timestamps; pasted plain text does not.';
    $('#audio-hint').textContent = `${l.audio_formats.join(', ')} · max ${l.max_audio_mb} MB · max ${l.max_audio_minutes} min`;
    applyModelOptions();
    if (!state.health.llm_ready) showBanner('No AI provider is configured on this server yet, so generation will not work.', true);
    if (!state.health.transcription_ready) {
      const tab = $('#tab-audio'); tab.disabled = true; tab.title = 'Audio transcription is not configured on this server.';
    }
  }

  function applyModelOptions() {
    for (const o of state.health.asr_options || []) {
      const opt = document.querySelector(`#asr-provider option[value="${o.id}"]`); if (opt) opt.disabled = !o.ready;
    }
    const ready = (id) => modelOptions().some((o) => o.id === id && o.ready);
    if (!ready(chosenProvider)) { const first = modelOptions().find((o) => o.ready); if (first) chosenProvider = first.id; }
    pickers.input.set(chosenProvider); pickers.results.set(chosenProvider);
    if (state.health.small_context_chars) {
      $('#model-hint').textContent = 'Choose one model to see only its output, or open Compare models after building to run Gemini and Groq side by side. ' +
        `Groq's free tier handles transcripts up to about ${state.health.small_context_chars.toLocaleString()} characters.`;
    }
  }

  // ------------------------------------------------------------------ model picker (styled like Claude's)
  const NICE_PROVIDER = { gemini: 'Gemini', groq: 'Groq', huggingface: 'Hugging Face' };
  function modelOptions() {
    const fromHealth = Object.fromEntries((state.health?.llm_options || []).map((o) => [o.id, o]));
    const known = (id) => fromHealth[id] || { id, ready: !state.health, models: [] };
    const auto = known('auto'), gem = known('gemini'), groq = known('groq');
    const chain = (auto.models || []).map((m) => m.split(':')[0]).filter((v, i, a) => a.indexOf(v) === i).map((p) => NICE_PROVIDER[p] || p);
    return [
      { id: 'auto', name: 'Auto', short: 'Auto', ready: auto.ready,
        desc: chain.length > 1 ? `Best available, switches automatically: ${chain.join(' → ')}` : 'Best available model, switches automatically if one is busy' },
      { id: 'gemini', name: 'Google Gemini', short: 'Gemini', ready: gem.ready,
        desc: gem.models?.length ? `${gem.models[0]} · handles long episodes` : 'Handles long episodes' },
      { id: 'groq', name: 'Groq', short: 'Groq', ready: groq.ready,
        desc: groq.models?.length ? `${groq.models[0]} · very fast` : 'Very fast; shorter transcripts' },
    ];
  }

  const SVG_NS = 'http://www.w3.org/2000/svg';
  function icon(path, cls) {
    const svgEl = document.createElementNS(SVG_NS, 'svg');
    svgEl.setAttribute('viewBox', '0 0 16 16'); svgEl.setAttribute('aria-hidden', 'true'); svgEl.setAttribute('class', cls);
    const pth = document.createElementNS(SVG_NS, 'path');
    pth.setAttribute('d', path); pth.setAttribute('fill', 'none'); pth.setAttribute('stroke', 'currentColor');
    pth.setAttribute('stroke-width', '1.6'); pth.setAttribute('stroke-linecap', 'round'); pth.setAttribute('stroke-linejoin', 'round');
    svgEl.append(pth); return svgEl;
  }
  const CHEVRON = 'M4 6l4 4 4-4', CHECK = 'M3.5 8.5l3 3 6-7';

  function makePicker(root, onSelect) {
    const id = root.id;
    const btn = h('button', { type: 'button', class: 'mp-trigger', id: `${id}-btn`, 'aria-haspopup': 'listbox', 'aria-expanded': 'false', 'aria-controls': `${id}-menu` });
    const menu = h('div', { class: 'mp-menu', id: `${id}-menu`, role: 'listbox', tabindex: '-1', 'aria-label': 'AI model' });
    menu.hidden = true;
    root.append(btn, menu);
    const api = { value: 'auto', set(v) { api.value = v; render(); }, open, close };

    function render() { renderButton(); renderMenu(); }
    function renderButton() {
      const opts = modelOptions();
      const cur = opts.find((o) => o.id === api.value) || opts[0];
      btn.setAttribute('aria-label', `AI model: ${cur.name}. Change model`);
      clear(btn).append(h('span', { class: 'mp-cap' }, 'Model'), h('span', { class: 'mp-cur' }, cur.name), icon(CHEVRON, 'mp-chev'));
    }
    function renderMenu() {
      const opts = modelOptions();
      clear(menu);
      menu.append(h('div', { class: 'mp-head', 'aria-hidden': 'true' }, 'AI model for the results'));
      for (const o of opts) {
        const sel = o.id === api.value;
        const item = h('div', { role: 'option', id: `${id}-opt-${o.id}`, class: `mp-item${sel ? ' sel' : ''}${o.ready ? '' : ' off'}`,
          'data-value': o.id, 'aria-selected': sel ? 'true' : 'false', 'aria-disabled': o.ready ? false : 'true', tabindex: '-1' },
        h('span', { class: 'mp-text' }, h('span', { class: 'mp-name' }, o.name), h('span', { class: 'mp-desc' }, o.ready ? o.desc : 'Not configured on this server (no API key)')),
        sel ? icon(CHECK, 'mp-check') : h('span', { class: 'mp-check-space' }));
        item.addEventListener('click', () => choose(o));
        menu.append(item);
      }
    }
    // Nudge the menu sideways so it never runs off a narrow (phone) screen.
    function keepOnScreen() {
      menu.style.left = ''; menu.style.right = '';
      const r = menu.getBoundingClientRect(), vw = document.documentElement.clientWidth, gap = 16;
      if (r.right > vw - gap) menu.style.left = `${Math.min(0, menu.offsetLeft - (r.right - (vw - gap)))}px`;
      else if (r.left < gap) { menu.style.left = `${menu.offsetLeft + (gap - r.left)}px`; menu.style.right = 'auto'; }
    }
    function enabledItems() { return [...menu.querySelectorAll('.mp-item:not(.off)')]; }
    function open() {
      if (!menu.hidden) return;
      Object.values(pickers).forEach((p) => p !== api && p.close(false));
      renderMenu(); menu.hidden = false; btn.setAttribute('aria-expanded', 'true'); root.classList.add('open');
      keepOnScreen();
      (menu.querySelector('.mp-item.sel:not(.off)') || enabledItems()[0] || menu).focus();
    }
    function close(focusBtn = true) {
      if (menu.hidden) return;
      menu.hidden = true; btn.setAttribute('aria-expanded', 'false'); root.classList.remove('open');
      if (focusBtn) btn.focus();
    }
    function choose(o) {
      if (!o.ready) return;
      const changed = o.id !== api.value;
      api.value = o.id; close(); render();
      if (changed) onSelect(o.id);
    }
    btn.addEventListener('click', () => (menu.hidden ? open() : close()));
    btn.addEventListener('keydown', (e) => { if (['ArrowDown', 'ArrowUp'].includes(e.key)) { e.preventDefault(); open(); } });
    menu.addEventListener('keydown', (e) => {
      const items = enabledItems(); const i = items.indexOf(document.activeElement);
      if (e.key === 'ArrowDown') { e.preventDefault(); (items[(i + 1) % items.length] || items[0]).focus(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); (items[(i - 1 + items.length) % items.length] || items[0]).focus(); }
      else if (e.key === 'Home') { e.preventDefault(); items[0]?.focus(); }
      else if (e.key === 'End') { e.preventDefault(); items[items.length - 1]?.focus(); }
      else if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault(); const o = modelOptions().find((x) => x.id === document.activeElement?.dataset?.value); if (o) choose(o);
      } else if (e.key === 'Escape') { e.preventDefault(); close(); }
      else if (e.key === 'Tab') close(false);
    });
    // composedPath() still includes the picker even if the clicked node was re-rendered away.
    document.addEventListener('click', (e) => { if (!e.composedPath().includes(root)) close(false); });
    render();
    return api;
  }

  const pickers = {};
  function wirePickers() {
    pickers.input = makePicker($('#model-input'), (v) => { chosenProvider = v; pickers.results.set(v); });
    pickers.results = makePicker($('#model-results'), (v) => {
      chosenProvider = v; state.provider = v; pickers.input.set(v);
      toast(`Regenerating with ${PROVIDER_NAMES[v]}…`);
      SECTIONS.forEach((sec) => { state.results[sec] = null; state.meta[sec] = null; state.history[sec] = []; state.revisionNote[sec] = ''; state.errors[sec] = null; });
      state.answers = {}; renderAll(); generateAll();
    });
  }

  // ------------------------------------------------------------------ samples
  // Every input tab gets a "Try a sample" row with one button per format it accepts.
  function wireSamples() {
    for (const row of $$('.sample-row')) {
      const mode = row.dataset.mode;
      const note = h('p', { class: 'sample-note', 'aria-live': 'polite' }, 'Each sample is the same 11-minute episode, so you can compare formats.');
      const chips = SAMPLES.filter((x) => x.mode === mode).map((smp) =>
        h('button', { type: 'button', class: 'chip sample-chip', 'data-sample': smp.id, title: smp.desc, onclick: (e) => loadSample(smp, e.currentTarget, note) }, smp.chip));
      row.append(h('div', { class: 'sample-chips' }, h('span', { class: 'label' }, 'Try a sample:'), chips), note);
    }
  }

  async function loadSample(smp, btn, note) {
    hideInputError();
    btn = btn || document.querySelector(`[data-sample="${smp.id}"]`); note = note || btn?.closest('.sample-row')?.querySelector('.sample-note');
    const label = btn ? btn.textContent : ''; if (btn) { btn.disabled = true; btn.textContent = 'Loading…'; }
    try {
      const res = await fetch(sampleUrl(smp)); if (!res.ok) throw new Error();
      if (smp.mode === 'paste') {
        const text = await res.text();
        $('#tab-text').click(); $('#text-input').value = text;
        $('#text-input').dispatchEvent(new Event('input'));
      } else {
        // Built from text/bytes rather than res.blob() so it also works in non-browser test DOMs.
        const body = smp.mode === 'file' ? await res.text() : new Uint8Array(await res.arrayBuffer());
        const file = new File([body], smp.file, { type: smp.mime || res.headers.get('content-type') || '' });
        if (smp.mode === 'file') {
          $('#tab-file').click(); setPickedTextFile(file);
        } else {
          if ($('#tab-audio').disabled) throw new Error('audio-off');
          $('#tab-audio').click(); setPickedAudio(file);
        }
      }
      $$('.sample-chip').forEach((c) => c.classList.toggle('on', c.dataset.sample === smp.id));
      if (note) {
        clear(note).append(h('strong', {}, `Loaded ${smp.file}. `), smp.desc, ' ',
          h('a', { href: sampleUrl(smp), download: smp.file, class: 'dl-link' }, `Download ${smp.file}`), ' to try uploading it yourself.');
      }
      toast(`Loaded ${smp.label}. Press “Build my companion”.`);
    } catch (e) {
      showInputError(e.message === 'audio-off' ? 'Audio transcription is not configured on this server, so audio samples cannot be used.' : 'Could not load that sample. Try another one or use your own file.');
    } finally { if (btn) { btn.disabled = false; btn.textContent = label; } }
  }
  function setPickedTextFile(file) {
    pickedTextFile = file;
    $('#file-name').textContent = file ? `${file.name} (${Math.max(1, Math.round(file.size / 1024))} KB)` : 'Choose a .txt, .md, .srt or .vtt file';
  }
  function setPickedAudio(file) {
    pickedAudio = file;
    $('#audio-name').textContent = file ? `${file.name} (${(file.size / 1048576).toFixed(1)} MB)` : 'Choose an audio file';
  }

  // ------------------------------------------------------------------ input view
  function wireInput() {
    const tabsApi = wireTabs($('#input-tabs'), (id) => { inputMode = { 'tab-text': 'text', 'tab-file': 'file', 'tab-audio': 'audio' }[id]; hideInputError(); });
    $('#text-input').addEventListener('input', (e) => { $('#char-count').textContent = `${e.target.value.length.toLocaleString()} characters`; });

    $('#file-input').addEventListener('change', (e) => setPickedTextFile(e.target.files[0] || null));
    $('#audio-input').addEventListener('change', (e) => setPickedAudio(e.target.files[0] || null));
    for (const id of ['file-drop', 'audio-drop']) {
      const zone = document.getElementById(id), input = zone.querySelector('input');
      ['dragenter', 'dragover'].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.add('over'); }));
      ['dragleave', 'drop'].forEach((ev) => zone.addEventListener(ev, (e) => { e.preventDefault(); zone.classList.remove('over'); }));
      zone.addEventListener('drop', (e) => {
        if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; input.dispatchEvent(new Event('change')); }
      });
    }
    wireSamples();
    $('#build').addEventListener('click', build);
    $('#new-episode').addEventListener('click', reset);
  }
  function showInputError(msg) { const e = $('#input-error'); e.textContent = msg; e.hidden = false; }
  function hideInputError() { $('#input-error').hidden = true; }

  function showView(name) {
    for (const v of ['input', 'progress', 'results']) document.getElementById(`${v}-view`).hidden = v !== name;
    $('#new-episode').hidden = name === 'input';
    window.scrollTo({ top: 0 });
  }
  function setProgress(title, stage, fraction, note = '') {
    $('#progress-title').textContent = title; $('#progress-stage').textContent = stage;
    $('#progress-fill').style.width = `${Math.round(Math.min(1, Math.max(0.04, fraction)) * 100)}%`;
    $('#progress-note').textContent = note;
  }

  function reset() {
    Object.assign(state, fresh(), { health: state.health });
    pickedTextFile = pickedAudio = null;
    $('#file-input').value = ''; $('#audio-input').value = '';
    $('#file-name').textContent = 'Choose a .txt, .md, .srt or .vtt file'; $('#audio-name').textContent = 'Choose an audio file';
    showView('input');
  }

  // ------------------------------------------------------------------ build pipeline
  function readFileAsText(file) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve(String(r.result)); r.onerror = () => reject(new Error('Could not read that file.'));
      r.readAsText(file);
    });
  }

  async function build() {
    hideInputError();
    const btn = $('#build'); btn.disabled = true;
    try {
      let transcript;
      if (inputMode === 'audio') transcript = await transcribeAudio();
      else transcript = await parseTextInput();
      if (!transcript) return;
      state.transcript = transcript;
      state.provider = currentProvider();
      showResults();
      generateAll();
    } catch (e) {
      showView('input');
      showInputError(e.message || 'Something went wrong. Please try again.');
    } finally { btn.disabled = false; }
  }

  async function parseTextInput() {
    let text, filename = null;
    if (inputMode === 'file') {
      if (!pickedTextFile) throw new Error('Choose a transcript file first.');
      if (!/\.(txt|md|srt|vtt)$/i.test(pickedTextFile.name)) throw new Error('Supported transcript files are .txt, .md, .srt and .vtt.');
      if (pickedTextFile.size > 2 * 1048576) throw new Error('That file is larger than 2 MB, which is more text than the app accepts.');
      text = await readFileAsText(pickedTextFile); filename = pickedTextFile.name;
    } else {
      text = $('#text-input').value;
      if (!text.trim()) throw new Error('Paste a transcript first, or load a sample episode.');
    }
    showView('progress'); setProgress('Reading your transcript', 'Splitting it into passages…', 0.3);
    return api('/api/transcript/parse', { method: 'POST', body: { text, filename } });
  }

  async function transcribeAudio() {
    if (!pickedAudio) throw new Error('Choose an audio file first.');
    const l = state.health?.limits;
    if (l && pickedAudio.size > l.max_audio_mb * 1048576) throw new Error(`That file is ${(pickedAudio.size / 1048576).toFixed(0)} MB; the limit is ${l.max_audio_mb} MB.`);
    const form = new FormData(); form.append('file', pickedAudio);
    const lang = $('#lang').value; if (lang) form.append('language', lang);
    form.append('asr_provider', $('#asr-provider').value || 'auto');
    showView('progress'); setProgress('Uploading your audio', `${pickedAudio.name}`, 0.08, 'Large files can take a while on a slow connection.');
    const { job_id } = await api('/api/transcribe', { method: 'POST', form, timeoutMs: 600000 });
    const started = Date.now();
    for (;;) {
      await sleep(1500);
      const job = await api(`/api/jobs/${encodeURIComponent(job_id)}`);
      if (job.status === 'error') throw new Error(job.error?.message || 'Transcription failed.');
      if (job.status === 'done') { state.notes = job.notes || []; if (state.notes.length) toast(state.notes[0]); return job.transcript; }
      const mins = Math.floor((Date.now() - started) / 60000);
      setProgress('Transcribing your audio', job.stage || 'Working…', job.progress || 0.1,
        job.status === 'queued' ? 'Another transcription is running; yours is next.' : (mins >= 2 ? 'Long recordings can take several minutes on free hosting.' : ''));
      if (Date.now() - started > 45 * 60000) throw new Error('Transcription is taking too long. Try a shorter recording.');
    }
  }

  // ------------------------------------------------------------------ results
  let resultTabs;
  function showResults() {
    showView('results');
    const t = state.transcript;
    $('#ep-title').textContent = 'Your episode'; $('#ep-line').textContent = '';
    const bits = [`${t.segments.length} passages`, t.source === 'audio' ? 'transcribed from audio' : 'from text',
      t.has_timestamps ? 'with real timestamps' : 'no timestamps'];
    $('#ep-meta').textContent = bits.join(' · ');
    if (!resultTabs) {
      resultTabs = wireTabs($('#result-tabs'), (id) => { state.activeTab = id.replace('rt-', ''); });
      $('#copy-all').addEventListener('click', () => copyText(fullMarkdown()));
      $('#dl-md').addEventListener('click', () => download('podcast-companion.md', fullMarkdown(), 'text/markdown'));
      $('#dl-json').addEventListener('click', () => download('podcast-companion.json', JSON.stringify(exportJson(), null, 2), 'application/json'));
    }
    pickers.results.set(state.provider);
    resultTabs.select('rt-overview');
    renderAll();
  }

  function renderAll() {
    renderHeader(); renderStrip(); renderOverview(); renderChapters(); renderQuiz(); renderAsk(); renderCompare(); renderTranscript();
  }

  function renderHeader() {
    const ov = state.results.overview;
    if (ov) { $('#ep-title').textContent = ov.title; $('#ep-line').textContent = ov.one_line; document.title = `${ov.title} · Podcast Companion`; }
    const m = state.meta.overview;
    const parts = [`${state.transcript.segments.length} passages`, state.transcript.source === 'audio' ? 'transcribed from audio' : 'from text',
      state.transcript.has_timestamps ? 'with real timestamps' : 'no timestamps'];
    if (m) parts.push(`written by ${providerLabel(m)} ${m.model}${m.fallback_used ? ' (backup model used)' : ''}`);
    else parts.push(`model: ${PROVIDER_NAMES[state.provider]}`);
    $('#ep-meta').textContent = parts.join(' · ');
  }

  // ---- chapter strip: the whole episode as one navigable bar
  function renderStrip() {
    const strip = clear($('#strip')); const cap = $('#strip-caption');
    const ch = state.results.chapters;
    if (!ch) {
      strip.className = 'strip empty'; strip.append(h('button', { type: 'button', tabindex: '-1', 'aria-hidden': 'true' }));
      cap.textContent = state.loading.chapters ? 'Finding chapters…' : (state.errors.chapters ? 'Chapters are unavailable. See the Chapters tab.' : 'Chapters will appear here.');
      return;
    }
    strip.className = 'strip';
    const total = state.transcript.segments.length;
    const defaultCap = state.transcript.has_timestamps ? 'Each block is a chapter. Select one to open it.' : 'Each block is a chapter, sized by how much of the transcript it covers. Select one to open it.';
    cap.textContent = defaultCap;
    ch.chapters.forEach((c, i) => {
      const span = c.end_segment - c.start_segment + 1;
      const label = `${i + 1}. ${c.title}${c.start_time != null ? ` (${fmtTime(c.start_time)})` : ''}`;
      const b = h('button', { type: 'button', role: 'listitem', 'aria-label': label, style: `flex-grow:${Math.max(1, span / total * 100)}`,
        onclick: () => { resultTabs.select('rt-chapters'); focusChapter(i); } });
      b.addEventListener('mouseenter', () => { cap.textContent = label; });
      b.addEventListener('focus', () => { cap.textContent = label; });
      b.addEventListener('mouseleave', () => { cap.textContent = defaultCap; });
      strip.append(b);
    });
  }
  function focusChapter(i) {
    const el = document.getElementById(`chapter-${i}`); if (!el) return;
    el.scrollIntoView({ block: 'center' }); el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 1800);
  }

  // ---- shared pieces
  function cite(segId) {
    const seg = state.transcript.segments[segId]; if (!seg) return null;
    const when = state.transcript.has_timestamps && seg.start != null ? fmtTime(seg.start) : `passage ${segId + 1}`;
    return h('button', { type: 'button', class: 'cite', 'aria-label': `Show source: ${when}`, onclick: () => jumpToSegment(segId) }, `source ${when}`);
  }

  function reviseBar(section, presets) {
    const bar = h('div', { class: 'section-tools' });
    bar.append(h('span', { class: 'label' }, 'Change this:'));
    for (const p of presets) bar.append(h('button', { type: 'button', class: 'chip', disabled: state.loading[section], onclick: () => revise(section, p.instruction, p) }, p.label));
    const input = h('input', { type: 'text', maxlength: '300', placeholder: 'Or describe a change…', 'aria-label': `Describe how to change the ${section}`, disabled: state.loading[section] });
    const apply = h('button', { type: 'button', class: 'secondary', disabled: state.loading[section], onclick: () => { if (input.value.trim()) revise(section, input.value.trim(), {}); } }, 'Apply');
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') apply.click(); });
    bar.append(h('div', { class: 'revise-row' }, input, apply));
    if (state.history[section].length) bar.append(h('button', { type: 'button', class: 'link', onclick: () => undo(section) }, 'Undo last change'));
    if (state.revisionNote[section]) bar.append(h('div', { class: 'revised-note' }, `Revised: “${state.revisionNote[section]}”. Only this section was regenerated.`));
    return bar;
  }

  function footerNote(section) {
    const m = state.meta[section]; if (!m) return null;
    const box = h('div');
    box.append(h('p', { class: 'note' }, `Generated by ${providerLabel(m)} ${m.model}${m.fallback_used ? ` after a backup model took over (${(m.skipped || []).join('; ') || 'primary unavailable'})` : ''}` +
      `${m.latency_ms ? ` in ${fmtMs(m.latency_ms)}` : ''}. AI can make mistakes; check the cited passages.`));
    for (const w of m.warnings || []) box.append(h('p', { class: 'note warn' }, w));
    return box;
  }

  function providerLabel(m) { return PROVIDER_NAMES[m.provider] || m.provider || ''; }
  function fmtMs(ms) { return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`; }

  function stateOrBody(section, render) {
    if (state.loading[section] && !state.results[section]) return h('div', { class: 'loading' }, h('span', { class: 'spinner' }), `Writing the ${section}…`);
    if (state.errors[section] && !state.results[section]) return failedBox(section);
    if (!state.results[section]) return h('div', { class: 'loading' }, 'Waiting to start…');
    return render(state.results[section]);
  }
  function failedBox(section) {
    const err = state.errors[section];
    return h('div', { class: 'failed' }, h('p', { class: 'error', role: 'alert' }, err.message),
      h('button', { type: 'button', class: 'secondary', onclick: () => loadSection(section) }, err.retryAfter ? `Try again (suggested wait ${err.retryAfter}s)` : 'Try again'));
  }
  function revisionFailure(section) {
    const err = state.errors[section];
    return err && state.results[section] ? h('p', { class: 'error', role: 'alert' }, `Couldn't apply that change: ${err.message} Your previous version is still shown.`) : null;
  }
  const panelWrap = (section) => (state.loading[section] && state.results[section] ? { 'aria-busy': 'true' } : {});

  // ---- overview
  const PRESETS = {
    overview: [
      { label: 'Shorter', instruction: 'Make the summary much shorter: about 60-80 words, and keep only 3 takeaways.' },
      { label: 'Simpler language', instruction: 'Explain it in simpler everyday language, as if to a teenager, with short sentences.' },
      { label: 'More detail', instruction: 'Make the summary more detailed, around 250-300 words, with more specifics from the episode.' },
      { label: 'Focus on actions', instruction: 'Emphasise practical, actionable advice mentioned in the episode.' },
    ],
    chapters: [
      { label: 'Fewer, broader chapters', instruction: 'Use fewer, broader chapters (merge related sections).' },
      { label: 'More granular', instruction: 'Split the episode into more, finer-grained chapters.' },
      { label: 'Shorter descriptions', instruction: 'Keep every chapter description to one short sentence.' },
    ],
    quiz: [
      { label: 'More challenging', instruction: 'Make the questions more challenging: test reasoning and connections, use closer distractors.' },
      { label: 'Easier', instruction: 'Make the questions easier and more direct, testing basic recall of key facts.' },
      { label: 'Add questions', instruction: 'Write more questions, covering parts of the episode not yet tested.', more: 3 },
    ],
  };

  function renderOverview() {
    const root = clear($('#rp-overview'));
    root.append(reviseBar('overview', PRESETS.overview));
    const body = h('div', { class: 'busy-dim', ...panelWrap('overview') });
    body.append(stateOrBody('overview', (ov) => {
      const wrap = h('div');
      wrap.append(h('div', { class: 'prose' }, ov.summary.split(/\n\s*\n/).map((p) => h('p', {}, p))));
      wrap.append(h('div', { class: 'cols' },
        h('section', {}, h('h3', {}, 'Main themes'),
          h('dl', { class: 'themes' }, ov.themes.flatMap((t) => [h('dt', {}, t.name), h('dd', {}, t.description)]))),
        h('section', {}, h('h3', {}, 'Key takeaways'),
          h('ul', { class: 'takeaways' }, ov.takeaways.map((t) => h('li', {}, t.text, ' ', t.evidence.map((id) => cite(id))))))));
      wrap.append(h('p', {}, h('button', { type: 'button', class: 'secondary', onclick: () => copyText(sectionMarkdown('overview')) }, 'Copy overview')));
      wrap.append(footerNote('overview'));
      return wrap;
    }));
    root.append(body); const rf = revisionFailure('overview'); if (rf) root.append(rf);
  }

  // ---- chapters
  function renderChapters() {
    const root = clear($('#rp-chapters'));
    root.append(reviseBar('chapters', PRESETS.chapters));
    const body = h('div', { class: 'busy-dim', ...panelWrap('chapters') });
    body.append(stateOrBody('chapters', (data) => {
      const wrap = h('div');
      if (!data.has_timestamps) wrap.append(h('p', { class: 'note' }, 'Pasted plain text has no timing information, so chapters point to positions in the transcript instead of timestamps. Upload audio or an .srt/.vtt file to get real times.'));
      const list = h('div', { class: 'chapters' });
      data.chapters.forEach((c, i) => {
        const when = c.start_time != null ? h('div', { class: 'when' }, fmtTime(c.start_time), h('small', {}, `to ${fmtTime(c.end_time)}`))
          : h('div', { class: 'when' }, `Part ${i + 1}`, h('small', {}, `passages ${c.start_segment + 1}–${c.end_segment + 1}`));
        list.append(h('article', { class: 'chapter', id: `chapter-${i}` }, when,
          h('div', {}, h('h3', {}, c.title), h('p', {}, c.summary),
            h('button', { type: 'button', class: 'cite', onclick: () => jumpToSegment(c.start_segment) }, 'open in transcript'))));
      });
      wrap.append(list);
      wrap.append(h('p', {}, h('button', { type: 'button', class: 'secondary', onclick: () => copyText(sectionMarkdown('chapters')) }, 'Copy chapters')));
      wrap.append(footerNote('chapters'));
      return wrap;
    }));
    root.append(body); const rf = revisionFailure('chapters'); if (rf) root.append(rf);
  }

  // ---- quiz
  function renderQuiz() {
    const root = clear($('#rp-quiz'));
    root.append(reviseBar('quiz', PRESETS.quiz));
    const body = h('div', { class: 'busy-dim', ...panelWrap('quiz') });
    body.append(stateOrBody('quiz', (data) => {
      const wrap = h('div');
      const answered = Object.keys(state.answers).length;
      const correct = Object.entries(state.answers).filter(([i, a]) => data.questions[i] && a === data.questions[i].correct_index).length;
      wrap.append(h('p', { class: 'quiz-score', 'aria-live': 'polite' },
        answered ? `Score: ${correct} of ${answered} answered (${data.questions.length} questions)` : `${data.questions.length} questions. Choose an answer to see if you're right.`,
        answered ? ' ' : null, answered ? h('button', { type: 'button', class: 'link', onclick: () => { state.answers = {}; renderQuiz(); } }, 'Reset answers') : null));
      data.questions.forEach((q, qi) => wrap.append(questionEl(q, qi)));
      wrap.append(h('p', {}, h('button', { type: 'button', class: 'secondary', onclick: () => copyText(sectionMarkdown('quiz')) }, 'Copy quiz with answers')));
      wrap.append(footerNote('quiz'));
      return wrap;
    }));
    root.append(body); const rf = revisionFailure('quiz'); if (rf) root.append(rf);
  }

  function questionEl(q, qi) {
    const chosen = state.answers[qi]; const done = chosen !== undefined;
    const fs = h('fieldset', { class: 'q' }, h('legend', {}, h('span', { class: 'qn' }, `${qi + 1}.`), q.question));
    const opts = h('div', { class: 'opts', role: 'group' });
    q.options.forEach((o, oi) => {
      const cls = ['opt']; if (done && oi === q.correct_index) cls.push('right'); if (done && oi === chosen && oi !== q.correct_index) cls.push('wrong');
      opts.append(h('button', { type: 'button', class: cls.join(' '), disabled: done, 'aria-pressed': done && oi === chosen ? 'true' : 'false',
        onclick: () => { state.answers[qi] = oi; renderQuiz(); const el = document.getElementById(`q-${qi}`); if (el) el.scrollIntoView({ block: 'nearest' }); } },
        done && oi === q.correct_index ? 'Correct answer: ' : (done && oi === chosen ? 'Your answer: ' : ''), o));
    });
    fs.id = `q-${qi}`; fs.append(opts);
    if (done) {
      const ok = chosen === q.correct_index;
      fs.append(h('p', { class: `verdict ${ok ? 'right' : 'wrong'}`, role: 'status' }, ok ? 'Correct.' : 'Not quite.'));
      if (q.explanation) fs.append(h('p', { class: 'explain' }, q.explanation));
      if (q.evidence_quote) {
        fs.append(h('blockquote', { class: 'source' }, `“${q.evidence_quote}”`,
          q.evidence_segment != null ? [' ', cite(q.evidence_segment)] : null));
      }
    }
    return fs;
  }

  // ---- ask
  function renderAsk() {
    const root = clear($('#rp-ask'));
    root.append(h('p', { class: 'note', style: 'margin-top:0' }, 'Ask anything about this episode. Answers must quote the transcript; if the episode does not cover it, you will be told so.'));
    const input = h('input', { type: 'text', maxlength: '300', placeholder: 'e.g. What does the episode say about sleep?', 'aria-label': 'Question about the episode', disabled: state.busyAsk });
    const btn = h('button', { type: 'button', class: 'primary', disabled: state.busyAsk, onclick: () => ask(input.value) }, state.busyAsk ? 'Thinking…' : 'Ask');
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') btn.click(); });
    root.append(h('div', { class: 'ask-form' }, input, btn));
    for (const item of state.qa) {
      const box = h('div', { class: 'qa' }, h('p', { class: 'question' }, item.question));
      if (item.error) box.append(h('p', { class: 'error', role: 'alert' }, item.error));
      else {
        box.append(h('p', { class: `answer${item.result.answerable ? '' : ' none'}` }, item.result.answer));
        if (item.meta) box.append(h('p', { class: 'note', style: 'margin-top:0' }, `Answered by ${providerLabel(item.meta)} ${item.meta.model}${item.meta.latency_ms ? ` in ${fmtMs(item.meta.latency_ms)}` : ''}`));
        for (const e of item.result.evidence || []) box.append(h('blockquote', { class: 'source' }, `“${e.quote}”`, ' ', cite(e.segment)));
      }
      root.append(box);
    }
  }
  async function ask(question) {
    question = question.trim(); if (question.length < 3 || state.busyAsk) return;
    const episode = state.transcript;
    state.busyAsk = true; renderAsk();
    try {
      const res = await api('/api/ask', { method: 'POST', body: { transcript: payloadTranscript(), question, provider: state.provider } });
      state.qa.unshift({ question, result: res.result, meta: res.meta });
    } catch (e) { state.qa.unshift({ question, error: e.message }); }
    if (state.transcript !== episode) return;
    state.busyAsk = false; renderAsk();
    const inp = $('#rp-ask input'); if (inp) inp.focus();
  }

  // ---- compare models: same transcript, same prompts, each provider pinned (no cross-fallback)
  const COMPARE_PROVIDERS = ['gemini', 'groq'];
  function providerReady(p) { return (state.health?.llm_options || []).some((o) => o.id === p && o.ready); }

  async function runCompare() {
    const c = state.compare; if (c.running) return;
    const episode = state.transcript;
    c.running = true; c.done = false; c.runs = {};
    for (const p of COMPARE_PROVIDERS) c.runs[p] = { overview: { loading: true }, chapters: { loading: true }, quiz: { loading: true } };
    renderCompare();
    const jobs = [];
    COMPARE_PROVIDERS.forEach((p, pi) => SECTIONS.forEach((section, si) => {
      jobs.push((async () => {
        await sleep((pi * 3 + si) * 400); // stagger: free tiers have small per-minute limits
        if (state.transcript !== episode) return;
        const slot = c.runs[p][section];
        if (!providerReady(p)) { Object.assign(slot, { loading: false, error: `${PROVIDER_NAMES[p]} isn't configured on this server.` }); renderCompare(); return; }
        const started = performance.now();
        try {
          const res = await api('/api/generate', { method: 'POST', body: { transcript: payloadTranscript(), section, options: { num_questions: 6 }, provider: p } });
          Object.assign(slot, { loading: false, result: res.result, meta: res.meta, wall_ms: Math.round(performance.now() - started) });
        } catch (e) { Object.assign(slot, { loading: false, error: e.message }); }
        if (state.transcript === episode) renderCompare();
      })());
    }));
    await Promise.all(jobs);
    if (state.transcript !== episode) return;
    c.running = false; c.done = true; renderCompare();
  }

  function compareMetrics(run) {
    const ov = run.overview.result, ch = run.chapters.result, qz = run.quiz.result;
    const lat = (slot) => (slot.meta ? fmtMs(slot.meta.latency_ms) : (slot.loading ? '…' : '—'));
    const model = [run.overview, run.chapters, run.quiz].map((s) => s.meta?.model).find(Boolean) || '—';
    const fallback = [run.overview, run.chapters, run.quiz].some((s) => s.meta?.fallback_used);
    const retries = [run.overview, run.chapters, run.quiz].reduce((n, s) => n + Math.max(0, (s.meta?.attempts || 1) - 1), 0);
    return [
      ['Model', model + (fallback ? ' (backup model used)' : '')],
      ['Overview time', lat(run.overview)],
      ['Chapters time', lat(run.chapters)],
      ['Quiz time', lat(run.quiz)],
      ['Why a backup model was used', [...new Set([run.overview, run.chapters, run.quiz].flatMap((s) => s.meta?.skipped || []))].join('; ') || (run.overview.meta || run.chapters.meta || run.quiz.meta ? 'not needed' : '—')],
      ['Re-asks after validation', run.overview.meta || run.chapters.meta || run.quiz.meta ? String(retries) : '—'],
      ['Summary length', ov ? `${ov.summary.split(/\s+/).filter(Boolean).length} words` : '—'],
      ['Themes / takeaways', ov ? `${ov.themes.length} / ${ov.takeaways.length}` : '—'],
      ['Chapters', ch ? String(ch.chapters.length) : '—'],
      ['Verified quiz questions', qz ? String(qz.questions.length) : '—'],
      ['Warnings', [run.overview, run.chapters, run.quiz].flatMap((s) => s.meta?.warnings || []).length || (ov || ch || qz ? '0' : '—')],
    ];
  }

  function compareColumn(p) {
    const run = state.compare.runs[p];
    const col = h('section', { class: 'cmp-col', 'aria-label': PROVIDER_NAMES[p] });
    col.append(h('h3', {}, PROVIDER_NAMES[p]));
    const errs = SECTIONS.filter((s) => run[s].error);
    for (const s of errs) col.append(h('p', { class: 'error', role: 'alert' }, `${s[0].toUpperCase() + s.slice(1)}: ${run[s].error}`));
    const ov = run.overview.result;
    if (run.overview.loading) col.append(h('p', { class: 'loading-inline' }, h('span', { class: 'spinner' }), 'Writing overview…'));
    if (ov) {
      col.append(h('h4', {}, ov.title));
      col.append(h('div', { class: 'prose small' }, ov.summary.split(/\n\s*\n/).map((x) => h('p', {}, x))));
      col.append(h('h4', {}, 'Takeaways'), h('ul', {}, ov.takeaways.map((t) => h('li', {}, t.text))));
    }
    const ch = run.chapters.result;
    if (run.chapters.loading) col.append(h('p', { class: 'loading-inline' }, h('span', { class: 'spinner' }), 'Finding chapters…'));
    if (ch) col.append(h('h4', {}, 'Chapters'), h('ol', {}, ch.chapters.map((c) => h('li', {}, c.start_time != null ? `${fmtTime(c.start_time)} · ` : '', c.title))));
    const qz = run.quiz.result;
    if (run.quiz.loading) col.append(h('p', { class: 'loading-inline' }, h('span', { class: 'spinner' }), 'Writing quiz…'));
    if (qz) col.append(h('h4', {}, 'Quiz questions'), h('ol', {}, qz.questions.map((q) => h('li', {}, q.question))));
    if (ov || ch || qz) {
      col.append(h('p', {}, h('button', { type: 'button', class: 'secondary', onclick: () => adoptCompare(p) }, `Use ${PROVIDER_NAMES[p]}'s results in the other tabs`)));
    }
    return col;
  }

  function adoptCompare(p) {
    const run = state.compare.runs[p];
    for (const s of SECTIONS) {
      if (run[s].result) { state.results[s] = run[s].result; state.meta[s] = run[s].meta; state.history[s] = []; state.revisionNote[s] = ''; state.errors[s] = null; }
    }
    state.provider = p; chosenProvider = p; pickers.results.set(p); pickers.input.set(p);
    state.answers = {}; renderAll(); toast(`Now showing ${PROVIDER_NAMES[p]}'s results`);
  }

  function compareMarkdown() {
    const lines = ['# Model comparison', '', `Transcript: ${state.transcript.segments.length} passages, ${state.transcript.has_timestamps ? 'with' : 'without'} timestamps`, ''];
    const metrics = Object.fromEntries(COMPARE_PROVIDERS.map((p) => [p, compareMetrics(state.compare.runs[p])]));
    lines.push(`| Metric | ${COMPARE_PROVIDERS.map((p) => PROVIDER_NAMES[p]).join(' | ')} |`, `|---|${COMPARE_PROVIDERS.map(() => '---').join('|')}|`);
    metrics[COMPARE_PROVIDERS[0]].forEach(([label], i) => lines.push(`| ${label} | ${COMPARE_PROVIDERS.map((p) => metrics[p][i][1]).join(' | ')} |`));
    for (const p of COMPARE_PROVIDERS) {
      const run = state.compare.runs[p]; lines.push('', `## ${PROVIDER_NAMES[p]}`, '');
      if (run.overview.result) lines.push(`### ${run.overview.result.title}`, '', run.overview.result.summary, '');
      if (run.chapters.result) lines.push('### Chapters', ...run.chapters.result.chapters.map((c, i) => `${i + 1}. ${c.title}`), '');
      if (run.quiz.result) lines.push('### Quiz', ...run.quiz.result.questions.map((q, i) => `${i + 1}. ${q.question}`), '');
      for (const s of SECTIONS) if (run[s].error) lines.push(`- ${s} failed: ${run[s].error}`);
    }
    return lines.join('\n') + '\n';
  }

  function renderCompare() {
    const root = clear($('#rp-compare'));
    const c = state.compare;
    root.append(h('p', { class: 'note', style: 'margin-top:0' },
      'Runs the overview, chapters and quiz on Google Gemini and on Groq with the same transcript and the same prompts. ' +
      'Each model is pinned (no fallback to the other), and both go through the same verification, so the numbers below are a fair comparison.'));
    const btn = h('button', { type: 'button', class: 'primary', disabled: c.running, onclick: runCompare },
      c.running ? 'Comparing…' : (c.done ? 'Run comparison again' : 'Run comparison (Gemini vs Groq)'));
    const tools = h('div', { class: 'actions' }, btn);
    if (c.done) {
      tools.append(h('button', { type: 'button', class: 'secondary', onclick: () => copyText(compareMarkdown()) }, 'Copy comparison'),
        h('button', { type: 'button', class: 'secondary', onclick: () => download('model-comparison.md', compareMarkdown(), 'text/markdown') }, 'Download .md'),
        h('button', { type: 'button', class: 'secondary', onclick: () => download('model-comparison.json', JSON.stringify({ generated_at: new Date().toISOString(), runs: c.runs }, null, 2), 'application/json') }, 'Download .json'));
    }
    root.append(tools);
    if (!Object.keys(c.runs).length) return;
    const metrics = Object.fromEntries(COMPARE_PROVIDERS.map((p) => [p, compareMetrics(c.runs[p])]));
    const table = h('table', { class: 'cmp-table' },
      h('thead', {}, h('tr', {}, h('th', { scope: 'col' }, 'Metric'), COMPARE_PROVIDERS.map((p) => h('th', { scope: 'col' }, PROVIDER_NAMES[p])))),
      h('tbody', {}, metrics[COMPARE_PROVIDERS[0]].map(([label], i) => h('tr', {}, h('th', { scope: 'row' }, label), COMPARE_PROVIDERS.map((p) => h('td', {}, metrics[p][i][1]))))));
    root.append(h('div', { class: 'cmp-table-wrap' }, table));
    root.append(h('div', { class: 'cmp-cols' }, COMPARE_PROVIDERS.map(compareColumn)));
  }

  // ---- transcript
  function renderTranscript() {
    const root = clear($('#rp-transcript'));
    root.append(h('p', { class: 'note', style: 'margin-top:0' }, 'The full text the companion worked from. Citations elsewhere in the app jump to the passage here.'));
    const wrap = h('div', { class: 'segments' });
    for (const s of state.transcript.segments) {
      wrap.append(h('div', { class: 'seg', id: `seg-${s.id}`, tabindex: '-1' },
        h('span', { class: 't' }, state.transcript.has_timestamps ? fmtTime(s.start) : `#${s.id + 1}`), h('span', {}, s.text)));
    }
    root.append(wrap);
  }
  function jumpToSegment(id) {
    resultTabs.select('rt-transcript');
    const el = document.getElementById(`seg-${id}`); if (!el) return;
    el.scrollIntoView({ block: 'center' });
    el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash'); el.focus({ preventScroll: true });
  }

  // ------------------------------------------------------------------ generation + revision
  function payloadTranscript() {
    const t = state.transcript;
    return { segments: t.segments.map(({ id, start, end, text }) => ({ id, start, end, text })), has_timestamps: t.has_timestamps, source: t.source, language: t.language || null };
  }

  function generateAll() {
    SECTIONS.forEach((s, i) => setTimeout(() => loadSection(s), i * 350)); // stagger to be kind to free-tier rate limits
  }

  async function loadSection(section, { instruction = null, more = 0 } = {}) {
    const episode = state.transcript; if (!episode) return; // user may have pressed "New episode"
    const revising = Boolean(instruction);
    state.loading[section] = true; if (!revising) state.errors[section] = null; else state.errors[section] = null;
    renderSection(section); if (section === 'chapters') renderStrip();
    if (section === 'quiz' && more) state.numQuestions = Math.min(12, state.numQuestions + more);
    try {
      const body = { transcript: payloadTranscript(), section, options: { num_questions: state.numQuestions }, provider: state.provider };
      if (revising) { body.instruction = instruction; body.previous = state.results[section]; }
      const res = await api('/api/generate', { method: 'POST', body });
      if (state.transcript !== episode) return; // a different episode is open now: drop the stale result
      if (revising) { state.history[section].push({ result: state.results[section], meta: state.meta[section], note: state.revisionNote[section] }); state.revisionNote[section] = instruction; }
      else { state.history[section] = []; state.revisionNote[section] = ''; }
      state.results[section] = res.result; state.meta[section] = res.meta;
      if (section === 'quiz') state.answers = {};
    } catch (e) {
      if (state.transcript !== episode) return;
      state.errors[section] = { message: e.message, retryAfter: e.retryAfter };
      if (revising && section === 'quiz' && more) state.numQuestions = Math.max(3, state.numQuestions - more);
    }
    state.loading[section] = false;
    renderSection(section); renderHeader(); if (section === 'chapters') renderStrip();
  }
  function renderSection(section) { ({ overview: renderOverview, chapters: renderChapters, quiz: renderQuiz })[section](); }

  function revise(section, instruction, preset) {
    if (state.loading[section]) return;
    loadSection(section, { instruction, more: preset?.more || 0 });
  }
  function undo(section) {
    const prev = state.history[section].pop(); if (!prev) return;
    state.results[section] = prev.result; state.meta[section] = prev.meta; state.revisionNote[section] = prev.note || '';
    if (section === 'quiz') { state.answers = {}; state.numQuestions = prev.result.questions.length; }
    state.errors[section] = null;
    renderSection(section); renderHeader(); if (section === 'chapters') renderStrip();
    toast('Reverted to the previous version');
  }

  // ------------------------------------------------------------------ export
  function chapterLine(c, i) {
    const when = c.start_time != null ? `${fmtTime(c.start_time)}–${fmtTime(c.end_time)}` : `passages ${c.start_segment + 1}–${c.end_segment + 1}`;
    return `${i + 1}. **${c.title}** (${when})\n   ${c.summary}`;
  }
  function sectionMarkdown(section) {
    const r = state.results[section]; if (!r) return '';
    const t = state.transcript;
    const where = (id) => (t.has_timestamps && t.segments[id]?.start != null ? fmtTime(t.segments[id].start) : `passage ${id + 1}`);
    if (section === 'overview') {
      return [`# ${r.title}`, '', r.one_line, '', r.summary, '', '## Main themes', ...r.themes.map((x) => `- **${x.name}**: ${x.description}`), '',
        '## Key takeaways', ...r.takeaways.map((x) => `- ${x.text} (${x.evidence.map(where).join(', ')})`)].join('\n');
    }
    if (section === 'chapters') {
      return ['## Chapters', '', ...(r.has_timestamps ? [] : ['_Plain text has no timestamps; ranges refer to transcript passages._', '']), ...r.chapters.map(chapterLine)].join('\n');
    }
    return ['## Quiz', '', ...r.questions.flatMap((q, i) => [
      `${i + 1}. ${q.question}`, ...q.options.map((o, oi) => `   ${String.fromCharCode(97 + oi)}) ${o}`),
      `   **Answer:** ${String.fromCharCode(97 + q.correct_index)}) ${q.options[q.correct_index]}. ${q.explanation}`,
      q.evidence_quote ? `   > "${q.evidence_quote}" (${q.evidence_segment != null ? where(q.evidence_segment) : 'source'})` : '', ''])].join('\n');
  }
  function fullMarkdown() { return SECTIONS.map(sectionMarkdown).filter(Boolean).join('\n\n') + '\n'; }
  function exportJson() {
    return { generated_at: new Date().toISOString(), provider_requested: state.provider, transcript: state.transcript, overview: state.results.overview, chapters: state.results.chapters, quiz: state.results.quiz, models: Object.fromEntries(SECTIONS.map((s) => [s, state.meta[s]?.model || null])) };
  }

  // ------------------------------------------------------------------ go
  wirePickers();
  wireInput();
  init();
})();
