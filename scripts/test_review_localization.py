#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Committed source bindings and presentation controls; no semantic review."""
import copy
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from check_localization import Audit, Document
from review_localization import FILENAME, FIELDS, REPOSITORY, ReviewLocalizations, original_fields, review_digest
from test_renditions import Scenario, BETA, EN_BETA, REVIEW_OK, commit

TRANSLATED = {
    "ru": {
        "independence_basis": "Синтетическая отдельная тестовая идентичность; реальной независимой рецензии не было.",
        "method": "Синтетическая проверка тестовых записей; научные результаты не проверялись.",
        "limitations": "Только синтетические данные; нет новой рецензии или подтверждения научной истинности.",
    },
    "zh-Hans": {
        "independence_basis": "合成的独立测试身份；没有进行真实的独立审查。",
        "method": "合成测试记录检查；未验证科学结果。",
        "limitations": "仅合成数据；没有新增审查或科学真实性认证。",
    },
}


def review_html(projection, original, compiled_review):
    locale = projection["language"]
    fields = "".join('<dd data-review-localization-field="' + key + '" lang="' + locale + '">'
                     + escape(projection["fields"][key]) + "</dd>" for key in FIELDS)
    values = original_fields(original)
    originals = "".join('<dd data-review-original-field="' + key + '" lang="en">'
                        + escape(values[key]) + "</dd>" for key in FIELDS)
    facts = {"review": compiled_review,
             "review_localization": {key: projection[key] for key in ("review_state", "language", "source")}}
    return ('<section lang="' + locale + '"><dl>' + fields + '</dl>'
            '<p data-review-localization-state="unreviewed" lang="' + locale + '">'
            + ("Перевод пояснений без новой рецензии." if locale == "ru" else "说明译文不构成新增审查。") + "</p>"
            '<details data-review-original="true" lang="en"><summary lang="' + locale + '">Original</summary><dl>'
            + originals + "</dl></details>"
            '<script type="application/json" class="rendition-facts">' + json.dumps(facts, ensure_ascii=False).replace("<", "\\u003c")
            + "</script></section>")


class ReviewLocalizationControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Keep beta's source current so all three synthetic review receipts are
        # active; the marker makes the scenario's third commit nonempty.
        self.sc = Scenario(self.root, review_zh=REVIEW_OK,
                           after_renditions={BETA: EN_BETA, "fixture-marker.txt": "Synthetic fixture marker\n"})
        self.source = self.sc.source
        self.documents = self.sc.catalog["documents"]
        self.revision = self.sc.manifest["commit"]
        self.sidecar_bytes = (self.source / "publication-renditions.json").read_bytes()
        self.originals = {(entry["work"], entry["language"]): copy.deepcopy(entry["review"])
                          for entry in self.sc.sidecar["renditions"] if entry.get("review")}
        self.data = {
            "schema_version": 1, "repository": REPOSITORY,
            "source_revision": self.revision, "source_path": "publication-renditions.json",
            "source_sha256": sha256(self.sidecar_bytes).hexdigest(), "review_state": "unreviewed",
            "entries": [{"work": work, "language": language, "review_sha256": review_digest(review),
                         "fields": copy.deepcopy(TRANSLATED[language])}
                        for (work, language), review in self.originals.items()],
        }
        self.write_descriptor(self.data)
        self.layer = self.load()

    def save(self, files):
        self.sc.manifest["commit"] = commit(self.source, files, "Synthetic review presentation change")
        self.sc.manifest_path.write_text(json.dumps(self.sc.manifest))
        status = subprocess.check_output(["git", "-C", str(self.source), "status", "--porcelain"], text=True)
        self.assertEqual(status, "")

    def write_descriptor(self, data):
        self.save({FILENAME: json.dumps(data, ensure_ascii=False, indent=2) + "\n"})

    def load(self):
        return ReviewLocalizations(self.source, self.sc.manifest, self.documents)

    def compiled_review(self, original):
        result = copy.deepcopy(original)
        result["author"] = "test-fixture-author"
        result["evidence"]["url"] = "https://example.invalid/exact-fixture-evidence"
        return result

    def test_complete_locale_inventory_is_bound_and_separate_from_unchanged_review(self):
        before = copy.deepcopy(self.originals)
        self.layer.validate_inventory(set(self.originals))
        self.assertEqual(len(self.layer.provenance()["entries"]), 3)
        for (work, language), original in self.originals.items():
            projection = self.layer.for_review(work, language, original)
            self.assertEqual(projection["fields"], TRANSLATED[language])
            self.assertEqual(projection["review_state"], "unreviewed")
            self.assertEqual(projection["source"]["review_sha256"], review_digest(original))
            self.assertEqual(projection["source"]["sidecar_revision"], self.revision)
            self.assertEqual(projection["source"]["revision"], self.sc.manifest["commit"])
        self.assertEqual(before, self.originals)
        self.assertEqual((self.source / "publication-renditions.json").read_bytes(), self.sidecar_bytes)

    def test_actual_rendition_compiler_adds_presentation_without_changing_review_or_body(self):
        _, _, _, compiled = self.sc.compile()
        for (work, language), original in self.originals.items():
            record = compiled.for_work(work)[language]
            self.assertEqual(record["state"], "reviewed")
            self.assertEqual(record["review_localization"], self.layer.for_review(work, language, original))
            actual = copy.deepcopy(record["review"])
            actual.pop("author")
            actual["evidence"].pop("url")
            self.assertEqual(actual, original)
            path = self.source / record["rendition"]["path"]
            self.assertEqual(sha256(path.read_bytes()).hexdigest(), record["rendition"]["sha256"])
        self.assertEqual((self.source / "publication-renditions.json").read_bytes(), self.sidecar_bytes)
        self.assertNotIn("review_localization", compiled.for_work("synthetic-beta")["zh-Hans"])

    def test_legacy_absence_keeps_original_review_without_inventing_localized_fields(self):
        (self.source / FILENAME).unlink()
        self.save({"fixture-marker.txt": "Descriptor absent in this synthetic legacy revision\n"})
        layer = self.load()
        self.assertIsNone(layer.provenance())
        layer.validate_inventory(set(self.originals))
        _, _, _, compiled = self.sc.compile()
        for work, language in self.originals:
            self.assertIsNone(layer.for_review(work, language))
            self.assertNotIn("review_localization", compiled.for_work(work)[language])
            self.assertEqual(compiled.for_work(work)[language]["state"], "reviewed")

    def test_complete_reader_audit_refuses_descriptor_removal_at_a_new_source_commit(self):
        from test_localization import ReaderControls
        # This is a new committed release, not dirty bytes at the old pin.
        previous = self.sc.manifest["commit"]
        (self.source / FILENAME).unlink()
        self.save({"fixture-marker.txt": "Repinned source without localized review explanations\n"})
        self.assertNotEqual(previous, self.sc.manifest["commit"])
        _, _, _, compiled = self.sc.compile()  # Legacy compilation is allowed.
        legacy = compiled.for_work("synthetic-alpha")["ru"]
        self.assertEqual(legacy["state"], "reviewed")
        self.assertNotIn("review_localization", legacy)
        self.assertIsNone(self.load().provenance())
        # Reuse the complete six-page HTML fixture. Its baseline passes before
        # adding the actual legacy compiler's untranslated review payload.
        surface = ReaderControls("test_positive_multiple_works_and_mixed_review_states")
        surface.setUp()
        self.addCleanup(surface.doCleanups)
        self.assertEqual(surface.audit().errors, [])
        surface.catalog["records"][0]["renditions"]["ru"]["review"] = copy.deepcopy(legacy["review"])
        file = surface.files["alpha", "ru"]
        prose = "<section lang=\"en\">" + "".join("<p>" + escape(value) + "</p>"
                                                  for value in original_fields(legacy["review"]).values()) + "</section>"
        file.write_text(file.read_text().replace("</main>", prose + "</main>"))
        result = surface.audit()
        self.assertEqual({error["code"] for error in result.errors}, {"REVIEW_LOCALIZATION_MISSING"})

    def test_missing_duplicate_unknown_entries_and_fields_are_refused(self):
        cases = []
        data = copy.deepcopy(self.data); data["entries"].pop(); cases.append((data, "COVERAGE"))
        data = copy.deepcopy(self.data); data["entries"].append(copy.deepcopy(data["entries"][0])); cases.append((data, "COVERAGE"))
        data = copy.deepcopy(self.data); data["entries"][0]["work"] = "unknown-work"; cases.append((data, "COVERAGE"))
        data = copy.deepcopy(self.data); del data["entries"][0]["fields"]["limitations"]; cases.append((data, "SCHEMA"))
        data = copy.deepcopy(self.data); data["entries"][0]["fields"]["scope"] = "full"; cases.append((data, "SCHEMA"))
        for data, code in cases:
            with self.subTest(code=code):
                self.write_descriptor(data)
                with self.assertRaisesRegex(ValueError, "REVIEW_LOCALIZATION_" + code):
                    self.load()

    def test_review_identity_and_whole_json_binding_cannot_be_retargeted(self):
        data = copy.deepcopy(self.data); data["entries"][0]["review_sha256"] = "0" * 64
        self.write_descriptor(data)
        with self.assertRaisesRegex(ValueError, "BINDING.*review JSON"):
            self.load()
        (work, language), original = next(iter(self.originals.items()))
        changed = copy.deepcopy(original)
        changed["reviewer"]["identity"] = "Different synthetic reviewer"
        with self.assertRaisesRegex(ValueError, "BINDING.*between validation"):
            self.layer.for_review(work, language, changed)

    def test_sidecar_change_is_refused_even_with_refreshed_outer_pin(self):
        sidecar = json.loads(self.sidecar_bytes)
        sidecar["renditions"][0]["review"]["limitations"] += " Changed scope."
        self.save({"publication-renditions.json": json.dumps(sidecar)})
        with self.assertRaisesRegex(ValueError, "BINDING.*sidecar"):
            self.load()

    def test_refreshed_sidecar_binding_still_requires_exact_original_review_hash(self):
        sidecar = json.loads(self.sidecar_bytes)
        sidecar["renditions"][0]["review"]["reviewer"]["identity"] = "Different synthetic reviewer"
        self.save({"publication-renditions.json": json.dumps(sidecar)})
        data = copy.deepcopy(self.data)
        data["source_revision"] = self.sc.manifest["commit"]
        data["source_sha256"] = sha256((self.source / "publication-renditions.json").read_bytes()).hexdigest()
        self.write_descriptor(data)
        with self.assertRaisesRegex(ValueError, "BINDING.*review JSON"):
            self.load()

    def test_unrelated_history_and_wrong_authority_path_are_refused(self):
        tree = subprocess.check_output(["git", "-C", str(self.source), "rev-parse", "HEAD^{tree}"], text=True).strip()
        unrelated = subprocess.check_output(["git", "-C", str(self.source), "-c", "user.name=Synthetic",
                                            "-c", "user.email=fixture@example.invalid", "commit-tree", tree],
                                           input="Unrelated review history\n", text=True).strip()
        data = copy.deepcopy(self.data); data["source_revision"] = unrelated
        self.write_descriptor(data)
        with self.assertRaisesRegex(ValueError, "BINDING.*ancestry"):
            self.load()
        data = copy.deepcopy(self.data); data["source_path"] = "another-sidecar.json"
        self.write_descriptor(data)
        with self.assertRaisesRegex(ValueError, "BINDING.*catalogue-declared"):
            self.load()

    def test_closed_schema_wrong_locale_plain_text_and_review_promotion_refused(self):
        cases = []
        data = copy.deepcopy(self.data); data["schema_version"] = True; cases.append(data)
        data = copy.deepcopy(self.data); data["review_state"] = "reviewed"; cases.append(data)
        data = copy.deepcopy(self.data); data["entries"][0]["reviewer"] = "invented"; cases.append(data)
        data = copy.deepcopy(self.data); data["entries"][0]["language"] = "en"; cases.append(data)
        for value in ("English instead of localized prose", "<b>Новая рецензия</b>", "", None):
            data = copy.deepcopy(self.data); data["entries"][0]["fields"]["method"] = value; cases.append(data)
        for data in cases:
            with self.subTest(data=data):
                self.write_descriptor(data)
                with self.assertRaisesRegex(ValueError, "REVIEW_LOCALIZATION_(SCHEMA|LANGUAGE)"):
                    self.load()

    def test_active_inventory_rejects_lost_review_and_unearned_addition(self):
        active = set(self.originals)
        with self.assertRaisesRegex(ValueError, "COVERAGE.*currently verified"):
            self.layer.validate_inventory(active - {next(iter(active))})
        with self.assertRaisesRegex(ValueError, "COVERAGE.*currently verified"):
            self.layer.validate_inventory(active | {("synthetic-beta", "zh-Hans")})

    def test_missing_dirty_or_duplicate_key_descriptor_cannot_disable_binding(self):
        file = self.source / FILENAME
        raw = file.read_text()
        file.unlink()
        with self.assertRaisesRegex(ValueError, "BINDING.*missing"):
            self.load()
        file.write_text(raw + " ")
        with self.assertRaisesRegex(ValueError, "BINDING.*publication commit"):
            self.load()
        duplicate = raw.replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1')
        self.save({FILENAME: duplicate})
        with self.assertRaisesRegex(ValueError, "SCHEMA.*duplicate JSON"):
            self.load()

    def test_source_bound_new_wording_has_new_digest_and_no_authority_promotion(self):
        before = self.layer.provenance()
        data = copy.deepcopy(self.data)
        data["entries"][0]["fields"]["method"] = "Другой синтетический перевод метода; новой рецензии не было."
        self.write_descriptor(data)
        layer = self.load()
        self.assertNotEqual(before["source"]["sha256"], layer.provenance()["source"]["sha256"])
        self.assertEqual(layer.provenance()["review_state"], "unreviewed")
        self.assertEqual(layer.originals, self.originals)
        self.assertEqual(layer.for_review(data["entries"][0]["work"], data["entries"][0]["language"])["fields"]["method"],
                         data["entries"][0]["fields"]["method"])

    def test_actual_dom_requires_translations_separate_status_and_verbatim_originals(self):
        for (work, language), original in self.originals.items():
            projection = self.layer.for_review(work, language, original)
            rendition = {"review": self.compiled_review(original), "review_localization": projection}
            html = review_html(projection, original, rendition["review"])
            audit = Audit(self.root / "public")
            audit.review_prose(Document(html).root, rendition, projection, original, language, work)
            self.assertEqual(audit.errors, [])
            mutants = [
                (html.replace(escape(projection["fields"]["limitations"]), "Omitted exception", 1), "REVIEW_FIELD_TEXT"),
                (html.replace('data-review-localization-field="method"', 'data-review-localization-field="extra"', 1), "REVIEW_FIELDS"),
                (html.replace('data-review-localization-field="method"', 'hidden data-review-localization-field="method"', 1), "REVIEW_FIELD_TEXT"),
                (html.replace('data-review-localization-state="unreviewed"', 'data-review-localization-state="reviewed"', 1), "REVIEW_PRESENTATION_STATE"),
                (html.replace('<details data-review-original', '<details open data-review-original', 1), "REVIEW_ORIGINAL_VIEW"),
                (html.replace(escape(original["method"]), "Changed original", 1), "REVIEW_ORIGINAL_TEXT"),
                (html.replace('"review_state": "unreviewed"', '"review_state": "reviewed"', 1), "REVIEW_FACTS"),
                (html.replace('"review_sha256": "' + projection["source"]["review_sha256"] + '"',
                              '"review_sha256": "' + "0" * 64 + '"', 1), "REVIEW_FACTS"),
            ]
            for changed, expected_code in mutants:
                with self.subTest(language=language, expected=expected_code):
                    self.assertNotEqual(changed, html)
                    audit = Audit(self.root / "public")
                    audit.review_prose(Document(changed).root, rendition, projection, original, language, work)
                    self.assertIn(expected_code, {error["code"] for error in audit.errors})
            changed = copy.deepcopy(rendition)
            changed["review"]["reviewer"]["identity"] = "Invented reviewer"
            audit = Audit(self.root / "public")
            audit.review_prose(Document(html).root, changed, projection, original, language, work)
            self.assertIn("REVIEW_ORIGINAL", {error["code"] for error in audit.errors})


if __name__ == "__main__":
    unittest.main()
