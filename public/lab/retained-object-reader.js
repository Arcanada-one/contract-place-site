// SPDX-License-Identifier: Apache-2.0
// Finite, private retained-object inspection. Identity is not an object grant.
// The host must supply an approved same-origin user-reader mapping. No default
// mapping, service credential, observation graph or automatic network bootstrap.
import { parseBoundedJson } from './access-contracts.46ab74e.js';

const JSON_LIMIT = 65532; // Existing shared bounded parser; never truncate a list.
const OBJECT_LIMIT = 8 * 1024 * 1024; // Browser cap = native schema/config maximum, not its active setting.
const COUNT_LIMIT = 2048; // Retained registry MAX_LIST_ENTRIES.
const ID = /^ro-[0-9a-f]{32}$/;
const OPAQUE = /^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$/;
const SUBJECT = /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const HASH = /^[0-9a-f]{64}$/;
const MEDIA = /^[a-z0-9][a-z0-9!#$&^_.+-]{0,63}\/[a-z0-9][a-z0-9!#$&^_.+-]{0,63}$/;
const TEXT_TYPES = new Set(['text/plain', 'text/markdown', 'application/json']);
const empty = Object.freeze([]);
const mounts = new WeakMap();
const closed = (value, keys) => value !== null && typeof value === 'object' &&
  !Array.isArray(value) && Object.keys(value).length === keys.length &&
  keys.every(key => Object.hasOwn(value, key));
const failure = code => Object.assign(new Error(code), { code });

/** One existing general JSON parser, then the native list's closed domain shape. */
export function decodeRetainedObjectList(bytes) {
  const data = parseBoundedJson(bytes);
  if (!closed(data, ['schema', 'objects']) || data.schema !== 'RetainedObjectList/v1' ||
      !Array.isArray(data.objects) || data.objects.length > COUNT_LIMIT) throw failure('LIST_INVALID');
  const seen = new Set();
  let run = null;
  const objects = data.objects.map(item => {
    if (!closed(item, ['id', 'run_id', 'media_type', 'size', 'sha256']) ||
        typeof item.id !== 'string' || !ID.test(item.id) ||
        typeof item.run_id !== 'string' || !OPAQUE.test(item.run_id) ||
        typeof item.media_type !== 'string' || !MEDIA.test(item.media_type) ||
        !Number.isSafeInteger(item.size) || item.size < 0 || item.size > OBJECT_LIMIT ||
        typeof item.sha256 !== 'string' || !HASH.test(item.sha256) ||
        seen.has(item.id) || (run !== null && run !== item.run_id)) throw failure('LIST_INVALID');
    seen.add(item.id);
    run = item.run_id; // The native retained registry is bound to ONE run.
    return Object.freeze({ ...item });
  });
  return Object.freeze(objects);
}

/**
 * A trusted host chooses the browser-facing mapping only after BFF admission.
 * objectListPath has NO default: /v1/lab/user/objects is an upstream candidate,
 * not an already-provisioned route on contract.place.
 *
 * No tokens or subject headers cross this transport. The BFF must authenticate
 * its HttpOnly session and obtain a current delegated READ server-side.
 */
export function createSameOriginRetainedTransport({ origin, objectListPath, fetchImpl = globalThis.fetch } = {}) {
  if (objectListPath === undefined || objectListPath === null || objectListPath === '') return null;
  let site;
  try { site = new URL(origin); } catch { throw failure('READER_CONFIGURATION_INVALID'); }
  if (site.protocol !== 'https:' || site.username || site.password ||
      site.href !== site.origin + '/' || typeof fetchImpl !== 'function' ||
      typeof objectListPath !== 'string' ||
      !/^\/(?:[A-Za-z0-9_-]+\/)*objects$/.test(objectListPath) ||
      objectListPath.startsWith('/v1/lab/service/')) throw failure('READER_CONFIGURATION_INVALID');
  const request = async (path, accept, signal) => {
    const url = new URL(path, site.origin).href;
    const response = await fetchImpl(url, {
      method: 'GET', mode: 'same-origin', credentials: 'same-origin',
      cache: 'no-store', redirect: 'error', referrerPolicy: 'no-referrer',
      headers: { Accept: accept }, signal,
    });
    if (response.url !== url || response.redirected || response.type === 'opaqueredirect') {
      throw failure('READER_RESPONSE_REFUSED');
    }
    return response;
  };
  return Object.freeze({
    session: ({ signal }) => request('/api/auth/session', 'application/json', signal),
    list: ({ signal }) => request(objectListPath, 'application/json', signal),
    read: ({ id, signal }) => {
      if (typeof id !== 'string' || !ID.test(id)) throw failure('OBJECT_NOT_LISTED');
      return request(objectListPath + '/' + id, 'application/octet-stream', signal);
    },
  });
}

function successfulPrivateResponse(response) {
  if (!response || response.status !== 200 || response.redirected ||
      !/(?:^|,)\s*no-store\s*(?:,|$)/i.test(response.headers.get('cache-control') || '')) {
    throw failure('READER_UNAVAILABLE');
  }
}

function waitFor(promise, signal) {
  if (signal.aborted) return Promise.reject(failure('READ_CANCELLED'));
  return new Promise((resolve, reject) => {
    const aborted = () => { cleanup(); reject(failure('READ_CANCELLED')); };
    const cleanup = () => signal.removeEventListener('abort', aborted);
    signal.addEventListener('abort', aborted, { once: true });
    Promise.resolve(promise).then(value => { cleanup(); resolve(value); }, error => { cleanup(); reject(error); });
  });
}

async function boundedBytes(response, limit, signal) {
  successfulPrivateResponse(response);
  const declared = response.headers.get('content-length');
  if (declared !== null && (!/^(?:0|[1-9][0-9]*)$/.test(declared) || Number(declared) > limit)) {
    throw failure('RESPONSE_TOO_LARGE');
  }
  if (!response.body || typeof response.body.getReader !== 'function') throw failure('READER_RESPONSE_REFUSED');
  const reader = response.body.getReader();
  const chunks = [];
  let total = 0, completed = false;
  try {
    for (;;) {
      const next = await waitFor(reader.read(), signal);
      if (next.done) break;
      if (!(next.value instanceof Uint8Array) || total + next.value.byteLength > limit) {
        throw failure('RESPONSE_TOO_LARGE');
      }
      total += next.value.byteLength;
      chunks.push(next.value);
    }
    if (signal.aborted) throw failure('READ_CANCELLED');
    const bytes = new Uint8Array(total);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    completed = true;
    return bytes;
  } finally {
    // Cancellation is best effort and never awaited indefinitely.
    if (!completed) void reader.cancel().catch(() => {});
    reader.releaseLock();
    chunks.length = 0;
  }
}

async function privateJson(response, signal) {
  if (!/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(response.headers.get('content-type') || '')) {
    throw failure('READER_RESPONSE_REFUSED');
  }
  return parseBoundedJson(await boundedBytes(response, JSON_LIMIT, signal));
}

const safeReason = error => [
  'RESPONSE_TOO_LARGE', 'LIST_INVALID', 'OBJECT_NOT_LISTED', 'OBJECT_CHANGED',
  'SESSION_CHANGED', 'IDENTITY_UNAVAILABLE', 'READ_CANCELLED',
].includes(error?.code) ? error.code : 'READER_UNAVAILABLE';

/**
 * Transport port: session/list/read each return an ordinary Fetch Response,
 * honor AbortSignal and enforce the same-origin transport contract above.
 * Authority lives at the BFF and backend. List membership is never a grant.
 *
 * The only private state is this controller's finite list, selected metadata
 * and text model. Clear/destroy removes that state and fences all late results.
 * The host MUST clear synchronously before logout/account/session-generation
 * or project/view changes, including cross-tab invalidations. The subject-only
 * identity endpoint cannot detect every such boundary or supply a grant.
 * requestTimeoutMs is a local UI resource limit, not an authorization lease.
 */
export function createRetainedObjectController({
  transport = null, onState = () => {}, cryptoImpl = globalThis.crypto, requestTimeoutMs = 10000,
} = {}) {
  if (transport !== null && ['session', 'list', 'read'].some(key => typeof transport[key] !== 'function')) {
    throw failure('READER_CONFIGURATION_INVALID');
  }
  if (!Number.isSafeInteger(requestTimeoutMs) || requestTimeoutMs < 1 || requestTimeoutMs > 120000) {
    throw failure('READER_CONFIGURATION_INVALID');
  }
  let generation = 0, active = null, disposed = false, objects = empty, principal = null;
  let model;
  const emit = (status, fields = {}) => {
    model = Object.freeze({ status, objects, selected: null, inspection: null, ...fields });
    onState(model);
    return model;
  };
  const discard = () => { objects = empty; principal = null; };
  const invalidate = () => {
    generation += 1;
    if (active) { clearTimeout(active.timer); active.abort.abort(); active = null; }
  };
  const current = attempt => !disposed && active === attempt && generation === attempt.generation && !attempt.abort.signal.aborted;
  const start = status => {
    invalidate();
    const attempt = { generation, abort: new AbortController(), timer: null };
    active = attempt;
    attempt.timer = setTimeout(() => {
      if (!current(attempt)) return;
      invalidate(); discard(); emit('unavailable', { reason: 'REQUEST_TIMEOUT' });
    }, requestTimeoutMs);
    emit(status);
    return attempt;
  };
  const finish = attempt => {
    if (active === attempt) { clearTimeout(attempt.timer); active = null; }
  };
  const session = async attempt => {
    const signal = attempt.abort.signal;
    const response = await waitFor(transport.session({ signal }), signal);
    const data = await privateJson(response, signal);
    if (!closed(data, ['authenticated', 'subject']) || data.authenticated !== true ||
        typeof data.subject !== 'string' || !SUBJECT.test(data.subject)) throw failure('IDENTITY_UNAVAILABLE');
    return data.subject;
  };
  const refused = (attempt, error) => {
    if (!current(attempt)) return { superseded: true };
    attempt.abort.abort(); // Also stop an unread denied/malformed response body.
    discard();
    return emit('unavailable', { reason: safeReason(error) });
  };
  const clear = () => {
    if (disposed) return;
    invalidate(); discard(); emit(transport ? 'idle' : 'not_configured');
  };

  async function refresh() {
    if (disposed) return { disposed: true };
    if (!transport) return emit('not_configured');
    discard();
    const attempt = start('loading');
    try {
      const signal = attempt.abort.signal;
      const before = await session(attempt);
      const response = await waitFor(transport.list({ signal }), signal);
      if (!/^application\/json(?:\s*;\s*charset=utf-8)?$/i.test(response.headers.get('content-type') || '')) {
        throw failure('READER_RESPONSE_REFUSED');
      }
      const list = decodeRetainedObjectList(await boundedBytes(response, JSON_LIMIT, signal));
      if (await session(attempt) !== before) throw failure('SESSION_CHANGED');
      if (!current(attempt)) return { superseded: true };
      objects = list; principal = before;
      return emit('listed');
    } catch (error) { return refused(attempt, error); }
    finally { finish(attempt); }
  }

  async function open(id) {
    if (disposed) return { disposed: true };
    if (!transport) return emit('not_configured');
    const object = objects.find(item => item.id === id);
    if (!object || principal === null) {
      invalidate(); discard(); return emit('unavailable', { reason: 'OBJECT_NOT_LISTED' });
    }
    const expectedPrincipal = principal;
    const attempt = start('reading'); // Clears the former selected text immediately.
    try {
      const signal = attempt.abort.signal;
      if (await session(attempt) !== expectedPrincipal) throw failure('SESSION_CHANGED');
      const response = await waitFor(transport.read({ id: object.id, signal }), signal);
      successfulPrivateResponse(response);
      if (response.headers.get('content-type') !== object.media_type ||
          response.headers.get('x-object-sha256') !== object.sha256 ||
          response.headers.get('x-object-size') !== String(object.size) ||
          response.headers.get('etag') !== '"' + object.sha256 + '"' ||
          response.headers.get('content-disposition') !== 'attachment') throw failure('OBJECT_CHANGED');
      const bytes = await boundedBytes(response, object.size, signal);
      if (bytes.byteLength !== object.size) throw failure('OBJECT_CHANGED');
      if (!cryptoImpl?.subtle?.digest) throw failure('READER_UNAVAILABLE');
      const digest = new Uint8Array(await waitFor(cryptoImpl.subtle.digest('SHA-256', bytes), signal));
      const actual = Array.from(digest, value => value.toString(16).padStart(2, '0')).join('');
      if (actual !== object.sha256) throw failure('OBJECT_CHANGED');
      if (await session(attempt) !== expectedPrincipal) throw failure('SESSION_CHANGED');
      if (!current(attempt)) return { superseded: true };
      let text = null;
      if (TEXT_TYPES.has(object.media_type)) {
        // Inert text only. No Markdown, HTML, JSON tree or source links execute.
        text = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bytes);
      }
      return emit('inspected', {
        selected: object,
        inspection: Object.freeze({ bytesVerified: true, encoding: text === null ? 'binary' : 'utf-8', text }),
      });
    } catch (error) { return refused(attempt, error); }
    finally { finish(attempt); }
  }

  const controller = {
    refresh, open, clear,
    snapshot: () => model,
    destroy() { if (!disposed) { clear(); disposed = true; } },
  };
  emit(transport ? 'idle' : 'not_configured');
  return controller;
}

