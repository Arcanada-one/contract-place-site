// Unit tests for the consent gate of the Google Analytics 4 loader.
// Run: node scripts/test_analytics.js
'use strict';
const assert = require('node:assert/strict');
const createAnalytics = require('../src/site/analytics.js');

let n = 0;
function t(name, fn) { fn(); n += 1; console.log('ok ' + name); }

// A minimal window stand-in: records every script the loader inserts.
function fakeWindow(initial) {
  const store = new Map(initial ? Object.entries(initial) : []);
  const scripts = [];
  const listeners = {};
  const head = {
    appendChild(node) { scripts.push(node); },
  };
  const body = {
    appendChild(node) { scripts.push(node); },
    removeChild(node) { const i = scripts.indexOf(node); if (i >= 0) scripts.splice(i, 1); },
  };
  const win = {
    document: {
      documentElement: { lang: 'en' },
      head,
      body,
      title: 'contract.place',
      createElement(tag) {
        const el = { tagName: String(tag).toUpperCase(), attributes: {}, className: '', textContent: '', children: [], setAttribute(k, v) { this.attributes[k] = v; }, appendChild(child) { this.children.push(child); return child; } };
        return el;
      },
      addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
    },
    location: { href: 'https://contract.place/en/' },
    localStorage: {
      getItem(key) { return store.has(key) ? store.get(key) : null; },
      setItem(key, value) { store.set(key, String(value)); },
    },
    listeners,
    scripts,
  };
  return win;
}

(t('a fresh reader stores no choice and no tag is requested', () => {
  const win = fakeWindow();
  const a = createAnalytics(win);
  a.install();
  assert.equal(a.storedChoice(), null);
  assert.equal(win.scripts.length, 1, 'only the consent banner is added');
  assert.equal(win.scripts[0].className, 'consent-banner');
  assert.equal(win.scripts.filter(s => s.tagName === 'SCRIPT').length, 0);
}));

(t('the tag URL is the reviewed measurement id on the Google host', () => {
  const a = createAnalytics(fakeWindow());
  assert.equal(a.MEASUREMENT_ID, 'G-C5J1NVE11Z');
  assert.equal(a.tagSrc(), 'https://www.googletagmanager.com/gtag/js?id=G-C5J1NVE11Z');
  assert.equal(a.STORAGE_KEY, 'cookie-consent');
}));

(t('a necessary-only choice never requests the tag', () => {
  const a = createAnalytics(fakeWindow());
  assert.equal(a.shouldLoadTag('functional'), false);
  assert.equal(a.shouldLoadTag(null), false);
  assert.equal(a.shouldLoadTag('accepted'), true);
}));

(t('only the two known choices are stored', () => {
  const a = createAnalytics(fakeWindow());
  assert.equal(a.storeChoice('nope'), null);
  assert.equal(a.storedChoice(), null);
  assert.equal(a.storeChoice('functional'), 'functional');
  assert.equal(a.storedChoice(), 'functional');
  assert.equal(a.storeChoice('accepted'), 'accepted');
  assert.equal(a.storedChoice(), 'accepted');
}));

(t('consent mode grants analytics only and denies advertising', () => {
  const a = createAnalytics(fakeWindow());
  assert.deepEqual(a.consentDefaults(), {
    analytics_storage: 'granted', ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied',
  });
}));

(t('the banner follows the interface language', () => {
  const win = fakeWindow();
  win.document.documentElement.lang = 'ru';
  assert.ok(/аналитик/i.test(createAnalytics(win).currentText().title));
  win.document.documentElement.lang = 'zh-Hans';
  assert.ok(/Cookie/.test(createAnalytics(win).currentText().title));
  win.document.documentElement.lang = 'en';
  assert.ok(/Analytics/.test(createAnalytics(win).currentText().title));
}));

(t('an accepted reader starts the tag on install, a declined one does not', () => {
  const accepted = fakeWindow({ 'cookie-consent': 'accepted' });
  const a1 = createAnalytics(accepted);
  a1.install();
  const tags = accepted.scripts.filter(s => s.tagName === 'SCRIPT');
  assert.equal(tags.length, 1);
  assert.equal(tags[0].src, 'https://www.googletagmanager.com/gtag/js?id=G-C5J1NVE11Z');
  assert.ok(accepted.dataLayer.length >= 3, 'consent default, js and config are queued');

  const declined = fakeWindow({ 'cookie-consent': 'functional' });
  const a2 = createAnalytics(declined);
  a2.install();
  assert.equal(declined.scripts.filter(s => s.tagName === 'SCRIPT').length, 0);
  assert.equal(declined.scripts.filter(s => s.className === 'consent-banner').length, 0);
}));

(t('no page view is sent before the tag exists', () => {
  const win = fakeWindow();
  const a = createAnalytics(win);
  a.install();
  a.pageView();
  assert.equal(win.dataLayer, undefined, 'no data layer before consent');
}));

(t('a page view is sent after consent and carries the current location', () => {
  const win = fakeWindow({ 'cookie-consent': 'accepted' });
  const a = createAnalytics(win);
  a.install();
  const before = win.dataLayer.length;
  win.location.href = 'https://contract.place/ru/about/';
  a.pageView();
  assert.equal(win.dataLayer.length, before + 1);
  const event = win.dataLayer[before];
  assert.equal(event[0], 'event');
  assert.equal(event[1], 'page_view');
  assert.equal(event[2].page_location, 'https://contract.place/ru/about/');
}));

(t('the open banner follows a later language change', () => {
  const win = fakeWindow();
  const a = createAnalytics(win);
  a.install();
  const banner = win.scripts[0];
  const title = banner.children[0].children[0];
  assert.ok(/Analytics/.test(title.textContent));
  win.document.documentElement.lang = 'ru';
  a.refreshBanner();
  assert.ok(/Аналитика/.test(title.textContent));
  win.document.documentElement.lang = 'zh-Hans';
  a.refreshBanner();
  assert.ok(/分析/.test(title.textContent));
}));

console.log('analytics consent tests OK (' + n + ' cases)');
