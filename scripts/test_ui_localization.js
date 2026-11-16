// Bounded UI tests against the shipped catalogue and the actual app renderer.
// Synthetic metadata verifies display plumbing, not translation quality or review.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const os = require('node:os');
const {spawnSync} = require('node:child_process');
const root = path.resolve(__dirname, '..');
const content = fs.readFileSync(path.join(root, 'public/content.js'), 'utf8');
const data = JSON.parse(content.slice(content.indexOf('=') + 1).trim().replace(/;$/, ''));
const app = fs.readFileSync(path.join(root, 'src/site/app.js'), 'utf8');
const langs = ['en', 'ru', 'zh-Hans'];
const elements = Object.fromEntries(['#header', '#main', '#footer', '.skip', 'meta[name="description"]'].map(k => [k, {innerHTML: '', textContent: '', content: '', querySelector: () => null, addEventListener() {}, focus() {}}]));
const assigned = [], pushed = [], listeners = {};
let scrolled;
const context = {
  document: {documentElement: {lang: 'en', dataset: {theme: 'light'}}, querySelector: s => elements[s] || null,
    querySelectorAll: () => [], addEventListener(type, fn) { (listeners[type] ||= []).push(fn); }, title: '',
    getElementById(id) { return {scrollIntoView() { scrolled = id; }}; }},
  location: {pathname: '/en/about/', search: '', hash: '', origin: 'https://contract.place', assign(href) { assigned.push(href); }},
  history: {replaceState() {}, pushState(...args) {pushed.push(args);}},
  localStorage: {getItem() {return null;}, setItem() {}},
  window: {CP_CONTENT: data, addEventListener() {}, scrollTo() {}},
  URL, URLSearchParams, Intl, Date, console, setTimeout
};
vm.createContext(context); vm.runInContext(app, context);
context.localeHref = vm.runInContext('localeHref', context);
let cases = 0, journalJoins = 0, programmeJoins = 0, readerJoins = 0;
function check(name, fn) {try {fn(); cases++;} catch(e) {e.message = name + ': ' + e.message; throw e;}}
function route(lang, bare, hash = '') {
  context.location.pathname = '/' + lang + '/' + (bare ? bare + '/' : '');
  context.location.hash = hash; context.location.search = '';
  vm.runInContext(`locale=${JSON.stringify(lang)}`, context);
}
function headings(html) {return [...html.matchAll(/<h([23])\b[^>]*\bid="([^"]+)"[^>]*>/g)].map(m => ({level: m[1], id: m[2]}));}

for (const lang of langs) {
  route(lang, 'about'); context.render();
  check('about and footer labels ' + lang, () => {
    assert.equal(context.document.documentElement.lang, lang);
    assert.equal(elements['.skip'].textContent, {en: 'Skip to main content', ru: 'Перейти к содержимому', 'zh-Hans': '跳转至主要内容'}[lang]);
    if (lang !== 'en') assert.doesNotMatch(elements['#main'].innerHTML + elements['#footer'].innerHTML, /Text by Pavel|Attribution guidance|Published source code is available|>Attribution<|Google Privacy &amp; Terms/);
    assert.match(elements['#main'].innerHTML, /CC BY 4\.0/);
    assert.match(elements['#main'].innerHTML, /NOTICE/);
  });
  route(lang, 'journal/building-a-place'); context.render();
  check('historic journal prose ' + lang, () => {
    assert.match(elements['#main'].innerHTML, /datetime="2026-11-04"/);
    if (lang !== 'en') assert.doesNotMatch(elements['#main'].innerHTML, /This first edition|A library with room to grow|The following article is available in English/);
  });
  route(lang, 'lab/knowledge-journey'); context.render();
  check('public Lab shell ' + lang, () => {
    assert.match(elements['#main'].innerHTML, /data-live-lab-state="unconnected"/);
    assert.match(elements['#main'].innerHTML, /fieldset disabled/);
    if (lang !== 'en') assert.doesNotMatch(elements['#main'].innerHTML, /Live|Replay/);
  });
  route(lang, '__missing_route__'); context.render();
  check('unknown routes retain their locale after JavaScript renders ' + lang, () => {
    const expected = {en: ['This page could not be found.', 'Back to home'], ru: ['Страница не найдена.', 'На главную'], 'zh-Hans': ['未找到此页面。', '返回首页']}[lang];
    assert.equal(context.document.documentElement.lang, lang);
    assert.ok(elements['#main'].innerHTML.includes(expected[0]));
    assert.ok(elements['#main'].innerHTML.includes(expected[1]));
    assert.ok(elements['#main'].innerHTML.includes('href="/' + lang + '/"'));
    assert.equal((elements['#main'].innerHTML.match(/<h1\b/g) || []).length, 1);
    assert.doesNotMatch(elements['#main'].innerHTML, /data-shared-error/);
  });
  route(lang, 'journal');
  for (const issue of data.journal_issues) check('daily issue searchable ' + lang + '/' + issue.slug, () => {
    assert.ok(context.searchItems(issue.languages[lang].title).some(i => i.path === issue.route));
  });
}

for (const issue of data.journal_issues) for (const from of langs) for (const to of langs.filter(l => l !== from)) {
  const before = headings(issue.languages[from].html), after = headings(issue.languages[to].html);
  check('journal structural correspondence ' + issue.slug + from + to, () => assert.deepEqual(before.map(h => h.level), after.map(h => h.level)));
  before.forEach((h, i) => {
    route(from, issue.route, '#' + encodeURIComponent(h.id));
    check('journal anchor ' + issue.slug + from + to + i, () => assert.equal(context.localeHref(to), '/' + to + '/' + issue.route + '/#' + encodeURIComponent(after[i].id)));
    journalJoins++;
  });
}
for (const from of langs) for (const to of langs.filter(l => l !== from)) {
  const before = data.programme.pages[from], after = data.programme.pages[to];
  const fromIds = [before.title_id, ...headings(before.html).map(h => h.id), 'programme-foundations', 'programme-source'];
  const toIds = [after.title_id, ...headings(after.html).map(h => h.id), 'programme-foundations', 'programme-source'];
  fromIds.forEach((id, i) => {
    route(from, 'programme', '#' + encodeURIComponent(id));
    check('programme anchor ' + from + to + i, () => assert.equal(context.localeHref(to), '/' + to + '/programme/#' + encodeURIComponent(toIds[i])));
    programmeJoins++;
  });
}
for (const record of data.records.filter(r => r.renditions?.ru && r.renditions?.['zh-Hans'])) {
  for (const from of langs) for (const to of langs.filter(l => l !== from)) {
    const before = from === 'en' ? record : record.renditions[from], after = to === 'en' ? record : record.renditions[to];
    if (!before.title_id || !after.title_id) continue;
    route(from, context.recordPath(record), '#' + encodeURIComponent(before.title_id));
    check('reader H1 ' + record.id + from + to, () => assert.equal(context.localeHref(to), '/' + to + '/' + context.recordPath(record) + '/#' + encodeURIComponent(after.title_id)));
    readerJoins++;
  }
}
check('malformed hash is not carried', () => {
  route('ru', 'programme', '#%E0%A4%A'); assert.equal(context.localeHref('zh-Hans'), '/zh-Hans/programme/');
});
check('unknown translated heading is not invented', () => {
  route('ru', data.journal_issues[0].route, '#unknown-heading'); assert.equal(context.localeHash('en', data.journal_issues[0].route), '');
});
check('structural mismatch refuses positional mapping', () => {
  const issue = data.journal_issues[0], old = issue.languages['zh-Hans'].html;
  issue.languages['zh-Hans'].html = old.replace(/<h2\b[^>]*>[\s\S]*?<\/h2>/, '');
  route('en', issue.route, '#' + headings(issue.languages.en.html)[0].id);
  assert.equal(context.localeHash('zh-Hans', issue.route), ''); issue.languages['zh-Hans'].html = old;
});
check('all locale changes load the prerendered page', () => {
  route('ru', 'about'); context.changeLocale('zh-Hans'); assert.equal(assigned.at(-1), '/zh-Hans/about/'); assert.equal(pushed.length, 0);
});
check('route changes load coherent head metadata, same-route query remains local', () => {
  route('ru', 'about'); context.navigate('/ru/research/');
  assert.equal(assigned.at(-1), 'https://contract.place/ru/research/'); assert.equal(pushed.length, 0);
  route('ru', 'search'); context.navigate('/ru/search/?q=knowledge'); assert.equal(pushed.length, 1);
});
check('Lab language links retain only permitted view selectors', () => {
  route('en', 'lab/knowledge-journey', '#private-fragment'); context.location.search = '?run=r1&node=n1&token=private-value';
  assert.equal(context.localeHref('ru'), '/ru/lab/knowledge-journey/?run=r1&node=n1');
  context.changeLocale('ru'); assert.equal(assigned.at(-1), '/ru/lab/knowledge-journey/?run=r1&node=n1');
});
check('same-language scrolling decodes Unicode safely', () => {
  route('ru', 'about', '#' + encodeURIComponent('источник')); context.navigate('/ru/about/#' + encodeURIComponent('источник'));
  assert.equal(scrolled, 'источник');
});
check('declared scientific section mapping uses canonical source alias', () => {
  const r = data.records.find(r => r.renditions?.ru?.state === 'reviewed'), old = r.renditions.ru.sections;
  r.renditions.ru.sections = [{source: r.toc[0].id, rendition: 'синтетический-раздел'}];
  route('ru', context.recordPath(r), '#' + encodeURIComponent('синтетический-раздел'));
  assert.equal(context.localeHash('zh-Hans', context.recordPath(r)), '#' + encodeURIComponent(r.toc[0].id)); r.renditions.ru.sections = old;
});

// A closed compiled metadata overlay localizes discovery, independently of body review.
const fixture = data.records[0], priorLocalization = fixture.localization;
fixture.localization = {ru: {title: 'Тестовое название', summary: 'Тестовое резюме', status: 'unreviewed'}, 'zh-Hans': {title: '测试标题', summary: '测试摘要', status: 'unreviewed'}};
for (const lang of ['ru', 'zh-Hans']) {
  route(lang, context.recordPath(fixture)); context.render();
  check('localized discovery and lead metadata ' + lang, () => {
    assert.equal(context.recordTitle(fixture), fixture.localization[lang].title);
    assert.equal(context.recordSummary(fixture), fixture.localization[lang].summary);
    assert.match(context.paperCard(fixture), new RegExp(fixture.localization[lang].title));
    assert.match(context.paperCard(fixture), new RegExp(fixture.localization[lang].summary));
    assert.match(elements['#main'].innerHTML, new RegExp('<p class="lead" lang="' + lang + '">' + fixture.localization[lang].summary));
    assert.ok(context.searchItems(fixture.localization[lang].title).some(r => r.path === context.recordPath(fixture)));
    assert.equal(elements['meta[name="description"]'].content, fixture.localization[lang].summary);
    assert.match(elements['#main'].innerHTML, new RegExp(fixture.revision));
  });
}
check('metadata overlay does not promote stale body translation', () => {
  const old = fixture.renditions;
  fixture.renditions = {ru: {state: 'stale', title: 'Устаревшее название'}}; route('ru', context.recordPath(fixture));
  assert.equal(context.recordRendition(fixture), null);
  assert.equal(context.recordTitle(fixture), 'Тестовое название');
  assert.match(context.recordBodyLabel(fixture), /английском/);
  fixture.renditions = old;
});
fixture.localization = priorLocalization;
check('legacy article overlay supplies prose and image description', () => {
  const a = data.articles[0], old = a.translations;
  a.translations = {ru: {title: 'Название статьи', description: 'Описание статьи', status: 'Статус\n\nОграничения результата', abstract: 'Перевод аннотации'}};
  route('ru', 'journal/' + a.id); const html = context.publication(a);
  assert.match(html, /Название статьи/); assert.match(html, /Перевод аннотации/); assert.match(html, /lang="ru"/);
  assert.match(html, /Перевод закреплённого английского отрывка\. Смысловая рецензия ещё не выполнена\./);
  assert.match(html, /Ограничения результата/);
  assert.doesNotMatch(html, /Original schematic|Original illustration/); a.translations = old;
});
check('roadmap prose overlay preserves identities', () => {
  const old = data.roadmap.translations;
  data.roadmap.translations = {ru: {introduction: 'Введение в план', tasks: data.roadmap.tasks.map(t => ({...t, display_name: 'Задача ' + t.id}))}};
  route('ru', 'roadmap'); assert.equal(context.roadmapView().introduction, 'Введение в план');
  assert.equal(context.roadmapName(data.roadmap.tasks[0].id), 'Задача ' + data.roadmap.tasks[0].id);
  assert.equal(context.roadmapView().pin.commit, data.roadmap.pin.commit);
  assert.match(context.roadmapPage(), /Перевод закреплённого снимка дорожной карты без смысловой рецензии/);
  data.roadmap.translations = old;
});
for (const lang of ['ru', 'zh-Hans']) check('human roadmap file roles ' + lang, () => {
  route(lang, 'roadmap');
  for (const role of ['rendered', 'linked', 'introduction', 'rendition', 'rendition-manifest']) assert.ok(!context.roadmapFileRole(role).includes(role));
});

// Exercise the actual prerenderer in a disposable directory, never generated public/.
let sharedErrorHtml;
check('no-JavaScript skip links are localized in prerendered bytes', () => {
  const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'kc-ui-localization-'));
  try {
    for (const [source, target] of [['src/site/index.html', 'index.html'], ['src/site/app.js', 'app.js'], ['public/content.js', 'content.js'], ['src/renditions/renditions.js', 'renditions.js']]) fs.copyFileSync(path.join(root, source), path.join(temp, target));
    const result = spawnSync(process.execPath, [path.join(root, 'src/prerender.mjs'), temp], {encoding: 'utf8'});
    assert.equal(result.status, 0, result.stderr);
    sharedErrorHtml = fs.readFileSync(path.join(temp, '404.html'), 'utf8');
    for (const lang of langs) assert.equal(fs.existsSync(path.join(temp, lang, 'not-found/index.html')), false);
    for (const [lang, skip] of [['en', 'Skip to main content'], ['ru', 'Перейти к содержимому'], ['zh-Hans', '跳转至主要内容']]) {
      const html = fs.readFileSync(path.join(temp, lang, 'about/index.html'), 'utf8');
      assert.ok(html.includes('<a class="skip" href="#main">' + skip + '</a>'));
      assert.ok(html.includes('https://contract.place/' + lang + '/about/'));
    }
  } finally {fs.rmSync(temp, {recursive: true, force: true});}
});
check('the one shared static 404 contains three complete language sections without JavaScript', () => {
  assert.equal((sharedErrorHtml.match(/<h1\b/g) || []).length, 1);
  assert.match(sharedErrorHtml, /data-shared-error="404"/);
  assert.match(sharedErrorHtml, /<meta name="robots" content="noindex">/);
  assert.doesNotMatch(sharedErrorHtml, /<link rel="canonical"|<link rel="alternate"|http-equiv="refresh"/);
  for (const [lang, label, text, home] of [
    ['en', 'English', 'This page could not be found.', 'Back to home'],
    ['ru', 'Русский', 'Страница не найдена.', 'На главную'],
    ['zh-Hans', '简体中文', '未找到此页面。', '返回首页']
  ]) {
    const section = sharedErrorHtml.match(new RegExp('<section lang="' + lang + '" aria-labelledby="error-language-' + lang + '">([\\s\\S]*?)</section>'));
    assert.ok(section, lang + ' language-labelled error section');
    assert.ok(section[1].includes('<h2 id="error-language-' + lang + '">' + label + '</h2>'));
    assert.ok(section[1].includes('<p class="lead">' + text + '</p>'));
    assert.ok(section[1].includes('<a class="button" href="/' + lang + '/">' + home + '</a>'));
  }
});


