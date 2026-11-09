# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Finite synthetic controls for named-graph metadata, not task-state evidence."""
import copy
import unittest
from roadmap import check_graph, EXECUTION_BINDINGS
from roadmap_names import validate_display_names, check_card_display_name


def fixture(named=True):
    nodes = []
    for i in range(1, 26):
        n = {'id': f'RM-{i:02}', 'priority': 'P0', 'content_owner': 'KC-Brain',
             'requires': [] if i == 1 else [f'RM-{i-1:02}']}
        if named:
            n.update(display_name='Work '+chr(64+i), display_name_ru='Работа '+chr(0x410+i-1))
        nodes.append(n)
    return {'nodes': nodes, 'execution_bindings': EXECUTION_BINDINGS, 'target_dates': None}


class DisplayNameTests(unittest.TestCase):
    def test_readable_graph_preserves_all_original_fields_and_input(self):
        graph=fixture(); original=copy.deepcopy(graph); nodes=check_graph(graph)
        self.assertEqual(graph,original)
        self.assertEqual(list(nodes), [n['id'] for n in graph['nodes']])
        self.assertEqual(sum(len(n['requires']) for n in nodes.values()),24)
        self.assertEqual(nodes['RM-01']['display_name'],'Work A')

    def test_legacy_graph_preserves_exact_nodes(self):
        graph=fixture(False); original=copy.deepcopy(graph)
        self.assertEqual(list(check_graph(graph).values()), original['nodes'])
        self.assertEqual(graph, original)

    def test_partial_pair_refused(self):
        g=fixture(); del g['nodes'][0]['display_name_ru']
        with self.assertRaises(ValueError): check_graph(g)

    def test_mixed_nodes_refused(self):
        g=fixture(); del g['nodes'][0]['display_name']; del g['nodes'][0]['display_name_ru']
        with self.assertRaises(ValueError): check_graph(g)

    def test_duplicate_english_refused(self):
        g=fixture(); g['nodes'][1]['display_name']=g['nodes'][0]['display_name']
        with self.assertRaises(ValueError): check_graph(g)

    def test_duplicate_russian_casefold_refused(self):
        g=fixture(); g['nodes'][1]['display_name_ru']=g['nodes'][0]['display_name_ru'].upper()
        with self.assertRaises(ValueError): check_graph(g)

    def test_unsafe_or_nontext_labels_refused(self):
        values=[None,[],42,'',' Claim Atlas','Claim  Atlas','Claim\nAtlas','Claim\tAtlas',
                '<b>Claim</b>','[Claim](x)','https://example.com','S01','RM-01',
                'Four Separate Words Here','x'*121,'Meaning\u200bTheory','A\x00B']
        for key in ('display_name','display_name_ru'):
            for value in values:
                g=fixture();g['nodes'][0][key]=value
                with self.subTest(key=key,value=value), self.assertRaises(ValueError): check_graph(g)

    def test_hyphenated_unicode_names_are_supported(self):
        nodes=[{'display_name':'Cross-Language Checks','display_name_ru':'Сверка языков'}]
        validate_display_names(nodes)

    def test_arbitrary_fields_still_refused(self):
        for key in ('display_name_zh','display_names','alias','unexpected'):
            g=fixture();g['nodes'][0][key]='Anything'
            with self.subTest(key=key), self.assertRaises(ValueError): check_graph(g)

    def test_execution_fields_still_refused(self):
        for key in ('status','state','progress','completed','eta'):
            g=fixture();g['nodes'][0][key]='done'
            with self.subTest(key=key), self.assertRaises(ValueError): check_graph(g)

    def test_top_level_extra_and_dates_still_refused(self):
        for key,value in [('state','done'),('unexpected',True),('target_dates','tomorrow')]:
            g=fixture();g[key]=value
            with self.subTest(key=key), self.assertRaises(ValueError): check_graph(g)

    def test_cycle_dangling_duplicate_and_missing_still_refused(self):
        for mutation in ('cycle','dangling','duplicate','missing'):
            g=fixture()
            if mutation=='cycle':g['nodes'][0]['requires']=['RM-25']
            if mutation=='dangling':g['nodes'][0]['requires']=['RM-99']
            if mutation=='duplicate':g['nodes'][0]['requires']=['RM-02','RM-02']
            if mutation=='missing':g['nodes'].pop()
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):check_graph(g)

    def test_owner_and_priority_gates_remain(self):
        for key,value in [('content_owner',''),('priority','done'),('requires','none')]:
            g=fixture();g['nodes'][0][key]=value
            with self.subTest(key=key), self.assertRaises(ValueError):check_graph(g)

    def test_named_card_and_node_agree(self):
        check_card_display_name({'title':'Claim Atlas: Exact claims'},
                                {'id':'RM-01','display_name':'Claim Atlas'})

    def test_named_card_and_node_mismatch_refused(self):
        for title in ('Different Name: Exact claims','Claim Atlas','Claim Atlas: '):
            with self.subTest(title=title),self.assertRaises(ValueError):
                check_card_display_name({'title':title},{'id':'RM-01','display_name':'Claim Atlas'})

    def test_legacy_card_title_not_reinterpreted(self):
        check_card_display_name({'title':'Original old title'},{'id':'RM-01'})


if __name__ == '__main__':
    unittest.main()
