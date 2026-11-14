// src/wire-snapshot.ts
function snapshotRecord(value, keys, exact = true) {
  if (typeof value !== "object" || value === null || Array.isArray(value))
    return null;
  const prototype = Object.getPrototypeOf(value);
  if (prototype !== Object.prototype && prototype !== null) return null;
  const ownKeys = Reflect.ownKeys(value);
  if (ownKeys.length > keys.length || exact && ownKeys.length !== keys.length)
    return null;
  const snapshot = {};
  for (const key of ownKeys) {
    if (typeof key !== "string" || !keys.includes(key)) return null;
    const property = Object.getOwnPropertyDescriptor(value, key);
    if (property === void 0 || !property.enumerable || !Object.hasOwn(property, "value"))
      return null;
    snapshot[key] = property.value;
  }
  return snapshot;
}
function snapshotArray(value, min, max) {
  if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype)
    return null;
  const lengthProperty = Object.getOwnPropertyDescriptor(value, "length");
  if (lengthProperty === void 0 || !Object.hasOwn(lengthProperty, "value"))
    return null;
  const length = lengthProperty.value;
  if (!counter(length, min) || length > max || Reflect.ownKeys(value).length !== length + 1)
    return null;
  const snapshot = [];
  for (let index = 0; index < length; index += 1) {
    const item = Object.getOwnPropertyDescriptor(value, String(index));
    if (item === void 0 || !Object.hasOwn(item, "value") || !item.enumerable)
      return null;
    snapshot.push(item.value);
  }
  return snapshot;
}
function counter(value, min = 0) {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= min;
}

// src/personal-capture.ts
var PERSONAL_CAPTURE_VERSION = "personal-capture/v1";
var PERSONAL_CAPTURE_LIMITS = {
  parts: 2,
  noteBytes: 64 * 1024,
  attachmentBytes: 1024 * 1024
};
var UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/u;
var SHA256 = /^[0-9a-f]{64}$/u;
var PART_KEYS = [
  "partId",
  "role",
  "objectId",
  "objectRevision",
  "sha256",
  "sizeBytes",
  "mediaType"
];
var DESCRIPTOR_KEYS = [
  "schemaVersion",
  "realmId",
  "captureId",
  "conversationId",
  "messageId",
  "expectedConversationRevision",
  "operation",
  "idempotencyKey",
  "requestFingerprint",
  "cancellationGeneration",
  "parts"
];
var RECEIPT_KEYS = [
  "schemaVersion",
  "realmId",
  "captureId",
  "partId",
  "objectId",
  "objectRevision",
  "sha256",
  "sizeBytes",
  "mediaType",
  "requestFingerprint",
  "cancellationGeneration"
];
var CANCELLATION_KEYS = [
  "schemaVersion",
  "purpose",
  "realmId",
  "captureId",
  "requestFingerprint",
  "intentRevision",
  "cancellationGeneration"
];
function fail(error) {
  return { ok: false, error };
}
function uuid(value) {
  return typeof value === "string" && value.length === 36 && UUID.test(value);
}
function digest(value) {
  return typeof value === "string" && value.length === 64 && SHA256.test(value);
}
function content(value, max) {
  return uuid(value["partId"]) && uuid(value["objectId"]) && uuid(value["objectRevision"]) && digest(value["sha256"]) && counter(value["sizeBytes"]) && value["sizeBytes"] <= max && value["mediaType"] === "text/plain;charset=utf-8";
}
function parseDescriptor(input) {
  const value = snapshotRecord(input, DESCRIPTOR_KEYS);
  if (value === null) return fail("descriptor: invalid fields");
  if (value["schemaVersion"] !== PERSONAL_CAPTURE_VERSION || value["operation"] !== "append_message")
    return fail("descriptor: invalid profile or operation");
  for (const key of [
    "realmId",
    "captureId",
    "conversationId",
    "messageId",
    "idempotencyKey"
  ]) {
    if (!uuid(value[key])) return fail("descriptor: invalid identifier");
  }
  if (!digest(value["requestFingerprint"]) || !counter(value["expectedConversationRevision"]) || value["expectedConversationRevision"] === Number.MAX_SAFE_INTEGER || !counter(value["cancellationGeneration"]) || value["cancellationGeneration"] === Number.MAX_SAFE_INTEGER)
    return fail("descriptor: invalid fingerprint or counter");
  const raw = snapshotArray(value["parts"], 1, PERSONAL_CAPTURE_LIMITS.parts);
  if (raw === null) return fail("descriptor: invalid part count");
  const parts = [];
  for (let index = 0; index < raw.length; index += 1) {
    const part2 = snapshotRecord(raw[index], PART_KEYS);
    const role = index === 0 ? "note" : "attachment";
    const limit = index === 0 ? PERSONAL_CAPTURE_LIMITS.noteBytes : PERSONAL_CAPTURE_LIMITS.attachmentBytes;
    if (part2 === null || part2["role"] !== role || !content(part2, limit))
      return fail("descriptor: invalid part");
    parts.push({ ...part2 });
  }
  if (new Set(parts.map((p) => p.partId)).size !== parts.length || new Set(parts.map((p) => p.objectId)).size !== parts.length)
    return fail("descriptor: duplicate part or object");
  return {
    ok: true,
    value: { ...value, parts }
  };
}
function parseReceipt(input) {
  const value = snapshotRecord(input, RECEIPT_KEYS);
  if (value === null || value["schemaVersion"] !== PERSONAL_CAPTURE_VERSION || !uuid(value["realmId"]) || !uuid(value["captureId"]) || !digest(value["requestFingerprint"]) || !counter(value["cancellationGeneration"]) || !content(value, PERSONAL_CAPTURE_LIMITS.attachmentBytes))
    return fail("receipt: invalid record");
  return { ok: true, value: { ...value } };
}
function parseCancellation(input) {
  const value = snapshotRecord(input, CANCELLATION_KEYS);
  if (value === null || value["schemaVersion"] !== PERSONAL_CAPTURE_VERSION || value["purpose"] !== "cancel_unpublished_capture" || !uuid(value["realmId"]) || !uuid(value["captureId"]) || !digest(value["requestFingerprint"]) || !counter(value["intentRevision"], 1) || !counter(value["cancellationGeneration"], 1))
    return fail("cancellation: invalid record");
  return {
    ok: true,
    value: { ...value }
  };
}
function safely(parse) {
  try {
    return parse();
  } catch {
    return fail("invalid wire value");
  }
}
function parsePersonalCaptureDescriptor(value) {
  return safely(() => parseDescriptor(value));
}
function parsePersonalObjectReceipt(value) {
  return safely(() => parseReceipt(value));
}
function parsePersonalCaptureCancellation(value) {
  return safely(() => parseCancellation(value));
}
function receiptMatches(descriptor, receipt) {
  const part2 = descriptor.parts.find((p) => p.partId === receipt.partId);
  return part2 !== void 0 && receipt.realmId === descriptor.realmId && receipt.captureId === descriptor.captureId && receipt.requestFingerprint === descriptor.requestFingerprint && receipt.cancellationGeneration === descriptor.cancellationGeneration && part2.objectId === receipt.objectId && part2.objectRevision === receipt.objectRevision && part2.sha256 === receipt.sha256 && part2.sizeBytes === receipt.sizeBytes && part2.mediaType === receipt.mediaType;
}
function personalObjectReceiptMatches(descriptor, receipt) {
  const d = parsePersonalCaptureDescriptor(descriptor);
  const r = parsePersonalObjectReceipt(receipt);
  return d.ok && r.ok && receiptMatches(d.value, r.value);
}
function parseStatus(input) {
  const baseKeys = ["schemaVersion", "descriptor", "intentRevision", "state"];
  const value = snapshotRecord(
    input,
    [
      ...baseKeys,
      "receipts",
      "manifestId",
      "conversationRevision",
      "cancellation"
    ],
    false
  );
  if (value === null) return fail("status: invalid record");
  const state = value["state"];
  const extra = state === "awaiting_bytes" ? [] : state === "staged" ? ["receipts"] : state === "committed" ? ["receipts", "manifestId", "conversationRevision"] : state === "cancelled" ? ["cancellation"] : null;
  if (extra === null || Object.keys(value).length !== baseKeys.length + extra.length || ![...baseKeys, ...extra].every((key) => Object.hasOwn(value, key)) || value["schemaVersion"] !== PERSONAL_CAPTURE_VERSION || !counter(value["intentRevision"], 1))
    return fail("status: invalid fields or revision");
  const descriptor = parseDescriptor(value["descriptor"]);
  if (!descriptor.ok) return descriptor;
  const base = {
    schemaVersion: PERSONAL_CAPTURE_VERSION,
    descriptor: descriptor.value,
    intentRevision: value["intentRevision"]
  };
  if (state === "awaiting_bytes")
    return { ok: true, value: { ...base, state } };
  if (state === "cancelled") {
    const c = parseCancellation(value["cancellation"]);
    if (!c.ok) return c;
    if (c.value.realmId !== descriptor.value.realmId || c.value.captureId !== descriptor.value.captureId || c.value.requestFingerprint !== descriptor.value.requestFingerprint || c.value.intentRevision !== base.intentRevision || c.value.cancellationGeneration !== descriptor.value.cancellationGeneration + 1)
      return fail("status: cancellation mismatch");
    return { ok: true, value: { ...base, state, cancellation: c.value } };
  }
  const raw = snapshotArray(
    value["receipts"],
    descriptor.value.parts.length,
    descriptor.value.parts.length
  );
  if (raw === null) return fail("status: incomplete receipts");
  const receipts = [];
  for (const item of raw) {
    const receipt = parseReceipt(item);
    if (!receipt.ok) return receipt;
    if (!receiptMatches(descriptor.value, receipt.value))
      return fail("status: receipt mismatch");
    receipts.push(receipt.value);
  }
  if (new Set(receipts.map((r) => r.partId)).size !== receipts.length)
    return fail("status: duplicate receipt");
  if (state === "staged")
    return { ok: true, value: { ...base, state, receipts } };
  if (!uuid(value["manifestId"]) || value["conversationRevision"] !== descriptor.value.expectedConversationRevision + 1)
    return fail("status: invalid committed result");
  return {
    ok: true,
    value: {
      ...base,
      state: "committed",
      receipts,
      manifestId: value["manifestId"],
      conversationRevision: value["conversationRevision"]
    }
  };
}
function parsePersonalCaptureStatus(value) {
  return safely(() => parseStatus(value));
}
function personalCaptureFingerprintInput(value) {
  const parsed = parsePersonalCaptureDescriptor(value);
  if (!parsed.ok) return parsed;
  const d = parsed.value;
  return {
    ok: true,
    value: JSON.stringify([
      PERSONAL_CAPTURE_VERSION,
      d.realmId,
      d.operation,
      d.conversationId,
      d.expectedConversationRevision,
      d.parts.map((p) => [p.role, p.sha256, p.sizeBytes, p.mediaType])
    ])
  };
}
function descriptorIdentity(d) {
  return JSON.stringify([
    d.schemaVersion,
    d.realmId,
    d.captureId,
    d.conversationId,
    d.messageId,
    d.expectedConversationRevision,
    d.operation,
    d.idempotencyKey,
    d.requestFingerprint,
    d.cancellationGeneration,
    d.parts.map((p) => [
      p.partId,
      p.role,
      p.objectId,
      p.objectRevision,
      p.sha256,
      p.sizeBytes,
      p.mediaType
    ])
  ]);
}
function comparePersonalCaptureRetry(existing, retry) {
  const a = parsePersonalCaptureDescriptor(existing);
  const b = parsePersonalCaptureDescriptor(retry);
  if (!a.ok || !b.ok) return "invalid";
  if (a.value.realmId !== b.value.realmId || a.value.idempotencyKey !== b.value.idempotencyKey)
    return "different_scope";
  return descriptorIdentity(a.value) === descriptorIdentity(b.value) ? "same_intent" : "conflict";
}
function evaluatePersonalCaptureTransition(current, proposed, expectedRevision) {
  const a = parsePersonalCaptureStatus(current);
  const b = parsePersonalCaptureStatus(proposed);
  if (!a.ok || !b.ok || !counter(expectedRevision, 1)) return "invalid";
  if (descriptorIdentity(a.value.descriptor) !== descriptorIdentity(b.value.descriptor))
    return "intent_mismatch";
  if (a.value.intentRevision !== expectedRevision || expectedRevision === Number.MAX_SAFE_INTEGER || b.value.intentRevision !== expectedRevision + 1)
    return "revision_conflict";
  if (a.value.state === "cancelled" || a.value.state === "committed")
    return "terminal";
  if (b.value.state === "cancelled" || a.value.state === "awaiting_bytes" && b.value.state === "staged" || a.value.state === "staged" && b.value.state === "committed")
    return "eligible";
  return "invalid_transition";
}

// src/bounded-json.ts
var MAX_BYTES = 65532;
var MAX_DEPTH = 16;
var typedArrayByteLength = Object.getOwnPropertyDescriptor(
  Object.getPrototypeOf(Uint8Array.prototype),
  "byteLength"
).get;
function invalid() {
  throw new SyntaxError("Invalid bounded JSON");
}
function decodeUtf8(raw) {
  const chars = [];
  for (let i = 0; i < raw.length; ) {
    const first = raw[i++];
    if (first < 128) {
      chars.push(String.fromCharCode(first));
      continue;
    }
    let remaining;
    let point;
    let minimum;
    if (first >= 194 && first <= 223) {
      remaining = 1;
      point = first & 31;
      minimum = 128;
    } else if (first >= 224 && first <= 239) {
      remaining = 2;
      point = first & 15;
      minimum = 2048;
    } else if (first >= 240 && first <= 244) {
      remaining = 3;
      point = first & 7;
      minimum = 65536;
    } else {
      return invalid();
    }
    if (i + remaining > raw.length) invalid();
    while (remaining-- > 0) {
      const next = raw[i++];
      if ((next & 192) !== 128) invalid();
      point = point << 6 | next & 63;
    }
    if (point < minimum || point > 1114111 || point >= 55296 && point <= 57343) {
      invalid();
    }
    chars.push(String.fromCodePoint(point));
  }
  return chars.join("");
}
function parseBoundedJson(raw) {
  try {
    if (!(raw instanceof Uint8Array)) invalid();
    const length = typedArrayByteLength.call(raw);
    if (length === 0 || length > MAX_BYTES) invalid();
    const text = decodeUtf8(new Uint8Array(raw));
    if (text.charCodeAt(0) === 65279) invalid();
    validateGrammar(text);
    return JSON.parse(text);
  } catch {
    return invalid();
  }
}
function validateGrammar(text) {
  let i = 0;
  const atom = /(?:true|false|null|-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?)/y;
  function whitespace() {
    while (text[i] === " " || text[i] === "	" || text[i] === "\r" || text[i] === "\n") {
      i++;
    }
  }
  function string() {
    const start = i;
    if (text[i++] !== '"') return invalid();
    while (i < text.length) {
      const char = text[i++];
      if (char === "\\") {
        i++;
      } else if (char === '"') {
        const decoded = JSON.parse(text.slice(start, i));
        for (let j = 0; j < decoded.length; j++) {
          const code = decoded.charCodeAt(j);
          if (code >= 55296 && code <= 56319) {
            const low = decoded.charCodeAt(++j);
            if (!(low >= 56320 && low <= 57343)) invalid();
          } else if (code >= 56320 && code <= 57343) {
            invalid();
          }
        }
        return decoded;
      }
    }
    return invalid();
  }
  function value(depth) {
    if (depth > MAX_DEPTH) invalid();
    whitespace();
    if (text[i] === "{") {
      i++;
      whitespace();
      const keys = /* @__PURE__ */ new Set();
      if (text[i] === "}") {
        i++;
        return;
      }
      for (; ; ) {
        whitespace();
        const key = string();
        if (keys.has(key)) invalid();
        keys.add(key);
        whitespace();
        if (text[i++] !== ":") invalid();
        value(depth + 1);
        whitespace();
        if (text[i] === "}") {
          i++;
          return;
        }
        if (text[i++] !== ",") invalid();
      }
    }
    if (text[i] === "[") {
      i++;
      whitespace();
      if (text[i] === "]") {
        i++;
        return;
      }
      for (; ; ) {
        value(depth + 1);
        whitespace();
        if (text[i] === "]") {
          i++;
          return;
        }
        if (text[i++] !== ",") invalid();
      }
    }
    if (text[i] === '"') {
      string();
      return;
    }
    atom.lastIndex = i;
    const match = atom.exec(text);
    if (match === null) return invalid();
    const token = match[0];
    if (token !== "true" && token !== "false" && token !== "null" && !Number.isFinite(Number(token))) {
      invalid();
    }
    i = atom.lastIndex;
  }
  value(0);
  whitespace();
  if (i !== text.length) invalid();
}

// src/personal-auth-capture-binding.ts
function parsePersonalCaptureBinding(input) {
  try {
    const value = snapshotRecord(input, ["descriptor", "status"]);
    if (value !== null) {
      const descriptor = parsePersonalCaptureDescriptor(value["descriptor"]);
      if (descriptor.ok) {
        if (value["status"] === null)
          return {
            ok: true,
            value: { descriptor: descriptor.value, status: null }
          };
        const status = parsePersonalCaptureStatus(value["status"]);
        if (status.ok && comparePersonalCaptureRetry(
          descriptor.value,
          status.value.descriptor
        ) === "same_intent")
          return {
            ok: true,
            value: { descriptor: descriptor.value, status: status.value }
          };
      }
    }
  } catch {
  }
  return { ok: false, error: "capture binding: invalid or mismatched intent" };
}
var PART_KEYS2 = [
  "part_id",
  "part_kind",
  "object_id",
  "object_revision",
  "sha256",
  "size_bytes",
  "media_type"
];
function partMatches(input, part2) {
  const value = snapshotRecord(input, PART_KEYS2);
  return value !== null && value["part_id"] === part2.partId && value["part_kind"] === part2.role && value["object_id"] === part2.objectId && value["object_revision"] === part2.objectRevision && value["sha256"] === part2.sha256 && value["size_bytes"] === part2.sizeBytes && value["media_type"] === part2.mediaType;
}
function personalCaptureResourceMatches(realmId, resource, binding) {
  try {
    const parsed = parsePersonalCaptureBinding(binding);
    if (!parsed.ok || realmId !== parsed.value.descriptor.realmId) return false;
    const { descriptor: d, status } = parsed.value;
    const value = snapshotRecord(
      resource,
      [
        "kind",
        "intent_id",
        "intent_revision",
        "conversation_id",
        "message_id",
        "expected_conversation_revision",
        "parts",
        ...PART_KEYS2,
        "terminal_intent_revision",
        "cancellation_generation",
        "owner_outcome_id",
        "part_ids",
        "cancellation"
      ],
      false
    );
    if (value === null || value["intent_id"] !== d.captureId) return false;
    const kind = value["kind"];
    const keys = kind === "intent" ? [
      "kind",
      "intent_id",
      "intent_revision",
      "conversation_id",
      "message_id",
      "expected_conversation_revision",
      "parts"
    ] : kind === "part" ? ["kind", "intent_id", "intent_revision", ...PART_KEYS2] : kind === "cancellation" ? [
      "kind",
      "intent_id",
      "terminal_intent_revision",
      "cancellation_generation",
      "owner_outcome_id",
      "part_ids",
      "cancellation"
    ] : null;
    if (keys === null || Object.keys(value).length !== keys.length || !keys.every((key) => Object.hasOwn(value, key)))
      return false;
    if (kind === "intent") {
      const parts = snapshotArray(
        value["parts"],
        d.parts.length,
        d.parts.length
      );
      return value["intent_revision"] === (status === null ? null : status.intentRevision) && value["conversation_id"] === d.conversationId && value["message_id"] === d.messageId && value["expected_conversation_revision"] === d.expectedConversationRevision && parts !== null && parts.every((part2, index) => partMatches(part2, d.parts[index]));
    }
    if (kind === "part") {
      if (status === null || value["intent_revision"] !== status.intentRevision)
        return false;
      const part2 = d.parts.find((p) => p.partId === value["part_id"]);
      const selector = Object.fromEntries(
        PART_KEYS2.map((key) => [key, value[key]])
      );
      return part2 !== void 0 && partMatches(selector, part2);
    }
    if (status === null || status.state !== "cancelled") return false;
    const ids = snapshotArray(
      value["part_ids"],
      d.parts.length,
      d.parts.length
    );
    const cancellation = snapshotRecord(value["cancellation"], [
      "schemaVersion",
      "purpose",
      "realmId",
      "captureId",
      "requestFingerprint",
      "intentRevision",
      "cancellationGeneration"
    ]);
    const outcome = value["owner_outcome_id"];
    return value["terminal_intent_revision"] === status.intentRevision && value["cancellation_generation"] === status.cancellation.cancellationGeneration && typeof outcome === "string" && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(
      outcome
    ) && ids !== null && new Set(ids).size === ids.length && ids.every((id4) => d.parts.some((part2) => part2.partId === id4)) && cancellation !== null && Object.entries(status.cancellation).every(
      ([key, expected]) => cancellation[key] === expected
    );
  } catch {
    return false;
  }
}

// src/personal-auth-json.ts
function parsePersonalAuthJson(text) {
  try {
    if (typeof text !== "string" || text.length > 65536 || [...text].reduce((n, c) => {
      const p = c.codePointAt(0);
      return n + (p < 128 ? 1 : p < 2048 ? 2 : p < 65536 ? 3 : 4);
    }, 0) > 65536)
      throw new Error();
    let position = 0;
    const space = () => {
      while (/[\x20\t\r\n]/u.test(text[position] ?? "x")) position++;
    };
    const string = () => {
      const start = position++;
      while (position < text.length) {
        const character = text[position++];
        if (character === "\\") position++;
        else if (character === '"') {
          const value2 = JSON.parse(text.slice(start, position));
          if (typeof value2 !== "string") throw new Error();
          for (const scalar of value2) {
            const point = scalar.codePointAt(0);
            if (point >= 55296 && point <= 57343) throw new Error();
          }
          return value2;
        }
      }
      throw new Error();
    };
    const value = (depth) => {
      if (depth > 24) throw new Error();
      space();
      const start = text[position];
      if (start === '"') {
        string();
        return;
      }
      if (start === "{" || start === "[") {
        const object = start === "{";
        const end = object ? "}" : "]";
        const keys = /* @__PURE__ */ new Set();
        position++;
        space();
        if (text[position] === end) {
          position++;
          return;
        }
        for (; ; ) {
          space();
          if (object) {
            if (text[position] !== '"') throw new Error();
            const key = string();
            if (keys.has(key)) throw new Error();
            keys.add(key);
            space();
            if (text[position++] !== ":") throw new Error();
          }
          value(depth + 1);
          space();
          if (text[position] === end) {
            position++;
            return;
          }
          if (text[position++] !== ",") throw new Error();
        }
      }
      for (const literal of ["true", "false", "null"]) {
        if (text.startsWith(literal, position)) {
          position += literal.length;
          return;
        }
      }
      const number = /^(?:0|[1-9][0-9]*)/u.exec(text.slice(position))?.[0];
      if (!number || !Number.isSafeInteger(Number(number))) throw new Error();
      position += number.length;
    };
    value(0);
    space();
    if (position !== text.length) throw new Error();
    return { ok: true, value: JSON.parse(text) };
  } catch {
    return { ok: false, error: "malformed personal wire JSON" };
  }
}