const WORDS = {
  en: {
    title: 'Retained source files', refresh: 'Read permitted files', clear: 'Hide private view',
    notice: 'The server checks current READ permission for each request. Identity and list membership are not a grant. Byte agreement does not establish knowledge admission or task acceptance.',
    not_configured: 'Protected reader is not connected. No request was sent.', idle: 'No private files are displayed.',
    loading: 'Checking the session and permitted file list…', listed: 'Permitted retained file metadata.',
    reading: 'Checking permission and exact retained bytes…', inspected: 'The bytes match the selected size and SHA-256.',
    unavailable: 'The private view is unavailable. Its previous contents have been cleared.',
    empty: 'The permitted list is empty.', open: 'Inspect bytes', binary: 'Binary bytes verified; inline rendering is not supported.',
  },
  ru: {
    title: 'Сохранённые файлы источника', refresh: 'Прочитать разрешённые файлы', clear: 'Скрыть приватное представление',
    notice: 'Сервер проверяет действующее право READ при каждом запросе. Идентификация и присутствие в списке не предоставляют доступ. Совпадение байтов не означает допуск знания или приёмку задачи.',
    not_configured: 'Защищённое чтение не подключено. Запросы не отправлены.', idle: 'Приватные файлы не отображаются.',
    loading: 'Проверяем сессию и список разрешённых файлов…', listed: 'Метаданные разрешённых сохранённых файлов.',
    reading: 'Проверяем доступ и точные сохранённые байты…', inspected: 'Байты совпадают с выбранными размером и SHA-256.',
    unavailable: 'Приватное представление недоступно. Предыдущее содержимое удалено.',
    empty: 'Список разрешённых файлов пуст.', open: 'Рассмотреть байты', binary: 'Бинарные байты проверены; встроенный просмотр не поддерживается.',
  },
  'zh-Hans': {
    title: '保留的来源文件', refresh: '读取获准文件', clear: '隐藏私密视图',
    notice: '服务器对每次请求检查当前 READ 权限。身份及列表成员关系并不授予访问权限。字节一致不代表知识准入或任务验收。',
    not_configured: '受保护的读取器尚未连接，未发送请求。', idle: '当前不显示私密文件。',
    loading: '正在检查会话及获准文件列表…', listed: '获准保留文件的元数据。',
    reading: '正在检查权限及保留的原始字节…', inspected: '字节与选定的大小和 SHA-256 一致。',
    unavailable: '私密视图不可用，先前内容已清除。',
    empty: '获准文件列表为空。', open: '查看字节', binary: '二进制字节已验证，不支持内嵌显示。',
  },
};

