#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Versioned language renditions (K8): positive and negative controls.

ALL TEXT IN THIS FILE IS SYNTHETIC TEST DATA: short invented documents with placeholder marker words in the target
scripts. They are not manuscripts and not translations, and they never leave this test.

Cases refer to docs/versioned-renditions.md section 8 (ML01-ML12 of the multilingual specification).
"""
import copy
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from build_publication import Renderer, load_inputs, run
from publication_checks import check_renditions
from renditions import RenditionError, compile_renditions

ROOT = Path(__file__).resolve().parents[1]


def sha256_text(text: str) -> str:
    return sha256(text.encode('utf-8')).hexdigest()


EN_ALPHA = '''---
name: "synthetic-alpha"
title: "Synthetic Alpha"
language: "en"
---

# Synthetic Alpha

SYNTHETIC TEST DATA, NOT A MANUSCRIPT.

## Rules {#rules}

Necessity: $P \\Rightarrow Q$ and the display

$$a + b = c$$

```text
SYN_CODE_ID = "alpha"
```

See the [companion](../synthetic-beta/PAPER.md#limits) and the [limits](#limits).

A note.[^n]

[^n]: Synthetic note.

## Limits {#limits}

| Key | Value |
|---|---|
| k | v |

Closing synthetic paragraph.
'''
EN_BETA = '''---
name: "synthetic-beta"
title: "Synthetic Beta"
language: "en"
---

# Synthetic Beta

SYNTHETIC TEST DATA, NOT A MANUSCRIPT.

## Limits {#limits}

Limits paragraph.
'''
EN_BETA_CHANGED = EN_BETA + "\nA later source edit.\n"
RU_ALPHA = '''---
name: "synthetic-alpha"
title: "ТЕСТ АЛЬФА"
language: "ru"
---

# ТЕСТ АЛЬФА

СИНТЕТИЧЕСКИЕ ТЕСТОВЫЕ ДАННЫЕ.

## ТЕСТ ПРАВИЛА {#pravila}

ТЕСТ: $P \\Rightarrow Q$ И ФОРМУЛА

$$a + b = c$$

```text
SYN_CODE_ID = "alpha"
```

СМ. [ТЕСТ СОСЕД](../../../papers/synthetic-beta/PAPER.md#limits) И [ТЕСТ ПРЕДЕЛЫ](#predely).

ТЕСТ СНОСКИ.[^n]

[^n]: ТЕСТ СНОСКА.

## ТЕСТ ПРЕДЕЛЫ {#predely}

| Key | Value |
|---|---|
| k | v |

ТЕСТ ЗАВЕРШЕНИЕ.
'''
ZH_ALPHA = '''---
name: "synthetic-alpha"
title: "测试甲"
language: "zh-Hans"
---

# 测试甲

合成测试数据。

## 测试规则 {#guize}

测试：$P \\Rightarrow Q$ 与公式

$$a + b = c$$

```text
SYN_CODE_ID = "alpha"
```

参见[测试邻篇](../../../papers/synthetic-beta/PAPER.md#limits)和[测试界限](#jiexian)。

测试脚注。[^n]

[^n]: 测试注。

## 测试界限 {#jiexian}

| Key | Value |
|---|---|
| k | v |

测试结尾。
'''
RU_BETA = '''---
name: "synthetic-beta"
title: "ТЕСТ БЕТА"
language: "ru"
---

# ТЕСТ БЕТА

СИНТЕТИЧЕСКИЕ ТЕСТОВЫЕ ДАННЫЕ.

## ТЕСТ ПРЕДЕЛЫ {#predely}

ТЕСТ.
'''
CATALOG = {"schema_version": 1, "edition": "1.1", "documents": [
    {"type": "paper", "slug": "synthetic-alpha", "title": "Synthetic Alpha", "path": "papers/synthetic-alpha/PAPER.md", "summary": "Synthetic test data.", "language": "en"},
    {"type": "paper", "slug": "synthetic-beta", "title": "Synthetic Beta", "path": "papers/synthetic-beta/PAPER.md", "summary": "Synthetic test data.", "language": "en"},
]}
REVIEW_OK = {"status": "reviewed", "scope": "full", "method": "synthetic test review; no real review took place",
             "reviewers": [{"kind": "agent", "ref": "test-fixture-reviewer"}], "evidence": ["test-evidence-ref"],
             "limits": "SYNTHETIC TEST DATA; agent-only, non-blind"}
REVIEW_NONE = {"status": "unreviewed", "scope": "full", "method": "", "reviewers": [], "evidence": [], "limits": ""}
SECTIONS_RU = [{"source": "rules", "rendition": "pravila"}, {"source": "limits", "rendition": "predely"}]
SECTIONS_ZH = [{"source": "rules", "rendition": "guize"}, {"source": "limits", "rendition": "jiexian"}]
ALPHA, BETA = "papers/synthetic-alpha/PAPER.md", "papers/synthetic-beta/PAPER.md"
REN = {"ru": "renditions/ru/synthetic-alpha/PAPER.md", "zh-Hans": "renditions/zh-Hans/synthetic-alpha/PAPER.md", "beta-ru": "renditions/ru/synthetic-beta/PAPER.md"}
GIT = ["git", "-c", "user.name=Synthetic fixture", "-c", "user.email=fixture@example.invalid"]


def commit(source: Path, files: dict[str, str], message: str) -> str:
    for path, content in files.items():
        target = source / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    run(["git", "add", "."], cwd=source)
    run([*GIT, "commit", "--quiet", "-m", message], cwd=source)
    return run(["git", "rev-parse", "HEAD"], cwd=source).strip()


def pin(path: str, revision: str, text: str) -> dict:
    return {"path": path, "sha256": sha256_text(text), "revision": revision}


class Scenario:
    """A synthetic knowledge repository in four commits: sources, renditions, a later source edit, then the sidecar."""

    def __init__(self, root: Path, *, alpha_ru=RU_ALPHA, alpha_zh=ZH_ALPHA, mutate_sidecar=None, via="catalog",
                 after_renditions=None, review_ru=REVIEW_OK, review_zh=REVIEW_NONE, alpha_en=EN_ALPHA, renditions_first=False, side_source=False):
        review_ru, review_zh = copy.deepcopy(review_ru), copy.deepcopy(review_zh)
        self.root = root
        self.source = root / "source"
        self.source.mkdir()
        run(["git", "init", "--quiet"], cwd=self.source)
        sources = {ALPHA: alpha_en, BETA: EN_BETA, "publication-catalog.json": json.dumps(CATALOG)}
        renditions = {REN["ru"]: alpha_ru, REN["zh-Hans"]: alpha_zh, REN["beta-ru"]: RU_BETA}
        if renditions_first:  # the renditions' bytes exist before the source revision that they claim to render
            self.c2 = commit(self.source, renditions, "renditions")
            self.c1 = commit(self.source, sources, "sources")
        else:
            self.c1 = commit(self.source, sources, "sources")
            self.c2 = commit(self.source, renditions, "renditions")
        self.side = None
        if side_source:  # a commit that holds the pinned source bytes but is not reachable from the publication commit
            run(["git", "checkout", "--quiet", "--orphan", "side"], cwd=self.source)
            run(["git", "rm", "-r", "-f", "--quiet", "."], cwd=self.source)
            self.side = commit(self.source, {ALPHA: alpha_en}, "side")
            run(["git", "checkout", "--quiet", "-f", self.c2 if not renditions_first else self.c1], cwd=self.source)
            run(["git", "checkout", "--quiet", "-B", "main-line"], cwd=self.source)
        later = {BETA: EN_BETA_CHANGED}
        later.update(after_renditions or {})
        self.c3 = commit(self.source, later, "later edits")
        sidecar = {"schema_version": 1, "kind": "arcanada-publication-renditions", "edition": "1.1", "renditions": [
            {"work": "synthetic-alpha", "language": "ru", "script": "Cyrl", "source": dict(pin(ALPHA, self.c1, alpha_en), language="en"),
             "rendition": pin(REN["ru"], self.c2, alpha_ru), "review": review_ru, "sections": SECTIONS_RU, "counts_as_independent_source": False},
            {"work": "synthetic-alpha", "language": "zh-Hans", "script": "Hans", "source": dict(pin(ALPHA, self.c1, alpha_en), language="en"),
             "rendition": pin(REN["zh-Hans"], self.c2, alpha_zh), "review": review_zh, "sections": SECTIONS_ZH, "counts_as_independent_source": False},
            {"work": "synthetic-beta", "language": "ru", "script": "Cyrl", "source": dict(pin(BETA, self.c1, EN_BETA), language="en"),
             "rendition": pin(REN["beta-ru"], self.c2, RU_BETA), "review": copy.deepcopy(REVIEW_OK), "sections": [{"source": "limits", "rendition": "predely"}], "counts_as_independent_source": False},
        ]}
        sidecar = copy.deepcopy(sidecar)  # never share the module-level constants with a mutation
        if mutate_sidecar:
            mutate_sidecar(sidecar)
        self.sidecar = sidecar
        self.fixture_file = None
        if via == "catalog":
            catalog = dict(CATALOG, renditions="publication-renditions.json")
            self.head = commit(self.source, {"publication-renditions.json": json.dumps(sidecar, indent=1), "publication-catalog.json": json.dumps(catalog)}, "sidecar")
        else:
            self.head = self.c3
            self.fixture_file = root / "fixture-sidecar.json"
            self.fixture_file.write_text(json.dumps(sidecar), encoding="utf-8")
        self.manifest = {"schema_version": 1, "edition": "1.1", "repository": "Arcanada-one/knowledge-contract", "commit": self.head, "catalog": "publication-catalog.json"}
        self.manifest_path = root / "manifest.json"
        self.manifest_path.write_text(json.dumps(self.manifest))

    def compile(self):
        manifest, documents = load_inputs(self.source, self.manifest_path)
        renderer = Renderer(self.source, self.root / "public", manifest, documents)
        compiled = compile_renditions(self.source, manifest, documents, renderer, run, self.fixture_file)
        return manifest, documents, renderer, compiled


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def refused(self, code, **kwargs):
        sub = tempfile.mkdtemp(dir=self.root)
        with self.assertRaisesRegex(RenditionError, "^(" + code + "):"):
            Scenario(Path(sub), **kwargs).compile()


def swap(text: str, old: str, new: str) -> str:
    assert old in text, old
    return text.replace(old, new, 1)


class CompilerPositiveControls(Base):
    def test_no_sidecar_leaves_the_build_unchanged(self):
        """No-rendition invariance at the unit level: with neither a catalogue key nor a fixture file nothing is compiled."""
        scenario = Scenario(self.root, via="catalog")
        run(["git", "rm", "--quiet", "publication-renditions.json"], cwd=scenario.source)
        catalog = json.dumps(CATALOG)
        head = commit(scenario.source, {"publication-catalog.json": catalog}, "no sidecar")
        scenario.manifest["commit"] = head
        scenario.manifest_path.write_text(json.dumps(scenario.manifest))
        manifest, documents, renderer, compiled = scenario.compile()
        self.assertIsNone(compiled)

    def test_reviewed_rendition_compiles_complete_text_with_stable_anchors(self):
        """ML01/ML02/ML11: a reviewed synthetic rendition has complete rendered text, exact pins and a stable section mapping."""
        manifest, documents, renderer, compiled = Scenario(self.root).compile()
        ru = compiled.for_work("synthetic-alpha")["ru"]
        self.assertEqual(ru["state"], "reviewed")
        for expected in ("ТЕСТ:", "ТЕСТОВЫЕ", "ТЕСТ ЗАВЕРШЕНИЕ", "SYN_CODE_ID", "ТЕСТ СНОСКА"):
            self.assertIn(expected, ru["html"])
        self.assertEqual(ru["title"], "ТЕСТ АЛЬФА")
        self.assertEqual(ru["math_count"], 2)
        self.assertIn('<h2 id="pravila" data-source-section="rules"', ru["html"])
        self.assertIn('<span id="rules" class="source-anchor"></span>', ru["html"])
        self.assertEqual([h["id"] for h in ru["toc"]], ["pravila", "predely"])
        self.assertEqual(ru["source"]["sha256"], sha256_text(EN_ALPHA))
        self.assertEqual(ru["rendition"]["sha256"], sha256_text(RU_ALPHA))
        self.assertIs(ru["counts_as_independent_source"], False)
        self.assertIn('/en/', ru["html"])  # cross-document link resolved to the catalogued route
        zh = compiled.for_work("synthetic-alpha")["zh-Hans"]
        self.assertEqual(zh["state"], "unreviewed")
        self.assertIn("测试结尾", zh["html"])

    def test_states_missing_and_stale_are_computed_not_declared(self):
        """ML07: a changed source makes an older rendition stale; an absent rendition is missing; neither is shown as current."""
        manifest, documents, renderer, compiled = Scenario(self.root).compile()
        beta = compiled.for_work("synthetic-beta")
        self.assertEqual(beta["ru"]["state"], "stale")
        self.assertNotIn("html", beta["ru"])
        self.assertNotEqual(beta["ru"]["source"]["sha256"], beta["ru"]["current_source_sha256"])
        self.assertEqual(beta["zh-Hans"]["state"], "missing")
        self.assertNotIn("rendition", beta["zh-Hans"])
        entries = {(e["work"], e["language"]): e["state"] for e in compiled.entries}
        self.assertEqual(entries[("synthetic-beta", "ru")], "stale")
        self.assertEqual(entries[("synthetic-beta", "zh-Hans")], "missing")

    def test_partial_review_is_labelled_partial(self):
        review = dict(REVIEW_OK, scope="sections", reviewed_sections=["rules"])
        _, _, _, compiled = Scenario(self.root, review_ru=review).compile()
        self.assertEqual(compiled.for_work("synthetic-alpha")["ru"]["state"], "partially-reviewed")

    def test_catalogue_sidecar_is_the_production_source_and_fixture_is_marked(self):
        _, _, _, production = Scenario(self.root).compile()
        self.assertEqual(production.source_kind, "knowledge-repository")
        other = Path(tempfile.mkdtemp(dir=self.root))
        _, _, _, fixture = Scenario(other, via="fixture").compile()
        self.assertEqual(fixture.source_kind, "fixture")
        self.assertEqual(fixture.provenance()["renditions_source"], "fixture")
        self.assertEqual(production.provenance()["renditions_source"], "knowledge-repository")


class CompilerNegativeControls(Base):
    # --- pins (ML02, ML07, ML11) ---
    def test_stale_source_pin_is_stale_never_current(self):
        """A source whose bytes changed after the pin cannot keep the reviewed state (ML02/ML07)."""
        _, _, _, compiled = Scenario(self.root, after_renditions={ALPHA: EN_ALPHA + "\nChanged source edition.\n"}).compile()
        ru = compiled.for_work("synthetic-alpha")["ru"]
        self.assertEqual(ru["state"], "stale")
        self.assertNotIn("html", ru)

    def test_source_revision_not_reachable_from_the_publication_commit(self):
        def unreachable(sidecar):
            sidecar["renditions"][0]["source"]["revision"] = "0" * 40
        self.refused("RENDITION_SOURCE_PIN", mutate_sidecar=unreachable)

    def test_source_revision_with_the_right_bytes_on_an_unrelated_history(self):
        """Exact bytes are not enough: the pinned revision must be part of the publication's history."""
        with self.assertRaisesRegex(RenditionError, "^RENDITION_SOURCE_PIN:.*not an ancestor"):
            self.build_with_side_pin(self.root)

    def build_with_side_pin(self, root):
        scenario = Scenario(root, side_source=True)
        sidecar = copy.deepcopy(scenario.sidecar)
        sidecar["renditions"][0]["source"]["revision"] = scenario.side
        catalog = dict(CATALOG, renditions="publication-renditions.json")
        head = commit(scenario.source, {"publication-renditions.json": json.dumps(sidecar), "publication-catalog.json": json.dumps(catalog)}, "pin the side commit")
        scenario.manifest["commit"] = head
        scenario.manifest_path.write_text(json.dumps(scenario.manifest))
        scenario.compile()

    def test_source_pin_with_wrong_bytes(self):
        def wrong(sidecar):
            sidecar["renditions"][0]["source"]["sha256"] = "1" * 64
        self.refused("RENDITION_SOURCE_PIN", mutate_sidecar=wrong)

    def test_mixed_pins_rendition_older_than_its_source(self):
        """The rendition's bytes exist, byte-exact, but in a commit older than the source revision it claims to render."""
        self.refused("RENDITION_REVISION_PIN", renditions_first=True)

    def test_rendition_revision_that_does_not_contain_the_bytes(self):
        def mixed(sidecar):
            entry = sidecar["renditions"][0]
            entry["rendition"]["revision"] = entry["source"]["revision"]
        self.refused("RENDITION_REVISION_PIN", mutate_sidecar=mixed)

    def test_rendition_bytes_changed_after_the_pin(self):
        self.refused("RENDITION_DIGEST", after_renditions={REN["ru"]: RU_ALPHA + "\nТЕСТ ПРАВКА.\n"})

    def test_source_path_not_the_catalogued_document(self):
        def other(sidecar):
            sidecar["renditions"][0]["source"]["path"] = BETA
        self.refused("RENDITION_SOURCE_PIN", mutate_sidecar=other)

    def test_unknown_work_and_duplicate(self):
        def unknown(sidecar):
            sidecar["renditions"][0]["work"] = "synthetic-gamma"
        self.refused("RENDITION_UNKNOWN_WORK", mutate_sidecar=unknown)

        def duplicate(sidecar):
            sidecar["renditions"].append(copy.deepcopy(sidecar["renditions"][0]))
        self.refused("RENDITION_DUPLICATE", mutate_sidecar=duplicate)

    # --- closed schema ---
    def test_unknown_fields_are_refused_at_every_level(self):
        for where in ("top", "entry", "source", "rendition", "review", "section"):
            with self.subTest(where=where):
                def add(sidecar, where=where):
                    entry = sidecar["renditions"][0]
                    target = {"top": sidecar, "entry": entry, "source": entry["source"], "rendition": entry["rendition"],
                              "review": entry["review"], "section": entry["sections"][0]}[where]
                    target["translation_state"] = "fine"
                self.refused("RENDITION_SIDECAR_SCHEMA", mutate_sidecar=add)

    def test_a_rendition_is_never_an_independent_source(self):
        def independent(sidecar):
            sidecar["renditions"][0]["counts_as_independent_source"] = True
        self.refused("RENDITION_SIDECAR_SCHEMA", mutate_sidecar=independent)

        def absent(sidecar):
            del sidecar["renditions"][0]["counts_as_independent_source"]
        self.refused("RENDITION_SIDECAR_SCHEMA", mutate_sidecar=absent)

    # --- language metadata (ML11) ---
    def test_language_outside_the_interface_set(self):
        for language in ("fr", "zh", "zh-Hant", "ru-RU", "en"):
            with self.subTest(language=language):
                def wrong(sidecar, language=language):
                    sidecar["renditions"][0]["language"] = language
                self.refused("RENDITION_LANGUAGE", mutate_sidecar=wrong)

    def test_script_that_does_not_belong_to_the_language(self):
        def wrong(sidecar):
            sidecar["renditions"][0]["script"] = "Hans"
        self.refused("RENDITION_LANGUAGE", mutate_sidecar=wrong)

    def test_front_matter_language_disagrees_with_the_sidecar(self):
        self.refused("RENDITION_LANGUAGE", alpha_ru=swap(RU_ALPHA, 'language: "ru"', 'language: "en"'))

    def test_english_text_labelled_russian(self):
        english_as_russian = swap(EN_ALPHA.replace("synthetic-alpha", "synthetic-alpha"), 'language: "en"', 'language: "ru"')
        english_as_russian = english_as_russian.replace("## Rules {#rules}", "## Rules {#pravila}").replace("## Limits {#limits}", "## Limits {#predely}").replace("(#limits)", "(#predely)")
        english_as_russian = english_as_russian.replace("../synthetic-beta/", "../../../papers/synthetic-beta/")
        self.refused("RENDITION_LANGUAGE", alpha_ru=english_as_russian)

    # --- review claims (ML05) ---
    def test_unreviewed_rendition_cannot_be_published_as_reviewed(self):
        for field, value in (("evidence", []), ("reviewers", []), ("method", ""), ("limits", "")):
            with self.subTest(field=field):
                self.refused("RENDITION_REVIEW_UNEVIDENCED", review_ru=dict(REVIEW_OK, **{field: value}))

    def test_unreviewed_status_cannot_carry_review_evidence(self):
        self.refused("RENDITION_REVIEW_UNEVIDENCED", review_zh=dict(REVIEW_NONE, evidence=["x"]))

    # --- sections (ML01) ---
    def test_missing_section(self):
        def drop(sidecar):
            sidecar["renditions"][0]["sections"] = SECTIONS_RU[:1]
        self.refused("RENDITION_SECTION_MISSING", mutate_sidecar=drop)

    def test_section_absent_from_the_rendition(self):
        without = RU_ALPHA.split("## ТЕСТ ПРЕДЕЛЫ")[0]
        self.refused("RENDITION_SECTION_UNRESOLVED", alpha_ru=without)

    def test_mapped_section_that_does_not_exist(self):
        def ghost(sidecar):
            sidecar["renditions"][0]["sections"][1]["rendition"] = "no-such-anchor"
        self.refused("RENDITION_SECTION_UNRESOLVED", mutate_sidecar=ghost)

    def test_section_mapping_drift(self):
        def swapped(sidecar):
            sidecar["renditions"][0]["sections"] = [{"source": "rules", "rendition": "predely"}, {"source": "limits", "rendition": "pravila"}]
        self.refused("RENDITION_SECTION_DRIFT", mutate_sidecar=swapped)

        def stale_source_anchor(sidecar):
            sidecar["renditions"][0]["sections"].append({"source": "removed-from-source", "rendition": "pravila-2"})
        self.refused("RENDITION_SECTION_DRIFT", mutate_sidecar=stale_source_anchor)

    def test_extra_rendition_section_outside_the_mapping(self):
        self.refused("RENDITION_SECTION_DRIFT", alpha_ru=RU_ALPHA + "\n## ТЕСТ ЛИШНИЙ {#lishnij}\n\nТЕСТ.\n")

    def test_section_text_emptied(self):
        emptied = RU_ALPHA.split("## ТЕСТ ПРЕДЕЛЫ")[0] + "## ТЕСТ ПРЕДЕЛЫ {#predely}\n\n| Key | Value |\n|---|---|\n| k | v |\n"
        self.refused("RENDITION_SECTION_MISSING", alpha_ru=emptied)

    def test_table_dropped(self):
        self.refused("RENDITION_STRUCTURE_MISMATCH", alpha_ru=swap(RU_ALPHA, "| Key | Value |\n|---|---|\n| k | v |\n", ""))

    # --- formula / code (ML04) ---
    def test_formula_changed(self):
        for old, new in (("$P \\Rightarrow Q$", "$P \\Leftrightarrow Q$"), ("$$a + b = c$$", "$$a - b = c$$"), ("$P \\Rightarrow Q$", "$$P \\Rightarrow Q$$")):
            with self.subTest(new=new):
                self.refused("RENDITION_FORMULA_CHANGED", alpha_ru=swap(RU_ALPHA, old, new))

    def test_formula_dropped(self):
        self.refused("RENDITION_FORMULA_CHANGED", alpha_ru=swap(RU_ALPHA, "$$a + b = c$$", ""))

    def test_code_identifier_changed(self):
        self.refused("RENDITION_CODE_CHANGED", alpha_ru=swap(RU_ALPHA, 'SYN_CODE_ID = "alpha"', 'SYN_CODE_ID = "альфа"'))

    # --- references (ML08/ML10) ---
    def test_reference_dropped(self):
        self.refused("RENDITION_REFERENCE_DROPPED", alpha_ru=swap(RU_ALPHA, "[ТЕСТ СОСЕД](../../../papers/synthetic-beta/PAPER.md#limits)", "ТЕСТ СОСЕД"))

    def test_footnote_dropped(self):
        self.refused("RENDITION_REFERENCE_DROPPED", alpha_ru=swap(swap(RU_ALPHA, "ТЕСТ СНОСКИ.[^n]", "ТЕСТ СНОСКИ."), "[^n]: ТЕСТ СНОСКА.\n", ""))

    def test_reference_retargeted(self):
        self.refused("RENDITION_REFERENCE_DROPPED", alpha_ru=swap(RU_ALPHA, "PAPER.md#limits)", "PAPER.md#elsewhere)"))

    def test_reference_added(self):
        self.refused("RENDITION_REFERENCE_CHANGED", alpha_ru=swap(RU_ALPHA, "ТЕСТ ЗАВЕРШЕНИЕ.", "ТЕСТ ЗАВЕРШЕНИЕ [ТЕСТ](https://example.invalid/extra)."))

    def test_local_fragment_that_is_a_guessed_anchor(self):
        self.refused("RENDITION_REFERENCE_DROPPED|RENDITION_REFERENCE_CHANGED", alpha_ru=swap(RU_ALPHA, "(#predely)", "(#limits)"))

    # --- authority ---
    def test_fixture_sidecar_cannot_override_a_declared_one(self):
        scenario = Scenario(self.root, via="catalog")
        scenario.fixture_file = self.root / "extra.json"
        scenario.fixture_file.write_text(json.dumps(scenario.sidecar))
        with self.assertRaisesRegex(RenditionError, "^RENDITION_SOURCE_AUTHORITY:"):
            scenario.compile()

    def test_sidecar_path_must_stay_inside_the_repository(self):
        scenario = Scenario(self.root, via="catalog")
        for value in ("../outside.json", "/abs.json", "notjson.md"):
            catalog = dict(CATALOG, renditions=value)
            head = commit(scenario.source, {"publication-catalog.json": json.dumps(catalog)}, "bad key")
            scenario.manifest["commit"] = head
            scenario.manifest_path.write_text(json.dumps(scenario.manifest))
            with self.subTest(value=value), self.assertRaisesRegex(RenditionError, "^RENDITION_SIDECAR_SCHEMA:"):
                scenario.compile()


