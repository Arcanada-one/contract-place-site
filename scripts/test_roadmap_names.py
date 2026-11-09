# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Finite parser/graph regression tests; no network, deployment or Pandoc calls."""
import copy
import json
import os
from pathlib import Path
import unittest

from roadmap import check_graph, split_cards, tasks_preamble, EXECUTION_BINDINGS
from roadmap_names import normalize_tasks, strip_editorial_markers


def named(ident='01', title='Claim Atlas', requires='none', priority='Immediate'):
    return f'''<!-- markdownlint-disable-next-line MD033 -->
<a id="rm-{ident}"></a>

<!-- markdownlint-disable-next-line MD033 -->
<a id="readable-{ident}"></a>

## {title}: A bounded output

**Artifact observation (8 November 2026).** An artifact exists; execution is not established.

**Priority:** {priority} · **Owner:** KC-Brain · **Required outputs:** {requires}.

**Original gap (6 November 2026).** A concrete gap remains.

**Work.** Inspect exact sources.

**Deliverables.** A readable record.

**Acceptance.** Keep the scope explicit.

**Adversarial check.** Remove a premise.

**Preparation boundary.** Follow the authorized scope.
'''


def legacy():
    return '''# Work packages

Preserved preamble.

## RM-01

### Original title

**Priority:** P0 · **Owner:** KC-Brain · **Required outputs:** none.

**Gap.** Original gap.

**Work.** Original work.

**Deliverables.** Original output.

**Acceptance.** Original acceptance.

**Adversarial check.** Original adverse case.

**Start boundary.** Original boundary.
'''


