// SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
// SPDX-License-Identifier: Apache-2.0
// Real renderer + retained registry identity; synthetic rows are never published.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {createHash} = require('node:crypto');
const root = path.resolve(__dirname, '..');
const app = fs.readFileSync(path.join(root, 'src/site/app.js'), 'utf8');
const content = fs.readFileSync(path.join(root, 'public/content.js'), 'utf8');
const data = JSON.parse(content.slice(content.indexOf('=') + 1).trim().replace(/;$/, ''));
const source = Object.freeze({
  repository: 'Arcanada-one/books-library',
  revision: '75f9d778c5159f1e42366b2c36167c0f33790909',
  path: 'registry/registry.json',
  blob: '03a51a17b4cb593b41a4b14ea77cff1b772d28de',
  sha256: '701c0f7194b38bf16e95f1a4d30e6b34acb3a33861e868f17b0d56b0188a2901',
});
// Exact registry bytes read at the source above, not a fabricated nonempty title.
const rawRegistry = '{\n  "schema": "BooksLibraryRegistry/v1",\n  "entries": []\n}\n';
assert.equal(createHash('sha256').update(rawRegistry).digest('hex'), source.sha256);
assert.equal(createHash('sha1').update('blob ' + Buffer.byteLength(rawRegistry) + '\0' + rawRegistry).digest('hex'), source.blob);
const registry = JSON.parse(rawRegistry);
const expected = {
  en: {empty: 'No books are listed in this snapshot.', scope: 'Historical snapshot of the library register.', limit: 'does not establish the current inventory or permission to publish or redistribute a book.', count: 'entries in this snapshot'},
  ru: {empty: 'В этом снимке нет записей о книгах.', scope: 'Исторический снимок реестра библиотеки.', limit: 'не подтверждает текущий состав библиотеки и не даёт разрешения публиковать или распространять книгу.', count: 'записей в этом снимке'},
  'zh-Hans': {empty: '此快照未列出任何图书。', scope: '图书库登记表的历史快照。', limit: '不能证明当前馆藏情况，也不授予出版或再分发图书的许可。', count: '条记录（仅限此快照）'},
};
function makeContext(code = app) {
  const elements = Object.fromEntries(['#header', '#main', '#footer', '.skip', 'meta[name="description"]'].map(k => [k, {innerHTML: '', textContent: '', content: '', querySelector: () => null, addEventListener() {}, focus() {}}]));
  const context = {
    document: {documentElement: {lang: 'en', dataset: {theme: 'light'}}, querySelector: s => elements[s] || null,
      querySelectorAll: () => [], addEventListener() {}, title: '', getElementById() {return null;}},
    location: {pathname: '/en/books/', search: '', hash: '', origin: 'https://contract.place', assign() {}},
    history: {replaceState() {}, pushState() {}}, localStorage: {getItem() {return null;}, setItem() {}},
    window: {CP_CONTENT: data, addEventListener() {}, scrollTo() {}}, URL, URLSearchParams, Intl, Date, console, setTimeout,
  };
  vm.createContext(context); vm.runInContext(code, context);
  return {context, elements};
}
function render(c, lang) {
  c.context.location.pathname = '/' + lang + '/books/';
  vm.runInContext(`locale=${JSON.stringify(lang)}`, c.context);
  c.context.render();
  return c.elements['#main'].innerHTML;
}
function checkSnapshot(html, lang) {
  const e = expected[lang];
  assert.ok(html.includes('data-library-pin="' + source.revision + '"'), 'exact source pin');
  assert.ok(html.includes(source.repository + '@' + source.revision), 'visible full source revision');
  assert.ok(html.includes(source.path), 'visible source path');
  assert.ok(html.includes('data-library-count="' + registry.entries.length + '"'), 'count bound to registry');
  assert.ok(html.includes('>' + registry.entries.length + ' ' + e.count + '</span>'), 'visible scoped count');
  assert.ok(html.includes(e.empty), 'snapshot empty state');
  assert.ok(html.includes(e.scope) && html.includes(e.limit), 'historical scope and authority limit');
  assert.ok(!html.includes('<tbody>'), 'no invented published row');
  assert.ok(!html.includes('href="https://github.com/Arcanada-one/books-library'), 'no promised public access to private source');
}
let positive = 0, mutants = 0;
const original = makeContext();
const index = JSON.parse(vm.runInContext('JSON.stringify(LIBRARY_INDEX)', original.context));
assert.deepEqual(index, {schema: 'ContractPlaceLibraryIndex/v1', source: source.repository,
  pin: source.revision, registry_path: source.path, registry_blob: source.blob,
  registry_sha256: source.sha256, entries: registry.entries});
positive++;
for (const lang of Object.keys(expected)) {
  checkSnapshot(render(original, lang), lang); positive++;
  checkSnapshot(fs.readFileSync(path.join(root, 'public', lang, 'books/index.html'), 'utf8'), lang); positive++;
}
// A correct, unrelated change must not be mistaken for source drift.
const unrelated = makeContext(app.replace('data-library-pin=', 'data-book-view="snapshot" data-library-pin='));
for (const lang of Object.keys(expected)) {checkSnapshot(render(unrelated, lang), lang); positive++;}
// Test the actual oracle against concrete broken renderer/source variants.
const mutations = [
  ['wrong source pin', s => s.replace("pin:'" + source.revision + "'", "pin:'" + '0'.repeat(40) + "'")],
  ['wrong rendered count', s => s.replace('data-library-count="${rows.length}">${rows.length}', 'data-library-count="1">1')],
  ['missing historical qualification', s => s.replace("${t('libraryHonesty')}", '')],
  ['truncated visible revision', s => s.replace('${esc(LIBRARY_INDEX.pin)}</code>', '${esc(LIBRARY_INDEX.pin.slice(0,12))}</code>')],
];
for (const [name, mutate] of mutations) {
  const changed = mutate(app); assert.notEqual(changed, app, name + ': mutation applied');
  const c = makeContext(changed);
  for (const lang of Object.keys(expected)) {
    assert.throws(() => checkSnapshot(render(c, lang), lang), {name: 'AssertionError'}, name + '/' + lang);
    mutants++;
  }
}
// The preserved table path is exercised with authored synthetic data only.
const synthetic = makeContext();
vm.runInContext(`LIBRARY_INDEX.entries.push({title:'<img src=x>',rights_class:'public_domain',status:'clean',damage_places:2})`, synthetic.context);
for (const lang of Object.keys(expected)) {
  const html = render(synthetic, lang);
  assert.ok(html.includes('&lt;img src=x&gt;') && !html.includes('<img src=x>'), 'escaped synthetic title');
  assert.ok(html.includes('<strong>DAMAGED') && !html.includes('<td>clean</td>'), 'declared damage is never clean');
  assert.ok(html.includes('data-library-count="1"'), 'count comes from supplied rows');
  positive++;
}
console.log(`PASS books snapshot: ${positive} positive controls; ${mutants} adverse locale checks (${mutations.length} actual mutants); retained source entries=${registry.entries.length}; synthetic table rows=1 (test only)`);
