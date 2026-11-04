#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Offline integration checks for renderer and snapshot boundaries."""
import json
from pathlib import Path
import tempfile
import unittest
from build_publication import Renderer, load_inputs, run, csp_table_classes


class PublicationBuild(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.doc = {"type": "paper", "slug": "example", "title": "Example", "path": "papers/example/PAPER.md"}
        self.target = {"type": "specification", "slug": "constraints", "title": "Constraints", "path": "engineering/specifications/constraints/SPECIFICATION.md"}
        for record, content in [(self.doc, '# Example\n\n## A claim\n\nAn inline formula $x^2 + y^2 = z^2$.\n\n| Input | Output |\n|---|---|\n| a | b |\n\nRead the [constraints](../../engineering/specifications/constraints/SPECIFICATION.md#rules).\n\nA footnote.[^basis]\n\n[^basis]: Explicit basis.\n'), (self.target, '# Constraints\n\n## Rules\n\nRequirements.\n')]:
            path = self.source / record["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        catalog = {"schema_version": 1, "edition": "1.0", "documents": [self.doc, self.target]}
        (self.source / "publication-catalog.json").write_text(json.dumps(catalog))
        run(["git", "init", "--quiet"], cwd=self.source)
        run(["git", "add", "."], cwd=self.source)
        run(["git", "-c", "user.name=Publication build test", "-c", "user.email=build@example.invalid", "commit", "--quiet", "-m", "Test fixture"], cwd=self.source)
        self.manifest = {"schema_version": 1, "edition": "1.0", "repository": "Arcanada-one/knowledge-contract", "commit": run(["git", "rev-parse", "HEAD"], cwd=self.source).strip(), "catalog": "publication-catalog.json"}
        self.manifest_path = self.root / "manifest.json"
        self.manifest_path.write_text(json.dumps(self.manifest))

    def tearDown(self):
        self.temp.cleanup()

    def test_actual_markdown_tables_math_links_and_footnotes(self):
        manifest, documents = load_inputs(self.source, self.manifest_path)
        renderer = Renderer(self.source, self.root / "public", manifest, documents)
        result = renderer.document(documents[0])
        html = result['html']
        self.assertIn("<table>", html)
        self.assertIn("<math", html)
        self.assertIn('<a href="/en/engineering/specifications/constraints/#rules">constraints</a>', html)
        self.assertIn("Explicit basis.", html)
        self.assertIn('id="a-claim"', html)
        self.assertNotIn("$x^2", html)
        self.assertEqual(result['math_count'], 1)
        self.assertEqual(result['toc'][0]['id'], 'a-claim')

    def test_executable_markdown_and_remote_embeds_rejected(self):
        manifest, documents = load_inputs(self.source, self.manifest_path)
        renderer = Renderer(self.source, self.root / 'public', manifest, documents)
        for target in ('javascript:alert(1)', 'data:text/html,test'):
            with self.assertRaises(ValueError):
                renderer.resolve_link(target, documents[0])
        with self.assertRaisesRegex(ValueError, 'Remote image'):
            renderer.resolve_link('https://example.org/remote.png', documents[0], image=True)
        with self.assertRaisesRegex(ValueError, 'Executable raw HTML'):
            renderer.transform({'t':'RawBlock','c':['html','<script>alert(1)</script>']}, documents[0])

    def test_wrong_pin_rejected(self):
        self.manifest["commit"] = "f" * 40
        self.manifest_path.write_text(json.dumps(self.manifest))
        with self.assertRaisesRegex(ValueError, "differs from manifest"):
            load_inputs(self.source, self.manifest_path)

    def test_dirty_source_rejected(self):
        (self.source / self.doc["path"]).write_text("Changed text")
        with self.assertRaisesRegex(ValueError, "uncommitted changes"):
            load_inputs(self.source, self.manifest_path)

    def test_missing_or_escaping_link_rejected(self):
        manifest, documents = load_inputs(self.source, self.manifest_path)
        renderer = Renderer(self.source, self.root / "public", manifest, documents)
        for target in ("missing.md", "../../../../outside.md"):
            with self.assertRaises(ValueError):
                renderer.resolve_link(target, documents[0])

    def test_table_presentation_preserves_csp_and_alignment(self):
        source = '<col style="width: 25%" /><th style="text-align: right;">Count</th>'
        rendered = csp_table_classes(source)
        self.assertNotIn('style=', rendered)
        self.assertIn('class="table-width-25"', rendered)
        self.assertIn('class="table-align-right"', rendered)
        with self.assertRaises(ValueError):
            csp_table_classes('<td style="background:url(https://example.org/track)">Text</td>')


if __name__ == "__main__":
    unittest.main()
