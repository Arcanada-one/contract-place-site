// SPDX-License-Identifier: Apache-2.0
// Read-only consumer of ONE already-decoded, scope-bound shared reducer state.
// The protected reader owns transport, parsing, binding and authorization. This
// module never reads page JSON, URL selectors, storage, tokens or remote services.
import {
  projectKnowledgeObservationGraph,
  projectKnowledgeObservation,
} from './access-contracts.46ab74e.js';
import { createObservationInspectorMount } from './observation-inspector.b35b9e7e.js';

const mountInspector = createObservationInspectorMount({
  projectGraph: projectKnowledgeObservationGraph,
  projectView: projectKnowledgeObservation,
});
const mounts = new WeakMap();
const TEXT = {
  en: {
    mode: 'Observed view mode', projection: 'Projection', stale: 'Stale observation',
    cursor: 'Cursor', plan: 'Plan revision', graphs: 'Observed graphs', nodes: 'Nodes',
    edges: 'Edges', links: 'Crosslinks', empty: 'No records retained in this group.',
    notice: 'This view displays received observations. It does not start a processing run or grant permission to open files.',
    unavailable: 'Observation unavailable · NOT_MEASURED',
  },
  ru: {
    mode: 'Режим наблюдаемого представления', projection: 'Проекция', stale: 'Устаревшее наблюдение',
    cursor: 'Курсор', plan: 'Версия плана', graphs: 'Наблюдаемые графы', nodes: 'Узлы',
    edges: 'Связи', links: 'Межграфовые связи', empty: 'В этой группе нет сохранённых записей.',
    notice: 'Здесь показаны полученные наблюдения. Это представление не запускает обработку и не предоставляет разрешение на открытие файлов.',
    unavailable: 'Наблюдение недоступно · NOT_MEASURED',
  },
  'zh-Hans': {
    mode: '观测视图模式', projection: '投影', stale: '过期观测',
    cursor: '游标', plan: '计划版本', graphs: '观测图', nodes: '节点',
    edges: '边', links: '跨图关联', empty: '此组未保留记录。',
    notice: '此视图显示已接收的观测，不启动处理流程，也不授予打开文件的权限。',
    unavailable: '观测不可用 · NOT_MEASURED',
  },
};

function element(doc, tag, attrs = {}, text) {
  const node = doc.createElement(tag);
  for (const [name, value] of Object.entries(attrs)) node.setAttribute(name, String(value));
  if (text !== undefined) node.append(doc.createTextNode(String(text)));
  return node;
}
const isolated = (doc, value) => element(doc, 'bdi', { dir: 'auto' }, value ?? '—');

// Only presentation: the shared projectors have already supplied all joins,
// qualified identities, edges and modes. No relation or status is inferred here.
function graphContent(doc, graph, words) {
  const surface = element(doc, 'div', {
    'data-lab-observation-graph': '', 'data-lab-view-kind': graph.viewKind,
    'data-lab-projection': graph.projection,
  });
  surface.append(element(doc, 'p', {}, words.notice));
  const metadata = element(doc, 'dl', { class: 'lab-observation-fields' });
  for (const [label, value] of [
    [words.mode, graph.viewKind], [words.projection, graph.projection],
    [words.stale, graph.stale], [words.cursor, graph.appliedCursor], [words.plan, graph.currentPlan],
  ]) {
    const detail = element(doc, 'dd'); detail.append(isolated(doc, value));
    metadata.append(element(doc, 'dt', {}, label), detail);
  }
  surface.append(metadata);
  const group = (title, items, attribute, key, describe) => {
    surface.append(element(doc, 'h3', {}, title));
    if (!items.length) { surface.append(element(doc, 'p', {}, words.empty)); return; }
    const list = element(doc, 'ul');
    for (const item of items) {
      const row = element(doc, 'li', attribute ? { [attribute]: item[key] } : {});
      row.append(isolated(doc, describe(item)));
      list.append(row);
    }
    surface.append(list);
  };
  group(words.graphs, graph.graphs, null, null, item =>
    [item.graphKind, item.authority, item.graphRevision].join(' / '));
  group(words.nodes, graph.nodes, 'data-node-key', 'key', item =>
    [item.graphKind, item.localId, item.nodeType].join(' / '));
  group(words.edges, graph.edges, 'data-edge-key', 'edgeKey', item =>
    item.kind + ': ' + item.from.key + ' → ' + item.to.key);
  group(words.links, graph.crosslinks, 'data-link-id', 'linkId', item =>
    item.kind + ': ' + item.from.key + ' → ' + item.to.key);
  return surface;
}