// src/personal-auth-v1.ts
var PERSONAL_AUTH_WIRE_VERSION = "auth-personal/1-proposed";
var PERSONAL_AUTH_PROFILE = "organize-me.synthetic/1";
var PERSONAL_AUTH_SELECTED_LIMITS = Object.freeze({
  activeFlows: 1,
  waitingFlows: 0,
  ordinaryLeasesPerFlow: 3,
  unresolvedLeaseCeiling: 8,
  uploadCeiling: 2,
  readCeiling: 4
});
var UUID2 = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/u;
var DIGEST = /^[0-9a-f]{64}$/u;
var id = (v) => typeof v === "string" && UUID2.test(v);
var opaque = (v, max = 256) => typeof v === "string" && v.length > 0 && v.length <= max && /^[\x21-\x7e]+$/u.test(v);
function isPersonalAuthCounter(v) {
  return typeof v === "string" && /^(?:0|[1-9][0-9]{0,19})$/u.test(v) && BigInt(v) <= 18446744073709551615n;
}
function owner(v, minimum = 0) {
  return typeof v === "number" && Number.isSafeInteger(v) && !Object.is(v, -0) && v >= minimum && v < Number.MAX_SAFE_INTEGER;
}
function record(v, required, optional = []) {
  const result = snapshotRecord(v, [...required, ...optional], false);
  if (result === null || !required.every((key) => Object.hasOwn(result, key)))
    throw new Error();
  return result;
}
function safely2(work) {
  try {
    return { ok: true, value: work() };
  } catch {
    return { ok: false, error: "invalid personal wire or binding" };
  }
}
function requireValue(condition) {
  if (!condition) throw new Error();
}
function participant(input) {
  const v = record(input, [
    "participant_id",
    "role",
    "process_generation",
    "boot_id",
    "deployment_generation"
  ]);
  requireValue(
    id(v.participant_id) && id(v.boot_id) && (v.role === "product" || v.role === "disk") && isPersonalAuthCounter(v.process_generation) && isPersonalAuthCounter(v.deployment_generation)
  );
  return v;
}
function parsePersonalAuthParticipant(input) {
  return safely2(() => participant(input));
}
function session(input) {
  const tag = record(
    input,
    ["kind"],
    ["session_id", "session_uid", "client_id", "client_sid", "grant_id"]
  );
  if (tag.kind === "paseto") {
    const v2 = record(tag, ["kind", "session_id"]);
    requireValue(id(v2.session_id));
    return v2;
  }
  const v = record(tag, [
    "kind",
    "session_uid",
    "client_id",
    "client_sid",
    "grant_id"
  ]);
  requireValue(
    v.kind === "oidc" && [v.session_uid, v.client_id, v.client_sid, v.grant_id].every(
      (x) => opaque(x)
    )
  );
  return v;
}
function part(input) {
  const v = record(input, [
    "part_id",
    "part_kind",
    "object_id",
    "object_revision",
    "sha256",
    "size_bytes",
    "media_type"
  ]);
  requireValue(
    id(v.part_id) && id(v.object_id) && id(v.object_revision) && (v.part_kind === "note" || v.part_kind === "attachment") && typeof v.sha256 === "string" && DIGEST.test(v.sha256) && owner(v.size_bytes) && v.size_bytes <= (v.part_kind === "note" ? 65536 : 1048576) && v.media_type === "text/plain;charset=utf-8"
  );
  return v;
}
function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value !== null && typeof value === "object")
    return `{${Object.keys(value).sort().map(
      (k) => `${JSON.stringify(k)}:${canonical(value[k])}`
    ).join(",")}}`;
  const encoded = JSON.stringify(value);
  if (encoded === void 0) throw new Error();
  return encoded;
}
function canonicalNumbers(value) {
  if (typeof value === "number")
    requireValue(
      Number.isSafeInteger(value) && value >= 0 && !Object.is(value, -0)
    );
  else if (Array.isArray(value)) value.forEach(canonicalNumbers);
  else if (value !== null && typeof value === "object")
    Object.values(value).forEach(canonicalNumbers);
}
function operation(input) {
  const v = record(
    input,
    [
      "wire_version",
      "profile_id",
      "request_id",
      "idempotency_key",
      "operation_id",
      "authority_kind",
      "person_proof",
      "operation",
      "purpose",
      "resource",
      "capture_binding",
      "participant"
    ],
    ["expected_realm_id"]
  );
  requireValue(
    v.wire_version === PERSONAL_AUTH_WIRE_VERSION && v.profile_id === PERSONAL_AUTH_PROFILE && id(v.request_id) && id(v.idempotency_key) && id(v.operation_id) && v.authority_kind === "person" && (v.operation === "intent.create" || v.operation === "capture.stage") && (v.purpose === "personal.capture" || v.purpose === "personal.resume")
  );
  if (Object.hasOwn(v, "expected_realm_id"))
    requireValue(id(v.expected_realm_id));
  const proof = record(v.person_proof, ["kind", "token"]);
  requireValue(
    (proof.kind === "oidc_access_token" || proof.kind === "paseto_session") && opaque(proof.token, 16384)
  );
  const actor = participant(v.participant);
  requireValue(actor.role === "product");
  const binding = parsePersonalCaptureBinding(v.capture_binding);
  requireValue(binding.ok);
  const { descriptor, status } = binding.value;
  canonicalNumbers(descriptor);
  if (status !== null) canonicalNumbers(status);
  requireValue(
    v.operation === "intent.create" ? status === null : status !== null && status.state === "awaiting_bytes"
  );
  const resource = record(v.resource, [
    "kind",
    "intent_id",
    "intent_revision",
    "conversation_id",
    "message_id",
    "expected_conversation_revision",
    "parts"
  ]);
  const rawParts = snapshotArray(resource.parts, 1, 2);
  requireValue(rawParts !== null);
  const parts = rawParts.map(part);
  const d = descriptor;
  requireValue(
    owner(resource.expected_conversation_revision) && (status === null ? resource.intent_revision === null : owner(resource.intent_revision, 1)) && personalCaptureResourceMatches(
      d.realmId,
      { ...resource, parts },
      binding.value
    )
  );
  if (v.expected_realm_id !== void 0)
    requireValue(v.expected_realm_id === d.realmId);
  return {
    ...v,
    person_proof: proof,
    participant: actor,
    resource: { ...resource, parts },
    capture_binding: { descriptor: d, status }
  };
}
function parsePersonalAuthOperation(input) {
  return safely2(() => operation(input));
}
function parsePersonalAuthOperationJson(input) {
  const parsed = parsePersonalAuthJson(input);
  return parsed.ok ? parsePersonalAuthOperation(parsed.value) : parsed;
}
function context(input) {
  const v = record(input, [
    "issuer",
    "subject",
    "session",
    "authority_ref",
    "authority_version",
    "actor_client_id",
    "consumer_client_id",
    "realm_id",
    "realm_binding_version",
    "policy_version",
    "policy_epoch",
    "deployment_generation",
    "participant_config_version",
    "participant",
    "provisioning"
  ]);
  requireValue(opaque(v.issuer, 2048));
  const issuer = new URL(v.issuer);
  requireValue(
    issuer.protocol === "https:" && (issuer.href === v.issuer || issuer.href === v.issuer + "/") && !issuer.username && !issuer.password && !issuer.search && !issuer.hash
  );
  requireValue(
    [v.subject, v.authority_ref, v.realm_id].every(id) && [v.actor_client_id, v.consumer_client_id, v.policy_version].every(
      (x) => opaque(x)
    ) && [
      v.authority_version,
      v.realm_binding_version,
      v.policy_epoch,
      v.deployment_generation,
      v.participant_config_version
    ].every(isPersonalAuthCounter)
  );
  const p = record(v.provisioning, [
    "realm_id",
    "product_client_id",
    "disk_client_id",
    "product_participant_id",
    "disk_participant_id",
    "deployment_generation",
    "participant_config_version"
  ]);
  requireValue(
    [p.realm_id, p.product_participant_id, p.disk_participant_id].every(id) && [p.product_client_id, p.disk_client_id].every((x) => opaque(x)) && p.product_client_id !== p.disk_client_id && p.product_participant_id !== p.disk_participant_id && [p.deployment_generation, p.participant_config_version].every(
      isPersonalAuthCounter
    )
  );
  const actor = participant(v.participant);
  const source = session(v.session);
  requireValue(
    actor.role === "product" && actor.participant_id === p.product_participant_id && v.actor_client_id === p.product_client_id && v.consumer_client_id === p.product_client_id && v.realm_id === p.realm_id && v.deployment_generation === p.deployment_generation && actor.deployment_generation === p.deployment_generation && v.participant_config_version === p.participant_config_version
  );
  return {
    ...v,
    session: source,
    participant: actor,
    provisioning: p
  };
}
function parsePersonalAuthBindingContext(input) {
  return safely2(() => context(input));
}
function bound(request, binding) {
  requireValue(
    request.capture_binding.descriptor.realmId === binding.realm_id && canonical(request.participant) === canonical(binding.participant)
  );
  requireValue(
    request.person_proof.kind === "paseto_session" ? binding.session.kind === "paseto" : binding.session.kind === "oidc"
  );
}
function personalAuthOperationMatchesBinding(request, binding) {
  return safely2(() => {
    bound(operation(request), context(binding));
    return true;
  }).ok;
}
function personalAuthOperationFingerprintInput(request, binding) {
  return safely2(() => {
    const r = operation(request);
    const c = context(binding);
    bound(r, c);
    return canonical({
      wire_version: r.wire_version,
      profile_id: r.profile_id,
      operation_id: r.operation_id,
      authority_kind: r.authority_kind,
      operation: r.operation,
      purpose: r.purpose,
      resource: r.resource,
      capture_binding: r.capture_binding,
      authority: c
    });
  });
}
function personalAuthMutationIdentity(request, binding) {
  return safely2(() => {
    const r = operation(request);
    const c = context(binding);
    bound(r, c);
    return canonical([
      c.issuer,
      c.actor_client_id,
      c.realm_id,
      "operations",
      r.idempotency_key
    ]);
  });
}
function comparePersonalAuthOperationRetry(first, firstBinding, retry, currentBinding) {
  const a = personalAuthOperationFingerprintInput(first, firstBinding);
  const b = personalAuthOperationFingerprintInput(retry, currentBinding);
  const ka = personalAuthMutationIdentity(first, firstBinding);
  const kb = personalAuthMutationIdentity(retry, currentBinding);
  if (!a.ok || !b.ok || !ka.ok || !kb.ok) return "invalid";
  return ka.value === kb.value && a.value === b.value ? "same_semantics" : "conflict";
}
function incrementPersonalAuthCounter(value) {
  return safely2(() => {
    requireValue(
      isPersonalAuthCounter(value) && value !== "18446744073709551615"
    );
    return (BigInt(value) + 1n).toString();
  });
}

// src/personal-auth-lease-v1.ts
var UUID3 = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
var id2 = (value) => typeof value === "string" && value.length === 36 && UUID3.test(value);
var integer = (value) => typeof value === "number" && Number.isSafeInteger(value) && value >= 0 && !Object.is(value, -0);
function requireValue2(value) {
  if (!value) throw new Error();
}
function record2(input, keys) {
  const value = snapshotRecord(input, keys);
  requireValue2(value !== null);
  return value;
}
function safely3(work) {
  try {
    return { ok: true, value: work() };
  } catch {
    return { ok: false, error: "invalid personal lease wire" };
  }
}
function time(input) {
  requireValue2(
    typeof input === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(input)
  );
  const parsed = Date.parse(input);
  requireValue2(
    Number.isFinite(parsed) && new Date(parsed).toISOString() === input
  );
  return parsed;
}
function release(input) {
  const value = record2(input, [
    "delivery_id",
    "frame_index",
    "object_revision",
    "representation_binding_id",
    "offset_bytes",
    "length_bytes",
    "destination",
    "destination_binding_id"
  ]);
  requireValue2(
    [
      value["delivery_id"],
      value["representation_binding_id"],
      value["destination_binding_id"]
    ].every(id2)
  );
  requireValue2(
    value["object_revision"] === null || id2(value["object_revision"])
  );
  requireValue2(
    integer(value["frame_index"]) && integer(value["offset_bytes"]) && integer(value["length_bytes"]) && value["length_bytes"] <= 65536 && value["offset_bytes"] + value["length_bytes"] <= 1048576
  );
  requireValue2(
    value["destination"] === "product" || value["destination"] === "client"
  );
  return value;
}
function parsePersonalAuthReleaseUnit(input) {
  return safely3(() => release(input));
}
function parsePersonalAuthLeaseAdmission(input) {
  return safely3(() => {
    const value = record2(input, [
      "lease_id",
      "flow_id",
      "grant_id",
      "participant",
      "realm_id",
      "policy_epoch",
      "participant_config_version",
      "lease_kind",
      "effect",
      "resource_binding_id",
      "release_unit",
      "admitted_seq",
      "admitted_at",
      "execute_before",
      "state"
    ]);
    requireValue2(
      [
        value["lease_id"],
        value["flow_id"],
        value["grant_id"],
        value["realm_id"]
      ].every(id2)
    );
    requireValue2(
      [
        value["policy_epoch"],
        value["participant_config_version"],
        value["admitted_seq"]
      ].every(isPersonalAuthCounter)
    );
    requireValue2(value["state"] === "admitted");
    const parsed = parsePersonalAuthParticipant(value["participant"]);
    requireValue2(parsed.ok);
    const participant2 = parsed.value;
    const kind = value["lease_kind"];
    const effect = value["effect"];
    const binding = value["resource_binding_id"];
    requireValue2(binding === null || id2(binding));
    let unit = null;
    if (kind === "release") {
      requireValue2(effect === null && binding !== null);
      unit = release(value["release_unit"]);
      requireValue2(
        unit.destination === (participant2.role === "disk" ? "product" : "client")
      );
    } else {
      requireValue2(value["release_unit"] === null);
      if (kind === "access")
        requireValue2(
          effect === null && (participant2.role === "product" || binding !== null)
        );
      else {
        requireValue2(kind === "effect");
        const allowed = participant2.role === "product" ? [
          "intent_create",
          "intent_stage",
          "intent_cancel",
          "product_publish",
          "repair_link"
        ] : ["disk_stage", "cleanup_cancelled", "repair_link"];
        requireValue2(typeof effect === "string" && allowed.includes(effect));
        requireValue2(binding !== null || effect === "intent_create");
      }
    }
    const admitted = time(value["admitted_at"]);
    const deadline = time(value["execute_before"]);
    requireValue2(
      deadline >= admitted && deadline - admitted <= (kind === "release" ? 1e3 : 3e4)
    );
    return {
      ...value,
      participant: participant2,
      release_unit: unit
    };
  });
}
function comparePersonalAuthLeaseAdmission(expected, received) {
  const a = parsePersonalAuthLeaseAdmission(expected);
  const b = parsePersonalAuthLeaseAdmission(received);
  if (!a.ok || !b.ok) return "invalid";
  const identity = (lease) => JSON.stringify([
    lease.lease_id,
    lease.flow_id,
    lease.grant_id,
    lease.realm_id,
    lease.policy_epoch,
    lease.participant_config_version,
    lease.admitted_seq,
    lease.admitted_at,
    lease.execute_before,
    lease.state,
    lease.lease_kind,
    lease.effect,
    lease.resource_binding_id,
    [
      lease.participant.participant_id,
      lease.participant.role,
      lease.participant.process_generation,
      lease.participant.boot_id,
      lease.participant.deployment_generation
    ],
    lease.release_unit === null ? null : [
      lease.release_unit.delivery_id,
      lease.release_unit.frame_index,
      lease.release_unit.object_revision,
      lease.release_unit.representation_binding_id,
      lease.release_unit.offset_bytes,
      lease.release_unit.length_bytes,
      lease.release_unit.destination,
      lease.release_unit.destination_binding_id
    ]
  ]);
  return identity(a.value) === identity(b.value) ? "same_admission" : "conflict";
}

// src/personal-auth-owner-outcome.ts
var COMMON = [
  "owner_receipt_id",
  "kind",
  "realm_id",
  "deployment_generation",
  "participant_id",
  "process_generation",
  "operation_id",
  "intent_id",
  "owner_commit_id",
  "local_seq",
  "resource_binding_digest"
];
var VARIANTS = {
  intent_created: ["capture_status"],
  intent_staged: ["capture_status", "storage_receipt_ids"],
  disk_stored: ["object_receipt", "storage_receipt_id"],
  product_committed: [
    "capture_status",
    "publication_id",
    "manifest_digest",
    "storage_receipt_ids"
  ],
  product_cancelled: ["capture_status"],
  link_repaired: [
    "committed_owner_outcome_id",
    "storage_receipt_id",
    "link_revision",
    "link_binding_digest"
  ],
  disk_cleaned: [
    "cancelled_owner_outcome_id",
    "cancellation",
    "cleaned_objects"
  ]
};
var EFFECTS = {
  intent_created: "intent_create",
  intent_staged: "intent_stage",
  disk_stored: "disk_stage",
  product_committed: "product_publish",
  product_cancelled: "intent_cancel",
  link_repaired: "repair_link",
  disk_cleaned: "cleanup_cancelled"
};
var ALL_KEYS = [...COMMON, ...new Set(Object.values(VARIANTS).flat())];
var id3 = (value) => typeof value === "string" && value.length === 36 && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/u.test(value);
var digest2 = (value) => typeof value === "string" && value.length === 64 && /^[0-9a-f]{64}$/u.test(value);
function requireValue3(value) {
  if (!value) throw new Error();
}
function storageIds(input, count) {
  const values = snapshotArray(input, count, count);
  requireValue3(values !== null && values.every(id3));
  requireValue3(new Set(values).size === count);
  return values;
}
function cleanedObjects(input) {
  const values = snapshotArray(input, 1, 2);
  requireValue3(values !== null);
  const objects = values.map((item) => {
    const value = snapshotRecord(item, [
      "part_id",
      "object_id",
      "object_revision"
    ]);
    requireValue3(value !== null && Object.values(value).every(id3));
    return value;
  });
  requireValue3(new Set(objects.map((x) => x.part_id)).size === objects.length);
  requireValue3(
    new Set(objects.map((x) => x.object_id)).size === objects.length
  );
  return objects;
}
function parsePersonalAuthOwnerOutcome(input) {
  try {
    const value = snapshotRecord(input, ALL_KEYS, false);
    requireValue3(value !== null);
    const kind = value["kind"];
    requireValue3(typeof kind === "string" && Object.hasOwn(VARIANTS, kind));
    const keys = [...COMMON, ...VARIANTS[kind]];
    requireValue3(
      Object.keys(value).length === keys.length && keys.every((key) => Object.hasOwn(value, key))
    );
    requireValue3(
      [
        "owner_receipt_id",
        "realm_id",
        "participant_id",
        "operation_id",
        "intent_id",
        "owner_commit_id"
      ].every((key) => id3(value[key]))
    );
    requireValue3(
      ["deployment_generation", "process_generation", "local_seq"].every(
        (key) => isPersonalAuthCounter(value[key])
      )
    );
    requireValue3(digest2(value["resource_binding_digest"]));
    if (Object.hasOwn(value, "capture_status")) {
      const status = parsePersonalCaptureStatus(value["capture_status"]);
      requireValue3(status.ok);
      const expected = {
        intent_created: "awaiting_bytes",
        intent_staged: "staged",
        product_committed: "committed",
        product_cancelled: "cancelled"
      };
      requireValue3(
        status.value.state === expected[kind]
      );
      requireValue3(
        status.value.descriptor.realmId === value["realm_id"] && status.value.descriptor.captureId === value["intent_id"]
      );
      if (kind === "intent_created")
        requireValue3(status.value.intentRevision === 1);
      if (status.value.state === "staged" || status.value.state === "committed") {
        value["storage_receipt_ids"] = storageIds(
          value["storage_receipt_ids"],
          status.value.receipts.length
        );
        if (status.value.state === "committed") {
          requireValue3(
            value["publication_id"] === status.value.manifestId && digest2(value["manifest_digest"])
          );
        }
      }
      value["capture_status"] = status.value;
    } else if (kind === "disk_stored") {
      const receipt = parsePersonalObjectReceipt(value["object_receipt"]);
      requireValue3(receipt.ok && id3(value["storage_receipt_id"]));
      requireValue3(
        receipt.value.realmId === value["realm_id"] && receipt.value.captureId === value["intent_id"]
      );
      value["object_receipt"] = receipt.value;
    } else if (kind === "link_repaired") {
      requireValue3(
        id3(value["committed_owner_outcome_id"]) && id3(value["storage_receipt_id"]) && counter(value["link_revision"]) && digest2(value["link_binding_digest"])
      );
    } else {
      requireValue3(
        kind === "disk_cleaned" && id3(value["cancelled_owner_outcome_id"])
      );
      const cancellation = parsePersonalCaptureCancellation(
        value["cancellation"]
      );
      requireValue3(cancellation.ok);
      requireValue3(
        cancellation.value.realmId === value["realm_id"] && cancellation.value.captureId === value["intent_id"]
      );
      value["cancellation"] = cancellation.value;
      value["cleaned_objects"] = cleanedObjects(value["cleaned_objects"]);
    }
    return { ok: true, value };
  } catch {
    return { ok: false, error: "invalid personal owner outcome" };
  }
}
function personalAuthOwnerOutcomeEffect(input) {
  const parsed = parsePersonalAuthOwnerOutcome(input);
  return parsed.ok ? { ok: true, value: EFFECTS[parsed.value.kind] } : parsed;
}
function canonical2(value) {
  if (Array.isArray(value)) return "[" + value.map(canonical2).join(",") + "]";
  if (typeof value === "object" && value !== null) {
    const record3 = value;
    return "{" + Object.keys(record3).sort().map((key) => JSON.stringify(key) + ":" + canonical2(record3[key])).join(",") + "}";
  }
  return JSON.stringify(value);
}
function comparePersonalAuthOwnerOutcome(expected, received) {
  const a = parsePersonalAuthOwnerOutcome(expected);
  const b = parsePersonalAuthOwnerOutcome(received);
  if (!a.ok || !b.ok) return "invalid";
  if (a.value.owner_receipt_id !== b.value.owner_receipt_id)
    return "different_receipt";
  return canonical2(a.value) === canonical2(b.value) ? "same_outcome" : "conflict";
}

