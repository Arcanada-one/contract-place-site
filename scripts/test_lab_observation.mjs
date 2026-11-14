// SPDX-License-Identifier: Apache-2.0
// Existing synthetic records run through the real shared decoder/reducer. This
// DOM double tests the consumer contract; it is not browser or native-run evidence.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';
import {
  createKnowledgeObservationState, reduceKnowledgeObservation,
  projectKnowledgeObservationGraph, projectKnowledgeObservation,
} from '../src/site/lab/access-contracts.46ab74e.js';
import { mountKnowledgeJourneyObservation } from '../src/site/lab/knowledge-journey-observation.js';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'scripts/fixtures/knowledge-journey-observation.json'), 'utf8'));
const edges = JSON.parse(fs.readFileSync(path.join(root, 'scripts/fixtures/agent-runs-edge-fixture.json'), 'utf8'));
function stateFor(ids, change) {
  let state = createKnowledgeObservationState({ mode: 'fixture' });
  state = reduceKnowledgeObservation(state, { kind: 'bind_trusted_projection', viewContext: fixture.default_view_context }).state;
  for (const id of ids) {
    const record = structuredClone(fixture.records[id]);
    if (change) change(record);
    const result = reduceKnowledgeObservation(state, { kind: 'receive', record });
    assert.deepEqual(result.commands, []);
    assert.ok(!['rejected', 'quarantined'].includes(result.outcome.disposition));
    state = result.state;
  }
  return state;
}
function edgeState() {
  let state = createKnowledgeObservationState({ mode: edges.mode, extensions: edges.extensions });
  state = reduceKnowledgeObservation(state, { kind: 'bind_trusted_projection', viewContext: edges.view_context }).state;
  for (const record of edges.records) {
    const result = reduceKnowledgeObservation(state, { kind: 'receive', record });
    assert.ok(!['rejected', 'quarantined'].includes(result.outcome.disposition));
    state = result.state;
  }
  return state;
}

class Element {
  constructor(tag, doc, text = '') { this.tag = tag; this.doc = doc; this.text = text; this.children = []; this.parent = null; this.attrs = {}; this.handlers = new Map(); }
  setAttribute(key, value) { this.attrs[key] = String(value); }
  getAttribute(key) { return this.attrs[key] ?? null; }
  hasAttribute(key) { return key in this.attrs; }
  removeAttribute(key) { delete this.attrs[key]; }
  get id() { return this.getAttribute('id'); }
  get tagName() { return this.tag.toUpperCase(); }
  get firstChild() { return this.children[0] || null; }
  get textContent() { return this.text + this.children.map(c => c.textContent).join(''); }
  append(...nodes) { for (const node of nodes) { node.remove(); node.parent = this; this.children.push(node); } }
  removeChild(node) { const i = this.children.indexOf(node); if (i >= 0) this.children.splice(i, 1); node.parent = null; return node; }
  remove() { if (this.parent) this.parent.removeChild(this); }
  contains(node) { return this === node || this.children.some(child => child.contains(node)); }
  addEventListener(kind, handler) { if (!this.handlers.has(kind)) this.handlers.set(kind, new Set()); this.handlers.get(kind).add(handler); }
  removeEventListener(kind, handler) { this.handlers.get(kind)?.delete(handler); }
  click() { for (const handler of [...(this.handlers.get('click') || [])]) handler({ target: this }); }
  focus() { this.doc.activeElement = this; }
  querySelectorAll(selector) {
    const match = /^\[([a-z-]+)(?:="([^"]*)")?\]$/.exec(selector), result = [];
    const walk = node => { for (const child of node.children) {
      if (match && child.hasAttribute(match[1]) && (match[2] === undefined || child.getAttribute(match[1]) === match[2])) result.push(child);
      walk(child);
    } };
    walk(this); return result;
  }
  querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
}
function surface(locale = 'en') {
  const doc = { activeElement: null, documentElement: { lang: locale } };
  doc.createElement = tag => new Element(tag, doc);
  doc.createTextNode = text => new Element('#text', doc, String(text));
  const node = doc.createElement('main');
  node.setAttribute('data-live-lab', 'knowledge-journey'); node.setAttribute('data-live-lab-state', 'unconnected');
  const input = doc.createElement('input'), start = doc.createElement('button');
  input.setAttribute('disabled', ''); start.setAttribute('disabled', ''); node.append(input, start);
  const regions = {}, placeholders = [];
  for (const name of ['graph', 'timeline', 'inspector']) {
    const region = doc.createElement('section'); region.setAttribute('data-live-lab-region', name);
    const heading = doc.createElement('h2'); heading.append(doc.createTextNode(name));
    const placeholder = doc.createElement('p'); placeholder.append(doc.createTextNode('empty')); placeholders.push(placeholder);
    region.append(heading, placeholder); node.append(region); regions[name] = region;
  }
  return { document: doc, root: node, input, start, regions, placeholders };
}
const buttons = (region, kind) => region.querySelectorAll('[data-lab-inspect-kind]').filter(b => b.getAttribute('data-lab-inspect-kind') === kind);
const details = s => s.regions.inspector.querySelector('[data-lab-observation-inspector]');