/** Explicit host mount; it leaves the existing observation graph and execution controls untouched. */
export function mountRetainedObjectReader({ document: doc, root, transport = null, locale = doc.documentElement?.lang || 'en', ...options }) {
  if (!root || root.getAttribute('data-live-lab') !== 'knowledge-journey') throw failure('READER_ROOT_UNAVAILABLE');
  mounts.get(root)?.destroy();
  const words = WORDS[locale] || WORDS.en;
  const node = (tag, text, attrs = {}) => {
    const value = doc.createElement(tag);
    for (const [key, attribute] of Object.entries(attrs)) value.setAttribute(key, attribute);
    if (text !== undefined) value.append(doc.createTextNode(text));
    return value;
  };
  const section = node('section', undefined, { 'data-lab-retained-reader': '' });
  const refresh = node('button', words.refresh, { type: 'button' });
  const clearButton = node('button', words.clear, { type: 'button' });
  if (!transport) refresh.setAttribute('disabled', '');
  const status = node('p', undefined, { role: 'status' });
  const contents = node('div');
  section.append(node('h2', words.title), node('p', words.notice), refresh, clearButton, status, contents);
  root.append(section);
  const removeChildren = parent => { while (parent.firstChild) parent.removeChild(parent.firstChild); };
  let rowButtons = [];
  const removeRows = () => {
    for (const [button, handler] of rowButtons) button.removeEventListener('click', handler);
    rowButtons = []; removeChildren(contents);
  };
  let controller;
  controller = createRetainedObjectController({
    ...options, transport,
    onState(model) {
      removeRows(); removeChildren(status); status.append(doc.createTextNode(words[model.status]));
      section.setAttribute('data-lab-reader-state', model.status);
      if (model.reason) section.setAttribute('data-lab-reader-reason', model.reason);
      else section.removeAttribute('data-lab-reader-reason');
      if (model.status === 'listed' && model.objects.length === 0) contents.append(node('p', words.empty));
      for (const object of model.objects) {
        const row = node('p');
        const identity = node('bdi', object.id + ' · ' + object.media_type + ' · ' + object.size, { dir: 'auto' });
        const button = node('button', words.open, { type: 'button' });
        const handler = () => { void controller.open(object.id); };
        button.addEventListener('click', handler); rowButtons.push([button, handler]);
        row.append(identity, doc.createTextNode(' '), button); contents.append(row);
      }
      if (model.selected) {
        const identity = node('p', undefined, { 'data-lab-retained-identity': '' });
        identity.append(node('bdi',
          model.selected.id + ' · ' + model.selected.run_id + ' · SHA-256 ' + model.selected.sha256,
          { dir: 'auto' }));
        contents.append(identity);
        if (model.inspection.text !== null) {
          const pre = node('pre', undefined, { tabindex: '0', 'data-lab-retained-text': '' });
          pre.append(node('bdi', model.inspection.text, { dir: 'auto' })); contents.append(pre);
        } else contents.append(node('p', words.binary));
      }
    },
  });
  const refreshHandler = () => { void controller.refresh(); };
  const clearHandler = () => controller.clear();
  const hidden = () => { if (doc.visibilityState !== 'visible') controller.clear(); };
  const pagehide = () => controller.clear();
  refresh.addEventListener('click', refreshHandler);
  clearButton.addEventListener('click', clearHandler);
  doc.addEventListener('visibilitychange', hidden);
  doc.defaultView?.addEventListener('pagehide', pagehide);
  let disposed = false;
  const mount = {
    refresh: controller.refresh, open: controller.open, clear: controller.clear,
    destroy() {
      if (disposed) return;
      disposed = true;
      controller.destroy(); removeRows(); section.remove();
      refresh.removeEventListener('click', refreshHandler);
      clearButton.removeEventListener('click', clearHandler);
      doc.removeEventListener('visibilitychange', hidden);
      doc.defaultView?.removeEventListener('pagehide', pagehide);
      if (mounts.get(root) === mount) mounts.delete(root);
    },
  };
  mounts.set(root, mount);
  return mount;
}
