#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Bounded formula-presentation controls with real committed synthetic inputs.

These tests check source binding, coverage and preservation, not the scientific
truth of the formulas or independent semantic review of the translations.
"""
import copy
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from xml.etree import ElementTree as ET

from build_publication import Renderer
from check_localization import Audit
from formula_localization import FILENAME, FormulaLocalizations, REPOSITORY

SOURCE_PATH = "papers/synthetic-formulas/PAPER.md"
OTHER_PATH = "papers/synthetic-untouched/PAPER.md"
LONG = "the two answer sets are not the same singleton"
RU_LONG = "два множества ответов не являются одним и тем же одноэлементным множеством"
ZH_LONG = "两个答案集合并非同一个单元素集合"
TEX = [
    ("InlineMath", "z^2+1"),
    ("DisplayMath", "\nf(x)=g(x)\\quad\\text{for every }x\\in X.\n"),
    ("DisplayMath", "\nA\\quad\\text{and}\\quad B\\quad\\text{equivalently}\\quad C.\n"),
    ("DisplayMath", "\nf(x)=g(x)\\quad\\text{for all }x\\in X.\n"),
    ("DisplayMath", "\nd(x,y)=0\\quad\\text{for }x,y\\in X.\n"),
    ("DisplayMath", "\nU(A,B)=\\mathbf 1[\\text{" + LONG + "}].\n"),
    ("InlineMath", "\\mathsf{unknown},\\mathsf{pass},\\operatorname{Admit}(x)"),
]
PHRASES = [
    (2, 1, "for every ", "для каждого ", "对于每个 "),
    (3, 1, "and", "и", "与"),
    (3, 2, "equivalently", "эквивалентно", "等价于"),
    (4, 1, "for all ", "для всех ", "对于任意 "),
    (5, 1, "for ", "для ", "对于 "),
    (6, 1, LONG, RU_LONG, ZH_LONG),
]
MARKDOWN = "# Synthetic formulas\n\n## Scope {#scope}\n\nSynthetic retained prose.\n\n"
MARKDOWN += "\n\n".join(("$" if kind == "InlineMath" else "$$") + tex
                        + ("$" if kind == "InlineMath" else "$$") for kind, tex in TEX) + "\n"
OTHER = "# Untouched synthetic source\n\n## Scope {#scope}\n\nKeep $x+y$ and $\\mathsf{unknown}$.\n"
NS = "{http://www.w3.org/1998/Math/MathML}"


def maths(html):
    return re.findall(r"<math\b[^>]*>.*?</math>", html, re.S)


def tree_without_mtext(xml):
    """Independent comparison which discards only mtext character data."""
    root = ET.fromstring(xml)

    def visit(node):
        return (node.tag, tuple(sorted(node.attrib.items())),
                None if node.tag == NS + "mtext" else node.text,
                node.tail, tuple(visit(child) for child in node))

    return visit(root)


def annotations(html):
    return re.findall(r'<annotation encoding="application/x-tex">.*?</annotation>', html, re.S)


class FormulaPresentationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic formula fixture")
        self.git("config", "user.email", "formula-fixture@example.invalid")
        self.documents = []
        for relative, text in ((SOURCE_PATH, MARKDOWN), (OTHER_PATH, OTHER)):
            path = self.source / relative
            path.parent.mkdir(parents=True)
            path.write_text(text)
            self.documents.append({"path": relative, "slug": relative.split("/")[1], "type": "paper",
                                   "route": "/en/science/" + relative.split("/")[1] + "/",
                                   "sha256": sha256(path.read_bytes()).hexdigest()})
        self.manifest = {"repository": REPOSITORY}
        self.commit()
        self.revision = self.manifest["commit"]
        entries = []
        for mi, ti, original, ru, zh in PHRASES:
            kind, tex = TEX[mi - 1]
            entries.append({"math_index": mi, "math_type": kind, "tex_sha256": sha256(tex.encode()).hexdigest(),
                            "mtext_index": ti, "source_text": original,
                            "translations": {"ru": ru, "zh-Hans": zh}})
        self.data = {"schema_version": 1, "repository": REPOSITORY, "source_revision": self.revision,
                     "review_state": "unreviewed", "documents": [{
                         "path": SOURCE_PATH, "source_sha256": self.documents[0]["sha256"], "annotations": entries}]}
        self.write_descriptor(self.data)
        renderer = Renderer(self.source, self.root / "output", self.manifest, self.documents)
        self.layer = renderer.formula_localizations
        self.html = renderer.document(self.documents[0])["html"]
        self.other_html = renderer.document(self.documents[1])["html"]

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.source), *args], text=True, stderr=subprocess.DEVNULL)

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "Synthetic formula fixture change", "--allow-empty")
        self.manifest["commit"] = self.git("rev-parse", "HEAD").strip()
        self.assertEqual(self.git("status", "--porcelain"), "")

    def write_descriptor(self, data):
        (self.source / FILENAME).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
        self.commit()

    def load(self):
        return FormulaLocalizations(self.source, self.manifest, self.documents)

    def test_both_locales_change_only_all_six_registered_mtext_phrases(self):
        for language in ("ru", "zh-Hans"):
            with self.subTest(language=language):
                result = self.layer.localize(SOURCE_PATH, language, self.html)
                self.assertNotEqual(result, self.html)
                self.assertEqual(len(maths(result)), 7)
                self.assertEqual(annotations(result), annotations(self.html))
                self.assertEqual([tree_without_mtext(x) for x in maths(result)],
                                 [tree_without_mtext(x) for x in maths(self.html)])
                expected = [entry["translations"][language] for entry in self.data["documents"][0]["annotations"]]
                actual = [node.text for xml in maths(result) for node in ET.fromstring(xml).iter(NS + "mtext")]
                self.assertEqual(actual, expected)
                self.assertEqual(self.layer.for_document(SOURCE_PATH, language)["review_state"], "unreviewed")
                self.assertEqual(self.layer.provenance()["source_revision"], self.revision)
                self.layer.validate_localized(SOURCE_PATH, language, result)

    def test_english_unaffected_formula_identifiers_and_outside_text_stay_exact(self):
        self.assertEqual(self.layer.localize(SOURCE_PATH, "en", self.html), self.html)
        for language in ("ru", "zh-Hans"):
            self.assertEqual(self.layer.localize(OTHER_PATH, language, self.other_html), self.other_html)
            outside = "<p>for every ordinary outside string</p>"
            result = self.layer.localize(SOURCE_PATH, language, outside + self.html + outside)
            self.assertTrue(result.startswith(outside) and result.endswith(outside))
            self.assertEqual(maths(result)[0], maths(self.html)[0])
            self.assertEqual(maths(result)[-1], maths(self.html)[-1])
            self.assertIn("\\mathsf{unknown}", annotations(result)[-1])

    def test_missing_descriptor_refuses_localized_mtext_but_keeps_legacy_en_and_no_mtext(self):
        (self.source / FILENAME).unlink()
        self.commit()
        layer = self.load()
        self.assertIsNone(layer.provenance())
        self.assertEqual(layer.localize(SOURCE_PATH, "en", self.html), self.html)
        self.assertEqual(layer.localize(OTHER_PATH, "ru", self.other_html), self.other_html)
        for language in ("ru", "zh-Hans"):
            with self.subTest(language=language), self.assertRaisesRegex(ValueError, "FORMULA_LOCALIZATION_COVERAGE"):
                layer.localize(SOURCE_PATH, language, self.html)

    def test_deleting_or_editing_pinned_descriptor_is_not_an_optional_fallback(self):
        file = self.source / FILENAME
        original = file.read_text()
        file.unlink()
        with self.assertRaisesRegex(ValueError, "BINDING.*missing"):
            self.load()
        file.write_text(original + " ")
        with self.assertRaisesRegex(ValueError, "BINDING.*publication commit"):
            self.load()

    def test_partial_duplicate_extra_and_wrong_location_bindings_refused(self):
        mutations = []
        data = copy.deepcopy(self.data); data["documents"][0]["annotations"].pop(); mutations.append((data, "COVERAGE"))
        data = copy.deepcopy(self.data); data["documents"][0]["annotations"].append(copy.deepcopy(data["documents"][0]["annotations"][0])); mutations.append((data, "SCHEMA"))
        for field, value in (("math_index", 99), ("mtext_index", 99), ("mtext_index", True),
                             ("math_index", -1), ("math_type", "InlineMath"), ("tex_sha256", "0" * 64),
                             ("source_text", "for all ")):
            data = copy.deepcopy(self.data); data["documents"][0]["annotations"][0][field] = value
            mutations.append((data, "BINDING"))
        for data, code in mutations:
            with self.subTest(code=code, data=data):
                self.write_descriptor(data)
                with self.assertRaisesRegex(ValueError, "FORMULA_LOCALIZATION_" + code):
                    self.load()

    def test_closed_schema_locale_script_and_boundary_space_controls(self):
        cases = []
        data = copy.deepcopy(self.data); data["schema_version"] = True; cases.append((data, "SCHEMA"))
        data = copy.deepcopy(self.data); data["review_state"] = "reviewed"; cases.append((data, "SCHEMA"))
        data = copy.deepcopy(self.data); data["documents"][0]["reviewer"] = "invented"; cases.append((data, "SCHEMA"))
        data = copy.deepcopy(self.data); del data["documents"][0]["annotations"][0]["translations"]["zh-Hans"]; cases.append((data, "SCHEMA"))
        for value, code in (("English only ", "LANGUAGE"), ("<script>bad</script>", "SCHEMA"),
                            ("для каждого", "STRUCTURE"), ("для\nкаждого ", "SCHEMA")):
            data = copy.deepcopy(self.data); data["documents"][0]["annotations"][0]["translations"]["ru"] = value
            cases.append((data, code))
        for data, code in cases:
            with self.subTest(code=code):
                self.write_descriptor(data)
                with self.assertRaisesRegex(ValueError, "FORMULA_LOCALIZATION_" + code):
                    self.load()
        with self.assertRaisesRegex(ValueError, "FORMULA_LOCALIZATION_LANGUAGE"):
            self.layer.localize(SOURCE_PATH, "zh", self.html)
        raw = json.dumps(self.data).replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1')
        (self.source / FILENAME).write_text(raw)
        self.commit()
        with self.assertRaisesRegex(ValueError, "SCHEMA.*duplicate JSON"):
            self.load()

    def test_current_source_changes_fail_after_refreshing_only_outer_commit(self):
        file = self.source / SOURCE_PATH
        file.write_text(file.read_text().replace("f(x)=g(x)", "f(x)=h(x)"))
        self.documents[0]["sha256"] = sha256(file.read_bytes()).hexdigest()
        self.commit()
        with self.assertRaisesRegex(ValueError, "BINDING.*stale"):
            self.load()

    def test_refreshed_source_binding_still_requires_exact_each_formula_digest(self):
        file = self.source / SOURCE_PATH
        file.write_text(file.read_text().replace("f(x)=g(x)", "f(x)=h(x)"))
        self.documents[0]["sha256"] = sha256(file.read_bytes()).hexdigest()
        self.commit()
        data = copy.deepcopy(self.data)
        data["source_revision"] = self.manifest["commit"]
        data["documents"][0]["source_sha256"] = self.documents[0]["sha256"]
        self.write_descriptor(data)
        with self.assertRaisesRegex(ValueError, "BINDING.*TeX"):
            self.load()

    def test_nonancestor_with_identical_tree_and_fabricated_history_refused(self):
        tree = self.git("rev-parse", "HEAD^{tree}").strip()
        unrelated = subprocess.check_output(["git", "-C", str(self.source), "commit-tree", tree],
                                            input="Unrelated synthetic history\n", text=True).strip()
        data = copy.deepcopy(self.data); data["source_revision"] = unrelated
        self.write_descriptor(data)
        with self.assertRaisesRegex(ValueError, "BINDING.*ancestry"):
            self.load()
        data = copy.deepcopy(self.data); data["documents"][0]["source_sha256"] = "0" * 64
        self.write_descriptor(data)
        with self.assertRaisesRegex(ValueError, "BINDING.*historical"):
            self.load()

    def test_new_published_document_with_mtext_cannot_evade_coverage(self):
        path = "papers/synthetic-new/PAPER.md"
        file = self.source / path
        file.parent.mkdir()
        file.write_text(MARKDOWN)
        self.documents.append({"path": path, "slug": "synthetic-new", "sha256": sha256(file.read_bytes()).hexdigest()})
        self.commit()
        layer = self.load()
        with self.assertRaisesRegex(ValueError, "FORMULA_LOCALIZATION_COVERAGE"):
            layer.localize(path, "ru", self.html)

    def test_changed_symbol_operator_tex_order_or_count_refused_in_actual_html(self):
        pieces = maths(self.html)
        mutations = [
            self.html.replace("<mi>f</mi>", "<mi>h</mi>", 1),
            self.html.replace("<mo>=</mo>", "<mo>≠</mo>", 1),
            self.html.replace("f(x)=g(x)", "f(x)=h(x)", 1),
            self.html.replace("f(x)=g(x)", "f(x)=&#103;(x)", 1),
            self.html.replace("<mi>f</mi>", "<mi>&#102;</mi>", 1),
            self.html.replace("<mi>f</mi>", "<mi><!--unexpected-->f</mi>", 1),
            self.html.replace(pieces[0], "", 1),
            self.html.replace(pieces[0], pieces[0] + pieces[0], 1),
            self.html.replace(pieces[1], pieces[2], 1),
        ]
        for changed in mutations:
            with self.subTest(changed=changed[:150]):
                self.assertNotEqual(changed, self.html)
                with self.assertRaisesRegex(ValueError, "FORMULA_LOCALIZATION_STRUCTURE"):
                    self.layer.localize(SOURCE_PATH, "ru", changed)
        localized = self.layer.localize(SOURCE_PATH, "ru", self.html)
        encoded = localized.replace("f(x)=g(x)", "f(x)=&#103;(x)", 1)
        self.assertNotEqual(encoded, localized)
        with self.assertRaisesRegex(ValueError, "FORMULA_LOCALIZATION_STRUCTURE"):
            self.layer.validate_localized(SOURCE_PATH, "ru", encoded)

    def test_long_predicate_negation_remains_exact_and_omission_is_rejected(self):
        # Preserves the supplied wording of not(same singleton); it does not
        # certify the author's translation via a synthetic truth-table claim.
        for language, expected, dropped in (("ru", RU_LONG, RU_LONG.replace("не являются", "являются")),
                                            ("zh-Hans", ZH_LONG, ZH_LONG.replace("并非", "是"))):
            with self.subTest(language=language):
                rendered = self.layer.localize(SOURCE_PATH, language, self.html)
                self.assertIn(expected, rendered)
                self.assertIn("\\text{" + LONG + "}", annotations(rendered)[5])
                mutant = rendered.replace(expected, dropped, 1)
                self.assertNotEqual(mutant, rendered)
                with self.assertRaisesRegex(ValueError, "FORMULA_LOCALIZATION_STRUCTURE"):
                    self.layer.validate_localized(SOURCE_PATH, language, mutant)

    def test_new_committed_presentation_text_has_new_provenance_without_changing_math(self):
        data = copy.deepcopy(self.data)
        data["documents"][0]["annotations"][1]["translations"]["zh-Hans"] = "且"
        old = self.layer.localize(SOURCE_PATH, "zh-Hans", self.html)
        self.write_descriptor(data)
        layer = self.load()
        new = layer.localize(SOURCE_PATH, "zh-Hans", self.html)
        self.assertNotEqual(old, new)
        self.assertNotEqual(layer.provenance()["sha256"], self.layer.provenance()["sha256"])
        self.assertEqual(annotations(new), annotations(old))
        self.assertEqual(layer.provenance()["review_state"], "unreviewed")

    def test_source_to_compiled_checker_applies_presentation_without_ignoring_math_or_body(self):
        compiled = self.layer.localize(SOURCE_PATH, "ru", self.html)
        audit = Audit(self.root / "public")
        audit.source_body(MARKDOWN, compiled, "synthetic/ru", formula_localizations=self.layer,
                          source_path=SOURCE_PATH, language="ru")
        self.assertEqual(audit.errors, [])
        wrong_math = compiled.replace("<mi>f</mi>", "<mi>h</mi>", 1)
        with self.assertRaisesRegex(ValueError, "FORMULA_LOCALIZATION_STRUCTURE"):
            audit.source_body(MARKDOWN, wrong_math, "synthetic/ru", formula_localizations=self.layer,
                              source_path=SOURCE_PATH, language="ru")
        omitted_body = compiled.replace("Synthetic retained prose.", "")
        self.assertNotEqual(omitted_body, compiled)
        audit.source_body(MARKDOWN, omitted_body, "synthetic/ru", formula_localizations=self.layer,
                          source_path=SOURCE_PATH, language="ru")
        self.assertEqual(audit.errors[-1]["code"], "SOURCE_BODY")


class RenditionIntegrationControls(unittest.TestCase):
    """Exercise the real parity/renderer entry point on committed renditions."""
    def scenario(self, *, changed_formula=False, reviewed=False, descriptor=True):
        from test_renditions import Scenario, ALPHA, EN_ALPHA, RU_ALPHA, ZH_ALPHA, REVIEW_OK, commit
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        tex = "\nU(A,B)=\\mathbf 1[\\text{" + LONG + "}].\n"
        formula = "\n\n$$" + tex + "$$\n"
        sc = Scenario(Path(temp.name), alpha_en=EN_ALPHA + formula, alpha_ru=RU_ALPHA + (
            formula.replace("U(A,B)", "V(A,B)") if changed_formula else formula),
            alpha_zh=ZH_ALPHA + formula, review_ru=REVIEW_OK if reviewed else None)
        if descriptor:
            data = {"schema_version": 1, "repository": REPOSITORY, "source_revision": sc.c1,
                    "review_state": "unreviewed", "documents": [{
                        "path": ALPHA, "source_sha256": sha256((EN_ALPHA + formula).encode()).hexdigest(),
                        "annotations": [{"math_index": 3, "math_type": "DisplayMath", "tex_sha256": sha256(tex.encode()).hexdigest(),
                                         "mtext_index": 1, "source_text": LONG,
                                         "translations": {"ru": RU_LONG, "zh-Hans": ZH_LONG}}]}]}
            sc.manifest["commit"] = commit(sc.source, {FILENAME: json.dumps(data, ensure_ascii=False)}, "Formula presentation")
            sc.manifest_path.write_text(json.dumps(sc.manifest))
        return sc

    def test_full_renderer_rendition_parity_then_presentation_positive(self):
        sc = self.scenario()
        _, _, renderer, compiled = sc.compile()
        for language, phrase in (("ru", RU_LONG), ("zh-Hans", ZH_LONG)):
            entry = compiled.for_work("synthetic-alpha")[language]
            self.assertEqual(entry["state"], "unreviewed")
            self.assertIn(phrase, entry["html"])
            self.assertEqual(entry["formula_localization"]["review_state"], "unreviewed")
            self.assertEqual(entry["math_count"], 3)
        english = renderer.document(renderer.by_path["papers/synthetic-alpha/PAPER.md"])["html"]
        self.assertIn(LONG, english)
        self.assertNotIn(RU_LONG, english)
        self.assertNotIn(ZH_LONG, english)

    def test_original_exact_math_parity_is_not_bypassed_by_the_presentation(self):
        with self.assertRaisesRegex(ValueError, "^RENDITION_FORMULA_CHANGED:"):
            self.scenario(changed_formula=True).compile()

    def test_missing_descriptor_cannot_publish_untranslated_rendition_mtext(self):
        with self.assertRaisesRegex(ValueError, "^RENDITION_FORMULA_LOCALIZATION:.*COVERAGE"):
            self.scenario(descriptor=False).compile()

    def test_new_unreviewed_presentation_cannot_inherit_historical_manuscript_review(self):
        with self.assertRaisesRegex(ValueError, "^RENDITION_FORMULA_REVIEW:"):
            self.scenario(reviewed=True).compile()


if __name__ == "__main__":
    unittest.main()