test('vendored shared bytes and reused test fixtures match their recorded pins', () => {
  const provenance = JSON.parse(fs.readFileSync(path.join(root, 'src/site/lab/OBSERVATION-PROVENANCE.json'), 'utf8'));
  for (const entry of provenance.files) {
    assert.equal(createHash('sha256').update(fs.readFileSync(path.join(root, entry.path))).digest('hex'), entry.sha256, entry.path);
  }
  for (const name of fs.readdirSync(path.join(root, 'src/site/lab'))) {
    assert.deepEqual(fs.readFileSync(path.join(root, 'public/lab', name)), fs.readFileSync(path.join(root, 'src/site/lab', name)), name);
  }
});

test('mount without an authorized reader state preserves the existing empty disabled page', () => {
  const s = surface(), before = s.root.textContent;
  const controller = mountKnowledgeJourneyObservation(s);
  assert.equal(s.root.textContent, before);
  assert.equal(s.root.getAttribute('data-live-lab-state'), 'unconnected');
  assert.equal(s.root.hasAttribute('data-lab-observation-state'), false);
  assert.equal(s.root.querySelectorAll('[data-lab-placeholder]').length, 0);
  assert.ok(s.input.hasAttribute('disabled') && s.start.hasAttribute('disabled'));
  assert.equal(controller.select('node', 'missing'), false);
  controller.destroy();
});

test('same decoded state supplies graph, edge evidence, timeline and localized inspector', () => {
  for (const [locale, inspect] of [['en', 'Inspect'], ['ru', 'Рассмотреть'], ['zh-Hans', '查看']]) {
    const s = surface(locale), state = edgeState(), graph = projectKnowledgeObservationGraph(state);
    const controller = mountKnowledgeJourneyObservation({ ...s, state });
    assert.ok(graph.edges.length > 0);
    assert.equal(s.regions.graph.querySelector('[data-lab-observation-graph]').getAttribute('data-lab-view-kind'), graph.viewKind);
    assert.equal(graph.viewKind, 'fixture');
    assert.equal(buttons(s.regions.graph, 'node').length, graph.nodes.length);
    assert.equal(buttons(s.regions.graph, 'edge').length, graph.edges.length);
    assert.equal(buttons(s.regions.graph, 'link').length, graph.crosslinks.length);
    assert.ok(buttons(s.regions.graph, 'edge')[0].textContent.startsWith(inspect));
    buttons(s.regions.graph, 'edge')[0].click();
    for (const reference of graph.edges[0].evidenceRefs) assert.ok(details(s).textContent.includes(reference));
    assert.equal(s.document.activeElement.id, 'knowledge-journey-observation-detail');
    assert.ok(s.regions.timeline.textContent.includes(projectKnowledgeObservation(state).dimensions.connection));
    assert.equal(s.root.getAttribute('data-live-lab-state'), 'unconnected');
    assert.ok(s.input.hasAttribute('disabled') && s.start.hasAttribute('disabled'));
    assert.ok(s.placeholders.every(p => p.hasAttribute('hidden') && p.hasAttribute('data-lab-placeholder')));
    controller.destroy();
    assert.ok(s.placeholders.every(p => !p.hasAttribute('hidden') && !p.hasAttribute('data-lab-placeholder')));
  }
});

