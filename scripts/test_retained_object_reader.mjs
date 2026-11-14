// SPDX-License-Identifier: Apache-2.0
// Native protocol shapes, synthetic bytes and browser doubles. No live grants.
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash, webcrypto } from 'node:crypto';
import {
  createSameOriginRetainedTransport, createRetainedObjectController,
  decodeRetainedObjectList, mountRetainedObjectReader,
} from '../src/site/lab/retained-object-reader.js';

const encode = value => new TextEncoder().encode(value);
const subject = '019af0aa-0000-7000-8000-000000000001';
const otherSubject = '019af0aa-0000-7000-8000-000000000002';
const payload = encode('# Synthetic source\n<script>throw new Error("not executable")</script>\n');
const object = Object.freeze({
  id: 'ro-' + 'a'.repeat(32), run_id: 'synthetic-retained-run', media_type: 'text/markdown',
  size: payload.byteLength, sha256: createHash('sha256').update(payload).digest('hex'),
});
const json = value => new Response(JSON.stringify(value), {
  headers: { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' },
});
const identity = value => json({ authenticated: true, subject: value });
const list = objects => json({ schema: 'RetainedObjectList/v1', objects });
const bytes = (body = payload, overrides = {}) => new Response(body, {
  headers: {
    'content-type': object.media_type, 'cache-control': 'private, no-store',
    'x-object-sha256': object.sha256, 'x-object-size': String(object.size),
    etag: '"' + object.sha256 + '"', 'content-disposition': 'attachment',
    ...overrides,
  },
});
const transport = overrides => ({
  session: async () => identity(subject),
  list: async () => list([object]),
  read: async () => bytes(),
  ...overrides,
});
const controller = (port, options = {}) => createRetainedObjectController({
  transport: port, cryptoImpl: webcrypto, ...options,
});
const deferred = () => {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
};

test('no route configuration means no transport, no network and an explicit unconnected view', async () => {
  let calls = 0;
  assert.equal(createSameOriginRetainedTransport({ fetchImpl: () => { calls += 1; } }), null);
  const view = controller(null);
  assert.equal(view.snapshot().status, 'not_configured');
  assert.equal((await view.refresh()).status, 'not_configured');
  assert.equal((await view.open(object.id)).status, 'not_configured');
  assert.equal(calls, 0);
  view.destroy();
});

test('host mapping refuses ambiguous or service paths and uses only same-origin GET/cookies', async () => {
  for (const path of [
    '//elsewhere.example/objects', 'https://elsewhere.example/objects',
    '/api/../objects', '/api/%2e%2e/objects', '/objects?run=1', '/objects#id',
    '/v1/lab/service/objects',
  ]) assert.throws(() => createSameOriginRetainedTransport({
    origin: 'https://fixture.example', objectListPath: path,
  }), /READER_CONFIGURATION_INVALID/);
  assert.throws(() => createSameOriginRetainedTransport({
    origin: 'http://fixture.example', objectListPath: '/approved/objects',
  }), /READER_CONFIGURATION_INVALID/);
  const seen = [];
  const port = createSameOriginRetainedTransport({
    origin: 'https://fixture.example', objectListPath: '/approved/objects',
    fetchImpl: async (url, options) => {
      seen.push({ url, options });
      const response = identity(subject);
      Object.defineProperty(response, 'url', { value: url });
      return response;
    },
  });
  const signal = new AbortController().signal;
  await port.session({ signal }); await port.list({ signal }); await port.read({ id: object.id, signal });
  assert.deepEqual(seen.map(item => item.url), [
    'https://fixture.example/api/auth/session',
    'https://fixture.example/approved/objects',
    'https://fixture.example/approved/objects/' + object.id,
  ]);
  for (const { options } of seen) {
    assert.equal(options.method, 'GET');
    assert.equal(options.mode, 'same-origin');
    assert.equal(options.credentials, 'same-origin');
    assert.equal(options.cache, 'no-store');
    assert.equal(options.redirect, 'error');
    assert.equal(options.referrerPolicy, 'no-referrer');
    assert.deepEqual(Object.keys(options.headers), ['Accept']);
  }
  assert.throws(() => port.read({ id: '../private', signal }), /OBJECT_NOT_LISTED/);
});

test('same-origin transport rejects a redirected or differently addressed response', async () => {
  for (const variant of ['redirected', 'different-url']) {
    const port = createSameOriginRetainedTransport({
      origin: 'https://fixture.example', objectListPath: '/approved/objects',
      fetchImpl: async url => {
        const response = identity(subject);
        Object.defineProperty(response, 'url', { value: variant === 'different-url' ? 'https://other.example/' : url });
        Object.defineProperty(response, 'redirected', { value: variant === 'redirected' });
        return response;
      },
    });
    await assert.rejects(port.session({ signal: new AbortController().signal }), /READER_RESPONSE_REFUSED/);
  }
});

test('uses the shared strict parser and refuses duplicate ids, locators, runs and oversized lists', () => {
  const source = JSON.stringify({ schema: 'RetainedObjectList/v1', objects: [object] });
  assert.deepEqual(decodeRetainedObjectList(encode(source)), [object]);
  assert.throws(() => decodeRetainedObjectList(encode('{"schema":"RetainedObjectList/v1","schema":"RetainedObjectList/v1","objects":[]}')));
  for (const objects of [
    [object, object],
    [{ ...object, locator: '/private/source.md' }],
    [object, { ...object, id: 'ro-' + 'b'.repeat(32), run_id: 'different-run' }],
    [{ ...object, size: -1 }],
    [{ ...object, sha256: 'incorrect' }],
  ]) assert.throws(() => decodeRetainedObjectList(encode(JSON.stringify({ schema: 'RetainedObjectList/v1', objects }))));
  assert.throws(() => decodeRetainedObjectList(encode(source + ' '.repeat(65532))));
});

test('lists and reads exact native representations with identity checks before and after each operation', async () => {
  let identities = 0, reads = 0;
  const view = controller(transport({
    session: async () => { identities += 1; return identity(subject); },
    read: async ({ id }) => { reads += 1; assert.equal(id, object.id); return bytes(); },
  }));
  assert.equal((await view.refresh()).status, 'listed');
  assert.equal(identities, 2);
  const shown = await view.open(object.id);
  assert.equal(identities, 4);
  assert.equal(reads, 1);
  assert.equal(shown.status, 'inspected');
  assert.equal(shown.inspection.text, new TextDecoder().decode(payload));
  assert.equal(shown.inspection.bytesVerified, true);
  assert.equal(shown.selected.sha256, object.sha256);
  assert.equal('graph' in shown, false);
  assert.equal('admitted' in shown, false);
  view.clear();
  assert.equal(view.snapshot().inspection, null);
  assert.deepEqual(view.snapshot().objects, []);
  view.destroy();
});

test('denied object reads clear old private details even with a valid identity', async () => {
  let deny = false;
  const view = controller(transport({
    read: async () => deny
      ? new Response('private-error-payload', { status: 403, headers: { 'cache-control': 'no-store' } })
      : bytes(),
  }));
  await view.refresh(); await view.open(object.id);
  deny = true;
  const refused = await view.open(object.id);
  assert.equal(refused.status, 'unavailable');
  assert.equal(refused.inspection, null);
  assert.deepEqual(refused.objects, []);
  assert.equal(JSON.stringify(refused).includes('private-error-payload'), false);
  assert.equal(JSON.stringify(refused).includes('not executable'), false);
  view.destroy();
});

test('changed byte content, representation headers and failed identity recheck are refused', async () => {
  for (const mode of ['digest', 'size', 'media', 'subject']) {
    let calls = 0;
    const view = controller(transport({
      session: async () => identity(++calls === 4 && mode === 'subject' ? otherSubject : subject),
      read: async () => {
        if (mode === 'digest') { const tampered = payload.slice(); tampered[0] ^= 1; return bytes(tampered); }
        if (mode === 'size') return bytes(payload, { 'x-object-size': String(object.size + 1) });
        if (mode === 'media') return bytes(payload, { 'content-type': 'text/html' });
        return bytes();
      },
    }));
    await view.refresh();
    const refused = await view.open(object.id);
    assert.equal(refused.status, 'unavailable', mode);
    assert.equal(refused.inspection, null);
    assert.deepEqual(refused.objects, []);
    view.destroy();
  }
});

test('unlisted ids and non-private replies are not used as a byte-reading authority', async () => {
  let reads = 0;
  const view = controller(transport({ read: async () => { reads += 1; return bytes(); } }));
  await view.refresh();
  assert.equal((await view.open('ro-' + 'b'.repeat(32))).reason, 'OBJECT_NOT_LISTED');
  assert.equal(reads, 0); view.destroy();
  const uncacheable = controller(transport({ list: async () => {
    const response = list([object]); response.headers.set('cache-control', 'public, max-age=60'); return response;
  } }));
  assert.equal((await uncacheable.refresh()).status, 'unavailable');
  uncacheable.destroy();
});

test('an oversized streaming list is refused whole and cancels its reader', async () => {
  let cancelled = false;
  const view = controller(transport({ list: async () => new Response(new ReadableStream({
    start(stream) { stream.enqueue(new Uint8Array(65533)); },
    cancel() { cancelled = true; },
  }), { headers: { 'content-type': 'application/json', 'cache-control': 'no-store' } }) }));
  const refused = await view.refresh();
  assert.equal(refused.status, 'unavailable');
  assert.equal(refused.reason, 'RESPONSE_TOO_LARGE');
  assert.deepEqual(refused.objects, []);
  assert.equal(cancelled, true);
  view.destroy();
});

test('clear and a later generation fence delayed successful reads', async () => {
  const pending = deferred();
  let started;
  const readStarted = new Promise(resolve => { started = resolve; });
  const view = controller(transport({ read: async () => { started(); return pending.promise; } }));
  await view.refresh();
  const reading = view.open(object.id);
  await readStarted;
  view.clear();
  await view.refresh();
  pending.resolve(bytes());
  assert.deepEqual(await reading, { superseded: true });
  assert.equal(view.snapshot().status, 'listed');
  assert.equal(view.snapshot().inspection, null);
  view.destroy();
});

test('a hung transport cannot retain an in-progress private view past the local timeout', async () => {
  const view = controller(transport({ list: () => new Promise(() => {}) }), { requestTimeoutMs: 15 });
  await view.refresh();
  assert.equal(view.snapshot().status, 'unavailable');
  assert.equal(view.snapshot().reason, 'REQUEST_TIMEOUT');
  assert.deepEqual(view.snapshot().objects, []);
  view.destroy();
});

class Element extends EventTarget {
  constructor(tag, doc, text = '') { super(); this.tagName = tag.toUpperCase(); this.doc = doc; this.text = text; this.children = []; this.attrs = new Map(); this.parent = null; }
  setAttribute(name, value) { this.attrs.set(name, String(value)); }
  getAttribute(name) { return this.attrs.get(name) ?? null; }
  removeAttribute(name) { this.attrs.delete(name); }
  append(...nodes) { for (const node of nodes) { node.remove(); node.parent = this; this.children.push(node); } }
  removeChild(node) { this.children.splice(this.children.indexOf(node), 1); node.parent = null; }
  remove() { this.parent?.removeChild(this); }
  get firstChild() { return this.children[0] || null; }
  get textContent() { return this.text + this.children.map(child => child.textContent).join(''); }
  all(predicate) { return this.children.flatMap(child => [...(predicate(child) ? [child] : []), ...child.all(predicate)]); }
}
function documentDouble(locale = 'en') {
  const doc = new EventTarget();
  doc.defaultView = new EventTarget();
  doc.documentElement = { lang: locale };
  doc.visibilityState = 'visible';
  doc.createElement = tag => new Element(tag, doc);
  doc.createTextNode = text => new Element('#text', doc, text);
  const root = doc.createElement('main'); root.setAttribute('data-live-lab', 'knowledge-journey');
  const start = doc.createElement('button'); start.setAttribute('disabled', ''); root.append(start);
  return { doc, root, start };
}

test('explicit mount renders only inert text and clears on hiding, replacement and disposal', async () => {
  const { doc, root, start } = documentDouble('ru');
  const mount = mountRetainedObjectReader({ document: doc, root, transport: transport(), cryptoImpl: webcrypto });
  await mount.refresh(); await mount.open(object.id);
  assert.equal(root.all(node => node.tagName === 'SCRIPT').length, 0);
  assert.equal(root.all(node => node.tagName === 'IFRAME').length, 0);
  assert.equal(root.all(node => node.tagName === 'A').length, 0);
  assert.ok(root.textContent.includes('<script>'));
  assert.equal(start.getAttribute('disabled'), '');
  doc.visibilityState = 'hidden'; doc.dispatchEvent(new Event('visibilitychange'));
  assert.equal(root.textContent.includes('<script>'), false);
  const next = mountRetainedObjectReader({ document: doc, root });
  assert.equal(root.all(node => node.getAttribute('data-lab-retained-reader') !== null).length, 1);
  assert.deepEqual(await mount.refresh(), { disposed: true });
  next.destroy();
  assert.equal(root.all(node => node.getAttribute('data-lab-retained-reader') !== null).length, 0);
  assert.equal(root.firstChild, start);
});