// src/personal-auth-outcome-request.ts
var ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/u;
function parsePersonalAuthOwnerOutcomeRequest(input) {
  try {
    const value = snapshotRecord(input, [
      "wire_version",
      "profile_id",
      "request_id",
      "idempotency_key",
      "participant",
      "lease_id",
      "outcome"
    ]);
    if (!value || value.wire_version !== PERSONAL_AUTH_WIRE_VERSION || value.profile_id !== PERSONAL_AUTH_PROFILE || ![value.request_id, value.idempotency_key, value.lease_id].every(
      (x) => typeof x === "string" && ID.test(x)
    ))
      throw new Error();
    const participant2 = parsePersonalAuthParticipant(value.participant);
    const outcome = parsePersonalAuthOwnerOutcome(value.outcome);
    if (!participant2.ok || !outcome.ok) throw new Error();
    const p = participant2.value, o = outcome.value;
    if (o.kind !== "link_repaired" && p.role !== (o.kind === "disk_stored" || o.kind === "disk_cleaned" ? "disk" : "product"))
      throw new Error();
    return {
      ok: true,
      value: {
        wire_version: PERSONAL_AUTH_WIRE_VERSION,
        profile_id: PERSONAL_AUTH_PROFILE,
        request_id: value.request_id,
        idempotency_key: value.idempotency_key,
        lease_id: value.lease_id,
        participant: p,
        outcome: o
      }
    };
  } catch {
    return { ok: false, error: "invalid personal owner outcome request" };
  }
}
function parsePersonalAuthOwnerOutcomeRequestJson(input) {
  const parsed = parsePersonalAuthJson(input);
  return parsed.ok ? parsePersonalAuthOwnerOutcomeRequest(parsed.value) : parsed;
}
function personalAuthOwnerOutcomeRequestMatchesSameGenerationLease(input, leaseInput) {
  const request = parsePersonalAuthOwnerOutcomeRequest(input);
  const lease = parsePersonalAuthLeaseAdmission(leaseInput);
  if (!request.ok || !lease.ok || lease.value.lease_kind !== "effect")
    return false;
  const r = request.value, l = lease.value;
  const effect = personalAuthOwnerOutcomeEffect(r.outcome);
  return effect.ok && effect.value === l.effect && r.lease_id === l.lease_id && r.outcome.realm_id === l.realm_id && r.outcome.participant_id === l.participant.participant_id && r.outcome.process_generation === l.participant.process_generation && r.outcome.deployment_generation === l.participant.deployment_generation && r.participant.participant_id === l.participant.participant_id && r.participant.role === l.participant.role && r.participant.process_generation === l.participant.process_generation && r.participant.boot_id === l.participant.boot_id && r.participant.deployment_generation === l.participant.deployment_generation;
}

