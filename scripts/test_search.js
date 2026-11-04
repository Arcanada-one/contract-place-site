// Unit tests for public/search.js (pure logic; no DOM, no network). Run: node scripts/test_search.js
'use strict';
const assert = require('node:assert/strict');
const S = require('../public/search.js');

let n = 0;
async function t(name, fn) { await fn(); n += 1; console.log('ok ' + name); }

function deps(handler, opts = {}) {
  const calls = [];
  const timers = [];
  return {
    calls, timers,
    fetch(url, init) { calls.push({ url, init }); return handler(url, init); },
    AbortController,
    setTimeout(f, ms) { timers.push(ms); return opts.fire ? setTimeout(f, 0) : 1; },
    clearTimeout() {},
  };
}
const json = (status, body) => Promise.resolve({ ok: status >= 200 && status < 300, status, json: () => Promise.resolve(body) });
const item = (over = {}) => Object.assign({
  id: 'a', document: { path: 'articles/x.md', document_id: '0123456789abcdef' },
  citation: { title: '# Title X', canonical_url: 'https://github.com/Arcanada-one/knowledge-contract/blob/abc/X.md' },
  source_revision: '39e05969728ea7a51f162cdbefac32fd8f54dbb6', status: 'current', license: 'CC-BY-4.0',
  snippet: 'text', snippet_truncated: true, kc2_admission: 'not_measured', uncertainty: ['kc2_admission:not_measured'], missing: [], injection_flag: false, score: 0.03, score_kind: 'rrf',
}, over);
const ok = (results, extra = {}) => json(200, Object.assign({ schema: 'ContractPlaceRead/v1', results, page: { limit: 10, returned: results.length, next_cursor: null }, withheld: 0 }, extra));