# ---------------------------------------------------------------------------------------------------------------
# Prerendered output: build a small real site from a synthetic source and check the pages.
# ---------------------------------------------------------------------------------------------------------------
class PrerenderedSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        (cls.root / "scenario").mkdir()
        cls.scenario = Scenario(cls.root / "scenario")
        manifest, documents, renderer, compiled = cls.scenario.compile()
        site = cls.root / "site"
        shutil.copytree(ROOT / "src", site / "src", ignore=shutil.ignore_patterns("node_modules"))
        for name in ("build.mjs", "roadmap-manifest.json"):
            shutil.copy(ROOT / name, site / name)
        (site / "publication-manifest.json").write_text(json.dumps(manifest))
        sys.path.insert(0, str(ROOT / "scripts"))
        from publication_catalog import write_catalog
        roadmap = json.loads((ROOT / "src/content/catalog.json").read_text())["roadmap"]
        write_catalog(cls.scenario.source, site, manifest, documents, renderer, roadmap, compiled)
        catalog_path = site / "src/content/catalog.json"
        catalog = json.loads(catalog_path.read_text())
        # The site's home and listing pages expect the real records, so the synthetic works are added to them; the real
        # records are re-pinned to the synthetic publication commit (metadata only) so that the pin checks stay consistent.
        real = json.loads((ROOT / "src/content/catalog.json").read_text())
        real_pin = real["publication"]["commit"]
        shared = json.loads(json.dumps(real["records"]).replace(real_pin, manifest["commit"]))
        catalog["records"] = shared + catalog["records"]
        catalog["aliases"] = {key: value for key, value in real["aliases"].items()}
        catalog_path.write_text(json.dumps(catalog, ensure_ascii=False))
        cls.build = subprocess.run(["node", "build.mjs"], cwd=site, capture_output=True, text=True, timeout=900)
        cls.site, cls.catalog, cls.compiled = site, catalog, compiled

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.assertEqual(self.build.returncode, 0, self.build.stderr + self.build.stdout)
        self.out = Path(tempfile.mkdtemp(dir=self.root))
        for work in ("synthetic-alpha", "synthetic-beta"):
            for locale in ("en", "ru", "zh-Hans"):
                target = self.out / locale / "science" / work / "index.html"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(self.site / "public" / locale / "science" / work / "index.html", target)
        shutil.copy(self.site / "public/renditions.js", self.out / "renditions.js")

    def page(self, locale, work="synthetic-alpha"):
        return self.out / locale / "science" / work / "index.html"

    def edit(self, locale, work, old, new, count=1):
        path = self.page(locale, work)
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, count), encoding="utf-8")

    def check(self, source="knowledge-repository"):
        return check_renditions(self.out, self.catalog["records"], source)

    def test_positive_control_all_states_are_labelled_and_complete(self):
        """ML01/ML11: reviewed and unreviewed renditions are prerendered completely with correct language metadata;
        stale and missing pages show the pinned English source with an explicit fallback statement."""
        self.assertEqual(self.check(), 4)
        ru = self.page("ru").read_text(encoding="utf-8")
        self.assertIn('<aside class="rendition-state" data-state="reviewed" data-language="ru" data-body-language="ru"', ru)
        self.assertIn("<strong>Рецензированный перевод</strong>", ru)
        self.assertIn('<div class="source-body prose" lang="ru">', ru)
        self.assertIn('<h1 id="', ru)
        self.assertIn('lang="ru">ТЕСТ АЛЬФА</h1>', ru)
        self.assertIn('"inLanguage":"ru"', ru)
        self.assertIn('"translationOfWork"', ru)
        self.assertEqual(ru.count("<math "), 2)
        self.assertNotIn("SYNTHETIC TEST DATA, NOT A MANUSCRIPT", ru)
        zh = self.page("zh-Hans").read_text(encoding="utf-8")
        self.assertIn('data-state="unreviewed" data-language="zh-Hans" data-body-language="zh-Hans"', zh)
        self.assertIn("<strong>未审校译文</strong>", zh)
        self.assertIn('<div class="source-body prose" lang="zh-Hans">', zh)
        stale = self.page("ru", "synthetic-beta").read_text(encoding="utf-8")
        self.assertIn('data-state="stale" data-language="ru" data-body-language="en"', stale)
        self.assertIn("Перевод устарел", stale)
        self.assertIn("Вместо него показан закреплённый английский исходный текст.", stale)
        self.assertIn('<div class="source-body prose" lang="en">', stale)
        self.assertIn('"inLanguage":"en"', stale)
        missing = self.page("zh-Hans", "synthetic-beta").read_text(encoding="utf-8")
        self.assertIn('data-state="missing"', missing)
        self.assertIn("本文档暂无译文。", missing)
        english = self.page("en").read_text(encoding="utf-8")
        self.assertNotIn("rendition-state", english)
        self.assertIn("SYNTHETIC TEST DATA, NOT A MANUSCRIPT", english)

    def test_anchors_survive_in_the_page_and_the_state_exposes_pins(self):
        ru = self.page("ru").read_text(encoding="utf-8")
        self.assertIn('id="pravila" data-source-section="rules"', ru)
        self.assertIn('<span id="rules" class="source-anchor"></span>', ru)
        self.assertIn(self.scenario.c1[:12], ru)
        self.assertIn(self.scenario.c2[:12], ru)
        self.assertIn(sha256_text(RU_ALPHA)[:12], ru)
        self.assertIn("agent: test-fixture-reviewer", ru)
        self.assertIn('data-independent-source="false"', ru)

    def test_published_manifest_reports_the_rendition_pins(self):
        published = json.loads((self.site / "public/publication.json").read_text())
        self.assertEqual(published["document_language"], "en")
        self.assertEqual(published["renditions"], {"schema_version": 1, "source": "knowledge-repository"})
        alpha = next(d for d in published["documents"] if d["slug"] == "synthetic-alpha")
        self.assertEqual(alpha["renditions"]["ru"]["rendition_sha256"], sha256_text(RU_ALPHA))
        self.assertIs(alpha["renditions"]["ru"]["counts_as_independent_source"], False)
        beta = next(d for d in published["documents"] if d["slug"] == "synthetic-beta")
        self.assertEqual(beta["renditions"]["ru"]["state"], "stale")
        self.assertEqual(beta["renditions"]["zh-Hans"]["state"], "missing")

    def test_silent_fallback_is_refused(self):
        """ML11: English text on a /ru/ page without its state statement."""
        path = self.page("ru", "synthetic-beta")
        text = path.read_text(encoding="utf-8")
        path.write_text(re.sub(r'<aside class="rendition-state".*?</aside>', "", text, flags=re.S), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "RENDITION_SILENT_FALLBACK"):
            self.check()

    def test_fallback_without_the_explicit_statement_is_refused(self):
        self.edit("ru", "synthetic-beta", "Вместо него показан закреплённый английский исходный текст.", "")
        with self.assertRaisesRegex(ValueError, "RENDITION_SILENT_FALLBACK"):
            self.check()

    def test_rendition_replaced_by_english_is_refused(self):
        """A reviewed Russian page that actually shows the English body."""
        english = self.page("en").read_text(encoding="utf-8")
        body = re.search(r'<div class="source-body prose" lang="en">.*?</div><section class="document-citation"', english, re.S)[0]
        path = self.page("ru")
        text = path.read_text(encoding="utf-8")
        path.write_text(re.sub(r'<div class="source-body prose" lang="ru">.*?</div><section class="document-citation"', lambda m: body, text, flags=re.S), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "RENDITION_LANGUAGE|RENDITION_SILENT_FALLBACK"):
            self.check()

    def test_wrong_language_metadata_is_refused(self):
        self.edit("ru", "synthetic-alpha", '<div class="source-body prose" lang="ru">', '<div class="source-body prose" lang="en">')
        with self.assertRaisesRegex(ValueError, "RENDITION_LANGUAGE"):
            self.check()
        self.setUp()
        self.edit("zh-Hans", "synthetic-alpha", '"inLanguage":"zh-Hans"', '"inLanguage":"en"')
        with self.assertRaisesRegex(ValueError, "RENDITION_LANGUAGE"):
            self.check()

    def test_fallback_declared_with_a_rendition_language_is_refused(self):
        self.edit("ru", "synthetic-beta", '<div class="source-body prose" lang="en">', '<div class="source-body prose" lang="ru">')
        with self.assertRaisesRegex(ValueError, "RENDITION_LANGUAGE"):
            self.check()

    def test_unreviewed_rendition_labelled_reviewed_is_refused(self):
        """ML05: the page of an unreviewed rendition carrying the 'reviewed' state or label."""
        self.edit("zh-Hans", "synthetic-alpha", "<strong>未审校译文</strong>", "<strong>已审校译文</strong>")
        with self.assertRaisesRegex(ValueError, "RENDITION_STATE_LABEL"):
            self.check()
        self.setUp()
        self.edit("zh-Hans", "synthetic-alpha", 'data-state="unreviewed"', 'data-state="reviewed"')
        with self.assertRaisesRegex(ValueError, "RENDITION_STATE_LABEL"):
            self.check()

    def test_stale_rendition_labelled_current_is_refused(self):
        """ML07: a stale rendition's page claiming to be reviewed."""
        self.edit("ru", "synthetic-beta", 'data-state="stale"', 'data-state="reviewed"')
        self.edit("ru", "synthetic-beta", "<strong>Перевод устарел: английский источник изменился.</strong>", "<strong>Рецензированный перевод</strong>")
        with self.assertRaisesRegex(ValueError, "RENDITION_STATE_LABEL"):
            self.check()

    def test_truncated_prerendered_text_is_refused(self):
        self.edit("ru", "synthetic-alpha", "ТЕСТ ЗАВЕРШЕНИЕ", "")
        with self.assertRaisesRegex(ValueError, "RENDITION_SILENT_FALLBACK"):
            self.check()

    def test_section_binding_drift_is_refused(self):
        self.edit("ru", "synthetic-alpha", 'id="pravila" data-source-section="rules"', 'id="pravila" data-source-section="limits"')
        with self.assertRaisesRegex(ValueError, "RENDITION_SECTION_DRIFT|RENDITION_SILENT_FALLBACK"):
            self.check()

    def test_formula_count_change_in_the_page_is_refused(self):
        path = self.page("ru")
        text = path.read_text(encoding="utf-8")
        path.write_text(re.sub(r"<math .*?</math>", "", text, count=1, flags=re.S), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "RENDITION_FORMULA_CHANGED|RENDITION_SILENT_FALLBACK"):
            self.check()

    def test_english_page_never_carries_a_rendition_label(self):
        self.edit("en", "synthetic-alpha", '<main id="main" tabindex="-1">', '<main id="main" tabindex="-1">' + re.search(r'<aside class="rendition-state".*?</aside>', self.page("ru").read_text(encoding="utf-8"), re.S)[0])
        with self.assertRaisesRegex(ValueError, "RENDITION_STATE_LABEL"):
            self.check()

    def test_fixture_built_output_is_refused(self):
        """A build made from --renditions-file is not a publication (condition 2 of the K8 decision)."""
        with self.assertRaisesRegex(ValueError, "RENDITION_FIXTURE_ONLY"):
            self.check(source="fixture")
        with self.assertRaisesRegex(ValueError, "RENDITION_FIXTURE_ONLY"):
            self.check(source=None)
        self.assertEqual(check_renditions(self.out, self.catalog["records"], "fixture", allow_fixture=True), 4)

    def test_assets_shipped_only_with_renditions(self):
        index = (self.site / "public/index.html").read_text(encoding="utf-8")
        self.assertRegex(index, r'<script src="/renditions\.js\?v=[0-9a-f]{64}" defer></script>')
        self.assertRegex(index, r'<link rel="stylesheet" href="/renditions\.css\?v=[0-9a-f]{64}">')