// src/knowledge-observation-v1.amendment-1.schema.json
var knowledge_observation_v1_amendment_1_schema_default = {
  $schema: "https://json-schema.org/draft/2020-12/schema",
  $id: "urn:arcanada:knowledge-collective-observation:v1:amendment-1",
  title: "Proposed Knowledge Collective observation profile v1, amendment 1",
  description: "Source preparation for existing KCLIVE-01; not a deployed protocol or modification of published KC schemas. Structural validation is necessary, not source authorization, semantic admission or runtime proof.",
  oneOf: [
    {
      $ref: "#/$defs/runRecord"
    },
    {
      $ref: "#/$defs/eventRecord"
    },
    {
      $ref: "#/$defs/snapshotRecord"
    },
    {
      $ref: "#/$defs/attemptRecord"
    },
    {
      $ref: "#/$defs/artifactRecord"
    },
    {
      $ref: "#/$defs/commandRecord"
    },
    {
      $ref: "#/$defs/deploymentRecord"
    }
  ],
  $defs: {
    opaque: {
      type: "string",
      minLength: 1,
      maxLength: 256,
      pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
    },
    decimal: {
      type: "string",
      pattern: "^(0|[1-9][0-9]*)$"
    },
    date: {
      type: "string",
      format: "date-time"
    },
    viewContext: {
      type: "object",
      properties: {
        project_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        run_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        authorized_view_scope: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        stream_epoch: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        }
      },
      required: [
        "project_id",
        "run_id",
        "authorized_view_scope",
        "stream_epoch"
      ],
      additionalProperties: false
    },
    build: {
      type: "object",
      properties: {
        repository: {
          type: "string",
          minLength: 1
        },
        commit: {
          type: "string",
          pattern: "^[0-9a-f]{40}$"
        },
        adapter_revision: {
          type: "string",
          minLength: 1
        }
      },
      required: [
        "repository",
        "commit",
        "adapter_revision"
      ],
      additionalProperties: false
    },
    producer: {
      type: "object",
      properties: {
        service: {
          type: "string",
          minLength: 1
        },
        instance_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        build: {
          $ref: "#/$defs/build"
        }
      },
      required: [
        "service",
        "instance_id",
        "build"
      ],
      additionalProperties: false
    },
    qualifiedRef: {
      type: "object",
      properties: {
        graph_kind: {
          enum: [
            "processing_execution",
            "contract_receipt_chain",
            "knowledge",
            "work"
          ]
        },
        authority: {
          type: "string",
          minLength: 1
        },
        namespace: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        local_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        revision: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        }
      },
      required: [
        "graph_kind",
        "authority",
        "namespace",
        "local_id",
        "revision"
      ],
      additionalProperties: false
    },
    artifactKey: {
      type: "object",
      properties: {
        authority: {
          type: "string",
          minLength: 1
        },
        namespace: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        artifact_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        revision: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        }
      },
      required: [
        "authority",
        "namespace",
        "artifact_id",
        "revision"
      ],
      additionalProperties: false
    },
    nativeVersions: {
      type: "object",
      properties: {
        revision: {
          type: "string",
          pattern: "^(0|[1-9][0-9]*)$"
        },
        aggregateVersion: {
          type: "string",
          pattern: "^(0|[1-9][0-9]*)$"
        },
        source_revision: {
          type: "string",
          minLength: 1
        }
      },
      required: [],
      additionalProperties: false
    },
    nativeState: {
      oneOf: [
        {
          type: "object",
          properties: {
            authority: {
              type: "string",
              minLength: 1
            },
            value: {
              type: "string",
              minLength: 1
            },
            reason: {
              oneOf: [
                {
                  type: "string",
                  minLength: 1
                },
                {
                  type: "null"
                }
              ]
            }
          },
          required: [
            "authority",
            "value",
            "reason"
          ],
          additionalProperties: false
        },
        {
          type: "null"
        }
      ]
    },
    sourceSequence: {
      type: "object",
      properties: {
        value: {
          oneOf: [
            {
              type: "string",
              pattern: "^(0|[1-9][0-9]*)$"
            },
            {
              type: "null"
            }
          ]
        },
        scope: {
          enum: [
            "database",
            "run",
            "task",
            "partition",
            "unknown"
          ]
        },
        scope_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        partition_id: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        contiguity: {
          enum: [
            "declared_contiguous",
            "not_contiguous",
            "unknown"
          ]
        },
        declaration_ref: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        }
      },
      required: [
        "value",
        "scope",
        "scope_id",
        "partition_id",
        "contiguity",
        "declaration_ref"
      ],
      additionalProperties: false
    },
    freshness: {
      type: "object",
      properties: {
        state: {
          enum: [
            "unknown",
            "awaiting_snapshot",
            "current",
            "stale",
            "reconciling"
          ]
        },
        as_of: {
          oneOf: [
            {
              type: "string",
              format: "date-time"
            },
            {
              type: "null"
            }
          ]
        },
        reason: {
          oneOf: [
            {
              type: "string",
              minLength: 1
            },
            {
              type: "null"
            }
          ]
        }
      },
      required: [
        "state",
        "as_of",
        "reason"
      ],
      additionalProperties: false
    },
    sourcePin: {
      type: "object",
      properties: {
        repository: {
          type: "string",
          minLength: 1
        },
        commit: {
          type: "string",
          pattern: "^[0-9a-f]{40}$"
        },
        path: {
          type: "string",
          minLength: 1
        }
      },
      required: [
        "repository",
        "commit",
        "path"
      ],
      additionalProperties: false
    },
    retention: {
      type: "object",
      properties: {
        policy_ref: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        expires_at: {
          oneOf: [
            {
              type: "string",
              format: "date-time"
            },
            {
              type: "null"
            }
          ]
        }
      },
      required: [
        "policy_ref",
        "expires_at"
      ],
      additionalProperties: false
    },
    checker: {
      type: "object",
      properties: {
        checker_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        checker_revision: {
          type: "string",
          minLength: 1
        },
        method_ref: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        verdict: {
          enum: [
            "PASS",
            "FAIL",
            "UNKNOWN",
            "NOT_APPLICABLE"
          ]
        },
        subject_refs: {
          type: "array",
          items: {
            $ref: "#/$defs/qualifiedRef"
          },
          minItems: 1
        },
        evidence_refs: {
          type: "array",
          items: {
            type: "string",
            minLength: 1,
            maxLength: 256,
            pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
          },
          minItems: 1
        },
        observed_at: {
          type: "string",
          format: "date-time"
        },
        reason: {
          oneOf: [
            {
              type: "string",
              minLength: 1
            },
            {
              type: "null"
            }
          ]
        },
        inapplicability_rule_ref: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        }
      },
      required: [
        "checker_id",
        "checker_revision",
        "method_ref",
        "verdict",
        "subject_refs",
        "evidence_refs",
        "observed_at",
        "reason",
        "inapplicability_rule_ref"
      ],
      additionalProperties: false,
      allOf: [
        {
          if: {
            properties: {
              verdict: {
                const: "UNKNOWN"
              }
            }
          },
          then: {
            properties: {
              reason: {
                type: "string",
                minLength: 1
              }
            }
          }
        },
        {
          if: {
            properties: {
              verdict: {
                const: "NOT_APPLICABLE"
              }
            }
          },
          then: {
            properties: {
              reason: {
                type: "string",
                minLength: 1
              },
              inapplicability_rule_ref: {
                type: "string",
                minLength: 1,
                maxLength: 256,
                pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
              }
            }
          }
        }
      ]
    },
    acceptance: {
      type: "object",
      properties: {
        verdict: {
          enum: [
            "PASS",
            "FAIL",
            "NOT_MEASURED"
          ]
        },
        claim_ids: {
          type: "array",
          items: {
            enum: [
              "CL01",
              "CL02",
              "CL03",
              "CL04",
              "CL05",
              "CL06",
              "CL07",
              "CL08",
              "CL09",
              "CL10",
              "CL11",
              "CL12",
              "CL13",
              "CL14",
              "CL15",
              "CL16",
              "CL17",
              "CL18"
            ]
          },
          minItems: 1
        },
        scope_ref: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        checks: {
          type: "array",
          items: {
            $ref: "#/$defs/checker"
          },
          minItems: 0
        },
        reason: {
          oneOf: [
            {
              type: "string",
              minLength: 1
            },
            {
              type: "null"
            }
          ]
        },
        observation: {
          $ref: "#/$defs/assessmentObservation"
        },
        decision_evidence_ref: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        decision_policy_ref: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        }
      },
      required: [
        "verdict",
        "claim_ids",
        "scope_ref",
        "checks",
        "reason",
        "observation",
        "decision_evidence_ref",
        "decision_policy_ref"
      ],
      additionalProperties: false,
      allOf: [
        {
          if: {
            properties: {
              verdict: {
                enum: [
                  "PASS",
                  "FAIL"
                ]
              }
            }
          },
          then: {
            properties: {
              checks: {
                minItems: 1
              },
              observation: {
                properties: {
                  subject_ref: {
                    $ref: "#/$defs/qualifiedRef"
                  },
                  subject_revision: {
                    type: "string",
                    minLength: 1,
                    maxLength: 256,
                    pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
                  },
                  criterion_revision: {
                    type: "string",
                    minLength: 1
                  },
                  method_ref: {
                    type: "string",
                    minLength: 1,
                    maxLength: 256,
                    pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
                  },
                  observer_id: {
                    type: "string",
                    minLength: 1,
                    maxLength: 256,
                    pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
                  },
                  observed_at: {
                    type: "string",
                    format: "date-time"
                  },
                  grounds: {
                    minItems: 1
                  },
                  source_unknowns: {
                    maxItems: 0
                  }
                }
              }
            }
          }
        },
        {
          if: {
            properties: {
              verdict: {
                const: "PASS"
              }
            }
          },
          then: {
            properties: {
              decision_evidence_ref: {
                type: "string",
                minLength: 1,
                maxLength: 256,
                pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
              },
              decision_policy_ref: {
                type: "string",
                minLength: 1,
                maxLength: 256,
                pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
              }
            }
          }
        }
      ]
    },
    exactDigest: {
      type: "object",
      properties: {
        algorithm: {
          enum: [
            "sha256",
            "blake3"
          ]
        },
        role: {
          const: "exact_content"
        },
        domain: {
          const: "raw-bytes"
        },
        preimage: {
          const: "exact-complete-representation-bytes"
        },
        representation: {
          type: "string",
          minLength: 1
        },
        byte_size: {
          type: "string",
          pattern: "^(0|[1-9][0-9]*)$"
        },
        value: {
          type: "string",
          pattern: "^[0-9a-f]{64}$"
        }
      },
      required: [
        "algorithm",
        "role",
        "domain",
        "preimage",
        "representation",
        "byte_size",
        "value"
      ],
      additionalProperties: false
    },
    canonicalDigest: {
      type: "object",
      properties: {
        algorithm: {
          const: "sha256"
        },
        role: {
          const: "domain_identity"
        },
        domain: {
          const: "Muneral.TaskActivitySnapshotCanonical/v1"
        },
        preimage: {
          const: "ASCII(domain) || 0x00 || JCS_bytes"
        },
        representation: {
          const: "application/json;canonicalization=JCS"
        },
        byte_size: {
          type: "string",
          pattern: "^(0|[1-9][0-9]*)$"
        },
        value: {
          type: "string",
          pattern: "^[0-9a-f]{64}$"
        }
      },
      required: [
        "algorithm",
        "role",
        "domain",
        "preimage",
        "representation",
        "byte_size",
        "value"
      ],
      additionalProperties: false
    },
    fingerprint: {
      type: "object",
      properties: {
        algorithm: {
          const: "blake3"
        },
        role: {
          const: "fingerprint"
        },
        domain: {
          const: "ARAS.audit-v2.native-field"
        },
        preimage: {
          const: "producer-defined-native-field-bytes"
        },
        representation: {
          type: "string",
          minLength: 1
        },
        byte_size: {
          oneOf: [
            {
              type: "string",
              pattern: "^(0|[1-9][0-9]*)$"
            },
            {
              type: "null"
            }
          ]
        },
        byte_size_reason: {
          oneOf: [
            {
              type: "string",
              minLength: 1
            },
            {
              type: "null"
            }
          ]
        },
        value: {
          type: "string",
          pattern: "^[0-9a-f]{16}$"
        }
      },
      required: [
        "algorithm",
        "role",
        "domain",
        "preimage",
        "representation",
        "byte_size",
        "byte_size_reason",
        "value"
      ],
      additionalProperties: false,
      allOf: [
        {
          if: {
            properties: {
              byte_size: {
                type: "null"
              }
            }
          },
          then: {
            properties: {
              byte_size_reason: {
                type: "string",
                minLength: 1
              }
            }
          }
        }
      ]
    },
    digest: {
      oneOf: [
        {
          $ref: "#/$defs/exactDigest"
        },
        {
          $ref: "#/$defs/canonicalDigest"
        },
        {
          $ref: "#/$defs/fingerprint"
        }
      ]
    },
    bodyRef: {
      type: "object",
      properties: {
        evidence_ref: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        digest: {
          $ref: "#/$defs/exactDigest"
        }
      },
      required: [
        "evidence_ref",
        "digest"
      ],
      additionalProperties: false
    },
    artifactLocator: {
      oneOf: [
        {
          type: "object",
          properties: {
            kind: {
              const: "repository"
            },
            repository: {
              type: "string",
              minLength: 1
            },
            commit: {
              type: "string",
              pattern: "^[0-9a-f]{40}$"
            },
            path: {
              type: "string",
              pattern: "^(?!/)(?!.*(?:^|/)\\.\\.(?:/|$))(?!.*[?#]).+$"
            }
          },
          required: [
            "kind",
            "repository",
            "commit",
            "path"
          ],
          additionalProperties: false
        },
        {
          type: "object",
          properties: {
            kind: {
              const: "opaque_service"
            },
            reference: {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            version: {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            }
          },
          required: [
            "kind",
            "reference",
            "version"
          ],
          additionalProperties: false
        },
        {
          type: "object",
          properties: {
            kind: {
              const: "drive_file"
            },
            file_id: {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            revision: {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            }
          },
          required: [
            "kind",
            "file_id",
            "revision"
          ],
          additionalProperties: false
        }
      ]
    },
    node: {
      type: "object",
      properties: {
        ref: {
          $ref: "#/$defs/qualifiedRef"
        },
        node_type: {
          type: "string",
          minLength: 1
        },
        native_state: {
          $ref: "#/$defs/nativeState"
        },
        native_versions: {
          $ref: "#/$defs/nativeVersions"
        },
        acceptance: {
          $ref: "#/$defs/acceptance"
        },
        evidence_refs: {
          type: "array",
          items: {
            type: "string",
            minLength: 1,
            maxLength: 256,
            pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
          },
          minItems: 0
        },
        attributes: {
          type: "object",
          properties: {
            profile: {
              type: "string",
              minLength: 1
            },
            text_source: {
              type: "string",
              minLength: 1
            },
            lease_ref: {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            fence: {
              type: "string",
              pattern: "^(0|[1-9][0-9]*)$"
            },
            execution_observed: {
              type: "boolean"
            },
            receipt_run_id: {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            database_run_id: {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            chain_id: {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            attempt_recording: {
              enum: [
                "observed",
                "not_measured"
              ]
            },
            availability: {
              enum: [
                "retained",
                "missing",
                "collected",
                "quarantined",
                "unknown"
              ]
            }
          },
          required: [],
          additionalProperties: false
        }
      },
      required: [
        "ref",
        "node_type",
        "native_state",
        "native_versions",
        "acceptance",
        "evidence_refs",
        "attributes"
      ],
      additionalProperties: false
    },
    edge: {
      type: "object",
      properties: {
        edge_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        kind: {
          enum: [
            "contains",
            "depends_on",
            "optional_dependency",
            "related_to",
            "uses",
            "produced_by",
            "verifies",
            "supersedes",
            "derives_from",
            "predecessor"
          ]
        },
        from: {
          $ref: "#/$defs/qualifiedRef"
        },
        to: {
          $ref: "#/$defs/qualifiedRef"
        },
        evidence_refs: {
          type: "array",
          items: {
            type: "string",
            minLength: 1,
            maxLength: 256,
            pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
          },
          minItems: 1
        }
      },
      required: [
        "edge_id",
        "kind",
        "from",
        "to",
        "evidence_refs"
      ],
      additionalProperties: false
    },
    crosslink: {
      type: "object",
      properties: {
        link_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        kind: {
          enum: [
            "uses",
            "produced_by",
            "verifies",
            "supersedes",
            "derives_from",
            "correlates"
          ]
        },
        from: {
          $ref: "#/$defs/qualifiedRef"
        },
        to: {
          $ref: "#/$defs/qualifiedRef"
        },
        association_ref: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        evidence_refs: {
          type: "array",
          items: {
            type: "string",
            minLength: 1,
            maxLength: 256,
            pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
          },
          minItems: 1
        }
      },
      required: [
        "link_id",
        "kind",
        "from",
        "to",
        "association_ref",
        "evidence_refs"
      ],
      additionalProperties: false
    },
    graph: {
      type: "object",
      properties: {
        graph_kind: {
          enum: [
            "processing_execution",
            "contract_receipt_chain",
            "knowledge",
            "work"
          ]
        },
        authority: {
          type: "string",
          minLength: 1
        },
        graph_revision: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        nodes: {
          type: "array",
          items: {
            $ref: "#/$defs/node"
          },
          minItems: 0
        },
        edges: {
          type: "array",
          items: {
            $ref: "#/$defs/edge"
          },
          minItems: 0
        }
      },
      required: [
        "graph_kind",
        "authority",
        "graph_revision",
        "nodes",
        "edges"
      ],
      additionalProperties: false
    },
    authorityRevision: {
      type: "object",
      properties: {
        authority: {
          type: "string",
          minLength: 1
        },
        scope_ref: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        versions: {
          $ref: "#/$defs/nativeVersions"
        },
        observed_at: {
          type: "string",
          format: "date-time"
        },
        evidence_ref: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        }
      },
      required: [
        "authority",
        "scope_ref",
        "versions",
        "observed_at",
        "evidence_ref"
      ],
      additionalProperties: false
    },
    actionObservation: {
      type: "object",
      properties: {
        operation: {
          type: "string",
          minLength: 1
        },
        status: {
          enum: [
            "allowed",
            "denied",
            "unknown"
          ]
        },
        evaluated_at: {
          type: "string",
          format: "date-time"
        },
        authorization_observation_ref: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        }
      },
      required: [
        "operation",
        "status",
        "evaluated_at",
        "authorization_observation_ref"
      ],
      additionalProperties: false
    },
    run: {
      type: "object",
      properties: {
        kind: {
          enum: [
            "knowledge",
            "agent"
          ]
        },
        root_task: {
          oneOf: [
            {
              $ref: "#/$defs/qualifiedRef"
            },
            {
              type: "null"
            }
          ]
        },
        owner_subject_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        environment: {
          type: "string",
          minLength: 1
        },
        selected_profile: {
          type: "string",
          minLength: 1
        },
        source_pins: {
          type: "array",
          items: {
            $ref: "#/$defs/sourcePin"
          },
          minItems: 1
        },
        budgets: {
          type: "object",
          properties: {
            policy_ref: {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            max_attempts: {
              type: "string",
              pattern: "^(0|[1-9][0-9]*)$"
            }
          },
          required: [
            "policy_ref",
            "max_attempts"
          ],
          additionalProperties: false
        },
        retention: {
          $ref: "#/$defs/retention"
        },
        current_cursor: {
          type: "string",
          pattern: "^(0|[1-9][0-9]*)$"
        },
        connection: {
          enum: [
            "connected",
            "disconnected",
            "unconnected"
          ]
        },
        freshness: {
          $ref: "#/$defs/freshness"
        },
        native_state: {
          $ref: "#/$defs/nativeState"
        },
        acceptance: {
          $ref: "#/$defs/acceptance"
        }
      },
      required: [
        "kind",
        "root_task",
        "owner_subject_id",
        "environment",
        "selected_profile",
        "source_pins",
        "budgets",
        "retention",
        "current_cursor",
        "connection",
        "freshness",
        "native_state",
        "acceptance"
      ],
      additionalProperties: false
    },
    snapshot: {
      type: "object",
      properties: {
        watermark: {
          type: "string",
          pattern: "^(0|[1-9][0-9]*)$"
        },
        snapshot_kind: {
          enum: [
            "full",
            "partial"
          ]
        },
        trusted_snapshot_ref: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        plan_revision: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        source_revisions: {
          type: "array",
          items: {
            $ref: "#/$defs/authorityRevision"
          },
          minItems: 1
        },
        coverage: {
          type: "object",
          properties: {
            extent: {
              const: "declared_authorized_projection"
            },
            declared_graph_kinds: {
              type: "array",
              items: {
                enum: [
                  "processing_execution",
                  "contract_receipt_chain",
                  "knowledge",
                  "work"
                ]
              },
              minItems: 1,
              maxItems: 4,
              uniqueItems: true
            },
            complete: {
              type: "boolean"
            },
            next_page_token: {
              oneOf: [
                {
                  type: "string",
                  minLength: 1,
                  maxLength: 256,
                  pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
                },
                {
                  type: "null"
                }
              ]
            },
            page_set: {
              type: "object",
              properties: {
                page_set_ref: {
                  type: "string",
                  minLength: 1,
                  maxLength: 256,
                  pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
                },
                page_index: {
                  type: "string",
                  pattern: "^(0|[1-9][0-9]*)$"
                },
                page_count: {
                  type: "string",
                  pattern: "^(0|[1-9][0-9]*)$"
                }
              },
              required: [
                "page_set_ref",
                "page_index",
                "page_count"
              ],
              additionalProperties: false
            }
          },
          required: [
            "extent",
            "declared_graph_kinds",
            "complete",
            "next_page_token"
          ],
          additionalProperties: false
        },
        source_atomicity: {
          enum: [
            "not_established",
            "source_asserted_with_evidence"
          ]
        },
        atomicity_evidence_ref: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        graphs: {
          type: "array",
          items: {
            $ref: "#/$defs/graph"
          },
          minItems: 1,
          maxItems: 4
        },
        crosslinks: {
          type: "array",
          items: {
            $ref: "#/$defs/crosslink"
          },
          minItems: 0
        },
        allowed_actions_observation: {
          type: "array",
          items: {
            $ref: "#/$defs/actionObservation"
          },
          minItems: 0
        },
        reset: {
          oneOf: [
            {
              type: "object",
              properties: {
                previous_epoch: {
                  type: "string",
                  minLength: 1,
                  maxLength: 256,
                  pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
                },
                reason: {
                  enum: [
                    "expired_cursor",
                    "authorization_scope_changed",
                    "server_restart"
                  ]
                },
                authorization_observation_ref: {
                  type: "string",
                  minLength: 1,
                  maxLength: 256,
                  pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
                }
              },
              required: [
                "previous_epoch",
                "reason",
                "authorization_observation_ref"
              ],
              additionalProperties: false
            },
            {
              type: "null"
            }
          ]
        },
        native_state: {
          $ref: "#/$defs/nativeState"
        },
        acceptance: {
          $ref: "#/$defs/acceptance"
        }
      },
      required: [
        "watermark",
        "snapshot_kind",
        "trusted_snapshot_ref",
        "plan_revision",
        "source_revisions",
        "coverage",
        "source_atomicity",
        "atomicity_evidence_ref",
        "graphs",
        "crosslinks",
        "allowed_actions_observation",
        "reset",
        "native_state",
        "acceptance"
      ],
      additionalProperties: false,
      allOf: [
        {
          if: {
            properties: {
              snapshot_kind: {
                const: "full"
              }
            }
          },
          then: {
            properties: {
              coverage: {
                properties: {
                  complete: {
                    const: true
                  },
                  next_page_token: {
                    type: "null"
                  }
                }
              }
            }
          }
        },
        {
          if: {
            properties: {
              source_atomicity: {
                const: "source_asserted_with_evidence"
              }
            }
          },
          then: {
            properties: {
              atomicity_evidence_ref: {
                type: "string",
                minLength: 1,
                maxLength: 256,
                pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
              }
            }
          }
        }
      ]
    },
    event: {
      type: "object",
      properties: {
        event_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        cursor: {
          type: "string",
          pattern: "^(0|[1-9][0-9]*)$"
        },
        producer_event_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        source_sequence: {
          $ref: "#/$defs/sourceSequence"
        },
        kind: {
          enum: [
            "native_state_observed",
            "plan_observed",
            "receipt_association_observed",
            "artifact_observed",
            "command_observed",
            "deployment_observed",
            "refusal_observed",
            "record_withdrawn",
            "capability_observed"
          ]
        },
        plan_revision: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        subject_refs: {
          type: "array",
          items: {
            $ref: "#/$defs/qualifiedRef"
          },
          minItems: 0
        },
        occurred_at: {
          oneOf: [
            {
              type: "string",
              format: "date-time"
            },
            {
              type: "null"
            }
          ]
        },
        causation_ref: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        correlation_ref: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        native_state: {
          $ref: "#/$defs/nativeState"
        },
        native_versions: {
          $ref: "#/$defs/nativeVersions"
        },
        evidence_refs: {
          type: "array",
          items: {
            type: "string",
            minLength: 1,
            maxLength: 256,
            pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
          },
          minItems: 0
        },
        body: {
          $ref: "#/$defs/bodyRef"
        },
        related_record_ids: {
          type: "array",
          items: {
            type: "string",
            minLength: 1,
            maxLength: 256,
            pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
          },
          minItems: 0
        }
      },
      required: [
        "event_id",
        "cursor",
        "producer_event_id",
        "source_sequence",
        "kind",
        "plan_revision",
        "subject_refs",
        "occurred_at",
        "causation_ref",
        "correlation_ref",
        "native_state",
        "native_versions",
        "evidence_refs",
        "body",
        "related_record_ids"
      ],
      additionalProperties: false
    },
    attempt: {
      type: "object",
      properties: {
        attempt_ref: {
          $ref: "#/$defs/qualifiedRef"
        },
        task_or_stage_ref: {
          $ref: "#/$defs/qualifiedRef"
        },
        ordinal: {
          type: "string",
          pattern: "^(0|[1-9][0-9]*)$"
        },
        parent_attempt_ref: {
          oneOf: [
            {
              $ref: "#/$defs/qualifiedRef"
            },
            {
              type: "null"
            }
          ]
        },
        retry_of: {
          oneOf: [
            {
              $ref: "#/$defs/qualifiedRef"
            },
            {
              type: "null"
            }
          ]
        },
        plan_revision: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        contract_binding_ref: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        context_binding_ref: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        executor: {
          oneOf: [
            {
              type: "object",
              properties: {
                principal_id: {
                  type: "string",
                  minLength: 1,
                  maxLength: 256,
                  pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
                },
                instance_id: {
                  type: "string",
                  minLength: 1,
                  maxLength: 256,
                  pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
                }
              },
              required: [
                "principal_id",
                "instance_id"
              ],
              additionalProperties: false
            },
            {
              type: "null"
            }
          ]
        },
        lease: {
          oneOf: [
            {
              type: "object",
              properties: {
                lease_ref: {
                  type: "string",
                  minLength: 1,
                  maxLength: 256,
                  pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
                },
                fence: {
                  type: "string",
                  pattern: "^(0|[1-9][0-9]*)$"
                },
                observed_at: {
                  type: "string",
                  format: "date-time"
                }
              },
              required: [
                "lease_ref",
                "fence",
                "observed_at"
              ],
              additionalProperties: false
            },
            {
              type: "null"
            }
          ]
        },
        started_at: {
          oneOf: [
            {
              type: "string",
              format: "date-time"
            },
            {
              type: "null"
            }
          ]
        },
        ended_at: {
          oneOf: [
            {
              type: "string",
              format: "date-time"
            },
            {
              type: "null"
            }
          ]
        },
        native_state: {
          $ref: "#/$defs/nativeState"
        },
        outputs: {
          type: "array",
          items: {
            $ref: "#/$defs/artifactKey"
          },
          minItems: 0
        },
        evidence_coverage: {
          enum: [
            "exact_attempt",
            "unbounded_slice",
            "unknown"
          ]
        },
        evidence_refs: {
          type: "array",
          items: {
            type: "string",
            minLength: 1,
            maxLength: 256,
            pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
          },
          minItems: 0
        },
        acceptance: {
          $ref: "#/$defs/acceptance"
        }
      },
      required: [
        "attempt_ref",
        "task_or_stage_ref",
        "ordinal",
        "parent_attempt_ref",
        "retry_of",
        "plan_revision",
        "contract_binding_ref",
        "context_binding_ref",
        "executor",
        "lease",
        "started_at",
        "ended_at",
        "native_state",
        "outputs",
        "evidence_coverage",
        "evidence_refs",
        "acceptance"
      ],
      additionalProperties: false
    },
    artifact: {
      type: "object",
      properties: {
        artifact: {
          $ref: "#/$defs/artifactKey"
        },
        profile: {
          type: "string",
          minLength: 1
        },
        kind: {
          type: "string",
          minLength: 1
        },
        representation: {
          type: "string",
          minLength: 1
        },
        byte_size: {
          oneOf: [
            {
              type: "string",
              pattern: "^(0|[1-9][0-9]*)$"
            },
            {
              type: "null"
            }
          ]
        },
        digests: {
          type: "array",
          items: {
            $ref: "#/$defs/digest"
          },
          minItems: 0
        },
        source_anchors: {
          type: "array",
          items: {
            type: "string",
            minLength: 1,
            maxLength: 256,
            pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
          },
          minItems: 0
        },
        admission_scope_ref: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        locator: {
          oneOf: [
            {
              $ref: "#/$defs/artifactLocator"
            },
            {
              type: "null"
            }
          ]
        },
        storage_identity: {
          enum: [
            "immutable",
            "versioned",
            "mutable",
            "unknown"
          ]
        },
        availability: {
          enum: [
            "retained",
            "missing",
            "collected",
            "quarantined",
            "unknown"
          ]
        },
        access: {
          enum: [
            "allowed",
            "denied",
            "unknown"
          ]
        },
        access_observed_at: {
          type: "string",
          format: "date-time"
        },
        availability_observed_at: {
          oneOf: [
            {
              type: "string",
              format: "date-time"
            },
            {
              type: "null"
            }
          ]
        },
        retention: {
          $ref: "#/$defs/retention"
        },
        supersedes: {
          oneOf: [
            {
              $ref: "#/$defs/artifactKey"
            },
            {
              type: "null"
            }
          ]
        },
        acceptance: {
          $ref: "#/$defs/acceptance"
        },
        upstream_contract_ref: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        upstream_conformance: {
          enum: [
            "NOT_MEASURED",
            "source_verified"
          ]
        }
      },
      required: [
        "artifact",
        "profile",
        "kind",
        "representation",
        "byte_size",
        "digests",
        "source_anchors",
        "admission_scope_ref",
        "locator",
        "storage_identity",
        "availability",
        "access",
        "access_observed_at",
        "availability_observed_at",
        "retention",
        "supersedes",
        "acceptance",
        "upstream_contract_ref",
        "upstream_conformance"
      ],
      additionalProperties: false
    },
    expectedRevision: {
      oneOf: [
        {
          type: "object",
          properties: {
            kind: {
              enum: [
                "revision",
                "aggregateVersion"
              ]
            },
            value: {
              type: "string",
              pattern: "^(0|[1-9][0-9]*)$"
            }
          },
          required: [
            "kind",
            "value"
          ],
          additionalProperties: false
        },
        {
          type: "object",
          properties: {
            kind: {
              const: "plan_revision"
            },
            value: {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            }
          },
          required: [
            "kind",
            "value"
          ],
          additionalProperties: false
        }
      ]
    },
    command: {
      type: "object",
      properties: {
        command_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        principal_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        operation: {
          type: "string",
          minLength: 1
        },
        input_digest: {
          $ref: "#/$defs/exactDigest"
        },
        idempotency_key: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        expected_revision: {
          oneOf: [
            {
              $ref: "#/$defs/expectedRevision"
            },
            {
              type: "null"
            }
          ]
        },
        journal_status: {
          enum: [
            "intent_observed",
            "accepted_observed",
            "rejected_observed",
            "unknown"
          ]
        },
        reason: {
          oneOf: [
            {
              type: "string",
              minLength: 1
            },
            {
              type: "null"
            }
          ]
        },
        authorization_observation_ref: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        canonical_operation_ref: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        canonical_run_id: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        canonical_task_ref: {
          oneOf: [
            {
              $ref: "#/$defs/qualifiedRef"
            },
            {
              type: "null"
            }
          ]
        },
        canonical_attempt_ref: {
          oneOf: [
            {
              $ref: "#/$defs/qualifiedRef"
            },
            {
              type: "null"
            }
          ]
        },
        evidence_refs: {
          type: "array",
          items: {
            type: "string",
            minLength: 1,
            maxLength: 256,
            pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
          },
          minItems: 0
        },
        acceptance: {
          $ref: "#/$defs/acceptance"
        }
      },
      required: [
        "command_id",
        "principal_id",
        "operation",
        "input_digest",
        "idempotency_key",
        "expected_revision",
        "journal_status",
        "reason",
        "authorization_observation_ref",
        "canonical_operation_ref",
        "canonical_run_id",
        "canonical_task_ref",
        "canonical_attempt_ref",
        "evidence_refs",
        "acceptance"
      ],
      additionalProperties: false,
      allOf: [
        {
          if: {
            properties: {
              journal_status: {
                const: "rejected_observed"
              }
            }
          },
          then: {
            properties: {
              reason: {
                type: "string",
                minLength: 1
              }
            }
          }
        }
      ]
    },
    deployment: {
      type: "object",
      properties: {
        service_alias: {
          type: "string",
          minLength: 1
        },
        environment: {
          type: "string",
          minLength: 1
        },
        actual_build: {
          oneOf: [
            {
              $ref: "#/$defs/build"
            },
            {
              type: "null"
            }
          ]
        },
        capabilities: {
          type: "array",
          items: {
            type: "object",
            properties: {
              name: {
                type: "string",
                minLength: 1
              },
              status: {
                enum: [
                  "observed",
                  "source_declared",
                  "not_measured",
                  "refused"
                ]
              },
              evidence_refs: {
                type: "array",
                items: {
                  type: "string",
                  minLength: 1,
                  maxLength: 256,
                  pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
                },
                minItems: 0
              }
            },
            required: [
              "name",
              "status",
              "evidence_refs"
            ],
            additionalProperties: false
          },
          minItems: 0
        },
        provenance_refs: {
          type: "array",
          items: {
            type: "string",
            minLength: 1,
            maxLength: 256,
            pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
          },
          minItems: 1
        },
        acceptance: {
          $ref: "#/$defs/acceptance"
        }
      },
      required: [
        "service_alias",
        "environment",
        "actual_build",
        "capabilities",
        "provenance_refs",
        "acceptance"
      ],
      additionalProperties: false
    },
    runRecord: {
      type: "object",
      properties: {
        profile: {
          const: "knowledge-collective-observation/v1"
        },
        record_type: {
          const: "run"
        },
        record_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        mode: {
          enum: [
            "live",
            "replay",
            "fixture"
          ]
        },
        view_context: {
          $ref: "#/$defs/viewContext"
        },
        producer: {
          $ref: "#/$defs/producer"
        },
        observed_at: {
          type: "string",
          format: "date-time"
        },
        recorded_at: {
          type: "string",
          format: "date-time"
        },
        evidence_basis: {
          enum: [
            "fixture",
            "source_inspection",
            "native_observation",
            "exact_byte_read",
            "checker_measurement"
          ]
        },
        data: {
          $ref: "#/$defs/run"
        },
        required_extensions: {
          type: "array",
          items: {
            const: "lossless-decimal-counters/v1"
          },
          minItems: 1,
          maxItems: 1
        }
      },
      required: [
        "profile",
        "record_type",
        "record_id",
        "mode",
        "view_context",
        "producer",
        "observed_at",
        "recorded_at",
        "evidence_basis",
        "data",
        "required_extensions"
      ],
      additionalProperties: false
    },
    eventRecord: {
      type: "object",
      properties: {
        profile: {
          const: "knowledge-collective-observation/v1"
        },
        record_type: {
          const: "event"
        },
        record_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        mode: {
          enum: [
            "live",
            "replay",
            "fixture"
          ]
        },
        view_context: {
          $ref: "#/$defs/viewContext"
        },
        producer: {
          $ref: "#/$defs/producer"
        },
        observed_at: {
          type: "string",
          format: "date-time"
        },
        recorded_at: {
          type: "string",
          format: "date-time"
        },
        evidence_basis: {
          enum: [
            "fixture",
            "source_inspection",
            "native_observation",
            "exact_byte_read",
            "checker_measurement"
          ]
        },
        data: {
          $ref: "#/$defs/event"
        },
        required_extensions: {
          type: "array",
          items: {
            const: "lossless-decimal-counters/v1"
          },
          minItems: 1,
          maxItems: 1
        }
      },
      required: [
        "profile",
        "record_type",
        "record_id",
        "mode",
        "view_context",
        "producer",
        "observed_at",
        "recorded_at",
        "evidence_basis",
        "data",
        "required_extensions"
      ],
      additionalProperties: false
    },
    snapshotRecord: {
      type: "object",
      properties: {
        profile: {
          const: "knowledge-collective-observation/v1"
        },
        record_type: {
          const: "snapshot"
        },
        record_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        mode: {
          enum: [
            "live",
            "replay",
            "fixture"
          ]
        },
        view_context: {
          $ref: "#/$defs/viewContext"
        },
        producer: {
          $ref: "#/$defs/producer"
        },
        observed_at: {
          type: "string",
          format: "date-time"
        },
        recorded_at: {
          type: "string",
          format: "date-time"
        },
        evidence_basis: {
          enum: [
            "fixture",
            "source_inspection",
            "native_observation",
            "exact_byte_read",
            "checker_measurement"
          ]
        },
        data: {
          $ref: "#/$defs/snapshot"
        },
        required_extensions: {
          type: "array",
          items: {
            const: "lossless-decimal-counters/v1"
          },
          minItems: 1,
          maxItems: 1
        }
      },
      required: [
        "profile",
        "record_type",
        "record_id",
        "mode",
        "view_context",
        "producer",
        "observed_at",
        "recorded_at",
        "evidence_basis",
        "data",
        "required_extensions"
      ],
      additionalProperties: false
    },
    attemptRecord: {
      type: "object",
      properties: {
        profile: {
          const: "knowledge-collective-observation/v1"
        },
        record_type: {
          const: "attempt"
        },
        record_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        mode: {
          enum: [
            "live",
            "replay",
            "fixture"
          ]
        },
        view_context: {
          $ref: "#/$defs/viewContext"
        },
        producer: {
          $ref: "#/$defs/producer"
        },
        observed_at: {
          type: "string",
          format: "date-time"
        },
        recorded_at: {
          type: "string",
          format: "date-time"
        },
        evidence_basis: {
          enum: [
            "fixture",
            "source_inspection",
            "native_observation",
            "exact_byte_read",
            "checker_measurement"
          ]
        },
        data: {
          $ref: "#/$defs/attempt"
        },
        required_extensions: {
          type: "array",
          items: {
            const: "lossless-decimal-counters/v1"
          },
          minItems: 1,
          maxItems: 1
        }
      },
      required: [
        "profile",
        "record_type",
        "record_id",
        "mode",
        "view_context",
        "producer",
        "observed_at",
        "recorded_at",
        "evidence_basis",
        "data",
        "required_extensions"
      ],
      additionalProperties: false
    },
    artifactRecord: {
      type: "object",
      properties: {
        profile: {
          const: "knowledge-collective-observation/v1"
        },
        record_type: {
          const: "artifact"
        },
        record_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        mode: {
          enum: [
            "live",
            "replay",
            "fixture"
          ]
        },
        view_context: {
          $ref: "#/$defs/viewContext"
        },
        producer: {
          $ref: "#/$defs/producer"
        },
        observed_at: {
          type: "string",
          format: "date-time"
        },
        recorded_at: {
          type: "string",
          format: "date-time"
        },
        evidence_basis: {
          enum: [
            "fixture",
            "source_inspection",
            "native_observation",
            "exact_byte_read",
            "checker_measurement"
          ]
        },
        data: {
          $ref: "#/$defs/artifact"
        },
        required_extensions: {
          type: "array",
          items: {
            const: "lossless-decimal-counters/v1"
          },
          minItems: 1,
          maxItems: 1
        }
      },
      required: [
        "profile",
        "record_type",
        "record_id",
        "mode",
        "view_context",
        "producer",
        "observed_at",
        "recorded_at",
        "evidence_basis",
        "data",
        "required_extensions"
      ],
      additionalProperties: false
    },
    commandRecord: {
      type: "object",
      properties: {
        profile: {
          const: "knowledge-collective-observation/v1"
        },
        record_type: {
          const: "command"
        },
        record_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        mode: {
          enum: [
            "live",
            "replay",
            "fixture"
          ]
        },
        view_context: {
          $ref: "#/$defs/viewContext"
        },
        producer: {
          $ref: "#/$defs/producer"
        },
        observed_at: {
          type: "string",
          format: "date-time"
        },
        recorded_at: {
          type: "string",
          format: "date-time"
        },
        evidence_basis: {
          enum: [
            "fixture",
            "source_inspection",
            "native_observation",
            "exact_byte_read",
            "checker_measurement"
          ]
        },
        data: {
          $ref: "#/$defs/command"
        },
        required_extensions: {
          type: "array",
          items: {
            const: "lossless-decimal-counters/v1"
          },
          minItems: 1,
          maxItems: 1
        }
      },
      required: [
        "profile",
        "record_type",
        "record_id",
        "mode",
        "view_context",
        "producer",
        "observed_at",
        "recorded_at",
        "evidence_basis",
        "data",
        "required_extensions"
      ],
      additionalProperties: false
    },
    deploymentRecord: {
      type: "object",
      properties: {
        profile: {
          const: "knowledge-collective-observation/v1"
        },
        record_type: {
          const: "deployment"
        },
        record_id: {
          type: "string",
          minLength: 1,
          maxLength: 256,
          pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
        },
        mode: {
          enum: [
            "live",
            "replay",
            "fixture"
          ]
        },
        view_context: {
          $ref: "#/$defs/viewContext"
        },
        producer: {
          $ref: "#/$defs/producer"
        },
        observed_at: {
          type: "string",
          format: "date-time"
        },
        recorded_at: {
          type: "string",
          format: "date-time"
        },
        evidence_basis: {
          enum: [
            "fixture",
            "source_inspection",
            "native_observation",
            "exact_byte_read",
            "checker_measurement"
          ]
        },
        data: {
          $ref: "#/$defs/deployment"
        },
        required_extensions: {
          type: "array",
          items: {
            const: "lossless-decimal-counters/v1"
          },
          minItems: 1,
          maxItems: 1
        }
      },
      required: [
        "profile",
        "record_type",
        "record_id",
        "mode",
        "view_context",
        "producer",
        "observed_at",
        "recorded_at",
        "evidence_basis",
        "data",
        "required_extensions"
      ],
      additionalProperties: false
    },
    assessmentObservation: {
      type: "object",
      properties: {
        subject_ref: {
          oneOf: [
            {
              $ref: "#/$defs/qualifiedRef"
            },
            {
              type: "null"
            }
          ]
        },
        subject_revision: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        assessed_property: {
          type: "string",
          minLength: 1
        },
        criterion_revision: {
          oneOf: [
            {
              type: "string",
              minLength: 1
            },
            {
              type: "null"
            }
          ]
        },
        method_ref: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        observer_id: {
          oneOf: [
            {
              type: "string",
              minLength: 1,
              maxLength: 256,
              pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
            },
            {
              type: "null"
            }
          ]
        },
        observed_at: {
          oneOf: [
            {
              type: "string",
              format: "date-time"
            },
            {
              type: "null"
            }
          ]
        },
        grounds: {
          type: "array",
          items: {
            type: "string",
            minLength: 1,
            maxLength: 256,
            pattern: "^[A-Za-z0-9][A-Za-z0-9._:/@+-]*$"
          },
          minItems: 0
        },
        limits: {
          type: "array",
          items: {
            type: "string",
            minLength: 1
          },
          minItems: 1
        },
        source_unknowns: {
          type: "array",
          items: {
            enum: [
              "subject_ref",
              "subject_revision",
              "criterion_revision",
              "method_ref",
              "observer_id",
              "observed_at",
              "grounds"
            ]
          },
          minItems: 0
        },
        upstream_status: {
          type: "object",
          properties: {
            profile_ref: {
              type: "string",
              minLength: 1
            },
            assessment: {
              type: "string",
              minLength: 1
            },
            reason: {
              type: "string",
              minLength: 1
            }
          },
          required: [
            "profile_ref",
            "assessment",
            "reason"
          ],
          additionalProperties: false
        },
        aggregation_policy_ref: {
          const: "observation-v1:no-cross-dimension-aggregation"
        }
      },
      required: [
        "subject_ref",
        "subject_revision",
        "assessed_property",
        "criterion_revision",
        "method_ref",
        "observer_id",
        "observed_at",
        "grounds",
        "limits",
        "source_unknowns",
        "upstream_status",
        "aggregation_policy_ref"
      ],
      additionalProperties: false
    }
  }
};

// src/knowledge-observation-v1.ts
var PROFILE_ID = "knowledge-collective-observation/v1";
var LOSSLESS_DECIMAL_EXTENSION = "lossless-decimal-counters/v1";
var DECIMAL = /^(0|[1-9][0-9]*)$/;
function isCanonicalDecimal(value) {
  return typeof value === "string" && DECIMAL.test(value);
}
function compareDecimal(a, b) {
  if (!isCanonicalDecimal(a) || !isCanonicalDecimal(b)) {
    throw new RangeError(
      "compareDecimal requires canonical nonnegative decimal strings"
    );
  }
  if (a.length !== b.length) return a.length < b.length ? -1 : 1;
  if (a === b) return 0;
  return a < b ? -1 : 1;
}
function nextDecimal(a) {
  if (!isCanonicalDecimal(a))
    throw new RangeError("nextDecimal requires a canonical decimal string");
  const digits = a.split("");
  let i = digits.length - 1;
  while (i >= 0) {
    if (digits[i] === "9") {
      digits[i] = "0";
      i -= 1;
    } else {
      digits[i] = String(Number(digits[i]) + 1);
      return digits.join("");
    }
  }
  return `1${digits.join("")}`;
}
function canonicalJson(value) {
  if (value === null || typeof value !== "object")
    return JSON.stringify(value) ?? "null";
  if (Array.isArray(value))
    return `[${value.map((v) => canonicalJson(v)).join(",")}]`;
  const obj = value;
  const keys = Object.keys(obj).sort();
  return `{${keys.map((k) => `${JSON.stringify(k)}:${canonicalJson(obj[k])}`).join(",")}}`;
}
function compareDigests(a, b) {
  if (a.algorithm !== b.algorithm || a.role !== b.role || a.domain !== b.domain || a.preimage !== b.preimage || a.representation !== b.representation) {
    return "INCOMPARABLE_DOMAINS";
  }
  return a.value === b.value ? "EQUAL" : "DIFFERENT";
}
function isExactContentAddress(d) {
  return d.role === "exact_content" && d.domain === "raw-bytes";
}
function evaluateAcceptance(acceptance, policy) {
  const issues = [];
  const checks = acceptance.checks;
  const executedUndecided = checks.filter((c) => c.verdict === "UNKNOWN" || c.verdict === "NOT_APPLICABLE").map((c) => c.checker_id);
  if (acceptance.verdict === "PASS") {
    if (checks.length === 0) issues.push("EMPTY_CHECKER_PASS");
    if (acceptance.decision_evidence_ref === null || acceptance.decision_policy_ref === null) {
      issues.push("ACCEPTANCE_DECISION_MISSING");
    }
    if (policy !== void 0) {
      const mandatory = policy.mandatoryChecks === "all-listed" ? checks : checks.filter((c) => policy.mandatoryChecks.includes(c.checker_id));
      if (mandatory.some((c) => c.verdict !== "PASS"))
        issues.push("ACCEPTANCE_POLICY_CONFLICT");
    }
  }
  let effective = "NOT_MEASURED";
  if (acceptance.verdict === "FAIL") {
    if (checks.some((c) => c.verdict === "FAIL")) effective = "FAIL";
    else issues.push("FAIL_WITHOUT_FAILING_CHECK");
  }
  return {
    sourceVerdict: acceptance.verdict,
    effectiveVerdict: effective,
    basis: effective === "FAIL" ? "source_fail_unverified" : "none",
    independentlyVerified: false,
    issues,
    executedUndecided,
    checkersObserved: checks.length > 0
  };
}
function classifyDoclabNativeShape(read) {
  if (typeof read !== "object" || read === null)
    return {
      shape: "unrecognized",
      workerStageNodes: 0,
      workerExecutionObserved: false
    };
  const r = read;
  const stages = Array.isArray(r.stage_tasks) ? r.stage_tasks.length : 0;
  const attempts = Array.isArray(r.stage_attempts) ? r.stage_attempts.length : 0;
  if (r.run === void 0 || !Array.isArray(r.stage_tasks))
    return {
      shape: "unrecognized",
      workerStageNodes: stages,
      workerExecutionObserved: false
    };
  const finishedEvent = (r.events ?? []).some(
    (e) => e.event_type === "run_inserted_finished"
  );
  const b2 = r.run.profile === "converted-text" && r.run.status === "SUCCEEDED" && finishedEvent && stages === 0;
  return {
    shape: b2 ? "b2_finished_converted_text" : "ordinary",
    workerStageNodes: stages,
    workerExecutionObserved: !b2 && (stages > 0 || attempts > 0)
  };
}
var ANNOTATION_KEYWORDS = /* @__PURE__ */ new Set([
  "$schema",
  "$id",
  "title",
  "description",
  "$defs"
]);
var SUPPORTED_KEYWORDS = /* @__PURE__ */ new Set([
  ...ANNOTATION_KEYWORDS,
  "oneOf",
  "allOf",
  "if",
  "then",
  "else",
  "$ref",
  "type",
  "const",
  "enum",
  "properties",
  "required",
  "additionalProperties",
  "items",
  "minItems",
  "maxItems",
  "uniqueItems",
  "minLength",
  "maxLength",
  "pattern",
  "format"
]);
var ROOT_SCHEMA = knowledge_observation_v1_amendment_1_schema_default;
var DEFS = ROOT_SCHEMA["$defs"] ?? {};
var REGEX_CACHE = /* @__PURE__ */ new Map();
function assertSupported(node, mapOfSchemas = false) {
  if (Array.isArray(node)) {
    for (const n of node) assertSupported(n);
    return;
  }
  if (typeof node !== "object" || node === null) return;
  if (mapOfSchemas) {
    for (const v of Object.values(node)) assertSupported(v);
    return;
  }
  for (const [key, value] of Object.entries(node)) {
    if (!SUPPORTED_KEYWORDS.has(key))
      throw new Error(
        `knowledge-observation schema uses unsupported keyword ${key}`
      );
    if (key === "properties" || key === "$defs") assertSupported(value, true);
    else if (key === "const" || key === "enum" || key === "required" || key === "pattern" || key === "type")
      continue;
    else assertSupported(value);
  }
}
assertSupported(ROOT_SCHEMA);
function regexFor(pattern) {
  let re = REGEX_CACHE.get(pattern);
  if (re === void 0) {
    re = new RegExp(pattern, "u");
    REGEX_CACHE.set(pattern, re);
  }
  return re;
}
function daysInMonth(year, month) {
  if (month === 2)
    return year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0) ? 29 : 28;
  return [4, 6, 9, 11].includes(month) ? 30 : 31;
}
function isRfc3339DateTime(value) {
  const m = /^(\d{4})-(\d{2})-(\d{2})[Tt](\d{2}):(\d{2}):(\d{2})(\.\d+)?([Zz]|[+-](\d{2}):(\d{2}))$/.exec(
    value
  );
  if (m === null) return false;
  const [year, month, day, hour, minute, second] = [
    m[1],
    m[2],
    m[3],
    m[4],
    m[5],
    m[6]
  ].map(Number);
  if (month < 1 || month > 12 || day < 1 || day > daysInMonth(year, month))
    return false;
  if (hour > 23 || minute > 59 || second > 60) return false;
  let offsetMinutes = 0;
  if (m[8] !== void 0 && m[8] !== "Z" && m[8] !== "z") {
    const oh = Number(m[9]);
    const om = Number(m[10]);
    if (oh > 23 || om > 59) return false;
    offsetMinutes = (m[8].startsWith("-") ? -1 : 1) * (oh * 60 + om);
  }
  if (second === 60) {
    const utcMinutes = ((hour * 60 + minute - offsetMinutes) % 1440 + 1440) % 1440;
    if (utcMinutes !== 23 * 60 + 59) return false;
  }
  return true;
}
function isPlainObject(v) {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}
function jsonEqual(a, b) {
  return canonicalJson(a) === canonicalJson(b);
}
function matches(node, value) {
  const ref = node["$ref"];
  if (typeof ref === "string") {
    const target = DEFS[ref.replace("#/$defs/", "")];
    if (target === void 0 || !matches(target, value)) return false;
  }
  if ("const" in node && !jsonEqual(node["const"], value)) return false;
  if ("enum" in node && !node["enum"].some((e) => jsonEqual(e, value)))
    return false;
  const type = node["type"];
  if (typeof type === "string") {
    const ok = type === "object" ? isPlainObject(value) : type === "array" ? Array.isArray(value) : type === "string" ? typeof value === "string" : type === "boolean" ? typeof value === "boolean" : type === "null" ? value === null : type === "integer" ? typeof value === "number" && Number.isInteger(value) : type === "number" ? typeof value === "number" && Number.isFinite(value) : false;
    if (!ok) return false;
  }
  if (typeof value === "string") {
    const len = Array.from(value).length;
    if (typeof node["minLength"] === "number" && len < node["minLength"])
      return false;
    if (typeof node["maxLength"] === "number" && len > node["maxLength"])
      return false;
    if (typeof node["pattern"] === "string" && !regexFor(node["pattern"]).test(value))
      return false;
    if (node["format"] === "date-time" && !isRfc3339DateTime(value))
      return false;
  }
  if (Array.isArray(value)) {
    if (typeof node["minItems"] === "number" && value.length < node["minItems"])
      return false;
    if (typeof node["maxItems"] === "number" && value.length > node["maxItems"])
      return false;
    if (node["uniqueItems"] === true && new Set(value.map((v) => canonicalJson(v))).size !== value.length)
      return false;
    const items = node["items"];
    if (isPlainObject(items) && !value.every((v) => matches(items, v)))
      return false;
  }
  if (isPlainObject(value)) {
    const props = node["properties"] ?? {};
    for (const key of node["required"] ?? [])
      if (!Object.hasOwn(value, key)) return false;
    for (const [key, sub] of Object.entries(props))
      if (Object.hasOwn(value, key) && !matches(sub, value[key])) return false;
    if (node["additionalProperties"] === false) {
      for (const key of Object.keys(value))
        if (!Object.hasOwn(props, key)) return false;
    }
  }
  const oneOf = node["oneOf"];
  if (Array.isArray(oneOf) && oneOf.filter((s) => matches(s, value)).length !== 1)
    return false;
  const allOf = node["allOf"];
  if (Array.isArray(allOf) && !allOf.every((s) => matches(s, value)))
    return false;
  if (isPlainObject(node["if"])) {
    const cond = matches(node["if"], value);
    if (cond && isPlainObject(node["then"]) && !matches(node["then"], value))
      return false;
    if (!cond && isPlainObject(node["else"]) && !matches(node["else"], value))
      return false;
  }
  return true;
}
function ownDataCopy(value, depth = 0) {
  if (depth > 16) return { ok: false };
  if (value === null || typeof value === "string" || typeof value === "boolean")
    return { ok: true, value };
  if (typeof value === "number")
    return Number.isFinite(value) ? { ok: true, value } : { ok: false };
  if (typeof value !== "object") return { ok: false };
  if (Array.isArray(value)) {
    if (Object.getPrototypeOf(value) !== Array.prototype) return { ok: false };
    const out2 = [];
    const lengthDesc = Object.getOwnPropertyDescriptor(value, "length");
    if (lengthDesc === void 0 || typeof lengthDesc.value !== "number")
      return { ok: false };
    if (Reflect.ownKeys(value).length !== lengthDesc.value + 1)
      return { ok: false };
    for (let i = 0; i < lengthDesc.value; i += 1) {
      const d = Object.getOwnPropertyDescriptor(value, String(i));
      if (d === void 0 || !Object.hasOwn(d, "value") || !d.enumerable)
        return { ok: false };
      const c = ownDataCopy(d.value, depth + 1);
      if (!c.ok) return c;
      out2.push(c.value);
    }
    return { ok: true, value: out2 };
  }
  const proto = Object.getPrototypeOf(value);
  if (proto !== Object.prototype && proto !== null) return { ok: false };
  const out = {};
  for (const key of Reflect.ownKeys(value)) {
    if (typeof key !== "string") return { ok: false };
    const d = Object.getOwnPropertyDescriptor(value, key);
    if (d === void 0 || !d.enumerable || !Object.hasOwn(d, "value"))
      return { ok: false };
    const c = ownDataCopy(d.value, depth + 1);
    if (!c.ok) return c;
    Object.defineProperty(out, key, {
      value: c.value,
      enumerable: true,
      writable: true,
      configurable: true
    });
  }
  return { ok: true, value: out };
}
var KNOWN_KINDS = [
  "run",
  "event",
  "snapshot",
  "attempt",
  "artifact",
  "command",
  "deployment"
];
function decodeObservationRecord(input, options = {}) {
  const copy = ownDataCopy(input);
  if (!copy.ok)
    return {
      ok: false,
      code: "NOT_AN_OBJECT",
      detail: "record is not plain bounded JSON data"
    };
  const obj = copy.value;
  if (!isPlainObject(obj))
    return {
      ok: false,
      code: "NOT_AN_OBJECT",
      detail: "record must be a JSON object"
    };
  if (typeof obj["profile"] !== "string")
    return {
      ok: false,
      code: "SCHEMA_INVALID",
      detail: "profile is missing or not a string"
    };
  if (obj["profile"] !== PROFILE_ID) {
    return {
      ok: false,
      code: "UNSUPPORTED_PROFILE",
      detail: `unsupported profile ${JSON.stringify(obj["profile"])}`
    };
  }
  const supported = options.supportedExtensions ?? [LOSSLESS_DECIMAL_EXTENSION];
  const exts = obj["required_extensions"];
  if (!Array.isArray(exts))
    return {
      ok: false,
      code: "SCHEMA_INVALID",
      detail: "required_extensions must be an array"
    };
  for (const ext of exts) {
    if (typeof ext !== "string" || !supported.includes(ext)) {
      return {
        ok: false,
        code: "UNSUPPORTED_REQUIRED_EXTENSION",
        detail: `required extension ${JSON.stringify(ext)} is not negotiated`
      };
    }
  }
  if (!KNOWN_KINDS.includes(obj["record_type"])) {
    return {
      ok: false,
      code: "UNSUPPORTED_RECORD_KIND",
      detail: "record_type is not a supported kind"
    };
  }
  if (!matches(ROOT_SCHEMA, obj))
    return {
      ok: false,
      code: "SCHEMA_INVALID",
      detail: "record does not match the v1 schema"
    };
  return { ok: true, record: obj };
}
function parseKnowledgeObservationJson(raw, options = {}) {
  let parsed;
  try {
    parsed = parseBoundedJson(raw);
  } catch {
    return {
      ok: false,
      code: "INVALID_FRAME",
      detail: "frame is not bounded strict JSON (1..65532 bytes, depth 16)"
    };
  }
  const decoded = decodeObservationRecord(parsed, options);
  if (!decoded.ok) return decoded;
  return { ok: true, record: decoded.record, bytes: new Uint8Array(raw) };
}

// src/knowledge-observation-sha256.ts
var K = new Uint32Array([
  1116352408,
  1899447441,
  3049323471,
  3921009573,
  961987163,
  1508970993,
  2453635748,
  2870763221,
  3624381080,
  310598401,
  607225278,
  1426881987,
  1925078388,
  2162078206,
  2614888103,
  3248222580,
  3835390401,
  4022224774,
  264347078,
  604807628,
  770255983,
  1249150122,
  1555081692,
  1996064986,
  2554220882,
  2821834349,
  2952996808,
  3210313671,
  3336571891,
  3584528711,
  113926993,
  338241895,
  666307205,
  773529912,
  1294757372,
  1396182291,
  1695183700,
  1986661051,
  2177026350,
  2456956037,
  2730485921,
  2820302411,
  3259730800,
  3345764771,
  3516065817,
  3600352804,
  4094571909,
  275423344,
  430227734,
  506948616,
  659060556,
  883997877,
  958139571,
  1322822218,
  1537002063,
  1747873779,
  1955562222,
  2024104815,
  2227730452,
  2361852424,
  2428436474,
  2756734187,
  3204031479,
  3329325298
]);
var rotr = (x, n) => x >>> n | x << 32 - n;
function sha256Hex(text) {
  const data = new TextEncoder().encode(text);
  const bitLength = data.length * 8;
  const padded = new Uint8Array(data.length + 9 + 63 >> 6 << 6);
  padded.set(data);
  padded[data.length] = 128;
  const view = new DataView(padded.buffer);
  view.setUint32(padded.length - 8, Math.floor(bitLength / 4294967296));
  view.setUint32(padded.length - 4, bitLength >>> 0);
  const h = new Uint32Array([
    1779033703,
    3144134277,
    1013904242,
    2773480762,
    1359893119,
    2600822924,
    528734635,
    1541459225
  ]);
  const w = new Uint32Array(64);
  for (let offset = 0; offset < padded.length; offset += 64) {
    for (let i = 0; i < 16; i += 1) w[i] = view.getUint32(offset + i * 4);
    for (let i = 16; i < 64; i += 1) {
      const a2 = w[i - 15];
      const b2 = w[i - 2];
      const s0 = rotr(a2, 7) ^ rotr(a2, 18) ^ a2 >>> 3;
      const s1 = rotr(b2, 17) ^ rotr(b2, 19) ^ b2 >>> 10;
      w[i] = w[i - 16] + s0 + w[i - 7] + s1 | 0;
    }
    let [a, b, c, d, e, f, g, hh] = h;
    for (let i = 0; i < 64; i += 1) {
      const s1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25);
      const ch = e & f ^ ~e & g;
      const t1 = hh + s1 + ch + K[i] + w[i] | 0;
      const s0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22);
      const maj = a & b ^ a & c ^ b & c;
      const t2 = s0 + maj | 0;
      hh = g;
      g = f;
      f = e;
      e = d + t1 | 0;
      d = c;
      c = b;
      b = a;
      a = t1 + t2 | 0;
    }
    h[0] = h[0] + a | 0;
    h[1] = h[1] + b | 0;
    h[2] = h[2] + c | 0;
    h[3] = h[3] + d | 0;
    h[4] = h[4] + e | 0;
    h[5] = h[5] + f | 0;
    h[6] = h[6] + g | 0;
    h[7] = h[7] + hh | 0;
  }
  return [...h].map((x) => (x >>> 0).toString(16).padStart(8, "0")).join("");
}