/**
 * Call from the protected reader only after its normal decoder and scope binding.
 * With no state the existing unconnected page is left untouched. update(state)
 * never accepts raw wire records or derives a trusted binding. clear()/destroy()
 * are mandatory on logout, reader failure, scope change and route disposal.
 * This is an internal rendering interface, not a browser authorization boundary.
 */
export function mountKnowledgeJourneyObservation({ document: doc, root, state, locale = doc.documentElement?.lang || 'en' }) {
  if (!root || root.getAttribute('data-live-lab') !== 'knowledge-journey') {
    throw new Error('knowledge-journey-root-unavailable');
  }
  const graphRoot = root.querySelector('[data-live-lab-region="graph"]');
  const timelineRoot = root.querySelector('[data-live-lab-region="timeline"]');
  const inspectorRoot = root.querySelector('[data-live-lab-region="inspector"]');
  if (!graphRoot || !timelineRoot || !inspectorRoot) throw new Error('knowledge-journey-regions-unavailable');
  mounts.get(root)?.destroy();
  const words = TEXT[locale] || TEXT.en;
  // The current prerendered shell has one direct empty paragraph per region.
  // Mark it only while displaying observations; no template or HTML rewrite is
  // needed, and every original attribute is restored on clear/disposal.
  const placeholders = [graphRoot, timelineRoot, inspectorRoot].flatMap(region => {
    const node = [...region.children].find(child => child.tagName === 'P');
    return node ? [{ node, hidden: node.getAttribute('hidden'), marker: node.getAttribute('data-lab-placeholder') }] : [];
  });
  let inspector = null, surface = null, failure = null, disposed = false;

  function clear() {
    if (disposed) return;
    inspector?.destroy(); inspector = null;
    surface?.remove(); surface = null;
    failure?.remove(); failure = null;
    root.removeAttribute('data-lab-observation-state');
    for (const { node, hidden, marker } of placeholders) {
      if (hidden !== null) node.setAttribute('hidden', hidden); else node.removeAttribute('hidden');
      if (marker === null) node.removeAttribute('data-lab-placeholder');
      else node.setAttribute('data-lab-placeholder', marker);
    }
  }

  function update(nextState) {
    if (disposed) return { disposed: true };
    // Discard all previous private DOM before projecting a different state.
    clear();
    try {
      if (nextState?.schema !== 'observation-reducer-state/v1') throw new Error('decoded-state-required');
      const presentation = projectKnowledgeObservationGraph(nextState);
      const view = projectKnowledgeObservation(nextState);
      if (presentation.viewKind === 'unconnected') return { unconnected: true, presentation, view };
      surface = graphContent(doc, presentation, words);
      graphRoot.append(surface);
      for (const { node } of placeholders) node.setAttribute('data-lab-placeholder', '');
      inspector = mountInspector({
        document: doc, graphRoot, timelineRoot, inspectorRoot,
        state: nextState, locale, idPrefix: 'knowledge-journey-observation',
      });
      for (const { node } of placeholders) node.setAttribute('hidden', '');
      root.setAttribute('data-lab-observation-state', 'displayed');
      return { presentation, view };
    } catch {
      clear();
      root.setAttribute('data-lab-observation-state', 'unavailable');
      failure = element(doc, 'p', { 'data-lab-observation-failure': '', role: 'status' }, words.unavailable);
      graphRoot.append(failure);
      return { unavailable: true };
    }
  }

  function destroy() {
    if (disposed) return;
    clear(); disposed = true;
    if (mounts.get(root) === controller) mounts.delete(root);
  }
  const controller = {
    update, clear, destroy,
    select: (kind, key) => !disposed && inspector !== null && inspector.select(kind, key),
  };
  mounts.set(root, controller);
  if (state !== undefined) update(state);
  return controller;
}
