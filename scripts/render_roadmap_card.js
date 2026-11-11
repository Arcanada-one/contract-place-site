'use strict';
/**
 * Test-only harness: load src/site/app.js under Node and print roadmapCard HTML.
 * Stubs browser globals; does not change browser behaviour of app.js.
 *
 * Usage: node scripts/render_roadmap_card.js <locale> [taskId]
 */
const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');
const locale = process.argv[2] || 'en';
const taskId = process.argv[3] || 'RM-12';
const appPath = process.argv[4]
  ? path.resolve(process.argv[4])
  : path.join(root, 'src/site/app.js');

const noop = () => {};
const el = () => ({
  innerHTML: '',
  textContent: '',
  content: '',
  focus: noop,
  addEventListener: noop,
  setAttribute: noop,
  getAttribute: () => null,
  querySelector: () => el(),
  querySelectorAll: () => [],
  classList: { add: noop, remove: noop },
  style: {},
});

global.window = global;
global.window.addEventListener = noop;
global.window.removeEventListener = noop;
global.matchMedia = () => ({
  matches: false,
  addListener: noop,
  removeListener: noop,
  addEventListener: noop,
  removeEventListener: noop,
});
global.localStorage = { getItem: () => null, setItem: noop, removeItem: noop };
global.document = {
  documentElement: { dataset: { theme: 'light' }, lang: 'en' },
  querySelector: () => el(),
  querySelectorAll: () => [],
  getElementById: () => null,
  addEventListener: noop,
  body: el(),
};
global.location = {
  pathname: `/${locale}/roadmap/`,
  search: '',
  hash: '',
  origin: 'https://contract.place',
  href: `https://contract.place/${locale}/roadmap/`,
};
global.history = { replaceState: noop, pushState: noop };
try {
  Object.defineProperty(global, 'navigator', {
    value: { clipboard: { writeText: async () => {} } },
    configurable: true,
  });
} catch {
  /* Node may expose a read-only navigator; app.js only needs it in browser handlers. */
}

const contentJs = fs.readFileSync(path.join(root, 'public/content.js'), 'utf8');
const data = JSON.parse(contentJs.replace(/^window\.CP_CONTENT\s*=\s*/, '').replace(/;\s*$/, ''));
global.window.CP_CONTENT = data;

delete require.cache[require.resolve(appPath)];
const api = require(appPath);
if (!api || typeof api.roadmapCard !== 'function' || typeof api.setTestLocale !== 'function') {
  console.error('app.js did not export roadmapCard/setTestLocale for tests');
  process.exit(2);
}
api.setTestLocale(locale);
const task = data.roadmap.tasks.find((t) => t.id === taskId);
if (!task) {
  console.error('missing task ' + taskId);
  process.exit(2);
}
process.stdout.write(api.roadmapCard(task));
