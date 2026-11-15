#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Synthetic source-binding and refusal controls, not translation review."""
import copy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from catalogue_localization import compile_localization, compile_article_localizations, FILENAME


class CatalogueLocalizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.source = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.documents = []
        for slug in ("alpha", "beta"):
            path = "papers/" + slug + "/PAPER.md"
            file = self.source / path
            file.parent.mkdir(parents=True)
            file.write_text("# Synthetic " + slug + "\n\nDeclared synthetic input.\n")
            self.documents.append({"slug": slug, "path": path, "title": slug,
                                   "summary": "Synthetic source metadata", "sha256": sha256(file.read_bytes()).hexdigest()})
        self.catalog = self.source / "publication-catalog.json"
        self.catalog.write_text(json.dumps({"documents": self.documents}) + "\n")
        self.git("add", ".")
        self.git("commit", "-qm", "Synthetic source")
        self.revision = self.git("rev-parse", "HEAD").strip()
        self.manifest = {"commit": self.revision, "catalog": "publication-catalog.json"}
        entries = []
        for doc in self.documents:
            for language, title, summary in (("ru", "Синтетический пример", "Описание синтетического примера."),
                                              ("zh-Hans", "合成示例", "合成示例的说明。")):
                entries.append({"work": doc["slug"], "language": language, "source_path": doc["path"],
                                "source_sha256": doc["sha256"], "title": title, "summary": summary, "status": "unreviewed"})
        self.data = {"schema_version": 1, "kind": "arcanada-publication-localization",
                     "source": {"catalog": self.catalog.name, "revision": self.revision,
                                "sha256": sha256(self.catalog.read_bytes()).hexdigest()}, "entries": entries}

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.source), *args], text=True, stderr=subprocess.DEVNULL)

    def compile(self, data=None):
        (self.source / FILENAME).write_text(json.dumps(self.data if data is None else data, ensure_ascii=False))
        return compile_localization(self.source, self.manifest, self.documents)

    def test_complete_multiwork_positive_and_harmless_metadata_change(self):
        result = self.compile()
        self.assertEqual(set(result["records"]), {"alpha", "beta"})
        self.assertEqual(len(result["provenance"]["entries"]), 4)
        self.assertEqual(result["records"]["alpha"]["ru"]["status"], "unreviewed")
        changed = copy.deepcopy(self.data)
        changed["entries"][0]["title"] = "Другой синтетический заголовок"
        self.assertEqual(self.compile(changed)["records"]["alpha"]["ru"]["title"], changed["entries"][0]["title"])

    def test_absent_file_preserves_legacy_compiler_behavior(self):
        self.assertIsNone(compile_localization(self.source, self.manifest, self.documents))

    def test_inventory_and_closed_schema_refusals(self):
        cases = []
        d = copy.deepcopy(self.data); d["entries"].pop(); cases.append(d)
        d = copy.deepcopy(self.data); d["entries"].append(copy.deepcopy(d["entries"][0])); cases.append(d)
        d = copy.deepcopy(self.data); d["entries"][0]["work"] = "not-published"; cases.append(d)
        d = copy.deepcopy(self.data); d["entries"][0]["reviewed"] = True; cases.append(d)
        d = copy.deepcopy(self.data); d["schema_version"] = True; cases.append(d)
        for data in cases:
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, "LOCALIZATION_INVALID"):
                self.compile(data)

    def test_wrong_source_and_fabricated_review_refused(self):
        for key, value in (("source_path", "papers/beta/PAPER.md"), ("source_sha256", "0" * 64),
                           ("status", "reviewed"), ("language", "en")):
            data = copy.deepcopy(self.data); data["entries"][0][key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "LOCALIZATION_INVALID"):
                self.compile(data)

    def test_actual_source_change_refused(self):
        (self.source / self.documents[0]["path"]).write_text("Changed source, same metadata.\n")
        with self.assertRaisesRegex(ValueError, "source bytes are stale"):
            self.compile()

    def test_catalogue_change_refused(self):
        self.catalog.write_text(self.catalog.read_text() + " ")
        with self.assertRaisesRegex(ValueError, "stale for the current catalogue"):
            self.compile()

    def test_nonancestor_pin_with_identical_tree_refused(self):
        tree = self.git("rev-parse", "HEAD^{tree}").strip()
        unrelated = subprocess.check_output(["git", "-C", str(self.source), "commit-tree", tree],
                                            input="Unrelated synthetic commit\n", text=True).strip()
        data = copy.deepcopy(self.data); data["source"]["revision"] = unrelated
        with self.assertRaisesRegex(ValueError, "source revision/ancestry"):
            self.compile(data)

    def test_plain_text_language_and_duplicate_json_key_refusals(self):
        for value in ("<script>alert(1)</script>", "English only title", "Первая\nВторая", None):
            data = copy.deepcopy(self.data); data["entries"][0]["title"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "LOCALIZATION_INVALID"):
                self.compile(data)
        raw = json.dumps(self.data).replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1', 1)
        (self.source / FILENAME).write_text(raw)
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            compile_localization(self.source, self.manifest, self.documents)


class ArticleLocalizationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.site = Path(self.tmp.name)
        self.file = self.site / "src/content/article-localizations.json"
        self.file.parent.mkdir(parents=True)
        self.originals = [{"id": key, "title": "Synthetic title", "status": "Historical status",
                           "abstract": "Synthetic retained excerpt.", "description": "Synthetic description"}
                          for key in ("first", "second")]
        self.data = {"schema_version": 1, "kind": "arcanada-article-localizations", "articles": []}
        for original in self.originals:
            digest = sha256(json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            translations = {
                "ru": {"title": "Синтетический текст", "description": "Описание примера", "status": "Исторический статус\n\nБез новой рецензии", "abstract": "Первый абзац.\n\nВторой абзац."},
                "zh-Hans": {"title": "合成文本", "description": "示例说明", "status": "历史状态\n\n没有新的审查", "abstract": "第一段。\n\n第二段。"},
            }
            self.data["articles"].append({"id": original["id"], "source_sha256": digest, "translations": translations})

    def compile(self, data=None, originals=None):
        self.file.write_text(json.dumps(self.data if data is None else data, ensure_ascii=False))
        return compile_article_localizations(self.site, self.originals if originals is None else originals)

    def test_complete_positive_and_repeated_build(self):
        records, provenance = self.compile()
        self.assertEqual(len(records), 2)
        self.assertEqual(len(provenance["articles"]), 2)
        self.assertEqual(records[0]["translations"]["ru"]["abstract"], "Первый абзац.\n\nВторой абзац.")
        again, second = self.compile(originals=records)
        self.assertEqual(records, again)
        self.assertEqual(provenance, second)
        self.assertNotIn("translations", self.originals[0])

    def test_absence_does_not_retain_unbound_cached_translation(self):
        original = dict(self.originals[0], translations={"ru": {"title": "Unbound cached value"}})
        result, provenance = compile_article_localizations(self.site, [original])
        self.assertEqual(result, [self.originals[0]])
        self.assertIsNone(provenance)

    def test_changed_english_original_refused(self):
        changed = copy.deepcopy(self.originals); changed[0]["abstract"] += " New conclusion."
        with self.assertRaisesRegex(ValueError, "article source record is stale"):
            self.compile(originals=changed)

    def test_article_inventory_and_closed_shape_refusals(self):
        cases = []
        d = copy.deepcopy(self.data); d["articles"].pop(); cases.append(d)
        d = copy.deepcopy(self.data); d["articles"].append(copy.deepcopy(d["articles"][0])); cases.append(d)
        d = copy.deepcopy(self.data); d["articles"][0]["translations"].pop("zh-Hans"); cases.append(d)
        d = copy.deepcopy(self.data); d["articles"][0]["translations"]["ru"]["reviewed"] = True; cases.append(d)
        for data in cases:
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, "LOCALIZATION_INVALID"):
                self.compile(data)

    def test_empty_unsafe_or_wrong_language_excerpt_refused(self):
        for field, value in (("abstract", ""), ("status", "<script>bad</script>"),
                              ("abstract", "English text only"), ("description", "Две\nстроки")):
            data = copy.deepcopy(self.data); data["articles"][0]["translations"]["ru"][field] = value
            with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, "LOCALIZATION_INVALID"):
                self.compile(data)


if __name__ == "__main__":
    unittest.main()