// src/knowledge-observation-reducer.ts
var deepClone = (value) => structuredClone(value);
var DEFAULT_BUFFER_LIMITS = {
  maxRecords: 256,
  maxSerializedBytes: 1048576,
  maxAgeMs: 3e4,
  maxPages: 64,
  maxRetainedIdentities: 4096,
  maxRetainedBytes: 8388608,
  maxAncillaryRecords: 1024
};
var MAX_DIAGNOSTICS = 256;
var MAX_HISTORY = 512;
var MAX_MANIFESTS = 8;
var SHA256_RE = /^[0-9a-f]{64}$/;
function snapshotPageDigest(page) {
  const decoded = decodeObservationRecord(page, {
    supportedExtensions: [LOSSLESS_DECIMAL_EXTENSION]
  });
  if (!decoded.ok || decoded.record.record_type !== "snapshot") return null;
  const canon = canonicalJson(decoded.record);
  return { sha256: sha256Hex(canon), byteSize: byteLength(canon) };
}
function createReducerState(options = {}) {
  return {
    schema: "observation-reducer-state/v1",
    mode: options.mode ?? "live",
    extensions: options.extensions ?? [LOSSLESS_DECIMAL_EXTENSION],
    limits: { ...DEFAULT_BUFFER_LIMITS, ...options.limits },
    binding: null,
    bindingSession: null,
    appliedEventsCompacted: 0,
    projection: "unbound",
    appliedCursor: null,
    holds: [],
    fullSnapshotRequired: false,
    currentPlan: null,
    planHistory: [],
    view: null,
    buffer: [],
    eventIdentities: {},
    cursorBindings: {},
    rejected: [],
    quarantined: [],
    ignored: [],
    historicalOnly: [],
    history: [],
    snapshotHistory: [],
    partialPages: 0,
    bindingDenials: 0,
    run: null,
    connection: "unconnected",
    sawFixture: false,
    sourceReconcile: [],
    sourceSequences: [],
    unassociatedSubjects: [],
    refusals: [],
    eventLog: [],
    eventLedger: [],
    pages: null,
    pageSetManifests: {},
    trustedReset: null,
    ancillary: {
      seen: {},
      attempts: {},
      artifacts: {},
      commands: {},
      deployments: {},
      joined: []
    },
    commands: []
  };
}
function nodeKey(ref) {
  return JSON.stringify([
    ref.graph_kind,
    ref.authority,
    ref.namespace,
    ref.local_id,
    ref.revision
  ]);
}
function sameContext(a, b) {
  return a.project_id === b.project_id && a.run_id === b.run_id && a.authorized_view_scope === b.authorized_view_scope && a.stream_epoch === b.stream_epoch;
}
function push(list, item) {
  list.push(item);
  if (list.length > MAX_DIAGNOSTICS) list.shift();
}
function eventIdentity(rec) {
  return JSON.stringify([
    rec.producer.service,
    rec.producer.instance_id,
    rec.data.producer_event_id
  ]);
}
function byteLength(text) {
  return new TextEncoder().encode(text).length;
}
function addHold(s, code) {
  if (!s.holds.includes(code)) s.holds.push(code);
}
function addHistory(s, entry) {
  s.history.push(entry);
  if (s.history.length > MAX_HISTORY) s.history.shift();
}
function findNode(s, ref) {
  if (s.view === null) return null;
  const key = nodeKey(ref);
  for (const graph of s.view.graphs) {
    if (graph.graph_kind !== ref.graph_kind) continue;
    const index = graph.nodes.findIndex((n) => nodeKey(n.ref) === key);
    if (index >= 0) return { graph, index };
  }
  return null;
}
function setNode(s, ref, patch) {
  const found = findNode(s, ref);
  if (found === null || s.view === null) return false;
  const node = found.graph.nodes[found.index];
  if (node === void 0) return false;
  const updated = { ...node, ...patch };
  const nodes = found.graph.nodes.map(
    (n, i) => i === found.index ? updated : n
  );
  const graphs = s.view.graphs.map(
    (g) => g === found.graph ? { ...g, nodes } : g
  );
  s.view = { ...s.view, graphs };
  return true;
}
function applyEvent(s, rec) {
  const d = rec.data;
  s.appliedCursor = d.cursor;
  const id4 = eventIdentity(rec);
  const known = s.eventIdentities[id4];
  s.eventIdentities = {
    ...s.eventIdentities,
    [id4]: {
      canon: known?.canon ?? canonicalJson(rec),
      cursor: d.cursor,
      status: "applied"
    }
  };
  s.eventLog = [...s.eventLog, d.event_id].slice(-MAX_HISTORY);
  s.eventLedger = [
    ...s.eventLedger,
    {
      eventId: d.event_id,
      recordId: rec.record_id,
      cursor: d.cursor,
      producer: {
        service: rec.producer.service,
        instanceId: rec.producer.instance_id,
        producerEventId: d.producer_event_id
      },
      sourceSequence: {
        value: d.source_sequence.value,
        scope: d.source_sequence.scope,
        scopeId: d.source_sequence.scope_id,
        partitionId: d.source_sequence.partition_id,
        contiguity: d.source_sequence.contiguity
      },
      causationRef: d.causation_ref,
      correlationRef: d.correlation_ref,
      planRevision: d.plan_revision,
      occurredAt: d.occurred_at,
      observedAt: rec.observed_at,
      recordedAt: rec.recorded_at
    }
  ].slice(-MAX_HISTORY);
  trackSourceSequence(s, rec);
  s.sourceSequences = [
    ...s.sourceSequences,
    {
      eventId: d.event_id,
      scope: d.source_sequence.scope,
      scopeId: d.source_sequence.scope_id,
      value: d.source_sequence.value,
      contiguity: d.source_sequence.contiguity
    }
  ].slice(-MAX_HISTORY);
  for (const related of d.related_record_ids) {
    if (!s.ancillary.joined.includes(related))
      s.ancillary = {
        ...s.ancillary,
        joined: [...s.ancillary.joined, related].slice(-MAX_HISTORY)
      };
  }
  if (d.kind === "plan_observed" && d.plan_revision !== null) {
    if (s.currentPlan !== null && s.currentPlan !== d.plan_revision)
      s.planHistory = [...s.planHistory, s.currentPlan].slice(-MAX_HISTORY);
    s.currentPlan = d.plan_revision;
    return "applied";
  }
  if (d.plan_revision !== null && s.currentPlan !== null && d.plan_revision !== s.currentPlan) {
    s.historicalOnly = [...s.historicalOnly, d.event_id].slice(-MAX_HISTORY);
    return "historical";
  }
  if (d.kind === "native_state_observed") {
    for (const ref of d.subject_refs) {
      if (setNode(s, ref, {
        native_state: d.native_state,
        native_versions: d.native_versions
      })) {
        addHistory(s, {
          kind: "native_state_observed",
          nodeKey: nodeKey(ref),
          value: d.native_state?.value ?? null,
          cursor: d.cursor,
          sourceRecordId: rec.record_id
        });
      } else {
        const k = nodeKey(ref);
        if (!s.unassociatedSubjects.includes(k))
          s.unassociatedSubjects = [...s.unassociatedSubjects, k].slice(
            -MAX_HISTORY
          );
      }
    }
  } else if (d.kind === "record_withdrawn") {
    for (const ref of d.subject_refs) {
      const found = findNode(s, ref);
      const prior = found?.graph.nodes[found.index]?.native_state?.value ?? null;
      if (found !== null && s.view !== null) {
        const graphs = s.view.graphs.map(
          (g) => g === found.graph ? { ...g, nodes: g.nodes.filter((_, i) => i !== found.index) } : g
        );
        s.view = {
          ...s.view,
          graphs,
          withdrawn: [...s.view.withdrawn, nodeKey(ref)]
        };
      }
      addHistory(s, {
        kind: "record_withdrawn",
        nodeKey: nodeKey(ref),
        value: prior,
        cursor: d.cursor,
        sourceRecordId: rec.record_id
      });
    }
  } else if (d.kind === "refusal_observed") {
    s.refusals = [
      ...s.refusals,
      {
        recordId: rec.record_id,
        service: rec.producer.service,
        state: d.native_state?.value ?? null
      }
    ].slice(-MAX_HISTORY);
  }
  return "applied";
}
function trackSourceSequence(s, rec) {
  const q = rec.data.source_sequence;
  if (q.value === null || q.contiguity !== "declared_contiguous" || !isCanonicalDecimal(q.value))
    return;
  const key = JSON.stringify([
    rec.producer.service,
    rec.producer.instance_id,
    q.scope,
    q.scope_id,
    q.partition_id
  ]);
  const marker = `${key}#${q.value}`;
  const prev = [...s.sourceReconcile].reverse().find((m) => m.startsWith(`${key}#last:`));
  if (prev !== void 0) {
    const last = prev.slice(key.length + "#last:".length);
    if (compareDecimal(q.value, nextDecimal(last)) > 0)
      s.sourceReconcile = [...s.sourceReconcile, `${marker}:gap`];
  }
  s.sourceReconcile = [
    ...s.sourceReconcile.filter((m) => !m.startsWith(`${key}#last:`)),
    `${key}#last:${q.value}`
  ].slice(-MAX_HISTORY);
}
function settle(s) {
  if (s.appliedCursor !== null) {
    const covered = s.buffer.filter(
      (b) => compareDecimal(b.cursor, s.appliedCursor) <= 0
    );
    for (const c of covered) markIdentity(s, c.identity, "covered");
    s.buffer = s.buffer.filter(
      (b) => compareDecimal(b.cursor, s.appliedCursor) > 0
    );
    s.buffer.sort((a, b) => compareDecimal(a.cursor, b.cursor));
    while (s.holds.length === 0) {
      const next = s.buffer[0];
      if (next === void 0 || next.cursor !== nextDecimal(s.appliedCursor))
        break;
      s.buffer.shift();
      applyEvent(s, next.record);
    }
    if (s.buffer.length > 0 && s.holds.length === 0) addHold(s, "GAP");
  }
  if (s.binding === null)
    s.projection = s.projection === "cleared" ? "cleared" : "unbound";
  else if (s.appliedCursor === null) s.projection = "awaiting_snapshot";
  else s.projection = s.holds.length > 0 ? "reconciling" : "current";
}
function markIdentity(s, id4, status) {
  const known = s.eventIdentities[id4];
  if (known !== void 0)
    s.eventIdentities = { ...s.eventIdentities, [id4]: { ...known, status } };
}
function reject(s, recordId, code) {
  push(s.rejected, { recordId, code });
  return { disposition: "rejected", code };
}
function overflowCheck(s, at) {
  const bytes = s.buffer.reduce((n, b) => n + b.bytes, 0);
  const oldest = s.buffer.reduce(
    (m, b) => Math.min(m, b.receivedAt),
    Number.POSITIVE_INFINITY
  );
  const overCount = s.buffer.length > s.limits.maxRecords;
  const overBytes = bytes > s.limits.maxSerializedBytes;
  const overAge = at !== void 0 && Number.isFinite(oldest) && at - oldest > s.limits.maxAgeMs;
  if (!overCount && !overBytes && !overAge) return false;
  for (const b of s.buffer) markIdentity(s, b.identity, "covered");
  s.buffer = [];
  addHold(
    s,
    overAge && !overCount && !overBytes ? "BUFFER_EXPIRED" : "BUFFER_LIMIT_EXCEEDED"
  );
  s.fullSnapshotRequired = true;
  return true;
}
function retainedBytes(s) {
  const texts = [
    ...Object.values(s.eventIdentities).map((e) => e.canon),
    ...Object.values(s.ancillary.seen)
  ];
  const units = texts.reduce((n, c) => n + c.length, 0);
  if (units * 3 <= s.limits.maxRetainedBytes) return units * 3;
  return texts.reduce((n, c) => n + byteLength(c), 0);
}
function retentionBlocked(s, addIdentities, addAncillary, addBytes) {
  return Object.keys(s.eventIdentities).length + addIdentities > s.limits.maxRetainedIdentities || Object.keys(s.ancillary.seen).length + addAncillary > s.limits.maxAncillaryRecords || retainedBytes(s) + addBytes > s.limits.maxRetainedBytes;
}
function retentionRefused(s, recordId) {
  push(s.quarantined, { recordId, code: "RETENTION_LIMIT_EXCEEDED" });
  addHold(s, "RETENTION_LIMIT_EXCEEDED");
  s.fullSnapshotRequired = true;
  settle(s);
  return { disposition: "quarantined", code: "RETENTION_LIMIT_EXCEEDED" };
}
function compactRetention(s, watermark) {
  const identities = {};
  const droppedCursors = /* @__PURE__ */ new Set();
  for (const [id4, e] of Object.entries(s.eventIdentities)) {
    if (compareDecimal(e.cursor, watermark) <= 0) {
      if (e.status === "applied") s.appliedEventsCompacted += 1;
      droppedCursors.add(e.cursor);
    } else identities[id4] = e;
  }
  s.eventIdentities = identities;
  s.cursorBindings = Object.fromEntries(
    Object.entries(s.cursorBindings).filter(
      ([cursor]) => !droppedCursors.has(cursor) && compareDecimal(cursor, watermark) > 0
    )
  );
  s.ancillary = {
    seen: {},
    attempts: {},
    artifacts: {},
    commands: {},
    deployments: {},
    joined: []
  };
}
function receiveEvent(s, rec, at) {
  const d = rec.data;
  const id4 = eventIdentity(rec);
  const canon = canonicalJson(rec);
  const known = s.eventIdentities[id4];
  if (known !== void 0) {
    if (known.canon === canon) {
      push(s.ignored, {
        recordId: rec.record_id,
        code: "DUPLICATE_SAME_IDENTITY_AND_BODY"
      });
      return {
        disposition: "ignored",
        code: "DUPLICATE_SAME_IDENTITY_AND_BODY"
      };
    }
    push(s.quarantined, {
      recordId: rec.record_id,
      code: "IDENTITY_BODY_CONFLICT"
    });
    addHold(s, "IDENTITY_BODY_CONFLICT");
    settle(s);
    return { disposition: "quarantined", code: "IDENTITY_BODY_CONFLICT" };
  }
  const boundIdentity = s.cursorBindings[d.cursor];
  if (boundIdentity !== void 0 && boundIdentity !== id4) {
    push(s.quarantined, {
      recordId: rec.record_id,
      code: "CURSOR_BINDING_CONFLICT"
    });
    addHold(s, "CURSOR_BINDING_CONFLICT");
    settle(s);
    return { disposition: "quarantined", code: "CURSOR_BINDING_CONFLICT" };
  }
  if (retentionBlocked(s, 1, 0, byteLength(canon)))
    return retentionRefused(s, rec.record_id);
  s.cursorBindings = { ...s.cursorBindings, [d.cursor]: id4 };
  if (s.appliedCursor !== null && compareDecimal(d.cursor, s.appliedCursor) <= 0) {
    s.eventIdentities = {
      ...s.eventIdentities,
      [id4]: { canon, cursor: d.cursor, status: "covered" }
    };
    push(s.ignored, { recordId: rec.record_id, code: "COVERED_BY_WATERMARK" });
    return { disposition: "ignored", code: "COVERED_BY_WATERMARK" };
  }
  if (s.appliedCursor !== null && s.holds.length === 0 && d.cursor === nextDecimal(s.appliedCursor)) {
    s.eventIdentities = {
      ...s.eventIdentities,
      [id4]: { canon, cursor: d.cursor, status: "applied" }
    };
    const result = applyEvent(s, rec);
    settle(s);
    return { disposition: result, code: null };
  }
  s.eventIdentities = {
    ...s.eventIdentities,
    [id4]: { canon, cursor: d.cursor, status: "buffered" }
  };
  s.buffer.push({
    recordId: rec.record_id,
    cursor: d.cursor,
    identity: id4,
    receivedAt: at ?? 0,
    bytes: byteLength(canon),
    record: rec
  });
  if (s.appliedCursor !== null && s.holds.length === 0) addHold(s, "GAP");
  if (overflowCheck(s, at)) {
    settle(s);
    return {
      disposition: "quarantined",
      code: s.holds.includes("BUFFER_EXPIRED") ? "BUFFER_EXPIRED" : "BUFFER_LIMIT_EXCEEDED"
    };
  }
  settle(s);
  return {
    disposition: "buffered",
    code: s.appliedCursor === null ? "AWAITING_SNAPSHOT" : s.holds.includes("GAP") ? "GAP" : null
  };
}
function sortedBy(items, key) {
  return [...items].sort((a, b) => {
    const ka = key(a);
    const kb = key(b);
    return ka < kb ? -1 : ka > kb ? 1 : 0;
  });
}
function completeProjectionCanon(p) {
  return canonicalJson({
    plan: p.plan,
    native_state: p.nativeState,
    acceptance: p.acceptance,
    source_atomicity: p.sourceAtomicity,
    atomicity_evidence_ref: p.atomicityEvidenceRef,
    declared_graph_kinds: [...p.declaredGraphKinds].sort(),
    source_revisions: sortedBy(p.sourceRevisions, canonicalJson),
    allowed_actions: sortedBy(p.allowedActions, canonicalJson),
    graphs: sortedBy(
      p.graphs,
      (g) => `${g.graph_kind}\0${g.authority}`
    ).map((g) => ({
      graph_kind: g.graph_kind,
      authority: g.authority,
      graph_revision: g.graph_revision,
      nodes: sortedBy(g.nodes, (n) => nodeKey(n.ref)),
      edges: sortedBy(g.edges, (e) => e.edge_id)
    })),
    crosslinks: sortedBy(p.crosslinks, (l) => l.link_id)
  });
}
function snapshotProjectionParts(d) {
  return {
    plan: d.plan_revision,
    nativeState: d.native_state,
    acceptance: d.acceptance,
    sourceAtomicity: d.source_atomicity,
    atomicityEvidenceRef: d.atomicity_evidence_ref ?? null,
    declaredGraphKinds: d.coverage.declared_graph_kinds,
    sourceRevisions: d.source_revisions,
    allowedActions: d.allowed_actions_observation,
    graphs: d.graphs,
    crosslinks: d.crosslinks
  };
}
function snapshotConsistent(s, snap) {
  const v = s.view;
  if (v === null) return true;
  const current = completeProjectionCanon({
    plan: s.currentPlan,
    nativeState: v.nativeState,
    acceptance: v.acceptanceRecord,
    sourceAtomicity: v.sourceAtomicity,
    atomicityEvidenceRef: v.atomicityEvidenceRef,
    declaredGraphKinds: v.declaredGraphKinds,
    sourceRevisions: v.sourceRevisions,
    allowedActions: v.allowedActions,
    graphs: v.graphs,
    crosslinks: v.crosslinks
  });
  return current === completeProjectionCanon(snapshotProjectionParts(snap.data));
}
function installSnapshot(s, snap) {
  const d = snap.data;
  if (s.holds.includes("RETENTION_LIMIT_EXCEEDED"))
    compactRetention(s, d.watermark);
  if (s.view !== null) {
    const incoming = new Set(
      d.graphs.flatMap((g) => g.nodes.map((n) => nodeKey(n.ref)))
    );
    for (const g of s.view.graphs) {
      for (const n of g.nodes) {
        const k = nodeKey(n.ref);
        if (!incoming.has(k))
          addHistory(s, {
            kind: "node_absent",
            nodeKey: k,
            value: n.native_state?.value ?? null,
            cursor: d.watermark,
            sourceRecordId: snap.record_id
          });
      }
    }
  }
  for (const g of d.graphs) {
    for (const n of g.nodes) {
      addHistory(s, {
        kind: "native_state_observed",
        nodeKey: nodeKey(n.ref),
        value: n.native_state?.value ?? null,
        cursor: d.watermark,
        sourceRecordId: snap.record_id
      });
    }
  }
  if (s.currentPlan !== null && s.currentPlan !== d.plan_revision)
    s.planHistory = [...s.planHistory, s.currentPlan].slice(-MAX_HISTORY);
  s.currentPlan = d.plan_revision;
  s.view = {
    snapshotRecordId: snap.record_id,
    watermark: d.watermark,
    planRevision: d.plan_revision,
    sourceAtomicity: d.source_atomicity,
    declaredGraphKinds: d.coverage.declared_graph_kinds,
    nativeState: d.native_state,
    acceptance: evaluateAcceptance(d.acceptance),
    acceptanceRecord: deepClone(d.acceptance),
    sourceRevisions: deepClone(d.source_revisions),
    allowedActions: deepClone(d.allowed_actions_observation),
    atomicityEvidenceRef: d.atomicity_evidence_ref ?? null,
    graphs: deepClone(d.graphs),
    crosslinks: deepClone(d.crosslinks),
    withdrawn: []
  };
  s.appliedCursor = d.watermark;
  s.holds = [];
  s.fullSnapshotRequired = false;
  s.trustedReset = null;
  s.pages = null;
}
function discardPages(s, code) {
  s.pages = null;
  if (s.appliedCursor !== null) addHold(s, code);
  s.fullSnapshotRequired = true;
  settle(s);
  push(s.rejected, { recordId: null, code });
  return { disposition: "rejected", code };
}
function mergePages(pages) {
  const last = pages[pages.length - 1];
  if (last === void 0) return null;
  const first = pages[0];
  const sameTop = (pick) => pages.every((p) => canonicalJson(pick(p)) === canonicalJson(pick(first)));
  if (!sameTop((p) => p.producer) || !sameTop((p) => p.view_context) || !sameTop((p) => p.data.native_state) || !sameTop((p) => p.data.acceptance) || !sameTop((p) => p.data.source_atomicity) || !sameTop((p) => p.data.reset) || !sameTop((p) => p.data.allowed_actions_observation) || !sameTop((p) => p.data.source_revisions) || !sameTop((p) => p.data.coverage.declared_graph_kinds)) {
    return null;
  }
  const kinds = last.data.coverage.declared_graph_kinds;
  const graphs = [];
  for (const kind of kinds) {
    const present = pages.flatMap(
      (p) => p.data.graphs.filter((g) => g.graph_kind === kind)
    );
    const head = present[0];
    if (head === void 0) return null;
    if (present.some(
      (g) => g.authority !== head.authority || g.graph_revision !== head.graph_revision
    ))
      return null;
    const nodes = /* @__PURE__ */ new Map();
    const edges = /* @__PURE__ */ new Map();
    for (const g of present) {
      for (const n of g.nodes) {
        const k = nodeKey(n.ref);
        const prior = nodes.get(k);
        if (prior !== void 0 && canonicalJson(prior) !== canonicalJson(n))
          return null;
        nodes.set(k, n);
      }
      for (const e of g.edges) {
        const prior = edges.get(e.edge_id);
        if (prior !== void 0 && canonicalJson(prior) !== canonicalJson(e))
          return null;
        edges.set(e.edge_id, e);
      }
    }
    graphs.push({
      graph_kind: kind,
      authority: head.authority,
      graph_revision: head.graph_revision,
      nodes: [...nodes.entries()].sort((a, b) => a[0] < b[0] ? -1 : 1).map(([, v]) => v),
      edges: [...edges.entries()].sort((a, b) => a[0] < b[0] ? -1 : 1).map(([, v]) => v)
    });
  }
  const links = /* @__PURE__ */ new Map();
  for (const p of pages) {
    for (const l of p.data.crosslinks) {
      const prior = links.get(l.link_id);
      if (prior !== void 0 && canonicalJson(prior) !== canonicalJson(l))
        return null;
      links.set(l.link_id, l);
    }
  }
  const merged = {
    ...last,
    record_id: `${last.record_id}.assembled`,
    data: {
      ...last.data,
      snapshot_kind: "full",
      coverage: (() => {
        const { page_set: _pageSet, ...rest } = last.data.coverage;
        void _pageSet;
        return { ...rest, complete: true, next_page_token: null };
      })(),
      graphs,
      crosslinks: [...links.entries()].sort((a, b) => a[0] < b[0] ? -1 : 1).map(([, v]) => v)
    }
  };
  return decodeObservationRecord(merged, {
    supportedExtensions: [LOSSLESS_DECIMAL_EXTENSION]
  }).ok ? merged : null;
}
var NON_INTERVAL_RECOVERABLE = (h) => h !== "GAP" && h !== "PAGE_SET_UNPROVEN";
function manifestFor(s, ref) {
  return s.pageSetManifests[ref] ?? null;
}
function pageViolatesManifest(m, a, entry) {
  const expected = m.pages.find((p) => p.pageIndex === entry.index);
  return m.watermark !== a.watermark || m.trustedSnapshotRef !== a.trustedSnapshotRef || m.planRevision !== a.planRevision || m.pageCount !== a.pageCount || expected === void 0 || expected.sha256 !== entry.sha256 || expected.byteSize !== entry.byteSize;
}
function ageExceeded(firstAt, at, maxAgeMs) {
  return at !== void 0 && at - firstAt > maxAgeMs;
}
function pagesExpired(s, at) {
  return s.pages !== null && ageExceeded(s.pages.firstAt, at, s.limits.maxAgeMs);
}
function expirePages(s, at) {
  if (!pagesExpired(s, at)) return false;
  discardPages(s, "PAGE_ASSEMBLY_LIMIT_EXCEEDED");
  return true;
}
function completePageSet(s, at) {
  if (s.pages === null) return null;
  if (expirePages(s, at))
    return { disposition: "rejected", code: "PAGE_ASSEMBLY_LIMIT_EXCEEDED" };
  const a = s.pages;
  if (a === null) return null;
  const lastRecord = a.pages[a.pages.length - 1]?.record;
  const record3 = (disposition) => {
    s.snapshotHistory = [
      ...s.snapshotHistory,
      {
        recordId: lastRecord?.record_id ?? a.pageSetRef,
        watermark: a.watermark,
        disposition
      }
    ].slice(-MAX_HISTORY);
  };
  if (a.pages.length < a.pageCount) {
    record3("partial_page_pending");
    return { disposition: "ignored", code: "PARTIAL_PAGE_PENDING" };
  }
  const m = manifestFor(s, a.pageSetRef);
  if (m === null) {
    record3("page_set_manifest_pending");
    return { disposition: "ignored", code: "PAGE_SET_MANIFEST_PENDING" };
  }
  if (a.pages.some((e) => pageViolatesManifest(m, a, e))) {
    record3("page_set_manifest_mismatch");
    return discardPages(s, "PAGE_SET_MISMATCH");
  }
  const ordered = [...a.pages].sort((x, y) => x.index - y.index).map((e) => e.record);
  const merged = mergePages(ordered);
  if (merged === null) {
    record3("page_assembly_inconsistent");
    return discardPages(s, "PAGE_ASSEMBLY_INVALID");
  }
  s.pages = null;
  record3("pages_assembled");
  const outcome = receiveSnapshot(s, merged, at, true);
  return outcome.disposition === "applied" ? { disposition: "applied", code: "PAGES_ASSEMBLED" } : outcome;
}
function receivePage(s, page, at, record3) {
  const d = page.data;
  s.partialPages += 1;
  if (s.appliedCursor !== null && s.holds.some(NON_INTERVAL_RECOVERABLE))
    s.fullSnapshotRequired = true;
  const set = d.coverage.page_set;
  if (set === void 0) {
    record3("page_set_proof_missing");
    push(s.quarantined, {
      recordId: page.record_id,
      code: "PAGE_SET_PROOF_MISSING"
    });
    if (s.appliedCursor !== null) addHold(s, "PAGE_SET_UNPROVEN");
    settle(s);
    return { disposition: "quarantined", code: "PAGE_SET_PROOF_MISSING" };
  }
  const index = Number(set.page_index);
  const count = Number(set.page_count);
  const lastOrdinal = index === count - 1;
  const incoherent = (
    // An unsafe `index` is always >= a safe `count`, or `count` is itself unsafe and refused here.
    !Number.isSafeInteger(count) || index >= count || lastOrdinal !== (d.coverage.next_page_token === null) || d.coverage.complete !== lastOrdinal
  );
  if (incoherent) {
    record3("page_ordinal_invalid");
    return discardPages(s, "PAGE_ASSEMBLY_INVALID");
  }
  if (count > s.limits.maxPages) {
    record3("page_assembly_limit_exceeded");
    return discardPages(s, "PAGE_ASSEMBLY_LIMIT_EXCEEDED");
  }
  const canon = canonicalJson(page);
  const entry = {
    index,
    sha256: sha256Hex(canon),
    byteSize: byteLength(canon),
    record: page
  };
  const prior = s.pages;
  const declared = canonicalJson(d.coverage.declared_graph_kinds);
  if (prior !== null && (prior.watermark !== d.watermark || prior.trustedSnapshotRef !== d.trusted_snapshot_ref || prior.planRevision !== d.plan_revision || prior.declaredKinds !== declared || prior.pageSetRef !== set.page_set_ref || prior.pageCount !== count)) {
    record3("page_assembly_inconsistent");
    return discardPages(s, "PAGE_ASSEMBLY_INVALID");
  }
  const dup = prior?.pages.find((e) => e.index === index);
  if (dup !== void 0) {
    if (dup.sha256 === entry.sha256) {
      record3("page_duplicate_identical");
      return { disposition: "ignored", code: "PAGE_DUPLICATE_IDENTICAL" };
    }
    record3("page_duplicate_conflict");
    return discardPages(s, "PAGE_ASSEMBLY_INVALID");
  }
  const base = {
    watermark: d.watermark,
    trustedSnapshotRef: d.trusted_snapshot_ref,
    planRevision: d.plan_revision,
    pageCount: count
  };
  const manifest = manifestFor(s, set.page_set_ref);
  if (manifest !== null && pageViolatesManifest(manifest, base, entry)) {
    record3("page_foreign_to_manifest");
    return discardPages(s, "PAGE_SET_MISMATCH");
  }
  const pages = [...prior?.pages ?? [], entry];
  const bytes = (prior?.bytes ?? 0) + entry.byteSize;
  const firstAt = prior?.firstAt ?? at ?? 0;
  if (bytes > s.limits.maxSerializedBytes || ageExceeded(firstAt, at, s.limits.maxAgeMs)) {
    record3("page_assembly_limit_exceeded");
    return discardPages(s, "PAGE_ASSEMBLY_LIMIT_EXCEEDED");
  }
  s.pages = {
    ...base,
    declaredKinds: declared,
    pageSetRef: set.page_set_ref,
    pages,
    bytes,
    firstAt
  };
  const outcome = completePageSet(s, at);
  if (outcome === null) return { disposition: "ignored", code: null };
  return outcome;
}
function validManifest(s, m) {
  if (s.binding === null || typeof m !== "object" || m === null) return false;
  if (typeof m.viewContext !== "object" || m.viewContext === null) return false;
  if (!sameContext(m.viewContext, s.binding)) return false;
  const ref = /^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,255}$/;
  const isRef = (v) => typeof v === "string" && ref.test(v);
  if (!isRef(m.pageSetRef) || !isRef(m.trustedSnapshotRef) || !isRef(m.adapterRef) || !isCanonicalDecimal(m.watermark) || m.pageCount < 1 || m.pageCount > s.limits.maxPages || !Array.isArray(m.pages) || m.pages.length !== m.pageCount)
    return false;
  const seen = /* @__PURE__ */ new Set();
  let total = 0;
  for (const p of m.pages) {
    if (typeof p !== "object" || p === null || !Number.isSafeInteger(p.pageIndex) || p.pageIndex < 0 || p.pageIndex >= m.pageCount || seen.has(p.pageIndex) || typeof p.sha256 !== "string" || !SHA256_RE.test(p.sha256) || !Number.isSafeInteger(p.byteSize) || p.byteSize < 1)
      return false;
    seen.add(p.pageIndex);
    total += p.byteSize;
  }
  return total === m.totalBytes;
}
function receivePageSetManifest(s, m, at) {
  if (!validManifest(s, m)) return reject(s, null, "INVALID_PAGE_SET_MANIFEST");
  const existing = s.pageSetManifests[m.pageSetRef];
  if (existing !== void 0 && canonicalJson(existing) !== canonicalJson(m)) {
    push(s.quarantined, { recordId: null, code: "PAGE_SET_MANIFEST_CONFLICT" });
    if (s.appliedCursor !== null) addHold(s, "PAGE_SET_MISMATCH");
    settle(s);
    return { disposition: "quarantined", code: "PAGE_SET_MANIFEST_CONFLICT" };
  }
  const keep = Object.entries({
    ...s.pageSetManifests,
    [m.pageSetRef]: deepClone(m)
  }).slice(-MAX_MANIFESTS);
  s.pageSetManifests = Object.fromEntries(keep);
  if (s.pages !== null && s.pages.pageSetRef === m.pageSetRef) {
    const outcome = completePageSet(s, at);
    if (outcome !== null) return outcome;
  }
  return { disposition: "state_changed", code: null };
}
function receiveSnapshot(s, snap, at, assembled = false) {
  const d = snap.data;
  const record3 = (disposition) => {
    s.snapshotHistory = [
      ...s.snapshotHistory,
      { recordId: snap.record_id, watermark: d.watermark, disposition }
    ].slice(-MAX_HISTORY);
  };
  if (!assembled && (d.snapshot_kind === "partial" || !d.coverage.complete)) {
    return receivePage(s, snap, at, record3);
  }
  if (d.reset !== null) {
    if (s.trustedReset === null || s.trustedReset.ref !== d.reset.authorization_observation_ref || s.trustedReset.previousEpoch !== d.reset.previous_epoch) {
      addHold(s, "RESET_NOT_AUTHORIZED");
      return reject(s, snap.record_id, "RESET_NOT_AUTHORIZED");
    }
  }
  if (s.appliedCursor !== null) {
    const order = compareDecimal(d.watermark, s.appliedCursor);
    if (order < 0) {
      record3("older_history_only");
      push(s.ignored, {
        recordId: snap.record_id,
        code: "OLDER_SNAPSHOT_HISTORY_ONLY"
      });
      return { disposition: "historical", code: "OLDER_SNAPSHOT_HISTORY_ONLY" };
    }
    if (order === 0) {
      if (!snapshotConsistent(s, snap)) {
        record3("contradiction_quarantined");
        push(s.quarantined, {
          recordId: snap.record_id,
          code: "SNAPSHOT_CONTRADICTION"
        });
        addHold(s, "SNAPSHOT_CONTRADICTION");
        settle(s);
        return { disposition: "quarantined", code: "SNAPSHOT_CONTRADICTION" };
      }
      if (s.holds.length === 1 && s.holds[0] === "RETENTION_LIMIT_EXCEEDED") {
        installSnapshot(s, snap);
        record3("installed_retention_compaction");
        settle(s);
        return { disposition: "applied", code: "RETENTION_COMPACTED" };
      }
      record3("same_watermark_consistent");
      return { disposition: "ignored", code: "SAME_WATERMARK_CONSISTENT" };
    }
  }
  installSnapshot(s, snap);
  record3("installed");
  settle(s);
  return { disposition: "applied", code: null };
}
function storeAncillary(s, rec) {
  const canon = canonicalJson(rec);
  const seenKey = `${rec.record_type}:${rec.record_id}`;
  const prior = s.ancillary.seen[seenKey];
  if (prior !== void 0) {
    if (prior === canon) {
      push(s.ignored, { recordId: rec.record_id, code: "DUPLICATE_RECORD" });
      return { disposition: "ignored", code: "DUPLICATE_RECORD" };
    }
    push(s.quarantined, {
      recordId: rec.record_id,
      code: "RECORD_ID_CONFLICT"
    });
    return { disposition: "quarantined", code: "RECORD_ID_CONFLICT" };
  }
  if (retentionBlocked(s, 0, 1, byteLength(canon)))
    return retentionRefused(s, rec.record_id);
  const seen = { ...s.ancillary.seen, [seenKey]: canon };
  switch (rec.record_type) {
    case "attempt": {
      const evaluation = evaluateAcceptance(rec.data.acceptance);
      s.ancillary = {
        ...s.ancillary,
        seen,
        attempts: {
          ...s.ancillary.attempts,
          [rec.record_id]: {
            record: rec,
            evaluation,
            semanticConflict: false,
            joinedByEvent: false
          }
        }
      };
      break;
    }
    case "artifact":
      s.ancillary = {
        ...s.ancillary,
        seen,
        artifacts: { ...s.ancillary.artifacts, [rec.record_id]: rec }
      };
      break;
    case "command":
      s.ancillary = {
        ...s.ancillary,
        seen,
        commands: { ...s.ancillary.commands, [rec.record_id]: rec }
      };
      break;
    case "deployment":
      s.ancillary = {
        ...s.ancillary,
        seen,
        deployments: { ...s.ancillary.deployments, [rec.record_id]: rec }
      };
      break;
  }
  return { disposition: "stored", code: null };
}
function receive(s, raw, at) {
  if (at !== void 0) {
    if (s.buffer.length > 0 && overflowCheck(s, at)) settle(s);
  }
  const rawId = typeof raw === "object" && raw !== null && typeof raw.record_id === "string" ? raw.record_id : null;
  const claimedContext = typeof raw === "object" && raw !== null ? raw.view_context : void 0;
  if (s.binding === null) {
    return reject(s, null, "NO_TRUSTED_VIEW_BINDING");
  }
  if (typeof claimedContext === "object" && claimedContext !== null) {
    const c = claimedContext;
    const full = c.project_id !== void 0 && c.run_id !== void 0 && c.authorized_view_scope !== void 0 && c.stream_epoch !== void 0;
    if (full && !sameContext(c, s.binding)) {
      const b = s.binding;
      const onlyEpoch = c.project_id === b.project_id && c.run_id === b.run_id && c.authorized_view_scope === b.authorized_view_scope;
      s.bindingDenials += 1;
      if (onlyEpoch) {
        addHold(s, "UNTRUSTED_EPOCH_CHANGE");
        settle(s);
        return { disposition: "rejected", code: "UNTRUSTED_EPOCH_CHANGE" };
      }
      return { disposition: "rejected", code: "OPAQUE_VIEW_BINDING_MISMATCH" };
    }
  }
  const decoded = raw instanceof Uint8Array ? parseKnowledgeObservationJson(raw, {
    supportedExtensions: s.extensions
  }) : decodeObservationRecord(raw, { supportedExtensions: s.extensions });
  if (!decoded.ok) {
    if (s.appliedCursor !== null) addHold(s, decoded.code);
    settle(s);
    return reject(s, rawId, decoded.code);
  }
  const rec = decoded.record;
  if (!sameContext(rec.view_context, s.binding)) {
    s.bindingDenials += 1;
    return { disposition: "rejected", code: "OPAQUE_VIEW_BINDING_MISMATCH" };
  }
  if (rec.mode === "fixture") s.sawFixture = true;
  switch (rec.record_type) {
    case "run": {
      s.run = rec.data;
      if (s.connection === "unconnected") s.connection = rec.data.connection;
      settle(s);
      return {
        disposition: "stored",
        code: "RUN_INFORMATIONAL_CURSOR_NOT_A_WATERMARK"
      };
    }
    case "event":
      return receiveEvent(s, rec, at);
    case "snapshot":
      return receiveSnapshot(s, rec, at);
    default:
      return storeAncillary(s, rec);
  }
}
function replayInterval(s, input) {
  if (s.binding === null || s.appliedCursor === null)
    return reject(s, null, "INVALID_REPLAY_INTERVAL");
  if (!isCanonicalDecimal(input.fromCursor) || !isCanonicalDecimal(input.throughCursor) || input.coverageRef.length === 0) {
    return reject(s, null, "INVALID_REPLAY_INTERVAL");
  }
  const events = [];
  for (const raw of input.records) {
    const decoded = decodeObservationRecord(raw, {
      supportedExtensions: s.extensions
    });
    if (!decoded.ok || decoded.record.record_type !== "event" || !sameContext(decoded.record.view_context, s.binding)) {
      return reject(s, null, "INVALID_REPLAY_INTERVAL");
    }
    events.push(decoded.record);
  }
  events.sort((a, b) => compareDecimal(a.data.cursor, b.data.cursor));
  let expect = input.fromCursor;
  for (const e of events) {
    if (e.data.cursor !== expect)
      return reject(s, null, "INVALID_REPLAY_INTERVAL");
    expect = nextDecimal(expect);
  }
  if (events.length === 0 || nextDecimal(events[events.length - 1]?.data.cursor ?? "0") !== nextDecimal(input.throughCursor)) {
    return reject(s, null, "INVALID_REPLAY_INTERVAL");
  }
  if (compareDecimal(input.fromCursor, nextDecimal(s.appliedCursor)) > 0)
    return reject(s, null, "INVALID_REPLAY_INTERVAL");
  const unseen = events.filter(
    (e) => s.eventIdentities[eventIdentity(e)] === void 0
  );
  if (unseen.length > 0 && retentionBlocked(
    s,
    unseen.length,
    0,
    unseen.reduce((n, e) => n + byteLength(canonicalJson(e)), 0)
  ))
    return retentionRefused(s, null);
  for (const e of events) {
    const id4 = eventIdentity(e);
    const canon = canonicalJson(e);
    const known = s.eventIdentities[id4];
    if (known !== void 0 && known.canon !== canon) {
      push(s.quarantined, {
        recordId: e.record_id,
        code: "IDENTITY_BODY_CONFLICT"
      });
      addHold(s, "IDENTITY_BODY_CONFLICT");
      return { disposition: "quarantined", code: "IDENTITY_BODY_CONFLICT" };
    }
    if (known === void 0 || known.status === "covered") {
      if (!s.buffer.some((b) => b.identity === id4)) {
        s.buffer.push({
          recordId: e.record_id,
          cursor: e.data.cursor,
          identity: id4,
          receivedAt: input.at ?? 0,
          bytes: byteLength(canon),
          record: e
        });
      }
      s.cursorBindings = { ...s.cursorBindings, [e.data.cursor]: id4 };
      s.eventIdentities = {
        ...s.eventIdentities,
        [id4]: { canon, cursor: e.data.cursor, status: "buffered" }
      };
    }
  }
  s.holds = s.holds.filter((h) => h !== "GAP");
  settle(s);
  return { disposition: "applied", code: "REPLAY_INTERVAL_APPLIED" };
}
function reduce(previous, input) {
  const s = deepClone(previous);
  let outcome;
  switch (input.kind) {
    case "set_mode":
      s.mode = input.mode;
      outcome = { disposition: "state_changed", code: null };
      break;
    case "set_buffer_limits":
      s.limits = { ...s.limits, ...input.limits };
      outcome = { disposition: "state_changed", code: null };
      break;
    case "bind_trusted_projection": {
      const next = input.viewContext;
      const session2 = input.sessionRef ?? null;
      if (s.binding === null) {
        s.binding = next;
        s.bindingSession = session2;
      } else if (sameContext(next, s.binding) && session2 === s.bindingSession) {
      } else if (!sameContext(next, s.binding) && next.project_id === s.binding.project_id && next.run_id === s.binding.run_id && next.authorized_view_scope === s.binding.authorized_view_scope) {
        outcome = reject(s, null, "REBIND_REQUIRES_TRUSTED_EPOCH_RESET");
        break;
      } else {
        const connection = s.connection;
        const fresh = createReducerState({
          mode: s.mode,
          extensions: s.extensions,
          limits: s.limits
        });
        Object.assign(s, fresh);
        s.connection = connection;
        s.binding = next;
        s.bindingSession = session2;
        s.fullSnapshotRequired = true;
        settle(s);
        outcome = {
          disposition: "state_changed",
          code: "BINDING_CHANGED_STATE_CLEARED"
        };
        break;
      }
      if (s.projection === "unbound" || s.projection === "cleared")
        s.projection = "awaiting_snapshot";
      settle(s);
      outcome = { disposition: "state_changed", code: null };
      break;
    }
    case "receive":
      outcome = receive(s, input.record, input.at);
      break;
    case "trusted_replay_interval":
      outcome = replayInterval(s, input);
      break;
    case "trusted_page_set_manifest":
      outcome = receivePageSetManifest(s, input.manifest, input.at);
      break;
    case "trusted_epoch_reset": {
      const o = input.oldViewContext;
      const n = input.newViewContext;
      const ok = s.binding !== null && sameContext(o, s.binding) && n.project_id === o.project_id && n.run_id === o.run_id && n.authorized_view_scope === o.authorized_view_scope && n.stream_epoch !== o.stream_epoch && input.authorizationObservationRef.length > 0;
      if (!ok) {
        outcome = reject(s, null, "INVALID_EPOCH_RESET");
        break;
      }
      s.binding = n;
      s.view = null;
      s.appliedCursor = null;
      s.buffer = [];
      s.holds = [];
      s.eventIdentities = {};
      s.cursorBindings = {};
      s.currentPlan = null;
      s.fullSnapshotRequired = true;
      s.pages = null;
      s.pageSetManifests = {};
      s.ancillary = {
        seen: {},
        attempts: {},
        artifacts: {},
        commands: {},
        deployments: {},
        joined: []
      };
      s.history = [];
      s.snapshotHistory = [];
      s.planHistory = [];
      s.historicalOnly = [];
      s.eventLog = [];
      s.eventLedger = [];
      s.sourceSequences = [];
      s.sourceReconcile = [];
      s.unassociatedSubjects = [];
      s.refusals = [];
      s.appliedEventsCompacted = 0;
      s.run = null;
      s.trustedReset = {
        previousEpoch: o.stream_epoch,
        ref: input.authorizationObservationRef
      };
      settle(s);
      outcome = { disposition: "state_changed", code: "EPOCH_RESET_TRUSTED" };
      break;
    }
    case "trusted_authorization_revoked": {
      if (s.binding === null || !sameContext(input.viewContext, s.binding)) {
        outcome = reject(s, null, "REVOCATION_BINDING_MISMATCH");
        break;
      }
      const fresh = createReducerState({
        mode: s.mode,
        extensions: s.extensions,
        limits: s.limits
      });
      Object.assign(s, fresh);
      s.projection = "cleared";
      s.fullSnapshotRequired = true;
      outcome = { disposition: "state_changed", code: "AUTHORIZATION_REVOKED" };
      break;
    }
    case "evaluate_acceptance": {
      const entry = s.ancillary.attempts[input.recordId];
      if (entry === void 0) {
        outcome = reject(s, input.recordId, "UNKNOWN_RECORD");
        break;
      }
      const evaluation = evaluateAcceptance(
        entry.record.data.acceptance,
        input.policy
      );
      const conflict = evaluation.issues.includes("ACCEPTANCE_POLICY_CONFLICT");
      s.ancillary = {
        ...s.ancillary,
        attempts: {
          ...s.ancillary.attempts,
          [input.recordId]: {
            ...entry,
            evaluation,
            semanticConflict: conflict
          }
        }
      };
      outcome = conflict ? { disposition: "quarantined", code: "ACCEPTANCE_POLICY_CONFLICT" } : { disposition: "state_changed", code: null };
      break;
    }
    case "transport_connected":
      s.connection = "connected";
      outcome = { disposition: "state_changed", code: null };
      break;
    case "transport_disconnected":
      s.connection = "disconnected";
      outcome = { disposition: "state_changed", code: "STALE_DISCONNECTED" };
      break;
    case "tick":
      if (s.buffer.length > 0) overflowCheck(s, input.at);
      expirePages(s, input.at);
      settle(s);
      outcome = { disposition: "state_changed", code: null };
      break;
  }
  return { state: s, commands: [], outcome };
}
function reduceAll(initial, inputs) {
  let state = initial;
  const outcomes = [];
  for (const input of inputs) {
    const r = reduce(state, input);
    state = r.state;
    outcomes.push(r.outcome);
  }
  return { state, outcomes, commands: [] };
}
var journalRank = {
  unknown: 0,
  intent_observed: 1,
  accepted_observed: 2,
  rejected_observed: 2
};
function projectNode(n) {
  return {
    key: nodeKey(n.ref),
    graphKind: n.ref.graph_kind,
    authority: n.ref.authority,
    namespace: n.ref.namespace,
    localId: n.ref.local_id,
    revision: n.ref.revision,
    nodeType: n.node_type,
    nativeState: n.native_state?.value ?? null,
    nativeVersions: n.native_versions,
    attributes: n.attributes
  };
}
function projectView(state) {
  const v = state.view;
  const nodes = v === null ? [] : v.graphs.flatMap((g) => g.nodes.map(projectNode)).sort((a, b) => a.key < b.key ? -1 : a.key > b.key ? 1 : 0);
  const attempts = Object.values(state.ancillary.attempts).map((e) => ({
    recordId: e.record.record_id,
    attemptKey: nodeKey(e.record.data.attempt_ref),
    nativeState: e.record.data.native_state?.value ?? null,
    acceptance: e.evaluation.effectiveVerdict,
    acceptanceBasis: e.evaluation.basis,
    sourceAcceptance: e.record.data.acceptance.verdict,
    issues: e.evaluation.issues,
    semanticConflict: e.semanticConflict,
    executedUndecided: e.evaluation.executedUndecided,
    checkersObserved: e.evaluation.checkersObserved,
    exactEvidenceCoverage: e.record.data.evidence_coverage === "exact_attempt",
    joinedByEvent: state.ancillary.joined.includes(e.record.record_id)
  })).sort((a, b) => a.recordId < b.recordId ? -1 : 1);
  const artifacts = Object.values(state.ancillary.artifacts).map((a) => {
    const denied = a.data.access === "denied";
    return {
      recordId: a.record_id,
      artifactKey: JSON.stringify([
        a.data.artifact.authority,
        a.data.artifact.namespace,
        a.data.artifact.artifact_id,
        a.data.artifact.revision
      ]),
      // On denial nothing locating or fingerprinting the content is exposed.
      availability: denied ? "unknown" : a.data.availability,
      access: a.data.access,
      storageIdentity: a.data.storage_identity,
      locator: denied ? null : a.data.locator,
      digests: denied ? [] : a.data.digests,
      open: {
        enabled: false,
        requires: "CURRENT_AUTHORIZATION_AND_BYTE_CHECK"
      },
      acceptance: evaluateAcceptance(a.data.acceptance).effectiveVerdict
    };
  }).sort((a, b) => a.recordId < b.recordId ? -1 : 1);
  const commandById = /* @__PURE__ */ new Map();
  for (const c of Object.values(state.ancillary.commands)) {
    const prior = commandById.get(c.data.command_id);
    if (prior === void 0 || (journalRank[c.data.journal_status] ?? 0) >= (journalRank[prior.data.journal_status] ?? 0)) {
      commandById.set(c.data.command_id, c);
    }
  }
  const nativeTop = v?.nativeState?.value ?? null;
  return {
    viewKind: v === null ? "unconnected" : state.sawFixture ? "fixture" : state.mode,
    projection: state.projection,
    stale: state.projection !== "current" || state.connection === "disconnected",
    appliedCursor: state.appliedCursor,
    holds: state.holds,
    fullSnapshotRequired: state.fullSnapshotRequired,
    currentPlan: state.currentPlan,
    dimensions: {
      connection: state.connection,
      freshness: state.projection,
      nativeState: nativeTop,
      independentAcceptance: v?.acceptance.effectiveVerdict ?? "NOT_MEASURED",
      acceptanceBasis: v?.acceptance.basis ?? "none",
      independentlyVerified: false
    },
    declaredGraphKinds: v?.declaredGraphKinds ?? [],
    nodes,
    crosslinks: (v?.crosslinks ?? []).map((c) => ({
      linkId: c.link_id,
      kind: c.kind,
      from: nodeKey(c.from),
      to: nodeKey(c.to),
      associationRef: c.association_ref
    })),
    implicitJoins: 0,
    workerStageNodes: nodes.filter(
      (n) => n.graphKind === "processing_execution" && n.nodeType === "stage_task"
    ).length,
    buffered: state.buffer.map((b) => b.recordId),
    rejected: state.rejected,
    quarantined: state.quarantined,
    ignored: state.ignored,
    historicalOnly: state.historicalOnly,
    uniqueSourceEventsApplied: Object.values(state.eventIdentities).filter((e) => e.status === "applied").length + state.appliedEventsCompacted,
    history: state.history,
    unassociatedSubjects: state.unassociatedSubjects,
    refusals: state.refusals,
    attempts,
    artifacts,
    immutableCaptureRevisions: Object.values(state.ancillary.artifacts).filter((a) => a.data.storage_identity === "immutable").map((a) => a.data.artifact.revision).sort(),
    commands: [...commandById.values()].map((c) => ({
      commandId: c.data.command_id,
      journalStatus: c.data.journal_status,
      reason: c.data.reason,
      canonicalRunId: c.data.canonical_run_id,
      canonicalAttemptRef: c.data.canonical_attempt_ref
    })).sort((a, b) => a.commandId < b.commandId ? -1 : 1),
    deployments: Object.values(state.ancillary.deployments).map((d) => ({
      recordId: d.record_id,
      observedBuild: d.data.actual_build,
      capabilities: d.data.capabilities
    })).sort((a, b) => a.recordId < b.recordId ? -1 : 1),
    eventLedger: state.eventLedger,
    sourceSequences: state.sourceSequences,
    sourceReconcile: state.sourceReconcile,
    snapshotAtomicity: v?.sourceAtomicity ?? "not_established",
    globalCompletenessAsserted: false,
    crossSourceAtomicityAsserted: false,
    emittedCommands: []
  };
}
function stableViewDigestInput(state) {
  const view = projectView(state);
  return canonicalJson({
    projection: view.projection,
    appliedCursor: view.appliedCursor,
    currentPlan: view.currentPlan,
    nodes: view.nodes,
    crosslinks: view.crosslinks,
    attempts: view.attempts,
    artifacts: view.artifacts,
    commands: view.commands
  });
}
var cmp = (a, b) => a < b ? -1 : a > b ? 1 : 0;
function presentedRef(r) {
  return {
    key: nodeKey(r),
    graphKind: r.graph_kind,
    authority: r.authority,
    namespace: r.namespace,
    localId: r.local_id,
    revision: r.revision
  };
}
function presentedAcceptance(a) {
  const e = evaluateAcceptance(a);
  return {
    sourceVerdict: a.verdict,
    independentVerdict: e.effectiveVerdict,
    independentBasis: e.basis,
    independentlyVerified: false,
    issues: e.issues
  };
}
function projectGraphPresentation(state) {
  const v = state.view;
  const graphs = v?.graphs ?? [];
  const base = projectView(state);
  return {
    viewKind: base.viewKind,
    projection: base.projection,
    stale: base.stale,
    appliedCursor: base.appliedCursor,
    currentPlan: base.currentPlan,
    sourceRevisions: deepClone(
      sortedBy(v?.sourceRevisions ?? [], canonicalJson)
    ),
    topAcceptance: v === null ? null : presentedAcceptance(v.acceptanceRecord),
    graphs: graphs.map((g) => ({
      graphKind: g.graph_kind,
      authority: g.authority,
      graphRevision: g.graph_revision,
      nodeCount: g.nodes.length,
      edgeCount: g.edges.length
    })).sort((a, b) => cmp(a.graphKind, b.graphKind)),
    nodes: graphs.flatMap(
      (g) => g.nodes.map((n) => ({
        ...presentedRef(n.ref),
        nodeType: n.node_type,
        nativeState: n.native_state?.value ?? null,
        acceptance: presentedAcceptance(n.acceptance),
        evidenceRefs: [...n.evidence_refs].sort(cmp)
      }))
    ).sort((a, b) => cmp(a.key, b.key)),
    edges: graphs.flatMap(
      (g) => g.edges.map((e) => ({
        edgeKey: JSON.stringify([g.graph_kind, e.edge_id]),
        edgeId: e.edge_id,
        graphKind: g.graph_kind,
        graphAuthority: g.authority,
        graphRevision: g.graph_revision,
        kind: e.kind,
        from: presentedRef(e.from),
        to: presentedRef(e.to),
        evidenceRefs: [...e.evidence_refs].sort(cmp)
      }))
    ).sort((a, b) => cmp(a.edgeKey, b.edgeKey)),
    crosslinks: (v?.crosslinks ?? []).map((c) => ({
      linkId: c.link_id,
      kind: c.kind,
      from: presentedRef(c.from),
      to: presentedRef(c.to),
      associationRef: c.association_ref,
      evidenceRefs: [...c.evidence_refs].sort(cmp)
    })).sort((a, b) => cmp(a.linkId, b.linkId)),
    implicitJoins: 0
  };
}
function graphPresentationDigestInput(state) {
  const p = projectGraphPresentation(state);
  return canonicalJson({
    stable: JSON.parse(stableViewDigestInput(state)),
    graphs: p.graphs,
    nodes: p.nodes,
    edges: p.edges,
    crosslinks: p.crosslinks,
    topAcceptance: p.topAcceptance,
    sourceRevisions: p.sourceRevisions
  });
}

