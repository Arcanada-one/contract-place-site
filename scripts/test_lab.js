// Bounded tests for the actual production renderer and locale selection fence.
// Synthetic view identifiers below are not runtime evidence or authority grants.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const element = () => ({innerHTML: '', textContent: '', content: '', querySelector: () => null, addEventListener() {}, focus() {}});
const elements = Object.fromEntries(['#header', '#main', '#footer', '.skip', 'meta[name="description"]'].map(key => [key, element()]));
const context = {
  document: {documentElement: {lang: 'en', dataset: {theme: 'light'}}, querySelector: key => elements[key] || null, querySelectorAll: () => [], addEventListener() {}, title: ''},
  location: {pathname: '/en/lab/knowledge-journey/', search: '', hash: ''},
  URLSearchParams, Intl, Date, console, setTimeout,
  history: {replaceState() {}}, localStorage: {getItem() {return null;}}, window: {addEventListener() {}}
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(root, 'public/content.js'), 'utf8'), context);
vm.runInContext(fs.readFileSync(path.join(root, 'src/site/app.js'), 'utf8'), context);
for (const [query, expected] of [
  ['?run=run-1&node=node.2', '?run=run-1&node=node.2'],
  ['?run=run-1&token=synthetic-only&download=https%3A%2F%2Fexample.invalid%2F&node=node.2', '?run=run-1&node=node.2'],
  ['?run=first&run=second&node=node.2', ''],
  ['?node=node.2', ''],
  ['?run=https%3A%2F%2Fexample.invalid&node=node.2', ''],
  ['?run=run-1&node=%3Cscript%3E', '?run=run-1'],
  ['?run=' + 'a'.repeat(129), '']
]) {
  assert.equal(context.labViewQuery(query), expected);
}
assert.match(elements['#main'].innerHTML, /data-live-lab-state="unconnected"/);
assert.doesNotMatch(elements['#header'].innerHTML, /lab\/knowledge-journey/);
assert.match(elements['#footer'].innerHTML, /lab\/knowledge-journey/);
let assigned;
context.location.assign = value => {assigned = value;};
context.location.search = '?run=run-1&node=node.2&token=synthetic-only';
context.location.hash = '#synthetic-credential';
context.changeLocale('ru');
assert.equal(assigned, '/ru/lab/knowledge-journey/?run=run-1&node=node.2');
console.log('Lab renderer and seven adverse locale-selection cases OK; no runtime invoked.');