class OutputWithoutRenditions(unittest.TestCase):
    """The committed site (no renditions) carries no rendition markup, assets or records."""

    def test_committed_public_tree_has_no_rendition_surface(self):
        catalog = json.loads((ROOT / "src/content/catalog.json").read_text())
        self.assertNotIn("renditions_source", catalog)
        self.assertFalse(any("renditions" in r for r in catalog["records"]))
        provenance = json.loads((ROOT / "src/site/content-provenance.json").read_text())
        self.assertNotIn("renditions", provenance)
        self.assertFalse((ROOT / "public/renditions.js").exists() or (ROOT / "public/renditions.css").exists())
        self.assertEqual(check_renditions(ROOT / "public", catalog["records"], None), 0)

    def test_check_publication_refuses_fixture_built_output(self):
        """End to end: the real check_publication.py exits non-zero on a tree whose provenance says fixture."""
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp)
            shutil.copytree(ROOT / "scripts", copy / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
            shutil.copytree(ROOT / "public", copy / "public")
            (copy / "src/content").mkdir(parents=True)
            (copy / "src/site").mkdir(parents=True)
            shutil.copy(ROOT / "publication-manifest.json", copy)
            control = subprocess.run([sys.executable, "-B", "scripts/check_publication.py"], cwd=copy, capture_output=True, text=True)
            catalog = json.loads((ROOT / "src/content/catalog.json").read_text())
            provenance = json.loads((ROOT / "src/site/content-provenance.json").read_text())
            published = json.loads((copy / "public/publication.json").read_text())
            (copy / "src/content/catalog.json").write_text(json.dumps(catalog))
            (copy / "src/site/content-provenance.json").write_text(json.dumps(provenance))
            control = subprocess.run([sys.executable, "-B", "scripts/check_publication.py"], cwd=copy, capture_output=True, text=True)
            self.assertEqual(control.returncode, 0, control.stdout + control.stderr)
            catalog["renditions_source"] = "fixture"
            provenance["renditions"] = {"renditions_source": "fixture"}
            published["renditions"] = {"schema_version": 1, "source": "fixture"}
            (copy / "src/content/catalog.json").write_text(json.dumps(catalog))
            (copy / "src/site/content-provenance.json").write_text(json.dumps(provenance))
            (copy / "public/publication.json").write_text(json.dumps(published))
            refused = subprocess.run([sys.executable, "-B", "scripts/check_publication.py"], cwd=copy, capture_output=True, text=True)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn("RENDITION_FIXTURE_ONLY", refused.stdout + refused.stderr)


if __name__ == "__main__":
    unittest.main()