// src/index.ts
var CAPABILITIES = [
  "spaces.read",
  "infrastructure.read",
  "dev_agents.read",
  "dev_agents.operate",
  "content.read",
  "content.write",
  "content.publish_live",
  "marketing.read",
  "support.tickets.read",
  "support.tickets.update",
  "provider_accounts.read_billing",
  "control.authorization.manage"
];
var CAPABILITY_SET = new Set(CAPABILITIES);
function isCapability(value) {
  return typeof value === "string" && CAPABILITY_SET.has(value);
}
var RESOURCE_KINDS = ["space"];
var RESOURCE_KIND_SET = new Set(RESOURCE_KINDS);
var UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/u;
function isUuid(value) {
  return typeof value === "string" && UUID_RE.test(value);
}
var MAX_CHECKS_PER_REQUEST = 32;
var EFFECTS2 = ["allow", "deny", "unavailable"];
function isPlainObject2(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
function rejectUnknownKeys(value, allowed, where) {
  for (const key of Object.keys(value)) {
    if (!allowed.includes(key)) return `${where}: unknown field '${key}'`;
  }
  return null;
}
function parseResource(value, where) {
  if (!isPlainObject2(value))
    return { ok: false, error: `${where}: resource must be an object` };
  const unknown = rejectUnknownKeys(value, ["kind", "id"], where);
  if (unknown !== null) return { ok: false, error: unknown };
  const kind = value["kind"];
  const id4 = value["id"];
  if (typeof kind !== "string" || !RESOURCE_KIND_SET.has(kind)) {
    return { ok: false, error: `${where}: unknown resource kind` };
  }
  if (typeof id4 !== "string" || id4.length === 0) {
    return {
      ok: false,
      error: `${where}: resource id must be a non-empty string`
    };
  }
  return { ok: true, value: { kind, id: id4 } };
}
function parseEntitlementRequest(value) {
  if (!isPlainObject2(value))
    return { ok: false, error: "request must be an object" };
  const unknown = rejectUnknownKeys(value, ["subject", "checks"], "request");
  if (unknown !== null) return { ok: false, error: unknown };
  const subject = value["subject"];
  const checks = value["checks"];
  if (!isUuid(subject))
    return { ok: false, error: "request: subject must be a UUID" };
  if (!Array.isArray(checks))
    return { ok: false, error: "request: checks must be an array" };
  if (checks.length === 0)
    return { ok: false, error: "request: checks must not be empty" };
  if (checks.length > MAX_CHECKS_PER_REQUEST) {
    return {
      ok: false,
      error: `request: batch exceeds ${MAX_CHECKS_PER_REQUEST} checks`
    };
  }
  const parsed = [];
  for (let index = 0; index < checks.length; index += 1) {
    const where = `request.checks[${index}]`;
    const raw = checks[index];
    if (!isPlainObject2(raw))
      return { ok: false, error: `${where}: must be an object` };
    const unknownCheck = rejectUnknownKeys(
      raw,
      ["capability", "resource"],
      where
    );
    if (unknownCheck !== null) return { ok: false, error: unknownCheck };
    const capability = raw["capability"];
    if (!isCapability(capability))
      return { ok: false, error: `${where}: unknown capability` };
    const resourceRaw = raw["resource"];
    if (resourceRaw === void 0) {
      parsed.push({ capability });
      continue;
    }
    const resource = parseResource(resourceRaw, where);
    if (!resource.ok) return { ok: false, error: resource.error };
    parsed.push({ capability, resource: resource.value });
  }
  return { ok: true, value: { subject, checks: parsed } };
}
function parseEntitlementResponse(value) {
  if (!isPlainObject2(value))
    return { ok: false, error: "response must be an object" };
  const unknown = rejectUnknownKeys(
    value,
    ["decisions", "policyVersion", "evaluatedAt"],
    "response"
  );
  if (unknown !== null) return { ok: false, error: unknown };
  const decisions = value["decisions"];
  const policyVersion = value["policyVersion"];
  const evaluatedAt = value["evaluatedAt"];
  if (typeof policyVersion !== "string" || policyVersion.length === 0) {
    return {
      ok: false,
      error: "response: policyVersion must be a non-empty string"
    };
  }
  if (typeof evaluatedAt !== "string" || Number.isNaN(Date.parse(evaluatedAt))) {
    return {
      ok: false,
      error: "response: evaluatedAt must be an ISO timestamp"
    };
  }
  if (!Array.isArray(decisions))
    return { ok: false, error: "response: decisions must be an array" };
  const parsed = [];
  for (let index = 0; index < decisions.length; index += 1) {
    const where = `response.decisions[${index}]`;
    const raw = decisions[index];
    if (!isPlainObject2(raw))
      return { ok: false, error: `${where}: must be an object` };
    const unknownDecision = rejectUnknownKeys(
      raw,
      ["capability", "resource", "effect"],
      where
    );
    if (unknownDecision !== null) return { ok: false, error: unknownDecision };
    const capability = raw["capability"];
    if (!isCapability(capability))
      return { ok: false, error: `${where}: unknown capability` };
    const effect = raw["effect"];
    if (typeof effect !== "string" || !EFFECTS2.includes(effect)) {
      return { ok: false, error: `${where}: unknown effect` };
    }
    const resourceRaw = raw["resource"];
    if (resourceRaw === void 0) {
      parsed.push({ capability, effect });
      continue;
    }
    const resource = parseResource(resourceRaw, where);
    if (!resource.ok) return { ok: false, error: resource.error };
    parsed.push({
      capability,
      resource: resource.value,
      effect
    });
  }
  return { ok: true, value: { decisions: parsed, policyVersion, evaluatedAt } };
}
function sameResource(a, b) {
  if (a === void 0 && b === void 0) return true;
  if (a === void 0 || b === void 0) return false;
  return a.kind === b.kind && a.id === b.id;
}
function resolveDecisions(requested, response) {
  return requested.map((check) => {
    const base = check.resource === void 0 ? { capability: check.capability } : { capability: check.capability, resource: check.resource };
    if (response === null) return { ...base, effect: "unavailable" };
    const matches2 = response.decisions.filter(
      (decision) => decision.capability === check.capability && sameResource(decision.resource, check.resource)
    );
    if (matches2.length === 0) return { ...base, effect: "unavailable" };
    if (matches2.some((decision) => decision.effect === "unavailable")) {
      return { ...base, effect: "unavailable" };
    }
    if (matches2.some((decision) => decision.effect === "deny")) {
      return { ...base, effect: "deny" };
    }
    return { ...base, effect: "allow" };
  });
}
function isAllowed(decision) {
  return decision.effect === "allow";
}
function buildSnapshot(args) {
  const allowed = args.decisions.filter(
    (decision) => decision.effect === "allow" && decision.resource === void 0
  ).map((decision) => decision.capability);
  return {
    subject: args.subject,
    sessionId: args.sessionId,
    allowed: [...new Set(allowed)],
    policyVersion: args.policyVersion,
    evaluatedAt: args.evaluatedAt
  };
}
function snapshotApplies(snapshot, subject, sessionId) {
  return snapshot.subject === subject && snapshot.sessionId === sessionId;
}
export {
  CAPABILITIES,
  DEFAULT_BUFFER_LIMITS as DEFAULT_KNOWLEDGE_OBSERVATION_LIMITS,
  EFFECTS2 as EFFECTS,
  LOSSLESS_DECIMAL_EXTENSION as KNOWLEDGE_OBSERVATION_LOSSLESS_DECIMAL_EXTENSION,
  PROFILE_ID as KNOWLEDGE_OBSERVATION_PROFILE_ID,
  MAX_CHECKS_PER_REQUEST,
  PERSONAL_AUTH_PROFILE,
  PERSONAL_AUTH_SELECTED_LIMITS,
  PERSONAL_AUTH_WIRE_VERSION,
  PERSONAL_CAPTURE_LIMITS,
  PERSONAL_CAPTURE_VERSION,
  RESOURCE_KINDS,
  buildSnapshot,
  canonicalJson as canonicalKnowledgeObservationJson,
  classifyDoclabNativeShape as classifyKnowledgeObservationDoclabShape,
  compareDecimal as compareKnowledgeObservationDecimal,
  compareDigests as compareKnowledgeObservationDigests,
  comparePersonalAuthLeaseAdmission,
  comparePersonalAuthOperationRetry,
  comparePersonalAuthOwnerOutcome,
  comparePersonalCaptureRetry,
  createReducerState as createKnowledgeObservationState,
  decodeObservationRecord as decodeKnowledgeObservationRecord,
  evaluateAcceptance as evaluateKnowledgeObservationAcceptance,
  evaluatePersonalCaptureTransition,
  incrementPersonalAuthCounter,
  isAllowed,
  isCapability,
  isRfc3339DateTime as isKnowledgeObservationDateTime,
  isCanonicalDecimal as isKnowledgeObservationDecimal,
  isExactContentAddress as isKnowledgeObservationExactContentAddress,
  isPersonalAuthCounter,
  isUuid,
  graphPresentationDigestInput as knowledgeObservationGraphDigestInput,
  nodeKey as knowledgeObservationNodeKey,
  snapshotPageDigest as knowledgeObservationPageDigest,
  stableViewDigestInput as knowledgeObservationStableDigestInput,
  nextDecimal as nextKnowledgeObservationDecimal,
  parseBoundedJson,
  parseEntitlementRequest,
  parseEntitlementResponse,
  parseKnowledgeObservationJson,
  parsePersonalAuthBindingContext,
  parsePersonalAuthJson,
  parsePersonalAuthLeaseAdmission,
  parsePersonalAuthOperation,
  parsePersonalAuthOperationJson,
  parsePersonalAuthOwnerOutcome,
  parsePersonalAuthOwnerOutcomeRequest,
  parsePersonalAuthOwnerOutcomeRequestJson,
  parsePersonalAuthParticipant,
  parsePersonalAuthReleaseUnit,
  parsePersonalCaptureBinding,
  parsePersonalCaptureCancellation,
  parsePersonalCaptureDescriptor,
  parsePersonalCaptureStatus,
  parsePersonalObjectReceipt,
  personalAuthMutationIdentity,
  personalAuthOperationFingerprintInput,
  personalAuthOperationMatchesBinding,
  personalAuthOwnerOutcomeEffect,
  personalAuthOwnerOutcomeRequestMatchesSameGenerationLease,
  personalCaptureFingerprintInput,
  personalCaptureResourceMatches,
  personalObjectReceiptMatches,
  projectView as projectKnowledgeObservation,
  projectGraphPresentation as projectKnowledgeObservationGraph,
  reduceAll as reduceAllKnowledgeObservations,
  reduce as reduceKnowledgeObservation,
  resolveDecisions,
  snapshotApplies
};