(async () => {
  await t('normalizeQuery trims and collapses whitespace', () => {
    assert.equal(S.normalizeQuery('  a \n\t b  '), 'a b');
    assert.equal(S.normalizeQuery(null), '');
  });
  await t('buildUrl: fixed origin and path, encoded query, limit, optional cursor', () => {
    const u = new URL(S.buildUrl('a&b=c d', null));
    assert.equal(u.origin, 'https://api.contract.place');
    assert.equal(u.pathname, '/v1/search');
    assert.equal(u.searchParams.get('q'), 'a&b=c d');
    assert.equal(u.searchParams.get('limit'), '10');
    assert.equal(u.searchParams.has('cursor'), false);
    assert.equal(new URL(S.buildUrl('x', 'abC_-1')).searchParams.get('cursor'), 'abC_-1');
    assert.equal([...new URL(S.buildUrl('x', null)).searchParams.keys()].sort().join(','), 'limit,q');
  });
  await t('safeLink accepts only https github.com/Arcanada-one links', () => {
    assert.ok(S.safeLink('https://github.com/Arcanada-one/knowledge-contract/blob/x/A.md'));
    for (const bad of ['http://github.com/Arcanada-one/x', 'https://github.com/Other/x', 'https://evil.example/Arcanada-one/', 'https://github.com.evil.example/Arcanada-one/x',
      'javascript:alert(1)', 'data:text/html,x', 'https://user:pw@github.com/Arcanada-one/x', 'https://github.com:8443/Arcanada-one/x', 'https://github.com/arcanada-one/x', '', null, 5, '//github.com/Arcanada-one/x']) {
      assert.equal(S.safeLink(bad), null, String(bad));
    }
  });
  await t('toViewItem: plain text only, title cleaned, fields bounded, unknown shapes safe', () => {
    const v = S.toViewItem(item({ citation: { title: '# <img src=x onerror=1> T', canonical_url: 'javascript:1' }, snippet: 'x'.repeat(5000) }));
    assert.equal(v.title, '<img src=x onerror=1> T'); // kept as TEXT; the page uses textContent
    assert.equal(v.link, null);
    assert.equal(v.snippet.length, 1200);
    assert.equal(v.revision, '39e05969728e');
    assert.equal(S.toViewItem(null), null);
    assert.equal(S.toViewItem(item({ injection_flag: true })).snippet, '');
    assert.equal(S.toViewItem(item({ kc2_admission: { state: 'admitted' } })).kc2, 'admitted');
    assert.deepEqual(S.toViewItem(item({ uncertainty: [1, 'ok', {}] })).uncertainty, ['ok']);
    assert.equal(S.toViewItem({}).title, 'Untitled passage');
  });
  await t('runSearch: empty and over-long queries make no request', async () => {
    const d = deps(() => { throw new Error('must not be called'); });
    for (const q of ['', '   ', null]) assert.equal((await S.runSearch(d, q)).kind, 'invalid_query');
    assert.equal((await S.runSearch(d, 'x'.repeat(257))).kind, 'invalid_query');
    assert.equal(d.calls.length, 0);
    const d2 = deps(() => ok([item()]));
    assert.equal((await S.runSearch(d2, 'x'.repeat(256))).state, 'ok'); // the limit itself is allowed
    assert.equal(d2.calls.length, 1);
  });
  await t('runSearch: request is an anonymous CORS GET (no credentials, no referrer, no cache, no redirect, no custom headers)', async () => {
    const d = deps(() => ok([item()]));
    await S.runSearch(d, 'openness');
    const { init } = d.calls[0];
    assert.equal(init.method, 'GET'); assert.equal(init.mode, 'cors'); assert.equal(init.credentials, 'omit');
    assert.equal(init.cache, 'no-store'); assert.equal(init.referrerPolicy, 'no-referrer'); assert.equal(init.redirect, 'error');
    assert.equal('headers' in init, false); assert.equal('body' in init, false);
    assert.deepEqual(d.timers, [15000]);
  });
  await t('runSearch: results keep the API order and carry no score', async () => {
    const d = deps(() => ok([item({ id: '1', citation: { title: 'First' } }), item({ id: '2', citation: { title: 'Second' } }), item({ id: '3', citation: { title: 'Third' } })]));
    const vm = await S.runSearch(d, 'q');
    assert.equal(vm.state, 'ok');
    assert.deepEqual(vm.items.map((i) => i.title), ['First', 'Second', 'Third']);
    assert.equal(vm.items.some((i) => 'score' in i), false);
  });
  await t('runSearch: genuinely empty answer is empty, with the API-withheld count', async () => {
    const vm = await S.runSearch(deps(() => ok([], { withheld: 2 })), 'q');
    assert.equal(vm.state, 'empty'); assert.equal(vm.withheld, 2);
    assert.match(vm.message, /returned no passages/);
  });
  await t('runSearch: a non-empty answer is never turned into "no results" (gibberish query still shows what the API returned)', async () => {
    const vm = await S.runSearch(deps(() => ok([item()])), 'zzqxv-no-such-term');
    assert.equal(vm.state, 'ok'); assert.equal(vm.items.length, 1);
  });
  await t('runSearch: next cursor accepted only in the API alphabet', async () => {
    assert.equal((await S.runSearch(deps(() => ok([item()], { page: { next_cursor: 'abC_-9' } })), 'q')).nextCursor, 'abC_-9');
    for (const bad of ['a b', '../x', 'x'.repeat(257), 5, '']) assert.equal((await S.runSearch(deps(() => ok([item()], { page: { next_cursor: bad } })), 'q')).nextCursor, null, String(bad));
  });
  await t('runSearch: HTTP failures map to distinct honest messages', async () => {
    const want = { 400: 'http_400', 429: 'rate_limited', 502: 'unavailable', 503: 'unavailable', 504: 'unavailable', 500: 'http_other', 404: 'http_other', 401: 'http_other' };
    for (const [status, kind] of Object.entries(want)) {
      const vm = await S.runSearch(deps(() => json(Number(status), { error: 'x' })), 'q');
      assert.equal(vm.state, 'error', status); assert.equal(vm.kind, kind, status); assert.deepEqual(vm.items, []);
    }
  });
  await t('runSearch: malformed 200 bodies are errors, not results', async () => {
    for (const body of [null, 'x', [], {}, { schema: 'Other/v9', results: [], page: {} }, { schema: 'ContractPlaceRead/v1', results: 'no', page: {} }, { schema: 'ContractPlaceRead/v1', results: [], page: null }, { schema: 'ContractPlaceRead/v1', results: [] }]) {
      const vm = await S.runSearch(deps(() => json(200, body)), 'q');
      assert.equal(vm.kind, 'bad_response', JSON.stringify(body));
    }
    const badJson = await S.runSearch(deps(() => Promise.resolve({ ok: true, status: 200, json: () => Promise.reject(new SyntaxError('x')) })), 'q');
    assert.equal(badJson.kind, 'bad_response');
  });
  await t('runSearch: network / CORS failure is an error that names both possibilities', async () => {
    const vm = await S.runSearch(deps(() => Promise.reject(new TypeError('Failed to fetch'))), 'q');
    assert.equal(vm.kind, 'network'); assert.match(vm.message, /cross-origin/);
  });
  await t('runSearch: a hanging request is aborted by the timer and reported as a timeout', async () => {
    const d = deps((u, init) => new Promise((_, rej) => init.signal.addEventListener('abort', () => rej(new DOMException('aborted', 'AbortError')))), { fire: true });
    const vm = await S.runSearch(d, 'q');
    assert.equal(vm.kind, 'timeout');
  });
  await t('runSearch: stray data in items cannot break the view model', async () => {
    const vm = await S.runSearch(deps(() => ok([null, 5, 'x', item()])), 'q');
    assert.equal(vm.state, 'ok'); assert.equal(vm.items.length, 1); // null, 5 and 'x' are dropped
  });
  await t('toViewItem: kc2.state (e.g. not_admitted) wins over the weaker kc2_admission string', () => {
    const v = S.toViewItem(item({ kc2_admission: 'not_measured', kc2: { state: 'not_admitted', action_rights: 'none' } }));
    assert.equal(v.kc2, 'not_admitted');
    assert.equal(S.toViewItem(item({ kc2_admission: 'not_measured' })).kc2, 'not_measured'); // no kc2 object: fall back
  });
  await t('messages: ru and zh-Hans have every key of en; unknown language falls back to en', () => {
    const en = Object.keys(S.messages('en')).sort();
    for (const l of ['ru', 'zh-Hans']) assert.deepEqual(Object.keys(S.messages(l)).sort(), en);
    assert.equal(S.messages('de'), S.messages('en'));
    assert.notEqual(S.messages('ru').searching, S.messages('en').searching);
  });
  await t('runSearch: error messages are localized by deps.lang', async () => {
    const d = deps(() => json(429, {})); d.lang = 'ru';
    const vm = await S.runSearch(d, 'q');
    assert.equal(vm.kind, 'rate_limited'); assert.equal(vm.message, S.messages('ru').rateLimited);
    const z = deps(() => Promise.reject(new Error('x'))); z.lang = 'zh-Hans';
    assert.equal((await S.runSearch(z, 'q')).message, S.messages('zh-Hans').network);
  });
  await t('runSearch: the controller is handed to the caller so a newer search can abort it', async () => {
    let got = null;
    await S.runSearch(deps(() => ok([item()])), 'q', null, { onController: (c) => { got = c; } });
    assert.ok(got && typeof got.abort === 'function');
  });
  await t('publicationState requires matching repository, full source revision and pinned URL', () => {
    const pin = { repository: 'Arcanada-one/knowledge-contract', commit: 'a'.repeat(40), edition: '1.0' };
    const matching = S.toViewItem(item({
      source_revision: pin.commit,
      citation: { title: 'Exact', canonical_url: 'https://github.com/' + pin.repository + '/blob/' + pin.commit + '/papers/example/PAPER.md' }
    }));
    assert.equal(S.publicationState(matching, pin).key, 'snapshotMatch');
    assert.equal(S.publicationState(matching, pin).matched, true);
    assert.equal(S.publicationState(Object.assign({}, matching, { fullRevision: 'b'.repeat(40), status: 'current' }), pin).key, 'snapshotDifferent');
    assert.equal(S.publicationState(Object.assign({}, matching, { fullRevision: pin.commit.slice(0,12) }), pin).key, 'snapshotUnknown');
    assert.equal(S.publicationState(Object.assign({}, matching, { fullRevision: pin.commit + 'x' }), pin).key, 'snapshotUnknown');
    assert.equal(S.publicationState(Object.assign({}, matching, { link: 'https://github.com/' + pin.repository + '/blob/main/papers/example/PAPER.md' }), pin).key, 'snapshotUnpinned');
    assert.equal(S.publicationState(Object.assign({}, matching, { link: 'https://github.com/Arcanada-one/other/blob/' + pin.commit + '/PAPER.md' }), pin).key, 'snapshotOutside');
    assert.equal(S.publicationState(Object.assign({}, matching, { link: 'https://github.com.evil.example/' + pin.repository + '/blob/' + pin.commit + '/PAPER.md' }), pin).matched, false);
  });
  await t('publicationState labels are localized without turning current into an admission', () => {
    const v = S.toViewItem(item({status:'current'}));
    const pin = {repository:'Arcanada-one/knowledge-contract',commit:'a'.repeat(40),edition:'1.0'};
    assert.equal(S.publicationState(v,pin,'ru').label,S.messages('ru').snapshotDifferent);
    assert.equal(S.publicationState(v,null,'zh-Hans').label,S.messages('zh-Hans').snapshotUnknown);
    assert.equal(v.kc2,'not_measured');
  });
  console.log('TESTS passed=' + n);
})().catch((e) => { console.error('FAILED', e); process.exit(1); });