test('retained timeline preserves real reducer order and producer, observed and stored clocks', () => {
  const state = stateFor(['snapshot-A', 'event-1', 'event-2'], record => {
    if (record.record_id === 'event-1') {
      record.data.occurred_at = '2000-01-01T00:01:00Z';
      record.observed_at = '2000-01-01T00:00:30Z';
      record.recorded_at = '2000-01-01T00:02:00Z';
    }
  });
  const s = surface(), controller = mountKnowledgeJourneyObservation({ ...s, state });
  const view = projectKnowledgeObservation(state), events = buttons(s.regions.timeline, 'event');
  assert.deepEqual(events.map(b => b.textContent), view.eventLedger.map(e => e.cursor + ' · ' + e.eventId));
  assert.equal(events.length, 2);
  events[0].click();
  for (const value of ['9007199254740993', '2000-01-01T00:01:00Z', '2000-01-01T00:00:30Z', '2000-01-01T00:02:00Z']) assert.ok(details(s).textContent.includes(value));
  controller.destroy();
});

test('allowed, denied and missing artifact metadata never enable or expose a file locator', () => {
  for (const id of ['receipt-captured-1', 'artifact-denied', 'artifact-missing']) {
    const state = stateFor(['snapshot-A', id]), s = surface();
    const controller = mountKnowledgeJourneyObservation({ ...s, state });
    assert.equal(controller.select('artifact', id), true);
    assert.equal(details(s).querySelector('[disabled]').getAttribute('aria-disabled'), 'true');
    const artifact = projectKnowledgeObservation(state).artifacts.find(a => a.recordId === id);
    assert.ok(details(s).textContent.includes(artifact.access));
    assert.ok(details(s).textContent.includes(artifact.availability));
    assert.equal(details(s).querySelectorAll('[href]').length, 0);
    assert.equal(details(s).querySelectorAll('[src]').length, 0);
    assert.ok(!details(s).textContent.includes('fixture-artifact:receipt-captured-1'));
    controller.destroy();
  }
});

test('actual authorization revocation removes previous graph, events, details and handlers', () => {
  const state = stateFor(['snapshot-A', 'event-1', 'receipt-captured-1']), s = surface();
  const controller = mountKnowledgeJourneyObservation({ ...s, state });
  const oldButton = buttons(s.regions.graph, 'node')[0];
  assert.equal(controller.select('artifact', 'receipt-captured-1'), true);
  const revoked = reduceKnowledgeObservation(state, { kind: 'trusted_authorization_revoked', viewContext: fixture.default_view_context }).state;
  assert.equal(controller.update(revoked).unconnected, true);
  assert.equal(s.regions.graph.querySelectorAll('[data-node-key]').length, 0);
  assert.ok(!s.root.textContent.includes('receipt-captured-1'));
  assert.ok(!s.root.textContent.includes('event-1'));
  assert.equal(oldButton.handlers.get('click').size, 0);
  assert.equal(controller.select('artifact', 'receipt-captured-1'), false);
  assert.ok(s.placeholders.every(p => !p.hasAttribute('hidden') && !p.hasAttribute('data-lab-placeholder')));
  controller.destroy();
});

test('failed state projection clears private details and valid recovery removes unavailable state', () => {
  const state = stateFor(['snapshot-A', 'receipt-captured-1']), s = surface();
  const controller = mountKnowledgeJourneyObservation({ ...s, state });
  controller.select('artifact', 'receipt-captured-1');
  assert.deepEqual(controller.update({ schema: 'observation-reducer-state/v1' }), { unavailable: true });
  assert.ok(!s.root.textContent.includes('receipt-captured-1'));
  assert.equal(s.root.querySelectorAll('[data-lab-observation-inspector]').length, 0);
  assert.equal(s.root.querySelectorAll('[data-lab-observation-graph]').length, 0);
  assert.equal(s.root.getAttribute('data-lab-observation-state'), 'unavailable');
  assert.ok(s.root.textContent.includes('NOT_MEASURED'));
  controller.update(state);
  assert.equal(s.root.getAttribute('data-lab-observation-state'), 'displayed');
  assert.equal(s.root.querySelectorAll('[data-lab-observation-failure]').length, 0);
  assert.equal(s.root.querySelectorAll('[data-lab-observation-inspector]').length, 1);
  controller.destroy();
});

