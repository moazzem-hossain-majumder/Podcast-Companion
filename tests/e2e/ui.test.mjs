// Drives the real index.html + app.js in jsdom against a live server (see ../e2e_server.py).
import { JSDOM } from 'jsdom';
import assert from 'node:assert/strict';

const BASE = process.env.BASE || 'http://127.0.0.1:8765';
const html = await (await fetch(BASE + '/')).text();
const dom = new JSDOM(html, { url: BASE + '/', runScripts: 'outside-only', pretendToBeVisual: true });
const { window } = dom; const { document } = window;
window.fetch = (u, o) => fetch(new URL(u, BASE), o);
window.scrollTo = () => {}; window.HTMLElement.prototype.scrollIntoView = () => {};
window.matchMedia = () => ({ matches: false, addEventListener() {}, removeEventListener() {} });
const styleAttrCalls = [];
const _set = window.Element.prototype.setAttribute;
window.Element.prototype.setAttribute = function (n, v) { if (String(n).toLowerCase() === 'style') styleAttrCalls.push(v); return _set.call(this, n, v); };
window.eval(await (await fetch(BASE + '/app.js')).text());

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function until(fn, label, ms = 8000) {
  const end = Date.now() + ms;
  while (Date.now() < end) { try { if (fn()) return; } catch {} await sleep(50); }
  throw new Error('timeout waiting for: ' + label + '\nBody: ' + document.body.textContent.replace(/\s+/g, ' ').slice(0, 600));
}
const $ = (s) => document.querySelector(s);
const click = (el) => el.dispatchEvent(new window.MouseEvent('click', { bubbles: true }));
const results = [];
async function step(name, fn) { await fn(); results.push(name); console.log('  ok  ' + name); }

await step('limits load from /api/health', async () => {
  await until(() => $('#limits').textContent.includes('150,000'), 'limits');
  assert.match($('#limits').textContent, /60 MB/);
});
await step('empty submit shows a helpful error', async () => {
  click($('#build')); await until(() => !$('#input-error').hidden, 'error');
  assert.match($('#input-error').textContent, /Paste a transcript/);
});
await step('sample loads into textarea', async () => {
  click($('[data-sample="paste"]')); await until(() => $('#text-input').value.length > 1000, 'sample');
});
await step('build produces overview, chapters, quiz', async () => {
  click($('#build'));
  await until(() => !$('#results-view').hidden, 'results view');
  await until(() => $('#ep-title').textContent.startsWith('Why we forget'), 'overview title');
  await until(() => $$('#strip button').length === 3, 'chapter strip');
  await until(() => $('#rp-quiz').textContent.includes('Fake question 1'), 'quiz');
  assert.match($('#rp-overview').textContent, /Key takeaways/);
});
function $$(s) { return [...document.querySelectorAll(s)]; }

