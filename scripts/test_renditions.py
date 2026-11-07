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
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from build_publication import Renderer, load_inputs, run
from publication_checks import check_renditions
from renditions import RenditionError, compile_renditions, tree_paths
from renditions_dry_run import audit

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

See the [companion](../synthetic-beta/PAPER.md#limits), the [limits](#limits) and the [schema](../../schemas/synthetic.schema.json).

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

СМ. [ТЕСТ СОСЕД](../synthetic-beta/PAPER.md#limits), [ТЕСТ ПРЕДЕЛЫ](#predely) И [ТЕСТ СХЕМА](../../schemas/synthetic.schema.json).

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

参见[测试邻篇](../synthetic-beta/PAPER.md#limits)、[测试界限](#jiexian)和[测试模式](../../schemas/synthetic.schema.json)。

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
EN_GAMMA = '''---
name: "synthetic-gamma"
title: "Synthetic Gamma"
language: "en"
---

# Synthetic Gamma

SYNTHETIC TEST DATA, NOT A MANUSCRIPT.

## Scope {#scope}

Scope paragraph.
'''
RU_GAMMA = '''---
name: "synthetic-gamma"
title: "ТЕСТ ГАММА"
language: "ru"
---

# ТЕСТ ГАММА

СИНТЕТИЧЕСКИЕ ТЕСТОВЫЕ ДАННЫЕ.

## ТЕСТ ОБЛАСТЬ {#oblast}

ТЕСТ.
'''
SCHEMA = '{"synthetic": "invariant artifact"}\n'
CATALOG = {"schema_version": 1, "edition": "1.1", "documents": [
    {"type": "paper", "slug": "synthetic-alpha", "title": "Synthetic Alpha", "path": "papers/synthetic-alpha/PAPER.md", "summary": "Synthetic test data.", "language": "en"},
    {"type": "paper", "slug": "synthetic-beta", "title": "Synthetic Beta", "path": "papers/synthetic-beta/PAPER.md", "summary": "Synthetic test data.", "language": "en"},
]}
CATALOG_GAMMA = dict(CATALOG, documents=CATALOG["documents"] + [
    {"type": "paper", "slug": "synthetic-gamma", "title": "Synthetic Gamma", "path": "papers/synthetic-gamma/PAPER.md", "summary": "Synthetic test data.", "language": "en"}])
REVIEW_OK = {"status": "reviewed", "scope": "full", "method": "synthetic test review; no real review took place",
             "reviewers": [{"kind": "agent", "ref": "test-fixture-reviewer"}], "evidence": ["test-evidence-ref"],
             "limits": "SYNTHETIC TEST DATA; agent-only, non-blind"}
REVIEW_NONE = {"status": "unreviewed", "scope": "full", "method": "", "reviewers": [], "evidence": [], "limits": ""}
SECTIONS_RU = [{"source": "rules", "rendition": "pravila"}, {"source": "limits", "rendition": "predely"}]
SECTIONS_ZH = [{"source": "rules", "rendition": "guize"}, {"source": "limits", "rendition": "jiexian"}]
ALPHA, BETA, GAMMA = "papers/synthetic-alpha/PAPER.md", "papers/synthetic-beta/PAPER.md", "papers/synthetic-gamma/PAPER.md"
# The real layout of the knowledge repository: translations/<language>/<same source-relative path>.
REN = {"ru": "translations/ru/" + ALPHA, "zh-Hans": "translations/zh-Hans/" + ALPHA, "beta-ru": "translations/ru/" + BETA, "gamma-ru": "translations/ru/" + GAMMA}
SCHEMA_PATH, DECOY_PATH = "schemas/synthetic.schema.json", "translations/ru/schemas/decoy.json"  # the decoy exists only where a naive resolution would look
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
                 after_renditions=None, review_ru=REVIEW_OK, review_zh=REVIEW_NONE, alpha_en=EN_ALPHA, renditions_first=False, side_source=False,
                 gamma=False, extra_sources=None):
        review_ru, review_zh = copy.deepcopy(review_ru), copy.deepcopy(review_zh)
        self.root = root
        self.source = root / "source"
        self.source.mkdir()
        run(["git", "init", "--quiet"], cwd=self.source)
        self.catalog = CATALOG_GAMMA if gamma else CATALOG
        sources = {ALPHA: alpha_en, BETA: EN_BETA, SCHEMA_PATH: SCHEMA, "publication-catalog.json": json.dumps(self.catalog)}
        sources.update(extra_sources or {})
        renditions = {REN["ru"]: alpha_ru, REN["zh-Hans"]: alpha_zh, REN["beta-ru"]: RU_BETA, DECOY_PATH: "{}\n"}
        if gamma:
            sources[GAMMA] = EN_GAMMA
            renditions[REN["gamma-ru"]] = RU_GAMMA
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
        if gamma:
            sidecar["renditions"].append({"work": "synthetic-gamma", "language": "ru", "script": "Cyrl", "source": dict(pin(GAMMA, self.c1, EN_GAMMA), language="en"),
                                          "rendition": pin(REN["gamma-ru"], self.c2, RU_GAMMA), "review": copy.deepcopy(REVIEW_NONE), "sections": [{"source": "scope", "rendition": "oblast"}], "counts_as_independent_source": False})
        sidecar = copy.deepcopy(sidecar)  # never share the module-level constants with a mutation
        if mutate_sidecar:
            mutate_sidecar(sidecar)
        self.sidecar = sidecar
        self.fixture_file = None
        if via == "catalog":
            catalog = dict(self.catalog, renditions="publication-renditions.json")
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
        # The sibling link goes to the same interface language; the stale sibling is linked with an explicit English-fallback state.
        self.assertRegex(ru["html"], r'<a href="/ru/science/synthetic-beta/#limits"[^>]*data-target-state="stale"[^>]*data-fallback="en"')
        self.assertNotIn('"/en/science/synthetic-beta/', ru["html"])
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
            sidecar["renditions"][0]["rendition"]["path"] = REN["beta-ru"]  # keep the mirrored layout valid so that the pin is what fails
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
        self.refused("RENDITION_REFERENCE_DROPPED", alpha_ru=swap(RU_ALPHA, "[ТЕСТ СОСЕД](../synthetic-beta/PAPER.md#limits)", "ТЕСТ СОСЕД"))

    def test_footnote_dropped(self):
        self.refused("RENDITION_REFERENCE_DROPPED", alpha_ru=swap(swap(RU_ALPHA, "ТЕСТ СНОСКИ.[^n]", "ТЕСТ СНОСКИ."), "[^n]: ТЕСТ СНОСКА.\n", ""))

    def test_reference_retargeted(self):
        self.refused("RENDITION_REFERENCE_DROPPED", alpha_ru=swap(RU_ALPHA, "PAPER.md#limits)", "PAPER.md#elsewhere)"))

    def test_reference_added(self):
        self.refused("RENDITION_REFERENCE_CHANGED", alpha_ru=swap(RU_ALPHA, "ТЕСТ ЗАВЕРШЕНИЕ.", "ТЕСТ ЗАВЕРШЕНИЕ [ТЕСТ](https://example.invalid/extra)."))

    def test_local_fragment_that_is_a_guessed_anchor(self):
        self.refused("RENDITION_LINK_FRAGMENT", alpha_ru=swap(RU_ALPHA, "(#predely)", "(#limits)"))

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


class RealLayout(Base):
    """The rendition lives at translations/<language>/<source-relative path> (the layout of the knowledge repository)."""

    def test_rendition_path_is_the_mirrored_source_path(self):
        _, _, _, compiled = Scenario(self.root).compile()
        for language in ("ru", "zh-Hans"):
            self.assertEqual(compiled.for_work("synthetic-alpha")[language]["rendition"]["path"], f"translations/{language}/{ALPHA}")

    def test_any_other_rendition_path_is_refused(self):
        wrong = {
            "the previous renditions/ layout": "renditions/ru/synthetic-alpha/PAPER.md",
            "another language directory": REN["zh-Hans"],
            "a renamed file": "translations/ru/papers/synthetic-alpha/README.md",
            "an extra directory": "translations/ru/extra/" + ALPHA,
            "no language directory": "translations/" + ALPHA,
            "the source path itself": ALPHA,
            "a different case": "translations/ru/papers/Synthetic-alpha/PAPER.md",
        }
        for name, path in wrong.items():
            with self.subTest(name):
                def mutate(sidecar, path=path):
                    sidecar["renditions"][0]["rendition"]["path"] = path
                self.refused("RENDITION_LAYOUT", mutate_sidecar=mutate)

    def test_a_source_document_cannot_live_under_translations(self):
        def mutate(sidecar):
            sidecar["renditions"][0]["source"]["path"] = "translations/ru/" + ALPHA
            sidecar["renditions"][0]["rendition"]["path"] = "translations/ru/translations/ru/" + ALPHA
        self.refused("RENDITION_LAYOUT", mutate_sidecar=mutate)


class PinControls(Base):
    def test_rendition_revision_with_the_right_bytes_on_an_unrelated_history(self):
        """A rendition pinned to a commit that holds exactly its bytes but is not an ancestor of the manifest commit is refused."""
        scenario = Scenario(self.root)
        run(["git", "checkout", "--quiet", "--orphan", "side-rendition"], cwd=scenario.source)
        run(["git", "rm", "-r", "-f", "--quiet", "."], cwd=scenario.source)
        side = commit(scenario.source, {REN["ru"]: RU_ALPHA}, "a rendition on an unrelated history")
        run(["git", "checkout", "--quiet", "-f", "-B", "main-line", scenario.head], cwd=scenario.source)
        self.assertEqual(run(["git", "show", f"{side}:{REN['ru']}"], cwd=scenario.source), RU_ALPHA)  # the bytes are right
        run(["git", "merge-base", "--is-ancestor", scenario.c1, scenario.head], cwd=scenario.source)  # the source pin is fine
        sidecar = copy.deepcopy(scenario.sidecar)
        sidecar["renditions"][0]["rendition"]["revision"] = side
        catalog = dict(CATALOG, renditions="publication-renditions.json")
        head = commit(scenario.source, {"publication-renditions.json": json.dumps(sidecar), "publication-catalog.json": json.dumps(catalog)}, "pin the side rendition")
        self.assertNotEqual(subprocess.run(["git", "merge-base", "--is-ancestor", side, head], cwd=scenario.source).returncode, 0)
        scenario.manifest["commit"] = head
        scenario.manifest_path.write_text(json.dumps(scenario.manifest))
        with self.assertRaisesRegex(RenditionError, "^RENDITION_REVISION_PIN:.*not an ancestor"):
            scenario.compile()

    def test_rendition_revision_that_does_not_exist(self):
        def ghost(sidecar):
            sidecar["renditions"][0]["rendition"]["revision"] = "0" * 40
        with self.assertRaisesRegex(RenditionError, "^RENDITION_REVISION_PIN:.*not an ancestor"):
            Scenario(self.root, mutate_sidecar=ghost).compile()


class LinkResolution(Base):
    """Every link of a rendition resolves deterministically from the SOURCE file's directory; nothing is guessed."""
    SCHEMA_LINK = "(../../schemas/synthetic.schema.json)"

    def test_mirrored_invariant_link_resolves_to_the_root_artifact(self):
        """The defect of PR76: ../../schemas/x from translations/ru/... looks like translations/ru/schemas/x, which does not exist."""
        scenario = Scenario(self.root)
        _, _, _, compiled = scenario.compile()
        literal = posixpath.normpath(posixpath.join(posixpath.dirname(REN["ru"]), "../../schemas/synthetic.schema.json"))
        tree = tree_paths(scenario.source, scenario.head)
        self.assertEqual(literal, "translations/ru/schemas/synthetic.schema.json")
        self.assertNotIn(literal, tree)  # a literal resolution would be a broken link
        self.assertIn(SCHEMA_PATH, tree)
        for language in ("ru", "zh-Hans"):
            html = compiled.for_work("synthetic-alpha")[language]["html"]
            self.assertIn(f'href="https://github.com/Arcanada-one/knowledge-contract/blob/{scenario.head}/{SCHEMA_PATH}"', html)
            self.assertNotIn("translations/", html)
        self.assertEqual(compiled.for_work("synthetic-alpha")["ru"]["link_classes"],
                         {"document": 1, "document_fallback": 1, "fragment": 1, "invariant": 1})

    def test_the_english_source_resolves_the_same_invariant_target(self):
        scenario = Scenario(self.root)
        manifest, documents, renderer, compiled = scenario.compile()
        english = renderer.document(next(d for d in documents if d["slug"] == "synthetic-alpha"))["html"]
        target = f'href="https://github.com/Arcanada-one/knowledge-contract/blob/{scenario.head}/{SCHEMA_PATH}"'
        self.assertIn(target, english)
        self.assertIn(target, compiled.for_work("synthetic-alpha")["ru"]["html"])

    def test_invariant_image_is_copied_from_the_canonical_tree(self):
        picture = ("images/synthetic.svg", "<svg xmlns=\"http://www.w3.org/2000/svg\"/>\n")
        scenario = Scenario(self.root, extra_sources=dict([picture]),
                            alpha_en=EN_ALPHA + "\nAn inline ![figure](../../images/synthetic.svg) image.\n",
                            alpha_ru=RU_ALPHA + "\nТЕСТ ![рисунок](../../images/synthetic.svg) РИСУНОК.\n",
                            alpha_zh=ZH_ALPHA + "\n测试![图](../../images/synthetic.svg)图。\n")
        _, _, _, compiled = scenario.compile()
        self.assertIn('src="/assets/documents/images/synthetic.svg"', compiled.for_work("synthetic-alpha")["ru"]["html"])
        self.assertTrue((self.root / "public/assets/documents/images/synthetic.svg").is_file())
        self.assertEqual(compiled.for_work("synthetic-alpha")["ru"]["link_classes"]["invariant"], 2)

    def test_depth_adjusted_invariant_link_is_refused(self):
        """An author who 'fixes' the depth for the translations/ directory points above the canonical root: refused, not guessed."""
        self.refused("RENDITION_LINK_ESCAPES", alpha_ru=swap(RU_ALPHA, self.SCHEMA_LINK, "(../../../../schemas/synthetic.schema.json)"))

    def test_invariant_link_whose_literal_location_exists_only_under_translations(self):
        """The file exists next to the rendition, but not where the source's link points: refused, never silently redirected."""
        scenario_root = Path(tempfile.mkdtemp(dir=self.root))
        scenario = Scenario(scenario_root, alpha_ru=swap(RU_ALPHA, self.SCHEMA_LINK, "(../../schemas/decoy.json)"))
        self.assertIn(DECOY_PATH, tree_paths(scenario.source, scenario.c2))
        with self.assertRaisesRegex(RenditionError, "^RENDITION_LINK_DANGLING:.*schemas/decoy.json"):
            scenario.compile()

    def test_link_that_names_a_translation_file_is_refused(self):
        self.refused("RENDITION_LINK_TRANSLATION", alpha_ru=swap(RU_ALPHA, self.SCHEMA_LINK, "(../../translations/ru/papers/synthetic-beta/PAPER.md)"))

    def test_dangling_links_are_refused(self):
        for name, link in {"missing file": "(../../schemas/missing.json)", "missing sibling document": "(../synthetic-delta/PAPER.md)"}.items():
            with self.subTest(name):
                self.refused("RENDITION_LINK_DANGLING", alpha_ru=swap(RU_ALPHA, self.SCHEMA_LINK, link))

    def test_link_that_escapes_the_repository_root_is_refused(self):
        for name, link in {"relative": "(../../../outside.txt)", "rooted": "(/../outside.txt)", "deep": "(../../../../../../etc/passwd)"}.items():
            with self.subTest(name):
                self.refused("RENDITION_LINK_ESCAPES", alpha_ru=swap(RU_ALPHA, self.SCHEMA_LINK, link))

    def test_unsupported_scheme_is_refused(self):
        self.refused("RENDITION_LINK_SCHEME", alpha_ru=swap(RU_ALPHA, self.SCHEMA_LINK, "(data:text/plain,x)"))

    def test_link_checks_run_before_the_parity_comparison(self):
        """A dangling link is reported as such, not as a dropped reference."""
        with self.assertRaisesRegex(RenditionError, "^RENDITION_LINK_DANGLING:"):
            Scenario(self.root, alpha_ru=swap(RU_ALPHA, self.SCHEMA_LINK, "(../../schemas/missing.json)")).compile()

    def test_sibling_document_links_go_to_the_same_language_route_with_an_explicit_state(self):
        """A shown rendition is linked as such; a stale or missing one is linked with an explicit English-fallback state."""
        scenario = Scenario(self.root, gamma=True,
                            alpha_en=EN_ALPHA + "\nSee [gamma](../synthetic-gamma/PAPER.md).\n",
                            alpha_ru=RU_ALPHA + "\nСМ. [ТЕСТ ГАММА](../synthetic-gamma/PAPER.md).\n",
                            alpha_zh=ZH_ALPHA + "\n参见[测试丙](../synthetic-gamma/PAPER.md)。\n")
        _, _, _, compiled = scenario.compile()
        alpha = compiled.for_work("synthetic-alpha")
        ru, zh = alpha["ru"]["html"], alpha["zh-Hans"]["html"]
        # ru -> gamma: an unreviewed rendition exists and is shown, so the link says so and carries no fallback.
        self.assertRegex(ru, r'<a href="/ru/science/synthetic-gamma/"[^>]*hreflang="ru"[^>]*data-target-state="unreviewed"')
        self.assertNotRegex(ru, r'<a href="/ru/science/synthetic-gamma/"[^>]*data-fallback')
        # ru -> beta: the rendition is stale, so the link carries the English-fallback state and the interface-language label.
        self.assertRegex(ru, r'<a href="/ru/science/synthetic-beta/#limits"[^>]*hreflang="en"[^>]*data-target-state="stale"[^>]*data-fallback="en"')
        self.assertIn("Перевод устарел: английский источник изменился. Вместо него показан закреплённый английский исходный текст.", ru)
        # zh-Hans -> gamma and beta: there is no rendition, so both are explicit fallbacks in the zh-Hans route space.
        self.assertRegex(zh, r'<a href="/zh-Hans/science/synthetic-gamma/"[^>]*hreflang="en"[^>]*data-target-state="missing"[^>]*data-fallback="en"')
        self.assertRegex(zh, r'<a href="/zh-Hans/science/synthetic-beta/#limits"[^>]*data-target-state="missing"[^>]*data-fallback="en"')
        self.assertNotIn('href="/en/', ru + zh)
        counts = alpha["ru"]["link_classes"]
        self.assertEqual((counts["document_shown"], counts["document_fallback"]), (1, 1))

    def test_same_document_fragments_map_through_the_section_mapping(self):
        _, _, _, compiled = Scenario(self.root).compile()
        self.assertIn('href="#predely"', compiled.for_work("synthetic-alpha")["ru"]["html"])
        self.assertIn('href="#jiexian"', compiled.for_work("synthetic-alpha")["zh-Hans"]["html"])

    def test_guessed_same_document_fragment_is_refused(self):
        self.refused("RENDITION_LINK_FRAGMENT", alpha_ru=swap(RU_ALPHA, "(#predely)", "(#no-such-section)"))
        self.refused("RENDITION_LINK_FRAGMENT", alpha_ru=swap(RU_ALPHA, "(#predely)", "(#limits)"))  # the source's anchor is not the rendition's


class DryRun(Base):
    """The read-only audit of a checkout's translations/ directory: every file is an unreviewed draft."""

    def test_counts_per_language_and_nothing_is_written(self):
        scenario = Scenario(self.root)
        before = run(["git", "status", "--porcelain", "--ignored"], cwd=scenario.source)
        report = audit(scenario.source, scenario.c1)
        self.assertEqual(run(["git", "status", "--porcelain", "--ignored"], cwd=scenario.source), before)
        ru, zh = report["languages"]["ru"], report["languages"]["zh-Hans"]
        self.assertEqual((ru["files_found"], ru["path_matches"], ru["absent_documents"], ru["unmatched_paths"]), (2, 2, 0, []))
        self.assertEqual((zh["files_found"], zh["path_matches"], zh["absent_documents"]), (1, 1, 1))
        self.assertEqual(ru["states"], {"stale": 1, "unreviewed": 1})  # nothing is reviewed, whatever the sidecar says
        self.assertEqual(zh["states"], {"unreviewed": 1})
        self.assertEqual(ru["link_classes"], {"document": 1, "document_fallback": 1, "fragment": 1, "invariant": 1})
        self.assertEqual(ru["literal_resolution_missing"], {"invariant": 1})  # translations/ru/schemas/... does not exist
        self.assertEqual((ru["unresolved_links"], ru["parity_failures"], ru["other_failures"]), ({}, {}, {}))
        self.assertEqual((ru["files_clean"], ru["files_with_a_failure"]), (2, 0))
        self.assertEqual(report["files"], [])

    def test_unresolved_links_and_parity_failures_are_counted_not_fatal(self):
        scenario = Scenario(self.root, alpha_ru=swap(swap(RU_ALPHA, "(../../schemas/synthetic.schema.json)", "(../../schemas/missing.json)"),
                                                     "| Key | Value |\n|---|---|\n| k | v |\n", ""))
        report = audit(scenario.source, scenario.c1)
        ru = report["languages"]["ru"]
        self.assertEqual(ru["unresolved_links"], {"RENDITION_LINK_DANGLING": 1})
        self.assertEqual(ru["parity_failures"], {"RENDITION_STRUCTURE_MISMATCH": 1})
        self.assertEqual((ru["files_clean"], ru["files_with_a_failure"]), (1, 1))
        self.assertEqual({(f["stage"], f["code"]) for f in report["files"]}, {("links", "RENDITION_LINK_DANGLING"), ("parity", "RENDITION_STRUCTURE_MISMATCH")})

    def test_a_misplaced_translation_is_counted_as_unmatched(self):
        scenario = Scenario(self.root)
        stray = commit(scenario.source, {"translations/zh-Hans/synthetic-alpha.md": ZH_ALPHA}, "a translation outside the mirrored layout")
        report = audit(scenario.source, scenario.c1)
        zh = report["languages"]["zh-Hans"]
        self.assertEqual((zh["files_found"], zh["path_matches"], zh["unmatched_paths"]), (2, 1, ["translations/zh-Hans/synthetic-alpha.md"]))


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
