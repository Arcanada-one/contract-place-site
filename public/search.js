/* Contract Place site search: a thin client of the public read API (ContractPlaceRead/v1).
 * Anonymous GET requests only: no credentials, no cookies, no storage, no third parties, no tracking.
 * All page text is written with textContent; API data is never parsed as HTML.
 * The API orders passages but does not state a calibrated relevance threshold, and neither does this page. */
(function (root) {
  'use strict';

  var API_ORIGIN = 'https://api.contract.place';
  var SCHEMA = 'ContractPlaceRead/v1';
  var PAGE_SIZE = 10;
  var MAX_RESULTS = 50;
  var TIMEOUT_MS = 15000;
  var MAX_QUERY = 256;
  var LINK_PREFIX = 'https://github.com/Arcanada-one/';

  function normalizeQuery(raw) {
    return String(raw == null ? '' : raw).trim().replace(/\s+/g, ' ');
  }

  function buildUrl(query, cursor) {
    var url = new URL('/v1/search', API_ORIGIN);
    url.searchParams.set('q', query);
    url.searchParams.set('limit', String(PAGE_SIZE));
    if (cursor) url.searchParams.set('cursor', cursor);
    return url.toString();
  }

  /** Only links into this organisation's GitHub are rendered as links; anything else is shown as text. */
  function safeLink(raw) {
    if (typeof raw !== 'string') return null;
    var url;
    try { url = new URL(raw); } catch (e) { return null; }
    if (url.protocol !== 'https:' || url.hostname !== 'github.com' || url.username || url.password || url.port) return null;
    if (url.pathname.indexOf('/Arcanada-one/') !== 0) return null;
    return url.toString();
  }

  function str(v, max) {
    return typeof v === 'string' ? v.slice(0, max) : '';
  }

  /** One API result -> the plain-text fields the page shows. Unknown or malformed fields become empty, never HTML. */
  function toViewItem(r) {
    if (!r || typeof r !== 'object') return null;
    var c = r.citation && typeof r.citation === 'object' ? r.citation : {};
    var doc = r.document && typeof r.document === 'object' ? r.document : {};
    var kc2 = r.kc2_admission;
    if (kc2 && typeof kc2 === 'object') kc2 = kc2.state;
    var flagged = r.injection_flag === true;
    return {
      title: str(c.title, 200).replace(/^#+\s*/, '') || str(doc.path, 200) || 'Untitled passage',
      link: safeLink(c.canonical_url),
      path: str(doc.path, 200),
      revision: str(r.source_revision, 40).slice(0, 12),
      status: str(r.status, 40),
      license: str(r.license, 40),
      snippet: flagged ? '' : str(r.snippet, 1200),
      snippetTruncated: r.snippet_truncated === true,
      flagged: flagged,
      kc2: typeof kc2 === 'string' ? kc2.slice(0, 40) : '',
      uncertainty: Array.isArray(r.uncertainty) ? r.uncertainty.filter(function (u) { return typeof u === 'string'; }).slice(0, 8).map(function (u) { return u.slice(0, 80); }) : [],
      missing: Array.isArray(r.missing) ? r.missing.filter(function (u) { return typeof u === 'string'; }).slice(0, 8).map(function (u) { return u.slice(0, 80); }) : []
    };
  }

  function failure(kind, message) {
    return { state: 'error', kind: kind, message: message, items: [], nextCursor: null };
  }

  function describeStatus(status) {
    if (status === 400) return failure('http_400', 'The API did not accept this query. Try different words.');
    if (status === 429) return failure('rate_limited', 'Too many searches in a short time. Wait a minute and try again.');
    if (status === 502 || status === 503 || status === 504) return failure('unavailable', 'The search service is unavailable right now. Try again later.');
    return failure('http_other', 'The API answered with an unexpected status (' + status + ').');
  }

  /**
   * One search request. deps = { fetch, AbortController, setTimeout, clearTimeout } (injectable for tests).
   * Resolves to a view model: { state: 'ok' | 'empty' | 'error', kind, message, items, nextCursor, withheld }.
   */
  function runSearch(deps, rawQuery, cursor) {
    var query = normalizeQuery(rawQuery);
    if (!query) return Promise.resolve(failure('invalid_query', 'Type a word or a phrase to search for.'));
    if (query.length > MAX_QUERY) return Promise.resolve(failure('invalid_query', 'The query is too long (at most ' + MAX_QUERY + ' characters).'));
    var controller = new deps.AbortController();
    var timedOut = false;
    var timer = deps.setTimeout(function () { timedOut = true; controller.abort(); }, TIMEOUT_MS);
    return deps.fetch(buildUrl(query, cursor), {
      method: 'GET',
      mode: 'cors',
      credentials: 'omit',
      cache: 'no-store',
      referrerPolicy: 'no-referrer',
      redirect: 'error',
      signal: controller.signal
    }).then(function (res) {
      if (!res.ok) return describeStatus(res.status);
      return res.json().then(function (body) {
        if (!body || typeof body !== 'object' || body.schema !== SCHEMA || !Array.isArray(body.results) || !body.page || typeof body.page !== 'object') {
          return failure('bad_response', 'The API answered in a format this page does not understand.');
        }
        var items = body.results.map(toViewItem).filter(Boolean);
        var next = typeof body.page.next_cursor === 'string' && /^[A-Za-z0-9_-]{1,256}$/.test(body.page.next_cursor) ? body.page.next_cursor : null;
        var withheld = typeof body.withheld === 'number' && isFinite(body.withheld) ? body.withheld : 0;
        if (items.length === 0) return { state: 'empty', kind: 'no_results', message: 'The API returned no passages for this query.', items: [], nextCursor: null, withheld: withheld };
        return { state: 'ok', kind: 'results', message: '', items: items, nextCursor: next, withheld: withheld };
      }, function () {
        return failure('bad_response', 'The API answered in a format this page does not understand.');
      });
    }, function () {
      if (timedOut) return failure('timeout', 'The search took too long and was stopped. Try again.');
      return failure('network', 'Could not reach the API. This can be a network problem or a browser cross-origin restriction.');
    }).then(function (vm) {
      deps.clearTimeout(timer);
      return vm;
    });
  }

  var api = {
    API_ORIGIN: API_ORIGIN, SCHEMA: SCHEMA, PAGE_SIZE: PAGE_SIZE, MAX_RESULTS: MAX_RESULTS, TIMEOUT_MS: TIMEOUT_MS, MAX_QUERY: MAX_QUERY,
    normalizeQuery: normalizeQuery, buildUrl: buildUrl, safeLink: safeLink, toViewItem: toViewItem, describeStatus: describeStatus, runSearch: runSearch
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.KcpSearch = api;

  // ---- DOM binding (browser only) ----------------------------------------------------------------------------------------
  var doc = root.document;
  if (!doc || !doc.getElementById) return;
  var form = doc.getElementById('search-form');
  if (!form) return;
  var input = doc.getElementById('search-q');
  var statusEl = doc.getElementById('search-status');
  var list = doc.getElementById('search-results');
  var more = doc.getElementById('search-more');
  var busy = false;
  var current = null; // { q, cursor }
  var serial = 0;

  var deps = {
    fetch: function (u, o) { return root.fetch(u, o); },
    AbortController: root.AbortController,
    setTimeout: function (f, ms) { return root.setTimeout(f, ms); },
    clearTimeout: function (t) { root.clearTimeout(t); }
  };

  function el(tag, cls, text) {
    var e = doc.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function setStatus(text, kind) {
    statusEl.textContent = text;
    statusEl.setAttribute('data-state', kind || '');
  }

  function renderItem(it, rank) {
    var li = el('li', 'result');
    var h = el('h3', 'result-title');
    if (it.link) {
      var a = el('a', null, it.title);
      a.href = it.link;
      a.rel = 'noopener noreferrer';
      h.appendChild(a);
    } else {
      h.textContent = it.title;
    }
    li.appendChild(h);
    if (it.flagged) li.appendChild(el('p', 'result-note', 'The API flagged this passage and its text is hidden here.'));
    else if (it.snippet) li.appendChild(el('p', 'result-snippet', it.snippet + (it.snippetTruncated ? ' …' : '')));
    var meta = ['API rank ' + rank];
    if (it.path) meta.push(it.path);
    if (it.revision) meta.push('revision ' + it.revision);
    if (it.status) meta.push('status ' + it.status);
    if (it.license) meta.push(it.license);
    if (meta.length) li.appendChild(el('p', 'result-meta', meta.join(' · ')));
    var marks = [];
    if (it.kc2) marks.push('KC2 admission: ' + it.kc2.replace(/_/g, ' ') + '; retrieval grants no action rights');
    if (it.uncertainty.length) marks.push('uncertainty: ' + it.uncertainty.join(', '));
    if (it.missing.length) marks.push('missing: ' + it.missing.join(', '));
    if (marks.length) li.appendChild(el('p', 'result-meta', marks.join(' | ')));
    return li;
  }

  function finish(vm, append, myserial, query) {
    if (myserial !== serial) return; // a newer search replaced this one
    busy = false;
    form.removeAttribute('aria-busy');
    form.querySelector('button[type=submit]').disabled = false;
    more.disabled = false;
    if (vm.state === 'error') {
      if (!append) list.textContent = '';
      more.hidden = true;
      setStatus(vm.message, 'error');
      return;
    }
    if (!append) list.textContent = '';
    if (vm.state === 'empty') {
      more.hidden = true;
      setStatus(vm.message + (vm.withheld ? ' ' + vm.withheld + ' matching record(s) are not published.' : ''), 'empty');
      return;
    }
    vm.items.forEach(function (it) { list.appendChild(renderItem(it, list.children.length + 1)); });
    var shown = list.children.length;
    current = { q: query, cursor: shown < MAX_RESULTS ? vm.nextCursor : null };
    more.hidden = !current.cursor;
    setStatus(shown + ' passage' + (shown === 1 ? '' : 's') + ' shown.' + (current.cursor ? '' : (vm.nextCursor ? ' Showing the first ' + MAX_RESULTS + '.' : '')), 'ok');
  }

  function start(query, cursor, append) {
    if (busy) return;
    busy = true;
    serial += 1;
    var myserial = serial;
    form.setAttribute('aria-busy', 'true');
    form.querySelector('button[type=submit]').disabled = true;
    more.disabled = true;
    setStatus('Searching…', 'loading');
    runSearch(deps, query, cursor).then(function (vm) { finish(vm, append, myserial, normalizeQuery(query)); });
  }

  form.hidden = false;
  form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    current = null;
    more.hidden = true;
    start(input.value, null, false);
  });
  more.addEventListener('click', function () {
    if (current && current.cursor) start(current.q, current.cursor, true);
  });
})(typeof globalThis !== 'undefined' ? globalThis : this);