await step('chapters tab: no-timestamp notice + passage ranges, not invented times', async () => {
  click($('#rt-chapters'));
  assert.equal($('#rp-chapters').hidden, false);
  const t = $('#rp-chapters').textContent;
  assert.match(t, /no timing information/); assert.match(t, /Part 1/); assert.doesNotMatch(t, /\d+:\d{2}/);
});
await step('quiz: answering reveals verdict, explanation, source quote; score updates', async () => {
  click($('#rt-quiz'));
  const first = $$('#q-0 .opt').find((b) => /^Right/.test(b.textContent)); click(first);
  await until(() => $('#q-0 .verdict'), 'verdict');
  assert.match($('#q-0').textContent, /Because the passage says so/);
  assert.ok($('#q-0 blockquote.source'), 'source quote shown');
  assert.match($('.quiz-score').textContent, /Score: 1 of 1/);
  const wrongBtn = $$('#q-1 .opt').find((b) => !/^Right/.test(b.textContent)); click(wrongBtn);
  await until(() => $('#q-1 .verdict.wrong'), 'wrong verdict');
  assert.match($('.quiz-score').textContent, /Score: 1 of 2/);
});
await step('citation chip jumps to transcript and highlights segment', async () => {
  click($('#q-0 .cite'));
  assert.equal($('#rp-transcript').hidden, false);
  assert.ok($('#rp-transcript .seg.flash'));
});
await step('revision: overview regenerates only that section, with undo', async () => {
  click($('#rt-overview'));
  const quizBefore = $('#rp-quiz').textContent;
  click($$('#rp-overview .chip')[0]);
  await until(() => $('#ep-title').textContent.includes('(shorter)'), 'revised title');
  assert.match($('#rp-overview .revised-note').textContent, /Only this section was regenerated/);
  assert.equal($('#rp-quiz').textContent, quizBefore);
  click($$('#rp-overview .link').find((b) => /Undo/.test(b.textContent)));
  await until(() => !$('#ep-title').textContent.includes('(shorter)'), 'undo');
});
await step('quiz revision changes difficulty and resets answers', async () => {
  click($('#rt-quiz'));
  click($$('#rp-quiz .chip')[0]);
  await until(() => !$('#q-0 .verdict') && $('#rp-quiz').textContent.includes('Fake question 1'), 'revised quiz');
  assert.match($('#rp-quiz .revised-note').textContent, /Revised/);
});
await step('free-text revision works via Enter key', async () => {
  click($('#rt-chapters'));
  const input = $('#rp-chapters .revise-row input'); input.value = 'make it punchy';
  input.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
  await until(() => /make it punchy/.test($('#rp-chapters .revised-note')?.textContent || ''), 'chapter revision');
});
await step('ask: grounded answer with source, and "not covered" state', async () => {
  click($('#rt-ask'));
  let input = $('#rp-ask input'); input.value = 'What about sleep?'; click($('#rp-ask .primary'));
  await until(() => $('#rp-ask .answer'), 'answer');
  assert.match($('#rp-ask').textContent, /Sleep consolidates/); assert.ok($('#rp-ask blockquote.source'));
  input = $('#rp-ask input'); input.value = 'Who won the 2022 world cup?'; click($('#rp-ask .primary'));
  await until(() => $('#rp-ask .answer.none'), 'unanswerable');
});
await step('new episode returns to the input view', async () => {
  click($('#new-episode')); assert.equal($('#input-view').hidden, false); assert.equal($('#results-view').hidden, true);
});
await step('server error surfaces as readable message with retry (parse failure)', async () => {
  $('#text-input').value = 'too short'; click($('#build'));
  await until(() => !$('#input-error').hidden && /too short/.test($('#input-error').textContent), 'parse error');
  assert.equal($('#input-view').hidden, false);
});
await step('XSS: hostile model output is rendered as inert text', async () => {
  const sample = await (await fetch(BASE + '/sample.txt')).text();
  $('#tab-text').click(); $('#text-input').value = sample + '\nXSSMARK'; click($('#build'));
  await until(() => !$('#results-view').hidden && $('#ep-title').textContent.includes('<img'), 'hostile title shown as text');
  assert.equal(document.querySelectorAll('#results-view img').length, 0);
  assert.equal(window.__xss, undefined);
});
await step('every tab has a sample for every format it accepts', async () => {
  click($('#new-episode'));
  const ids = (sel) => [...document.querySelectorAll(sel + ' .sample-chip')].map((b) => b.dataset.sample);
  assert.deepEqual(ids('#pane-text'), ['paste', 'paste-ts', 'short']);
  assert.deepEqual(ids('#pane-file'), ['txt', 'md', 'srt', 'vtt']);
  assert.deepEqual(ids('#pane-audio'), ['mp3', 'm4a', 'mp4', 'wav', 'ogg', 'flac', 'webm', 'aac']);
  for (const f of ['episode.txt', 'episode.md', 'episode.srt', 'episode.vtt', 'episode.mp4', 'episode.aac']) {
    assert.equal((await fetch(BASE + '/samples/' + f, { method: 'HEAD' })).status, 200, f);
  }
});
await step('file-tab sample (.srt) loads, shows a download link and keeps real timestamps', async () => {
  click($('#tab-file')); click($('#pane-file [data-sample="srt"]'));
  await until(() => /episode\.srt/.test($('#file-name').textContent), 'srt picked');
  assert.match($('#pane-file .sample-note a').getAttribute('href'), /\/samples\/episode\.srt$/);
  assert.ok($('#pane-file [data-sample="srt"]').classList.contains('on'));
  click($('#build'));
  await until(() => !$('#results-view').hidden && /with real timestamps/.test($('#ep-meta').textContent), 'timestamped results');
  await until(() => $$('#strip button').length === 3, 'chapter strip');
  click($('#rt-chapters')); assert.match($('#rp-chapters').textContent, /\d+:\d{2}/);
});
await step('audio-tab sample (.mp4) is placed in the audio input', async () => {
  click($('#new-episode')); click($('#tab-audio')); click($('#pane-audio [data-sample="mp4"]'));
  await until(() => /episode\.mp4/.test($('#audio-name').textContent), 'audio picked', 15000);
  assert.equal($('#pane-audio').hidden, false);
  assert.ok($('#asr-provider').options.length === 3);
});
await step('model selector: "Groq" pins every section to Groq', async () => {
  click($('#tab-text')); click($('[data-sample="paste"]')); await until(() => $('#text-input').value.length > 5000, 'paste sample');
  click($('#model-input-btn .mp-cur')); // click the text inside the button, as a real user does
  assert.equal($('#model-input-menu').hidden, false, 'picker opens');
  assert.equal($$('#model-input-menu [role="option"]').length, 3);
  click($('#model-input-opt-groq'));
  assert.equal($('#model-input-menu').hidden, true, 'picker closes after choosing');
  assert.match($('#model-input-btn').textContent, /Groq/);
  click($('#build'));
  await until(() => $('#ep-title').textContent.includes('[groq]'), 'groq overview');
  await until(() => /Groq fake-groq/.test($('#rp-quiz').textContent), 'quiz by groq');
  assert.match($('#model-results-btn').textContent, /Groq/);
});
await step('results model switch regenerates everything with the other model', async () => {
  click($('#model-results-btn')); click($('#model-results-opt-gemini'));
  await until(() => $('#ep-title').textContent.startsWith('Why we forget') && !$('#ep-title').textContent.includes('[groq]') && /Google Gemini fake-gemini/.test($('#rp-overview').textContent), 'gemini overview');
});
await step('compare tab: runs both models side by side with metrics and export', async () => {
  click($('#rt-compare'));
  click($('#rp-compare .primary'));
  await until(() => $('#rp-compare .cmp-table') && /Run comparison again/.test($('#rp-compare .primary').textContent), 'comparison done', 15000);
  const cols = $$('#rp-compare .cmp-col');
  assert.equal(cols.length, 2);
  assert.doesNotMatch(cols[0].textContent, /\[groq\]/); assert.match(cols[1].textContent, /\[groq\]/);
  const heads = $$('#rp-compare thead th').map((x) => x.textContent);
  assert.deepEqual(heads, ['Metric', 'Google Gemini', 'Groq']);
  assert.match($('#rp-compare .cmp-table').textContent, /fake-gemini/); assert.match($('#rp-compare .cmp-table').textContent, /fake-groq/);
  assert.match($('#rp-compare .cmp-table').textContent, /Verified quiz questions/);
  click($$('#rp-compare .cmp-col button').find((b) => /Groq's results/.test(b.textContent)));
  await until(() => $('#ep-title').textContent.includes('[groq]'), 'adopted groq results');
});
await step('model picker: keyboard (ArrowDown opens, Escape closes) and selected option is marked', async () => {
  const btn = $('#model-results-btn');
  btn.dispatchEvent(new window.KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true }));
  assert.equal($('#model-results-menu').hidden, false);
  assert.equal($('#model-results-menu [aria-selected="true"]').dataset.value, 'groq');
  $('#model-results-menu').dispatchEvent(new window.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
  assert.equal($('#model-results-menu').hidden, true);
});
await step('CSP: app never sets inline style via setAttribute (blocked by our CSP)', async () => { assert.deepEqual(styleAttrCalls, []); });
console.log(`\n${results.length} UI steps passed`);
window.close(); process.exit(0);