class ReadableRoadmapTests(unittest.TestCase):
    def test_legacy_normalization_is_byte_identical(self):
        self.assertEqual(legacy(), normalize_tasks(legacy()))
        self.assertEqual(split_cards(legacy())['RM-01']['title'], 'Original title')

    def test_named_title_and_anchor(self):
        card = split_cards(named())['RM-01']
        self.assertEqual(card['title'], 'Claim Atlas: A bounded output')
        self.assertEqual(card['priority'], 'P0')
        self.assertEqual(card['requires'], [])

    def test_dated_observations_and_gap_are_preserved(self):
        gap = split_cards(named())['RM-01']['fields']['gap']
        for value in ['8 November 2026', 'An artifact exists; execution is not established.',
                      '6 November 2026', 'A concrete gap remains.']:
            self.assertIn(value, gap)

    def test_named_forward_dependencies_resolve_by_identity_not_order(self):
        text = named('05', 'Meaning Bridge', 'Source Audit', 'Next') + named('06', 'Source Audit')
        self.assertEqual(split_cards(text)['RM-05']['requires'], ['RM-06'])
        self.assertEqual(split_cards(text)['RM-05']['priority'], 'P1')

    def test_expansion_priority(self):
        self.assertEqual(split_cards(named(priority='Expansion'))['RM-01']['priority'], 'P2')

    def test_unknown_dependency_refused(self):
        with self.assertRaises(ValueError):
            split_cards(named(requires='Missing Work'))

    def test_duplicate_dependency_refused(self):
        with self.assertRaises(ValueError):
            split_cards(named(requires='Claim Atlas, Claim Atlas'))

    def test_duplicate_short_name_refused(self):
        with self.assertRaises(ValueError):
            split_cards(named() + named('02'))

    def test_duplicate_identity_refused(self):
        with self.assertRaises(ValueError):
            split_cards(named() + named(title='Other Name'))

    def test_duplicate_readable_alias_refused(self):
        with self.assertRaises(ValueError):
            split_cards(named() + named('02', 'Other Name').replace('readable-02', 'readable-01'))

    def test_mixed_legacy_and_named_refused(self):
        with self.assertRaises(ValueError):
            split_cards(legacy() + named('02', 'Other Name'))

    def test_missing_compatibility_anchor_not_assigned_positionally(self):
        with self.assertRaises(ValueError):
            split_cards(named() + named('02', 'Other Name').replace('<a id="rm-02"></a>', ''))

    def test_unexpected_header_prose_refused(self):
        with self.assertRaises(ValueError):
            split_cards(named().replace('**Priority:**', 'Unaccounted text.\n\n**Priority:**'))

    def test_missing_observation_refused(self):
        with self.assertRaises(ValueError):
            split_cards(named().replace('**Artifact observation (8 November 2026).** An artifact exists; execution is not established.', ''))

    def test_opaque_heading_refused(self):
        with self.assertRaises(ValueError):
            split_cards(named(title='S01'))

    def test_unknown_field_refused_by_retained_parser(self):
        with self.assertRaises(ValueError):
            split_cards(named().replace('**Work.**', '**Execution status.** done\n\n**Work.**'))

    def test_missing_field_refused_by_retained_parser(self):
        with self.assertRaises(ValueError):
            split_cards(named().replace('**Deliverables.** A readable record.\n', ''))

    def test_unknown_markup_before_title_refused(self):
        with self.assertRaises(ValueError):
            split_cards(named().replace('## Claim Atlas', '<script>unsafe()</script>\n\n## Claim Atlas'))

    def test_only_known_whole_line_comments_removed(self):
        source = '<!-- WORKSTREAM_TABLE -->\nRetain this.\n<!-- /WORKSTREAM_TABLE -->\n'
        self.assertEqual(strip_editorial_markers(source), 'Retain this.\n')
        unsafe = '<!-- hidden state -->\n<script>unsafe()</script>\n'
        self.assertEqual(strip_editorial_markers(unsafe), unsafe)

    def test_preamble_does_not_include_first_card_or_anchors(self):
        head = '# Work packages\n\nKeep this preamble.\n\n'
        self.assertEqual(tasks_preamble(head + named()), head.strip())

    def test_all_twenty_five_ids_and_original_graph_gates(self):
        text = ''.join(named(f'{i:02}', f'Work {chr(64+i)}',
                             'none' if i == 1 else f'Work {chr(63+i)}') for i in range(1, 26))
        cards = split_cards(text)
        self.assertEqual(len(cards), 25)
        graph = {'nodes': [{'id': k, 'priority': c['priority'], 'content_owner': c['owner'],
                            'requires': c['requires']} for k, c in cards.items()],
                 'execution_bindings': EXECUTION_BINDINGS, 'target_dates': None}
        self.assertEqual(set(check_graph(graph)), set(cards))
        for mutate in ['state', 'cycle', 'dangling', 'missing']:
            bad = copy.deepcopy(graph)
            if mutate == 'state': bad['nodes'][0]['status'] = 'done'
            if mutate == 'cycle': bad['nodes'][0]['requires'] = ['RM-25']
            if mutate == 'dangling': bad['nodes'][0]['requires'] = ['RM-99']
            if mutate == 'missing': bad['nodes'].pop()
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                check_graph(bad)

    def test_optional_scope_still_limited_to_agent_application(self):
        body = named('18', 'Agent Application').replace('**Deliverables.**', '**Scope separation.** Bounded.\n\n**Deliverables.**')
        self.assertIn('scope', split_cards(body)['RM-18']['fields'])
        with self.assertRaises(ValueError):
            split_cards(body.replace('rm-18', 'rm-17'))


class PinnedPublicationRoadmapTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('READABLE_ROADMAP_SOURCE_DIR'),
                         'requires the actual pinned publication checkout')
    def test_complete_pinned_readable_cards_match_their_graph(self):
        source = Path(os.environ['READABLE_ROADMAP_SOURCE_DIR'])
        text = (source / 'roadmap/TASKS.md').read_text(encoding='utf-8')
        self.assertIn('<a id="rm-01"></a>', text,
                      'this test must exercise the readable source, not the old numbered format')
        cards = split_cards(text)
        graph = check_graph(json.loads((source / 'roadmap/dependencies.json').read_text(encoding='utf-8')))
        self.assertEqual(set(cards), set(graph))
        self.assertEqual(len(cards), 25)
        for ident, card in cards.items():
            with self.subTest(ident=ident):
                self.assertEqual(card['priority'], graph[ident]['priority'])
                self.assertEqual(card['owner'], graph[ident]['content_owner'])
                self.assertEqual(sorted(card['requires']), sorted(graph[ident]['requires']))
                self.assertIn(': ', card['title'])
                self.assertIn('Artifact observation', card['fields']['gap'])


if __name__ == '__main__':
    unittest.main()
