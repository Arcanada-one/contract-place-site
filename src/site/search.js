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

  // Interface strings of the result list in the three site locales (the API data itself stays as published).
  var I18N = {
    en: {
      searching: 'Searching…', typeQuery: 'Type a word or a phrase to search for.',
      tooLong: function (n) { return 'The query is too long (at most ' + n + ' characters).'; },
      http400: 'The API did not accept this query. Try different words.',
      rateLimited: 'Too many searches in a short time. Wait a minute and try again.',
      unavailable: 'The search service is unavailable right now. Try again later.',
      httpOther: function (s) { return 'The API answered with an unexpected status (' + s + ').'; },
      badResponse: 'The API answered in a format this page does not understand.',
      timeout: 'The search took too long and was stopped. Try again.',
      network: 'Could not reach the API. This can be a network problem or a browser cross-origin restriction.',
      noResults: 'The API returned no passages for this query.',
      withheld: function (n) { return ' ' + n + ' matching record(s) are not published.'; },
      shown: function (n) { return n + ' passage' + (n === 1 ? '' : 's') + ' shown.'; },
      firstN: function (n) { return ' Showing the first ' + n + '.'; },
      flagged: 'The API flagged this passage and its text is hidden here.',
      rank: 'API rank', revision: 'revision', status: 'status',
      kc2: function (st) { return 'KC2 admission: ' + st + '; retrieval grants no action rights'; },
      uncertainty: 'uncertainty', missing: 'missing'
    },
    ru: {
      searching: 'Поиск…', typeQuery: 'Введите слово или фразу для поиска.',
      tooLong: function (n) { return 'Запрос слишком длинный (не более ' + n + ' символов).'; },
      http400: 'API не принял этот запрос. Попробуйте другие слова.',
      rateLimited: 'Слишком много запросов за короткое время. Подождите минуту и повторите.',
      unavailable: 'Поисковая служба сейчас недоступна. Повторите позже.',
      httpOther: function (s) { return 'API ответил неожиданным статусом (' + s + ').'; },
      badResponse: 'API ответил в формате, который эта страница не понимает.',
      timeout: 'Поиск занял слишком много времени и был остановлен. Повторите.',
      network: 'Не удалось связаться с API. Это может быть сетевая проблема или ограничение источника в браузере.',
      noResults: 'API не вернул фрагментов по этому запросу.',
      withheld: function (n) { return ' Подходящих записей, не опубликованных: ' + n + '.'; },
      shown: function (n) { return 'Показано фрагментов: ' + n + '.'; },
      firstN: function (n) { return ' Показаны первые ' + n + '.'; },
      flagged: 'API пометил этот фрагмент, его текст скрыт.',
      rank: 'место в ответе API', revision: 'ревизия', status: 'статус',
      kc2: function (st) { return 'допуск KC2: ' + st + '; извлечение не даёт прав на действия'; },
      uncertainty: 'неопределённость', missing: 'отсутствует'
    },
    'zh-Hans': {
      searching: '正在搜索…', typeQuery: '请输入要搜索的词或短语。',
      tooLong: function (n) { return '查询过长（最多 ' + n + ' 个字符）。'; },
      http400: 'API 未接受此查询，请换个说法。',
      rateLimited: '短时间内搜索次数过多，请稍等一分钟后重试。',
      unavailable: '搜索服务暂不可用，请稍后再试。',
      httpOther: function (s) { return 'API 返回了意外状态（' + s + '）。'; },
      badResponse: 'API 返回的格式本页无法识别。',
      timeout: '搜索耗时过长，已停止，请重试。',
      network: '无法连接 API。可能是网络问题，也可能是浏览器跨源限制。',
      noResults: 'API 未返回与此查询相关的段落。',
      withheld: function (n) { return ' 另有 ' + n + ' 条匹配记录未发布。'; },
      shown: function (n) { return '已显示 ' + n + ' 个段落。'; },
      firstN: function (n) { return ' 仅显示前 ' + n + ' 个。'; },
      flagged: 'API 已标记此段落，其文本在此隐藏。',
      rank: 'API 排序', revision: '修订', status: '状态',
      kc2: function (st) { return 'KC2 准入：' + st + '；检索不授予任何操作权限'; },
      uncertainty: '不确定性', missing: '缺失'
    }
  };
  function messages(lang) { return I18N[lang] || I18N.en; }

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
    var kc2 = r.kc2 && typeof r.kc2 === 'object' && typeof r.kc2.state === 'string' ? r.kc2.state : r.kc2_admission;
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

  function describeStatus(status, lang) {
    var M = messages(lang);
    if (status === 400) return failure('http_400', M.http400);
    if (status === 429) return failure('rate_limited', M.rateLimited);
    if (status === 502 || status === 503 || status === 504) return failure('unavailable', M.unavailable);
    return failure('http_other', M.httpOther(status));
  }

  /**
   * One search request. deps = { fetch, AbortController, setTimeout, clearTimeout } (injectable for tests).
   * Resolves to a view model: { state: 'ok' | 'empty' | 'error', kind, message, items, nextCursor, withheld }.
   */
  function runSearch(deps, rawQuery, cursor, hooks) {
    var M = messages(deps.lang);
    var query = normalizeQuery(rawQuery);
    if (!query) return Promise.resolve(failure('invalid_query', M.typeQuery));
    if (query.length > MAX_QUERY) return Promise.resolve(failure('invalid_query', M.tooLong(MAX_QUERY)));
    var controller = new deps.AbortController();
    if (hooks && hooks.onController) hooks.onController(controller);
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
      if (!res.ok) return describeStatus(res.status, deps.lang);
      return res.json().then(function (body) {
        if (!body || typeof body !== 'object' || body.schema !== SCHEMA || !Array.isArray(body.results) || !body.page || typeof body.page !== 'object') {
          return failure('bad_response', M.badResponse);
        }
        var items = body.results.map(toViewItem).filter(Boolean);
        var next = typeof body.page.next_cursor === 'string' && /^[A-Za-z0-9_-]{1,256}$/.test(body.page.next_cursor) ? body.page.next_cursor : null;
        var withheld = typeof body.withheld === 'number' && isFinite(body.withheld) ? body.withheld : 0;
        if (items.length === 0) return { state: 'empty', kind: 'no_results', message: M.noResults, items: [], nextCursor: null, withheld: withheld };
        return { state: 'ok', kind: 'results', message: '', items: items, nextCursor: next, withheld: withheld };
      }, function () {
        return failure('bad_response', M.badResponse);
      });
    }, function () {
      if (timedOut) return failure('timeout', M.timeout);
      return failure('network', M.network);
    }).then(function (vm) {
      deps.clearTimeout(timer);
      return vm;
    });
  }

  var api = {
    API_ORIGIN: API_ORIGIN, SCHEMA: SCHEMA, PAGE_SIZE: PAGE_SIZE, MAX_RESULTS: MAX_RESULTS, TIMEOUT_MS: TIMEOUT_MS, MAX_QUERY: MAX_QUERY,
    messages: messages, normalizeQuery: normalizeQuery, buildUrl: buildUrl, safeLink: safeLink, toViewItem: toViewItem, describeStatus: describeStatus, runSearch: runSearch
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;

  // ---- DOM binding (browser only) ----------------------------------------------------------------------------------------
  // The page is a client-rendered single-page app: the search form exists only on the search route, so the
  // application calls KcpSearch.mount(document) after each render of that route.
  function mount(doc) {
  if (!doc || !doc.getElementById) return;
  var form = doc.getElementById('search-form');
  if (!form) return;
  var input = doc.getElementById('search-q');
  var statusEl = doc.getElementById('search-status');
  var list = doc.getElementById('search-results');
  var more = doc.getElementById('search-more');
  var inflight = null; // AbortController of the request that is currently running
  var current = null; // { q, cursor }
  var serial = 0;
  var lang = (doc.documentElement && doc.documentElement.lang) || 'en';
  var M = messages(lang);

  var deps = {
    fetch: function (u, o) { return root.fetch(u, o); },
    AbortController: root.AbortController,
    setTimeout: function (f, ms) { return root.setTimeout(f, ms); },
    clearTimeout: function (t) { root.clearTimeout(t); },
    lang: lang
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
    if (it.flagged) li.appendChild(el('p', 'result-note', M.flagged));
    else if (it.snippet) li.appendChild(el('p', 'result-snippet', it.snippet + (it.snippetTruncated ? ' …' : '')));
    var meta = [M.rank + ' ' + rank];
    if (it.path) meta.push(it.path);
    if (it.revision) meta.push(M.revision + ' ' + it.revision);
    if (it.status) meta.push(M.status + ' ' + it.status);
    if (it.license) meta.push(it.license);
    if (meta.length) li.appendChild(el('p', 'result-meta', meta.join(' · ')));
    var marks = [];
    if (it.kc2) marks.push(M.kc2(it.kc2.replace(/_/g, ' ')));
    if (it.uncertainty.length) marks.push(M.uncertainty + ': ' + it.uncertainty.join(', '));
    if (it.missing.length) marks.push(M.missing + ': ' + it.missing.join(', '));
    if (marks.length) li.appendChild(el('p', 'result-meta', marks.join(' | ')));
    return li;
  }

  function finish(vm, append, myserial, query) {
    if (myserial !== serial) return; // a newer search replaced this one
    inflight = null;
    form.removeAttribute('aria-busy');
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
      setStatus(vm.message + (vm.withheld ? M.withheld(vm.withheld) : ''), 'empty');
      return;
    }
    vm.items.forEach(function (it) { list.appendChild(renderItem(it, list.children.length + 1)); });
    var shown = list.children.length;
    current = { q: query, cursor: shown < MAX_RESULTS ? vm.nextCursor : null };
    more.hidden = !current.cursor;
    setStatus(M.shown(shown) + (current.cursor ? '' : (vm.nextCursor ? M.firstN(MAX_RESULTS) : '')), 'ok');
  }

  function start(query, cursor, append) {
    // A newer search replaces the one in flight: abort it and ignore whatever it still reports.
    if (inflight) inflight.abort();
    serial += 1;
    var myserial = serial;
    form.setAttribute('aria-busy', 'true');
    more.disabled = true;
    setStatus(M.searching, 'loading');
    runSearch(deps, query, cursor, { onController: function (c) { inflight = c; } }).then(function (vm) { finish(vm, append, myserial, normalizeQuery(query)); });
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
  var prefill = '';
  // The header search sends ?q=, in-page links may send ?dq=; accept both.
  try { var qs = new URLSearchParams(root.location.search); prefill = qs.get('dq') || qs.get('q') || ''; } catch (e) { prefill = ''; }
  if (prefill) { input.value = prefill; start(prefill, null, false); }
  }

  api.mount = mount;
  root.KcpSearch = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