// Feed discovery updates only existing metadata on eligible, indexable pages.
// These controls run the actual app render, including locale selection.
{
  const queryOne = context.document.querySelector;
  const queryMany = context.document.querySelectorAll;
  let robots = null, feedLinks = [];
  const makeLinks = () => ['rss', 'atom'].map(format => ({
    attrs: {'data-journal-feed': format, href: 'https://contract.place/en/journal/' + format + '.xml'},
    removed: false,
    getAttribute(name) {return this.attrs[name];},
    setAttribute(name, value) {this.attrs[name] = value;},
    remove() {this.removed = true;},
  }));
  context.document.querySelector = selector => selector === 'meta[name="robots"]' ? robots : queryOne(selector);
  context.document.querySelectorAll = selector => selector === 'link[data-journal-feed]' ? feedLinks : queryMany(selector);
  try {
    for (const lang of langs) {
      for (const bare of ['', 'journal', data.journal_issues[0].route]) {
        robots = null; feedLinks = makeLinks(); route(lang, bare); context.render();
        check('feed discovery locale ' + lang + '/' + bare, () => {
          assert.equal(feedLinks.length, 2);
          for (const link of feedLinks) {
            assert.equal(link.removed, false);
            assert.equal(link.attrs.href, 'https://contract.place/' + lang + '/journal/' + link.attrs['data-journal-feed'] + '.xml');
          }
        });
      }
      for (const bare of ['journal/building-a-place', 'lab/knowledge-journey', '__missing_route__',
                           Object.keys(data.aliases)[0], data.records[0].route.replace(/^\/en\/|\/$/g, '')]) {
        robots = null; feedLinks = makeLinks(); route(lang, bare); context.render();
        check('feed discovery stale tags removed ' + lang + '/' + bare, () => {
          assert.ok(feedLinks.every(link => link.removed));
        });
      }
      robots = {content: 'noindex,follow'}; feedLinks = makeLinks(); route(lang, 'journal'); context.render();
      check('feed discovery obeys noindex even on a journal route ' + lang, () => {
        assert.ok(feedLinks.every(link => link.removed));
      });
      robots = {content: 'noindex,follow'}; feedLinks = []; route(lang, 'journal/building-a-place'); context.render();
      check('feed discovery never creates missing metadata on noindex ' + lang, () => {
        assert.deepEqual(feedLinks, []);
      });
    }
  } finally {
    context.document.querySelector = queryOne;
    context.document.querySelectorAll = queryMany;
  }
}

console.log(JSON.stringify({schema: 'kc-ui-localization/v1', scope: 'compiled UI and navigation; no native execution or translation acceptance', cases, journal_anchor_joins: journalJoins, programme_anchor_joins: programmeJoins, reader_title_joins: readerJoins, result: 'PASS'}));

