#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Offline integration checks for renderer and snapshot boundaries."""
import json
from pathlib import Path
import tempfile
import unittest
import shutil
from build_publication import Renderer, load_inputs, run, csp_table_classes
from publication_checks import check_status_labels, STATUS_LABELS, LOCALES

ROOT = Path(__file__).resolve().parents[1]


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




class CatalogueStatusLabels(unittest.TestCase):
    """A document with a catalogue status (research-draft) must be labelled on every page that shows it."""

    @classmethod
    def setUpClass(cls):
        cls.records = json.loads((ROOT / "src/content/catalog.json").read_text())["records"]
        cls.drafts = [r for r in cls.records if r.get("status") == "research-draft"]
        if not cls.drafts:
            raise unittest.SkipTest("no research-draft document in the pinned catalogue")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.out = Path(self.temp.name)
        for locale in LOCALES:
            shutil.copytree(ROOT / "public" / locale, self.out / locale)
        self.record = self.drafts[0]

    def tearDown(self):
        self.temp.cleanup()

    def page(self, locale, route):
        return self.out / route.replace("/en/", f"/{locale}/", 1).strip("/") / "index.html"

    def strip(self, path):
        text = path.read_text(encoding="utf-8")
        for label in STATUS_LABELS["research-draft"].values():
            text = text.replace(f'<span class="status-badge">{label}</span>', "")
        path.write_text(text, encoding="utf-8")

    def test_control_built_site_is_labelled_everywhere_in_three_languages(self):
        self.assertGreaterEqual(check_status_labels(self.out, self.records), 3 * 3)

    def test_unlabelled_reading_page_fails_in_every_language(self):
        for locale in LOCALES:
            with self.subTest(locale=locale):
                self.strip(self.page(locale, self.record["route"]))
                with self.assertRaisesRegex(ValueError, "without the label"):
                    check_status_labels(self.out, self.records)
                shutil.copytree(ROOT / "public" / locale, self.out / locale, dirs_exist_ok=True)

    def test_missing_draft_notice_fails(self):
        path = self.page("en", self.record["route"])
        path.write_text(path.read_text(encoding="utf-8").replace('class="draft-notice"', 'class="other"'), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "no draft notice"):
            check_status_labels(self.out, self.records)

    def test_zh_hans_notice_lead_ends_with_chinese_full_stop(self):
        zh = self.page("zh-Hans", self.record["route"])
        text = zh.read_text(encoding="utf-8")
        self.assertIn("<strong>研究草稿。</strong>", text)  # control: the built page
        self.assertNotIn("研究草稿.", text)
        check_status_labels(self.out, self.records)
        zh.write_text(text.replace("<strong>研究草稿。</strong>", "<strong>研究草稿.</strong>"), encoding="utf-8")  # negative control
        with self.assertRaisesRegex(ValueError, "Chinese full stop"):
            check_status_labels(self.out, self.records)
        en = self.page("en", self.record["route"])
        self.assertIn("<strong>Research draft.</strong> ", en.read_text(encoding="utf-8"))  # en/ru keep the ASCII stop

    def test_unlabelled_listing_fails(self):
        self.strip(self.out / "en/research/index.html")
        with self.assertRaisesRegex(ValueError, "research/index.html: shows"):
            check_status_labels(self.out, self.records)

    def test_label_on_a_page_that_does_not_show_the_document_fails(self):
        about = self.out / "en/about/index.html"
        text = about.read_text(encoding="utf-8")
        about.write_text(text.replace("<main", '<span class="status-badge">Research draft</span><main', 1), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "shows no such document"):
            check_status_labels(self.out, self.records)

    def test_status_without_public_label_fails(self):
        records = [dict(self.record, status="accepted-ish")]
        with self.assertRaisesRegex(ValueError, "without a public label"):
            check_status_labels(self.out, records)

    def test_unknown_catalogue_status_stops_the_build(self):
        case = PublicationBuild("test_wrong_pin_rejected")
        case.setUp()
        try:
            case.doc["status"] = "accepted-ish"
            (case.source / "publication-catalog.json").write_text(json.dumps({"schema_version": 1, "edition": "1.0", "documents": [case.doc, case.target]}))
            run(["git", "add", "."], cwd=case.source)
            run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "--quiet", "-m", "status"], cwd=case.source)
            case.manifest["commit"] = run(["git", "rev-parse", "HEAD"], cwd=case.source).strip()
            case.manifest_path.write_text(json.dumps(case.manifest))
            with self.assertRaisesRegex(ValueError, "Unknown catalogue status"):
                load_inputs(case.source, case.manifest_path)
        finally:
            case.tearDown()


if __name__ == "__main__":
    unittest.main()