test('replacing a mount disposes its controls; stale clear and destroy cannot affect its successor', () => {
  const s = surface(), state = stateFor(['snapshot-A']);
  const first = mountKnowledgeJourneyObservation({ ...s, state });
  const oldButton = buttons(s.regions.graph, 'node')[0];
  const second = mountKnowledgeJourneyObservation({ ...s, state: edgeState() });
  first.clear(); first.destroy();
  assert.deepEqual(first.update(state), { disposed: true });
  assert.equal(oldButton.handlers.get('click').size, 0);
  assert.equal(s.root.getAttribute('data-lab-observation-state'), 'displayed');
  assert.equal(s.root.querySelectorAll('[data-lab-observation-inspector]').length, 1);
  assert.ok(s.placeholders.every(p => p.hasAttribute('hidden') && p.hasAttribute('data-lab-placeholder')));
  const selected = projectKnowledgeObservationGraph(edgeState()).edges[0];
  for (let i = 0; i < 20; i += 1) assert.equal(second.select('edge', selected.edgeKey), true);
  second.destroy();
  assert.equal(s.root.querySelectorAll('[data-lab-observation-inspector]').length, 0);
});

test('valid native-state markup remains isolated text after the actual decoder', () => {
  const hostile = '<img src=x onerror=alert(1)>\u202eprivate';
  const state = stateFor(['snapshot-A'], record => { record.data.graphs.find(g => g.nodes.length).nodes[0].native_state.value = hostile; });
  const s = surface(), controller = mountKnowledgeJourneyObservation({ ...s, state });
  assert.equal(controller.select('node', projectKnowledgeObservationGraph(state).nodes[0].key), true);
  assert.ok(details(s).textContent.includes(hostile));
  const isolated = [];
  const walk = node => { if (node.tag === 'bdi') isolated.push(node.textContent); for (const child of node.children) walk(child); };
  walk(details(s));
  assert.ok(isolated.includes(hostile));
  assert.equal(details(s).querySelectorAll('[src]').length, 0);
  controller.destroy();
});

test('original hidden and placeholder values survive clear, replacement and destroy exactly', () => {
  const s = surface(), state = stateFor(['snapshot-A']);
  s.placeholders[0].setAttribute('hidden', 'until-found');
  s.placeholders[0].setAttribute('data-lab-placeholder', 'original-graph');
  s.placeholders[1].setAttribute('hidden', '');
  s.placeholders[1].setAttribute('data-lab-placeholder', 'original-timeline');
  s.placeholders[2].setAttribute('data-lab-placeholder', 'original-inspector');
  const attributes = () => s.placeholders.map(node => ({
    hidden: node.getAttribute('hidden'), marker: node.getAttribute('data-lab-placeholder'),
  }));
  const original = attributes();
  const first = mountKnowledgeJourneyObservation({ ...s, state });
  assert.ok(attributes().every(value => value.hidden === '' && value.marker === ''));
  first.clear();
  assert.deepEqual(attributes(), original);
  first.update(state);
  const second = mountKnowledgeJourneyObservation({ ...s, state: edgeState() });
  const successor = attributes();
  assert.ok(successor.every(value => value.hidden === '' && value.marker === ''));
  first.clear(); first.destroy();
  assert.deepEqual(attributes(), successor, 'disposed controller cannot restore attributes over its successor');
  second.clear();
  assert.deepEqual(attributes(), original);
  second.update(state);
  second.destroy();
  assert.deepEqual(attributes(), original);
});

test('raw records are not accepted as state and forbidden evidence references stay rejected', () => {
  const s = surface(), controller = mountKnowledgeJourneyObservation(s);
  assert.deepEqual(controller.update(fixture.records['snapshot-A']), { unavailable: true });
  let state = createKnowledgeObservationState({ mode: 'fixture' });
  state = reduceKnowledgeObservation(state, { kind: 'bind_trusted_projection', viewContext: fixture.default_view_context }).state;
  const record = structuredClone(fixture.records['snapshot-A']);
  record.data.graphs.find(g => g.nodes.length).nodes[0].evidence_refs = ['<img>\u202eprivate'];
  const result = reduceKnowledgeObservation(state, { kind: 'receive', record });
  assert.ok(['rejected', 'quarantined'].includes(result.outcome.disposition));
  assert.equal(controller.update(result.state).unconnected, true);
  assert.equal(s.root.querySelectorAll('[data-node-key]').length, 0);
  controller.destroy();
});
