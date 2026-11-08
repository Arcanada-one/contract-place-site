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
from publication_checks import RENDITION_FALLBACK, RENDITION_INDEXED, RENDITION_ISSUES, RENDITION_LABELS, check_renditions
from renditions import RenditionError, classify_link, compile_renditions, normalize_target, tree_paths
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

СМ. [ТЕСТ СОСЕД](../synthetic-beta/PAPER.md#limits), [ТЕСТ ПРЕДЕЛЫ](#predely) И [ТЕСТ СХЕМА](../../../../schemas/synthetic.schema.json).

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

参见[测试邻篇](../../../../papers/synthetic-beta/PAPER.md#limits)、[测试界限](#jiexian)和[测试模式](../../../../schemas/synthetic.schema.json)。

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
AUTHOR = "test-fixture-author"
EVIDENCE_PATH = "reviews/synthetic-review-record.md"
EVIDENCE_TEXT = "SYNTHETIC TEST REVIEW RECORD. Not a real review.\n"


def review_ok(sections=("rules", "limits"), coverage="full"):
    """A complete synthetic review object. "@source" / "@rendition" / "@evidence" are bound to the real blobs by the Scenario."""
    return {"reviewer": {"identity": "test-fixture-reviewer", "kind": "agent", "independent_of_author": True,
                         "independence_basis": "synthetic: a different fixture identity than the author, no shared prompt"},
            "method": "synthetic test review; no real review took place",
            "reviewed": {"source_blob": "@source", "rendition_blob": "@rendition"},
            "scope": {"coverage": coverage, "sections": list(sections), "claims": ["synthetic claim one"], "proofs": []},
            "corrections": [], "reviewed_at": "2026-01-02T03:04:05Z",
            "limitations": "SYNTHETIC TEST DATA; agent-only, non-blind",
            "evidence": {"path": EVIDENCE_PATH, "blob": "@evidence"}}


REVIEW_OK = review_ok()
REVIEW_NONE = None  # an author draft: the entry carries no review object
SECTIONS_RU = [{"source": "rules", "rendition": "pravila"}, {"source": "limits", "rendition": "predely"}]
SECTIONS_ZH = [{"source": "rules", "rendition": "guize"}, {"source": "limits", "rendition": "jiexian"}]
ALPHA, BETA, GAMMA = "papers/synthetic-alpha/PAPER.md", "papers/synthetic-beta/PAPER.md", "papers/synthetic-gamma/PAPER.md"
# The real layout of the knowledge repository: translations/<language>/<same source-relative path>.
REN = {"ru": "translations/ru/" + ALPHA, "zh-Hans": "translations/zh-Hans/" + ALPHA, "beta-ru": "translations/ru/" + BETA, "gamma-ru": "translations/ru/" + GAMMA}
SCHEMA_PATH, DECOY_PATH = "schemas/synthetic.schema.json", "translations/ru/schemas/decoy.json"  # the decoy exists only where a link written from the SOURCE depth would land
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
                 gamma=False, extra_sources=None, review_gamma=REVIEW_NONE, author=AUTHOR):
        review_ru, review_zh, review_gamma = copy.deepcopy(review_ru), copy.deepcopy(review_zh), copy.deepcopy(review_gamma)
        self.root = root
        self.source = root / "source"
        self.source.mkdir()
        run(["git", "init", "--quiet"], cwd=self.source)
        self.catalog = CATALOG_GAMMA if gamma else CATALOG
        sources = {ALPHA: alpha_en, BETA: EN_BETA, SCHEMA_PATH: SCHEMA, "publication-catalog.json": json.dumps(self.catalog)}
        sources.update(extra_sources or {})
        renditions = {REN["ru"]: alpha_ru, REN["zh-Hans"]: alpha_zh, REN["beta-ru"]: RU_BETA, DECOY_PATH: "{}\n", EVIDENCE_PATH: EVIDENCE_TEXT}
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
        def entry(work, language, script, doc_path, doc_text, rendition_path, rendition_text, review, sections):
            built = {"work": work, "language": language, "script": script, "source": dict(pin(doc_path, self.c1, doc_text), language="en"),
                     "rendition": pin(rendition_path, self.c2, rendition_text), "sections": sections, "counts_as_independent_source": False}
            if review is not None:
                built["review"] = self.bind(review, built)
                built["author"] = {"identity": author}
            return built
        sidecar = {"schema_version": 2, "kind": "arcanada-publication-renditions", "edition": "1.1", "renditions": [
            entry("synthetic-alpha", "ru", "Cyrl", ALPHA, alpha_en, REN["ru"], alpha_ru, review_ru, SECTIONS_RU),
            entry("synthetic-alpha", "zh-Hans", "Hans", ALPHA, alpha_en, REN["zh-Hans"], alpha_zh, review_zh, SECTIONS_ZH),
            entry("synthetic-beta", "ru", "Cyrl", BETA, EN_BETA, REN["beta-ru"], RU_BETA, review_ok(("limits",)), [{"source": "limits", "rendition": "predely"}]),
        ]}
        if gamma:
            sidecar["renditions"].append(entry("synthetic-gamma", "ru", "Cyrl", GAMMA, EN_GAMMA, REN["gamma-ru"], RU_GAMMA, review_gamma, [{"source": "scope", "rendition": "oblast"}]))
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

    def bind(self, review: dict, entry: dict) -> dict:
        """Replace the @source / @rendition / @evidence placeholders by the real git blob ids of the pinned bytes."""
        def blob(revision, path):
            return run(["git", "rev-parse", f"{revision}:{path}"], cwd=self.source).strip()
        values = {"@source": blob(entry["source"]["revision"], entry["source"]["path"]),
                  "@rendition": blob(entry["rendition"]["revision"], entry["rendition"]["path"]),
                  "@evidence": blob(self.c2, EVIDENCE_PATH)}
        return json.loads(json.dumps(review), object_hook=lambda d: {k: values.get(v, v) if isinstance(v, str) else v for k, v in d.items()})

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
        _, _, _, compiled = Scenario(self.root, review_ru=review_ok(("rules",), "partial")).compile()
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

    # --- review claims (ML05); the binding of a complete review is covered by ReviewGate ---
    def test_a_review_with_a_missing_fact_cannot_be_published(self):
        for field in ("reviewer", "method", "reviewed", "scope", "corrections", "reviewed_at", "limitations", "evidence"):
            with self.subTest(field=field):
                def drop(sidecar, field=field):
                    del sidecar["renditions"][0]["review"][field]
                self.refused("RENDITION_REVIEW_UNEVIDENCED", mutate_sidecar=drop)

    def test_a_review_without_an_author_identity_cannot_test_independence(self):
        def drop(sidecar):
            del sidecar["renditions"][0]["author"]
        self.refused("RENDITION_REVIEW_UNEVIDENCED", mutate_sidecar=drop)

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
        self.refused("RENDITION_REFERENCE_DROPPED", alpha_ru=swap(RU_ALPHA, "(../../../../schemas/synthetic.schema.json)", "(../../../../papers/synthetic-beta/PAPER.md)"))

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
    """Links of a rendition are ordinary relative Markdown: they resolve literally from the rendition file's own directory, as
    GitHub renders them; nothing is guessed. Written in the rendition at translations/ru/papers/synthetic-alpha/PAPER.md."""
    SCHEMA_LINK = "(../../../../schemas/synthetic.schema.json)"
    SOURCE_DEPTH_LINK = "(../../schemas/synthetic.schema.json)"  # correct from papers/synthetic-alpha/, wrong from translations/ru/papers/synthetic-alpha/

    def test_literal_invariant_link_resolves_to_the_root_artifact(self):
        """Read from the rendition's own directory the link names a real root file; the page links the same pinned blob as the English page."""
        scenario = Scenario(self.root)
        _, _, _, compiled = scenario.compile()
        tree = tree_paths(scenario.source, scenario.head)
        literal = posixpath.normpath(posixpath.join(posixpath.dirname(REN["ru"]), "../../../../schemas/synthetic.schema.json"))
        self.assertEqual(literal, SCHEMA_PATH)
        self.assertIn(literal, tree)
        for language in ("ru", "zh-Hans"):
            html = compiled.for_work("synthetic-alpha")[language]["html"]
            self.assertIn(f'href="https://github.com/Arcanada-one/knowledge-contract/blob/{scenario.head}/{SCHEMA_PATH}"', html)
            self.assertNotIn("translations/", html)
        self.assertEqual(compiled.for_work("synthetic-alpha")["ru"]["link_classes"], {"document_fallback": 1, "fragment": 1, "invariant": 1, "peer": 1})
        self.assertEqual(compiled.for_work("synthetic-alpha")["zh-Hans"]["link_classes"], {"document": 1, "document_fallback": 1, "fragment": 1, "invariant": 1})

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
                            alpha_ru=RU_ALPHA + "\nТЕСТ ![рисунок](../../../../images/synthetic.svg) РИСУНОК.\n",
                            alpha_zh=ZH_ALPHA + "\n测试![图](../../../../images/synthetic.svg)图。\n")
        _, _, _, compiled = scenario.compile()
        self.assertIn('src="/assets/documents/images/synthetic.svg"', compiled.for_work("synthetic-alpha")["ru"]["html"])
        self.assertTrue((self.root / "public/assets/documents/images/synthetic.svg").is_file())
        self.assertEqual(compiled.for_work("synthetic-alpha")["ru"]["link_classes"]["invariant"], 2)

    def test_a_link_written_with_the_depth_of_the_source_directory_is_refused(self):
        """The previous (mirrored) convention: ../../schemas/x from translations/ru/papers/y/ is translations/ru/schemas/x. That path
        is under translations/ but is no rendition of a catalogue document, so it is refused; it is never silently re-resolved
        from the source's directory (rules 3 and 6). Written with one level fewer it is still under translations/ and refused."""
        scenario = Scenario(self.root)
        tree = tree_paths(scenario.source, scenario.head)
        self.assertNotIn("translations/ru/schemas/synthetic.schema.json", tree)
        self.refused("RENDITION_LINK_TRANSLATION", alpha_ru=swap(RU_ALPHA, self.SCHEMA_LINK, self.SOURCE_DEPTH_LINK))
        self.refused("RENDITION_LINK_TRANSLATION", alpha_ru=swap(RU_ALPHA, self.SCHEMA_LINK, "(../../../schemas/synthetic.schema.json)"))

    def test_a_source_depth_link_that_lands_on_an_uncatalogued_translation_path_is_refused(self):
        """The decoy exists under translations/ru/, so the file is there, but it is not a rendition of a catalogue document."""
        scenario_root = Path(tempfile.mkdtemp(dir=self.root))
        scenario = Scenario(scenario_root, alpha_ru=swap(RU_ALPHA, self.SCHEMA_LINK, "(../../schemas/decoy.json)"))
        self.assertIn(DECOY_PATH, tree_paths(scenario.source, scenario.c2))
        with self.assertRaisesRegex(RenditionError, "^RENDITION_LINK_TRANSLATION:.*translations/ru/schemas/decoy.json"):
            scenario.compile()

    def test_links_into_translations_other_than_a_pinned_rendition_of_this_language_are_refused(self):
        for name, link in {"another language": "(../../../zh-Hans/papers/synthetic-alpha/PAPER.md)",
                           "the coverage file": "(../../../EDITION-1.1-COVERAGE.md)",
                           "a path that is no catalogue document": "(../synthetic-delta/PAPER.md)",
                           "the translations directory": "(../../../ru)"}.items():
            with self.subTest(name):
                self.refused("RENDITION_LINK_TRANSLATION", alpha_ru=swap(RU_ALPHA, self.SCHEMA_LINK, link))

    def test_a_translated_peer_must_be_a_pinned_entry_of_the_sidecar(self):
        """gamma's Russian draft exists in the tree, but the sidecar does not pin it: no link to an unpinned draft (rule 2)."""
        def unpin(sidecar):
            sidecar["renditions"] = [e for e in sidecar["renditions"] if e["work"] != "synthetic-gamma"]
        self.refused("RENDITION_LINK_UNPINNED", gamma=True, mutate_sidecar=unpin,
                     alpha_en=EN_ALPHA + "\nSee [gamma](../synthetic-gamma/PAPER.md).\n",
                     alpha_ru=RU_ALPHA + "\nСМ. [ТЕСТ ГАММА](../synthetic-gamma/PAPER.md).\n")
        # zh-Hans has no beta entry: the same literal peer link in its text is refused as unpinned, not silently sent to English.
        self.refused("RENDITION_LINK_UNPINNED", alpha_zh=swap(ZH_ALPHA, "(../../../../papers/synthetic-beta/PAPER.md#limits)", "(../synthetic-beta/PAPER.md#limits)"))

    def test_dangling_links_are_refused(self):
        for name, link in {"missing root file": "(../../../../schemas/missing.json)", "missing English document": "(../../../../papers/synthetic-delta/PAPER.md)"}.items():
            with self.subTest(name):
                self.refused("RENDITION_LINK_DANGLING", alpha_ru=swap(RU_ALPHA, self.SCHEMA_LINK, link))

    def test_link_that_escapes_the_repository_root_is_refused(self):
        for name, link in {"relative": "(../../../../../outside.txt)", "rooted": "(/../outside.txt)", "deep": "(../../../../../../../../etc/passwd)"}.items():
            with self.subTest(name):
                self.refused("RENDITION_LINK_ESCAPES", alpha_ru=swap(RU_ALPHA, self.SCHEMA_LINK, link))

    def test_unsupported_scheme_is_refused(self):
        self.refused("RENDITION_LINK_SCHEME", alpha_ru=swap(RU_ALPHA, self.SCHEMA_LINK, "(data:text/plain,x)"))

    def test_link_checks_run_before_the_parity_comparison(self):
        """A dangling link is reported as such, not as a dropped reference."""
        with self.assertRaisesRegex(RenditionError, "^RENDITION_LINK_DANGLING:"):
            Scenario(self.root, alpha_ru=swap(RU_ALPHA, self.SCHEMA_LINK, "(../../../../schemas/missing.json)")).compile()

    def test_a_link_to_the_english_original_is_allowed_and_compares_equal_to_the_peer_form(self):
        """Rule 4: the rendition may deliberately name the root English document; the target identity is the same as a translated peer's."""
        _, _, _, compiled = Scenario(self.root, alpha_ru=swap(RU_ALPHA, "(../synthetic-beta/PAPER.md#limits)", "(../../../../papers/synthetic-beta/PAPER.md#limits)")).compile()
        ru = compiled.for_work("synthetic-alpha")["ru"]
        self.assertEqual(ru["link_classes"], {"document": 1, "document_fallback": 1, "fragment": 1, "invariant": 1})
        self.assertRegex(ru["html"], r'<a href="/ru/science/synthetic-beta/#limits"[^>]*data-target-state="stale"[^>]*data-fallback="en"')

    def test_sibling_document_links_go_to_the_same_language_route_with_an_explicit_state(self):
        """A shown rendition is linked as such; a stale or missing one is linked with an explicit English-fallback state."""
        scenario = Scenario(self.root, gamma=True,
                            alpha_en=EN_ALPHA + "\nSee [gamma](../synthetic-gamma/PAPER.md).\n",
                            alpha_ru=RU_ALPHA + "\nСМ. [ТЕСТ ГАММА](../synthetic-gamma/PAPER.md).\n",
                            alpha_zh=ZH_ALPHA + "\n参见[测试丙](../../../../papers/synthetic-gamma/PAPER.md)。\n")
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
        self.assertEqual((counts["document_shown"], counts["document_fallback"], counts["peer"]), (1, 1, 2))

    def test_a_fragment_into_a_translated_peer_maps_to_the_source_anchor(self):
        """beta's Russian text calls its section #predely, the source #limits: the emitted link and the compared identity use #limits."""
        _, _, _, compiled = Scenario(self.root, alpha_ru=swap(RU_ALPHA, "PAPER.md#limits)", "PAPER.md#predely)")).compile()
        self.assertIn('href="/ru/science/synthetic-beta/#limits"', compiled.for_work("synthetic-alpha")["ru"]["html"])

    def test_same_document_fragments_map_through_the_section_mapping(self):
        _, _, _, compiled = Scenario(self.root).compile()
        self.assertIn('href="#predely"', compiled.for_work("synthetic-alpha")["ru"]["html"])
        self.assertIn('href="#jiexian"', compiled.for_work("synthetic-alpha")["zh-Hans"]["html"])

    def test_guessed_same_document_fragment_is_refused(self):
        self.refused("RENDITION_LINK_FRAGMENT", alpha_ru=swap(RU_ALPHA, "(#predely)", "(#no-such-section)"))
        self.refused("RENDITION_LINK_FRAGMENT", alpha_ru=swap(RU_ALPHA, "(#predely)", "(#limits)"))  # the source's anchor is not the rendition's


LABEL_LINE = re.compile(r"^\s+(?:'([\w-]+)'|([\w-]+)): L\('((?:[^'\\]|\\.)*)', '((?:[^'\\]|\\.)*)', '((?:[^'\\]|\\.)*)'\)", re.M)


class Labels(unittest.TestCase):
    """Every state is labelled in all three languages, the client and the checker agree, and the review labels say what they are."""
    STATES = ("reviewed", "partially-reviewed", "unreviewed", "stale", "missing")
    LOCALES = ("en", "ru", "zh-Hans")

    def test_all_states_are_labelled_in_all_three_languages(self):
        self.assertEqual(tuple(RENDITION_LABELS), self.STATES)
        for state in self.STATES:
            self.assertEqual(set(RENDITION_LABELS[state]), set(self.LOCALES), state)
            for locale in self.LOCALES:
                self.assertTrue(RENDITION_LABELS[state][locale].strip(), (state, locale))
            self.assertEqual(len({RENDITION_LABELS[state][l] for l in self.LOCALES}), 3, f"{state}: the three languages must differ")
        self.assertEqual(set(RENDITION_FALLBACK), set(self.LOCALES))
        for code in ("RENDITION_REVIEW_UNBOUND", "RENDITION_REVIEW_NOT_INDEPENDENT"):
            self.assertEqual(set(RENDITION_ISSUES[code]), set(self.LOCALES), code)
        for locale in self.LOCALES:  # no two states share a label in one language
            self.assertEqual(len({RENDITION_LABELS[s][locale] for s in self.STATES}), len(self.STATES), locale)

    def test_the_client_script_and_the_output_check_carry_identical_wording(self):
        labels = {m[1] or m[2]: (m[3], m[4], m[5]) for m in LABEL_LINE.finditer((ROOT / "src/renditions/renditions.js").read_text(encoding="utf-8"))}
        for state in self.STATES:
            self.assertEqual(labels[state], tuple(RENDITION_LABELS[state][l] for l in self.LOCALES), state)
        self.assertEqual(labels["fallback"], tuple(RENDITION_FALLBACK[l] for l in self.LOCALES))
        self.assertEqual(labels["issueUnbound"], tuple(RENDITION_ISSUES["RENDITION_REVIEW_UNBOUND"][l] for l in self.LOCALES))
        self.assertEqual(labels["issueIndependent"], tuple(RENDITION_ISSUES["RENDITION_REVIEW_NOT_INDEPENDENT"][l] for l in self.LOCALES))
        for key, texts in labels.items():  # every interface string exists in all three languages
            self.assertTrue(all(t.strip() for t in texts), key)

    def test_wording_given_by_kc_brain_is_used_verbatim(self):
        """KC-Brain letter 7b4d2cc6 (5)."""
        self.assertEqual(RENDITION_LABELS["unreviewed"]["ru"], "Перевод без смысловой рецензии")
        self.assertEqual(RENDITION_LABELS["unreviewed"]["zh-Hans"], "尚未经语义审校的译文")
        self.assertEqual(RENDITION_LABELS["reviewed"]["ru"], "Перевод проверен в указанном объёме (внутренняя агентная рецензия)")
        self.assertEqual(RENDITION_LABELS["reviewed"]["zh-Hans"], "译文已按所述范围完成内部代理审查")

    def test_review_labels_say_internal_and_never_external_or_peer_review(self):
        for state in ("reviewed", "partially-reviewed"):
            for locale, marker in (("en", "internal agent review"), ("ru", "внутренняя агентная рецензия"), ("zh-Hans", "内部代理审查")):
                self.assertIn(marker, RENDITION_LABELS[state][locale], (state, locale))
        for state in self.STATES:
            for locale in self.LOCALES:
                label = RENDITION_LABELS[state][locale].lower()
                for forbidden in ("external", "peer", "внешн", "рецензированный", "同行", "外部", "已审校译文"):
                    self.assertNotIn(forbidden, label, (state, locale))
        for locale in self.LOCALES:  # an unreviewed rendition's label makes no review claim
            self.assertNotIn("internal", RENDITION_LABELS["unreviewed"][locale].lower())
            self.assertNotIn("внутренн", RENDITION_LABELS["unreviewed"][locale])
            self.assertNotIn("内部", RENDITION_LABELS["unreviewed"][locale])


class ReviewGate(Base):
    """A reviewed state needs a closed, bound, independent review. Anything weaker renders as unreviewed with a typed issue."""

    def state(self, **kwargs):
        _, _, _, compiled = Scenario(Path(tempfile.mkdtemp(dir=self.root)), **kwargs).compile()
        record = compiled.for_work("synthetic-alpha")["ru"]
        return record["state"], record.get("review_issue"), compiled

    def mutated(self, change, **kwargs):
        review = review_ok()
        change(review)
        return self.state(review_ru=review, **kwargs)

    def test_a_bound_independent_review_is_reviewed_and_keeps_its_facts(self):
        state, issue, compiled = self.state()
        record = compiled.for_work("synthetic-alpha")["ru"]
        self.assertEqual((state, issue), ("reviewed", None))
        self.assertEqual(record["review"]["reviewer"]["identity"], "test-fixture-reviewer")
        self.assertEqual(record["review"]["author"], AUTHOR)
        self.assertEqual(record["review"]["evidence"]["path"], EVIDENCE_PATH)
        self.assertIn(EVIDENCE_PATH, record["review"]["evidence"]["url"])
        provenance = {(e["work"], e["language"]): e for e in compiled.entries}[("synthetic-alpha", "ru")]
        self.assertEqual((provenance["review_status"], provenance["review_scope"], provenance["review_issue"]), ("internal-agent-review", "full", None))

    def test_no_review_object_is_an_unreviewed_author_draft(self):
        _, _, _, compiled = Scenario(self.root).compile()
        zh = compiled.for_work("synthetic-alpha")["zh-Hans"]
        self.assertEqual((zh["state"], zh["review"], zh["review_issue"]), ("unreviewed", None, None))

    def test_partial_scope_is_partially_reviewed(self):
        state, issue, _ = self.state(review_ru=review_ok(("rules",), "partial"))
        self.assertEqual((state, issue), ("partially-reviewed", None))

    def test_a_two_section_scope_never_yields_a_whole_paper_reviewed_label(self):
        """FID-01/02 style: a review whose scope names two sections of a longer paper is partial, never reviewed."""
        state, issue, compiled = self.state(review_ru=review_ok(("rules", "limits"), "partial"))
        self.assertEqual((state, issue), ("partially-reviewed", None))
        self.assertNotEqual(state, "reviewed")
        provenance = {(e["work"], e["language"]): e for e in compiled.entries}[("synthetic-alpha", "ru")]
        self.assertEqual((provenance["review_status"], provenance["review_scope"]), ("internal-agent-review", "partial"))

    def test_reviewed_source_blob_must_equal_the_pinned_source_blob(self):
        state, issue, compiled = self.mutated(lambda r: r["reviewed"].update(source_blob="1" * 40))
        self.assertEqual((state, issue["code"]), ("unreviewed", "RENDITION_REVIEW_UNBOUND"))
        self.assertIsNone(compiled.for_work("synthetic-alpha")["ru"]["review"])
        self.assertIn("html", compiled.for_work("synthetic-alpha")["ru"])  # the page is still built, rendered as unreviewed

    def test_reviewed_rendition_blob_must_equal_the_pinned_rendition_blob(self):
        for blob in ("2" * 40, "@source"):  # a made-up blob, and the blob of the English source in place of the translation
            with self.subTest(blob=blob):
                state, issue, _ = self.mutated(lambda r, blob=blob: r["reviewed"].update(rendition_blob=blob))
                self.assertEqual((state, issue and issue["code"]), ("unreviewed", "RENDITION_REVIEW_UNBOUND"))

    def test_review_of_another_edition_of_the_rendition_is_unbound(self):
        """The translation is rewritten after the review: the sidecar pins the new bytes, the review still names the old blob."""
        review = review_ok()
        review["reviewed"]["rendition_blob"] = run(["git", "hash-object", "--stdin"], RU_ALPHA).strip()
        state, issue, _ = self.state(alpha_ru=RU_ALPHA + "\nТЕСТ ДОБАВЛЕНИЕ.\n", review_ru=review)
        self.assertEqual((state, issue and issue["code"]), ("unreviewed", "RENDITION_REVIEW_UNBOUND"))

    def test_evidence_must_be_a_pinned_path_and_blob_that_exist(self):
        for change in (lambda r: r["evidence"].update(blob="3" * 40),                         # wrong blob
                       lambda r: r["evidence"].update(path="reviews/missing.md"),             # the path is not in the publication commit
                       lambda r: r["evidence"].update(path=ALPHA)):                           # an existing file that is not the evidence
            state, issue, _ = self.mutated(change)
            self.assertEqual((state, issue and issue["code"]), ("unreviewed", "RENDITION_REVIEW_UNBOUND"))

    def test_evidence_cannot_be_a_bare_url_or_a_name(self):
        for value in ("https://example.invalid/review", "test-evidence-ref", "http://example.invalid/x/y.md", ["x"], "../outside.md", "/abs/path.md", ""):
            with self.subTest(value=value):
                def change(sidecar, value=value):
                    sidecar["renditions"][0]["review"]["evidence"] = value if not isinstance(value, str) or "/" not in value or value.startswith("..") or value.startswith("/") else {"path": value, "blob": "4" * 40}
                self.refused("RENDITION_SIDECAR_SCHEMA", mutate_sidecar=change)

    def test_a_reviewer_not_independent_of_the_author_never_renders_reviewed(self):
        state, issue, _ = self.mutated(lambda r: r["reviewer"].update(independent_of_author=False))
        self.assertEqual((state, issue["code"]), ("unreviewed", "RENDITION_REVIEW_NOT_INDEPENDENT"))

    def test_reviewer_identity_equal_to_the_author_never_renders_reviewed(self):
        for identity in (AUTHOR, "Test-Fixture-Author", AUTHOR.upper()):
            with self.subTest(identity=identity):
                review = review_ok()
                review["reviewer"]["identity"] = identity
                state, issue, _ = self.state(review_ru=review)
                self.assertEqual((state, issue["code"]), ("unreviewed", "RENDITION_REVIEW_NOT_INDEPENDENT"))

    def test_independence_must_be_stated_with_a_basis(self):
        for change in (lambda s: s["renditions"][0]["review"]["reviewer"].pop("independence_basis"),
                       lambda s: s["renditions"][0]["review"]["reviewer"].update(independence_basis=""),
                       lambda s: s["renditions"][0]["review"]["reviewer"].update(independent_of_author="yes"),
                       lambda s: s["renditions"][0]["review"]["reviewer"].pop("independent_of_author")):
            self.refused("RENDITION_SIDECAR_SCHEMA", mutate_sidecar=change)

    def test_scope_must_name_real_sections_and_full_coverage_must_cover_them_all(self):
        for review, label in ((review_ok(("rules",), "full"), "full coverage that omits a section"),
                              (review_ok(("rules", "nonexistent"), "partial"), "a section that is not in the source"),
                              (review_ok(("rules", "rules"), "partial"), "a repeated section")):
            state, issue, _ = self.state(review_ru=review)
            self.assertEqual((state, issue and issue["code"]), ("unreviewed", "RENDITION_REVIEW_UNBOUND"), label)
        review = review_ok()
        review["corrections"] = [{"section": "nonexistent", "description": "x"}]
        self.assertEqual(self.state(review_ru=review)[1]["code"], "RENDITION_REVIEW_UNBOUND")

    def test_corrections_are_recorded_and_may_be_empty(self):
        review = review_ok()
        review["corrections"] = [{"section": "rules", "description": "synthetic correction"}]
        state, issue, compiled = self.state(review_ru=review)
        self.assertEqual((state, issue), ("reviewed", None))
        self.assertEqual(compiled.for_work("synthetic-alpha")["ru"]["review"]["corrections"], review["corrections"])

    def test_malformed_review_fields_are_refused(self):
        cases = {
            "kind human (no label exists for it)": lambda r: r["reviewer"].update(kind="human"),
            "kind unknown": lambda r: r["reviewer"].update(kind="committee"),
            "time without Z": lambda r: r.update(reviewed_at="2026-01-02T03:04:05+00:00"),
            "time date only": lambda r: r.update(reviewed_at="2026-01-02"),
            "time impossible": lambda r: r.update(reviewed_at="2026-13-40T25:61:61Z"),
            "coverage unknown": lambda r: r["scope"].update(coverage="mostly"),
            "no sections in scope": lambda r: r["scope"].update(sections=[]),
            "claims not a list": lambda r: r["scope"].update(claims="all"),
            "blob not hex": lambda r: r["reviewed"].update(source_blob="zz"),
            "blob abbreviated": lambda r: r["reviewed"].update(rendition_blob="abc123"),
            "corrections not a list": lambda r: r.update(corrections="none"),
            "correction unknown field": lambda r: r.update(corrections=[{"section": "rules", "description": "x", "by": "y"}]),
            "method empty": lambda r: r.update(method=""),
            "limitations empty": lambda r: r.update(limitations=" "),
            "unknown field in review": lambda r: r.update(status="reviewed"),
            "unknown field in reviewer": lambda r: r["reviewer"].update(url="https://example.invalid"),
            "unknown field in scope": lambda r: r["scope"].update(level="high"),
            "unknown field in reviewed": lambda r: r["reviewed"].update(sha256="0" * 64),
            "unknown field in evidence": lambda r: r["evidence"].update(url="https://example.invalid"),
        }
        for label, change in cases.items():
            with self.subTest(label):
                def mutate(sidecar, change=change):
                    change(sidecar["renditions"][0]["review"])
                sub = tempfile.mkdtemp(dir=self.root)
                with self.assertRaisesRegex(RenditionError, "^RENDITION_(SIDECAR_SCHEMA|REVIEW_UNEVIDENCED):"):
                    Scenario(Path(sub), mutate_sidecar=mutate).compile()

    def test_the_old_review_shape_and_schema_version_are_refused(self):
        def old_shape(sidecar):
            sidecar["renditions"][0]["review"] = {"status": "reviewed", "scope": "full", "method": "m", "reviewers": [{"kind": "agent", "ref": "x"}], "evidence": ["ref"], "limits": "l"}
        self.refused("RENDITION_SIDECAR_SCHEMA|RENDITION_REVIEW_UNEVIDENCED", mutate_sidecar=old_shape)

        def old_version(sidecar):
            sidecar["schema_version"] = 1
        self.refused("RENDITION_SIDECAR_SCHEMA", mutate_sidecar=old_version)

    def test_a_changed_source_is_stale_whatever_the_review_says(self):
        state, issue, _ = self.state(after_renditions={ALPHA: EN_ALPHA + "\nA later source edit.\n"})
        self.assertEqual((state, issue), ("stale", None))

    def test_an_unbound_claim_in_the_catalogue_sidecar_does_not_stop_the_build_but_the_state_is_typed(self):
        _, _, _, compiled = Scenario(Path(tempfile.mkdtemp(dir=self.root)), review_ru=dict(review_ok(), reviewed={"source_blob": "5" * 40, "rendition_blob": "6" * 40})).compile()
        ru = compiled.for_work("synthetic-alpha")["ru"]
        self.assertEqual((ru["state"], ru["review_issue"]["code"]), ("unreviewed", "RENDITION_REVIEW_UNBOUND"))
        entries = {(e["work"], e["language"]): e for e in compiled.entries}
        self.assertEqual(entries[("synthetic-alpha", "ru")]["review_issue"], "RENDITION_REVIEW_UNBOUND")
        self.assertEqual(entries[("synthetic-alpha", "ru")]["review_status"], "unreviewed")

    def test_a_link_to_an_unbound_rendition_is_linked_as_unreviewed(self):
        review = review_ok()
        review["reviewed"]["source_blob"] = "7" * 40
        _, _, _, compiled = Scenario(Path(tempfile.mkdtemp(dir=self.root)), gamma=True, review_gamma=review).compile()
        self.assertEqual(compiled.for_work("synthetic-gamma")["ru"]["state"], "unreviewed")


class RealPR76LinkIdentity(unittest.TestCase):
    """Logical link identity against the EXACT PR76 46566787 href spellings (R-K8-LINK-BASE1 + Agent-Brain 6717017943).

    Red-before on head 82cdcdb0: resolving these hrefs from the English SOURCE directory raises RENDITION_LINK_ESCAPES
    (measured separately in the round-3 worker report). Green here: resolve from the rendition file directory, map to one
    canonical identity, and refuse the listed negatives with the existing RENDITION_LINK_* codes.
    """
    # Exact relative hrefs from knowledge-contract@46566787 translations/*/engineering/specifications/book-package/SPECIFICATION.md
    BOOK = "engineering/specifications/book-package/SPECIFICATION.md"
    REN_RU = "translations/ru/engineering/specifications/book-package/SPECIFICATION.md"
    REN_ZH = "translations/zh-Hans/engineering/specifications/book-package/SPECIFICATION.md"
    SCHEMA_HREF = "../../../../../schemas/book-package.schema.json"  # PR76 RU and zh-Hans, line 22
    SCHEMA_CANON = "schemas/book-package.schema.json"
    SIBLING_HREF = "../knowledge-contract-core/SPECIFICATION.md"
    SIBLING_CANON = "engineering/specifications/knowledge-contract-core/SPECIFICATION.md"
    EN_ONLY = "engineering/specifications/reuse-policy/SPECIFICATION.md"  # no rendition in the pilot set for this check

    def setUp(self):
        self.by_path = {
            self.BOOK: {"slug": "book-package", "route": "/en/engineering/book-package/"},
            self.SIBLING_CANON: {"slug": "knowledge-contract-core", "route": "/en/engineering/knowledge-contract-core/"},
            self.EN_ONLY: {"slug": "reuse-policy", "route": "/en/engineering/reuse-policy/"},
        }
        self.tree = frozenset({
            ".", self.BOOK, self.REN_RU, self.REN_ZH, self.SCHEMA_CANON, self.SIBLING_CANON, self.EN_ONLY,
            "translations/ru/" + self.SIBLING_CANON, "translations/zh-Hans/" + self.SIBLING_CANON,
        })
        self.pinned = frozenset({self.BOOK, self.SIBLING_CANON})  # reuse-policy deliberately unpinned as a peer

    def test_red_before_source_base_escapes_on_exact_pr76_href(self):
        """Document the 82cdcdb0 failure mode: the same href from the English source directory leaves the root."""
        from pathlib import PurePosixPath
        relative = posixpath.normpath(str(PurePosixPath(self.BOOK).parent / self.SCHEMA_HREF))
        self.assertTrue(relative == ".." or relative.startswith("../"), relative)

    def test_ru_and_zh_hans_schema_hrefs_map_to_one_canonical_invariant(self):
        for language, rendition_path in (("ru", self.REN_RU), ("zh-Hans", self.REN_ZH)):
            with self.subTest(language=language):
                kind, path = classify_link(self.SCHEMA_HREF, rendition_path, language, self.tree, self.by_path, self.pinned)
                self.assertEqual((kind, path), ("invariant", self.SCHEMA_CANON))
                self.assertEqual(normalize_target(self.SCHEMA_HREF, rendition_path, {}, language, {}), self.SCHEMA_CANON)

    def test_sibling_peer_maps_to_the_english_work(self):
        kind, path = classify_link(self.SIBLING_HREF, self.REN_RU, "ru", self.tree, self.by_path, self.pinned)
        self.assertEqual((kind, path), ("peer", self.SIBLING_CANON))
        self.assertEqual(normalize_target(self.SIBLING_HREF, self.REN_RU, {}, "ru", {}), self.SIBLING_CANON)
        # English-path form of the same work (depth from translations/<lang>/...) compares equal for parity.
        english_form = "../../../../../" + self.SIBLING_CANON
        self.assertEqual(normalize_target(english_form, self.REN_RU, {}, "ru", {}), self.SIBLING_CANON)
        self.assertEqual(classify_link(english_form, self.REN_RU, "ru", self.tree, self.by_path, self.pinned), ("document", self.SIBLING_CANON))

    def test_english_target_without_a_rendition_is_a_document_for_explicit_fallback(self):
        href = "../../../../../" + self.EN_ONLY
        kind, path = classify_link(href, self.REN_RU, "ru", self.tree, self.by_path, self.pinned)
        self.assertEqual((kind, path), ("document", self.EN_ONLY))

    def test_refusals_keep_existing_rendition_link_codes(self):
        cases = {
            "RENDITION_LINK_TRANSLATION": ("../../../zh-Hans/engineering/specifications/book-package/SPECIFICATION.md", self.REN_RU, "ru"),
            "RENDITION_LINK_UNPINNED": ("../reuse-policy/SPECIFICATION.md", self.REN_RU, "ru"),  # peer path exists only if registered
            "RENDITION_LINK_DANGLING": ("../../../../../schemas/no-such.schema.json", self.REN_RU, "ru"),
            "RENDITION_LINK_ESCAPES": ("../../../../../../outside.txt", self.REN_RU, "ru"),
            "RENDITION_LINK_SCHEME": ("javascript:alert(1)", self.REN_RU, "ru"),
        }
        # Unpinned peer: register the translations path in the tree so the refusal is UNPINNED, not DANGLING.
        tree = self.tree | {"translations/ru/" + self.EN_ONLY}
        for code, (href, base, language) in cases.items():
            with self.subTest(code=code):
                with self.assertRaisesRegex(RenditionError, f"^{code}:"):
                    classify_link(href, base, language, tree if code == "RENDITION_LINK_UNPINNED" else self.tree, self.by_path, self.pinned)

    def test_encoded_traversal_is_refused(self):
        with self.assertRaisesRegex(RenditionError, "^RENDITION_LINK_ESCAPES:"):
            classify_link("../../../../../%2e%2e/outside.txt", self.REN_RU, "ru", self.tree, self.by_path, self.pinned)

    def test_changed_citation_or_fragment_is_a_different_canonical_identity(self):
        peer_maps = {("ru", self.SIBLING_CANON): {"введение": "introduction"}}
        a = normalize_target(self.SIBLING_HREF + "#введение", self.REN_RU, {}, "ru", peer_maps)
        b = normalize_target(self.SIBLING_HREF + "#другое", self.REN_RU, {}, "ru", peer_maps)
        self.assertEqual(a, self.SIBLING_CANON + "#introduction")
        self.assertNotEqual(a, b)


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
        self.assertEqual(ru["link_classes"], {"document_fallback": 1, "fragment": 1, "invariant": 1, "peer": 1})
        self.assertNotIn("literal_resolution_missing", ru)  # literal resolution is the rule now, not a metric
        self.assertEqual((ru["unresolved_links"], ru["parity_failures"], ru["other_failures"]), ({}, {}, {}))
        self.assertEqual((ru["files_clean"], ru["files_with_a_failure"]), (2, 0))
        self.assertEqual(report["files"], [])

    def test_unresolved_links_and_parity_failures_are_counted_not_fatal(self):
        scenario = Scenario(self.root, alpha_ru=swap(swap(RU_ALPHA, "(../../../../schemas/synthetic.schema.json)", "(../../../../schemas/missing.json)"),
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
        unbound = review_ok(("scope",))
        unbound["reviewed"]["rendition_blob"] = "0" * 40  # a review of other bytes than the pinned rendition
        cls.scenario = Scenario(cls.root / "scenario", gamma=True, review_gamma=unbound)
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
        for work in ("synthetic-alpha", "synthetic-beta", "synthetic-gamma"):
            for locale in ("en", "ru", "zh-Hans"):
                target = self.out / locale / "science" / work / "index.html"
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(self.site / "public" / locale / "science" / work / "index.html", target)
        shutil.copy(self.site / "public/renditions.js", self.out / "renditions.js")
        shutil.copy(self.site / "public/sitemap.xml", self.out / "sitemap.xml")

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
        self.assertEqual(self.check(), 6)
        ru = self.page("ru").read_text(encoding="utf-8")
        self.assertIn('<aside class="rendition-state" data-state="reviewed" data-language="ru" data-body-language="ru"', ru)
        self.assertIn("<strong>Перевод проверен в указанном объёме (внутренняя агентная рецензия)</strong>", ru)
        self.assertIn('<div class="source-body prose" lang="ru">', ru)
        self.assertIn('<h1 id="', ru)
        self.assertIn('lang="ru">ТЕСТ АЛЬФА</h1>', ru)
        self.assertIn('"inLanguage":"ru"', ru)
        self.assertIn('"translationOfWork"', ru)
        self.assertEqual(ru.count("<math "), 2)
        self.assertNotIn("SYNTHETIC TEST DATA, NOT A MANUSCRIPT", ru)
        zh = self.page("zh-Hans").read_text(encoding="utf-8")
        self.assertIn('data-state="unreviewed" data-language="zh-Hans" data-body-language="zh-Hans"', zh)
        self.assertIn("<strong>尚未经语义审校的译文</strong>", zh)
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

    def test_c4_machine_readable_facts_carry_full_digests_and_rendition_of(self):
        ru = self.page("ru").read_text(encoding="utf-8")
        self.assertIn('data-relation="rendition_of"', ru)
        self.assertIn('data-work="synthetic-alpha"', ru)
        facts = json.loads(re.search(r'<script type="application/json" class="rendition-facts">(.*?)</script>', ru, re.S)[1])
        self.assertEqual(facts["relation"], "rendition_of")
        self.assertEqual(facts["digest_label"], "sha256")
        self.assertEqual(facts["source_language"], "en")
        self.assertEqual(facts["rendition_language"], "ru")
        self.assertEqual(len(facts["source"]["sha256"]), 64)
        self.assertEqual(len(facts["rendition"]["sha256"]), 64)
        self.assertEqual(facts["source"]["sha256"], re.search(r'data-source-sha256="([0-9a-f]{64})"', ru)[1])
        self.assertEqual(facts["review"]["reviewer"]["identity"], "test-fixture-reviewer")
        missing = self.page("zh-Hans", "synthetic-beta").read_text(encoding="utf-8")
        missing_facts = json.loads(re.search(r'<script type="application/json" class="rendition-facts">(.*?)</script>', missing, re.S)[1])
        self.assertEqual(missing_facts["state"], "missing")
        self.assertNotIn("review", missing_facts)

    def test_c6_missing_page_source_link_is_never_undefined(self):
        missing = self.page("zh-Hans", "synthetic-beta").read_text(encoding="utf-8")
        self.assertNotIn('href="undefined"', missing)
        self.assertRegex(missing, r'<a href="https://github\.com/Arcanada-one/knowledge-contract/blob/[0-9a-f]{40}/papers/synthetic-beta/PAPER\.md" lang="en">')

    def test_c9_json_ld_url_is_the_localized_route_for_a_shown_rendition(self):
        def doc_ld(html):
            for raw in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
                data = json.loads(raw)
                if data.get("@type") in {"ScholarlyArticle", "CreativeWork"} and "inLanguage" in data:
                    return data
            self.fail("no document JSON-LD on the page")
        ru = self.page("ru").read_text(encoding="utf-8")
        ld = doc_ld(ru)
        self.assertEqual(ld["url"], "https://contract.place/ru/science/synthetic-alpha/")
        self.assertEqual(ld["inLanguage"], "ru")
        self.assertEqual(ld["translationOfWork"]["url"], "https://contract.place/en/science/synthetic-alpha/")
        stale = self.page("ru", "synthetic-beta").read_text(encoding="utf-8")
        stale_ld = doc_ld(stale)
        self.assertEqual(stale_ld["url"], "https://contract.place/en/science/synthetic-beta/")
        self.assertEqual(stale_ld["inLanguage"], "en")

    def test_anchors_survive_in_the_page_and_the_state_exposes_pins(self):
        ru = self.page("ru").read_text(encoding="utf-8")
        self.assertIn('id="pravila" data-source-section="rules"', ru)
        self.assertIn('<span id="rules" class="source-anchor"></span>', ru)
        self.assertIn(self.scenario.c1[:12], ru)
        self.assertIn(self.scenario.c2[:12], ru)
        self.assertIn(sha256_text(RU_ALPHA)[:12], ru)
        self.assertIn("test-fixture-reviewer (agent)", ru)
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
        self.edit("zh-Hans", "synthetic-alpha", "<strong>尚未经语义审校的译文</strong>", "<strong>译文已按所述范围完成内部代理审查</strong>")
        with self.assertRaisesRegex(ValueError, "RENDITION_STATE_LABEL"):
            self.check()
        self.setUp()
        self.edit("zh-Hans", "synthetic-alpha", 'data-state="unreviewed"', 'data-state="reviewed"')
        with self.assertRaisesRegex(ValueError, "RENDITION_STATE_LABEL"):
            self.check()

    def test_stale_rendition_labelled_current_is_refused(self):
        """ML07: a stale rendition's page claiming to be reviewed."""
        self.edit("ru", "synthetic-beta", 'data-state="stale"', 'data-state="reviewed"')
        self.edit("ru", "synthetic-beta", "<strong>Перевод устарел: английский источник изменился.</strong>", "<strong>Перевод проверен в указанном объёме (внутренняя агентная рецензия)</strong>")
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
        self.assertEqual(check_renditions(self.out, self.catalog["records"], "fixture", allow_fixture=True), 6)

    # --- review facts, labels and issues on the page (K8 round 3) ---
    def test_a_reviewed_page_shows_every_fact_of_the_review_and_says_internal(self):
        ru = self.page("ru").read_text(encoding="utf-8")
        for fact in ("test-fixture-reviewer (agent)", "test-fixture-author", "synthetic: a different fixture identity than the author",
                     "synthetic test review; no real review took place", "SYNTHETIC TEST DATA; agent-only, non-blind", "2026-01-02T03:04:05Z",
                     EVIDENCE_PATH, "synthetic claim one", "rules", "независим от автора"):
            self.assertIn(fact, ru)
        self.assertIn("Внутренняя агентная рецензия рецензентом, независимым от автора. Это не внешняя экспертная рецензия.", ru)
        blobs = [run(["git", "rev-parse", f"{self.scenario.c1}:{ALPHA}"], cwd=self.scenario.source).strip()[:12],
                 run(["git", "rev-parse", f"{self.scenario.c2}:{REN['ru']}"], cwd=self.scenario.source).strip()[:12]]
        for blob in blobs:
            self.assertIn(f"<code>{blob}</code>", ru)
        self.assertRegex(ru, r'<a href="https://github\.com/[^"]*reviews/synthetic-review-record\.md"[^>]*>' + re.escape(EVIDENCE_PATH))
        self.assertNotIn("peer review", ru.replace("not an external peer review", ""))

    def test_an_unreviewed_draft_shows_no_review_facts_and_no_issue(self):
        zh = self.page("zh-Hans").read_text(encoding="utf-8")
        self.assertNotIn("data-review-issue", zh)
        self.assertNotIn("test-fixture-reviewer", zh)
        self.assertNotIn("内部", zh.split("</aside>")[0].split("<aside")[1].split("</p>", 1)[0])  # the label itself carries no review claim

    def test_an_unbound_review_claim_is_shown_as_unreviewed_with_its_typed_issue(self):
        gamma = self.page("ru", "synthetic-gamma").read_text(encoding="utf-8")
        self.assertIn('data-state="unreviewed" data-language="ru" data-body-language="ru"', gamma)
        self.assertIn("<strong>Перевод без смысловой рецензии</strong>", gamma)
        self.assertIn('data-review-issue="RENDITION_REVIEW_UNBOUND"', gamma)
        self.assertIn(RENDITION_ISSUES["RENDITION_REVIEW_UNBOUND"]["ru"], gamma)
        self.assertNotIn("Внутренняя агентная рецензия", gamma)
        self.assertNotIn("test-fixture-reviewer", gamma)
        record = next(r for r in self.catalog["records"] if r["id"] == "synthetic-gamma")["renditions"]["ru"]
        self.assertEqual((record["state"], record["review_issue"]["code"], record["review"]), ("unreviewed", "RENDITION_REVIEW_UNBOUND", None))

    def test_the_review_issue_cannot_be_hidden_or_invented(self):
        self.edit("ru", "synthetic-gamma", RENDITION_ISSUES["RENDITION_REVIEW_UNBOUND"]["ru"], "")
        with self.assertRaisesRegex(ValueError, "RENDITION_STATE_LABEL"):
            self.check()
        self.setUp()
        self.edit("zh-Hans", "synthetic-alpha", "</aside>", '<p data-review-issue="RENDITION_REVIEW_UNBOUND">x</p></aside>')
        with self.assertRaisesRegex(ValueError, "RENDITION_STATE_LABEL"):
            self.check()

    def test_a_reviewed_record_without_an_independent_reviewer_is_refused_by_the_output_check(self):
        for mutate in (lambda r: r["review"]["reviewer"].update(independent_of_author=False),
                       lambda r: r["review"].update(author="Test-Fixture-Reviewer ")):
            records = copy.deepcopy(self.catalog["records"])
            mutate(next(r for r in records if r["id"] == "synthetic-alpha")["renditions"]["ru"])
            with self.assertRaisesRegex(ValueError, "RENDITION_REVIEW_NOT_INDEPENDENT"):
                check_renditions(self.out, records, "knowledge-repository")

    def test_published_manifest_reports_the_review_state_not_a_claim(self):
        published = json.loads((self.site / "public/publication.json").read_text())
        by_slug = {d["slug"]: d["renditions"] for d in published["documents"] if d["slug"].startswith("synthetic-")}
        self.assertEqual((by_slug["synthetic-alpha"]["ru"]["review_status"], by_slug["synthetic-alpha"]["ru"]["review_scope"]), ("internal-agent-review", "full"))
        self.assertEqual((by_slug["synthetic-alpha"]["zh-Hans"]["review_status"], by_slug["synthetic-alpha"]["zh-Hans"]["review_issue"]), ("unreviewed", None))
        self.assertEqual((by_slug["synthetic-gamma"]["ru"]["review_status"], by_slug["synthetic-gamma"]["ru"]["review_issue"]), ("unreviewed", "RENDITION_REVIEW_UNBOUND"))

    # --- fallback indexing (K8 round 3): lang, hreflang, sitemap, robots ---
    def head(self, locale, work="synthetic-alpha"):
        html = self.page(locale, work).read_text(encoding="utf-8")
        robots = re.search(r'<meta name="robots" content="([^"]*)"', html)
        return {"robots": robots[1] if robots else None, "canonical": (re.search(r'<link rel="canonical" href="([^"]*)"', html) or [None, None])[1],
                "hreflang": dict(re.findall(r'<link rel="alternate" hreflang="([^"]*)" href="([^"]*)"', html)),
                "body_lang": re.search(r'<div class="source-body prose" lang="([^"]*)">', html)[1], "html_lang": re.search(r'<html lang="([^"]*)"', html)[1]}

    def sitemap(self):
        return set(re.findall(r"<loc>([^<]*)</loc>", (self.out / "sitemap.xml").read_text(encoding="utf-8")))

    def test_indexing_rule_per_state(self):
        base = "https://contract.place"
        # reviewed rendition (alpha/ru): indexable, canonical to itself, alternates for the languages that really exist
        ru = self.head("ru")
        self.assertEqual((ru["robots"], ru["canonical"], ru["body_lang"], ru["html_lang"]), (None, f"{base}/ru/science/synthetic-alpha/", "ru", "ru"))
        self.assertEqual(ru["hreflang"], {"en": f"{base}/en/science/synthetic-alpha/", "ru": f"{base}/ru/science/synthetic-alpha/", "x-default": f"{base}/en/science/synthetic-alpha/"})
        # the English page does not list a translation that does not count
        en = self.head("en")
        self.assertEqual(set(en["hreflang"]), {"en", "ru", "x-default"})
        # unreviewed rendition (alpha/zh-Hans): noindex, no canonical, no alternates, not in the sitemap
        zh = self.head("zh-Hans")
        self.assertEqual((zh["robots"], zh["canonical"], zh["hreflang"], zh["body_lang"], zh["html_lang"]), ("noindex,follow", None, {}, "zh-Hans", "zh-Hans"))
        # English fallback under /ru/ (stale) and /zh-Hans/ (missing): English body, lang=en, same rule
        for locale, work in (("ru", "synthetic-beta"), ("zh-Hans", "synthetic-beta")):
            fallback = self.head(locale, work)
            self.assertEqual((fallback["robots"], fallback["canonical"], fallback["hreflang"], fallback["body_lang"], fallback["html_lang"]), ("noindex,follow", None, {}, "en", locale))
        # an unbound review claim does not make a page indexable
        self.assertEqual(self.head("ru", "synthetic-gamma")["robots"], "noindex,follow")
        # works without any translation that counts: English only
        beta_en = self.head("en", "synthetic-beta")
        self.assertEqual(set(beta_en["hreflang"]), {"en", "x-default"})
        listed = self.sitemap()
        self.assertIn(f"{base}/en/science/synthetic-alpha/", listed)
        self.assertIn(f"{base}/ru/science/synthetic-alpha/", listed)
        for url in ("zh-Hans/science/synthetic-alpha", "ru/science/synthetic-beta", "zh-Hans/science/synthetic-beta", "ru/science/synthetic-gamma", "zh-Hans/science/synthetic-gamma"):
            self.assertNotIn(f"{base}/{url}/", listed, url)
        for work in ("synthetic-beta", "synthetic-gamma"):
            self.assertIn(f"{base}/en/science/{work}/", listed)

    def test_indexing_rule_violations_are_refused(self):
        base = "https://contract.place"
        self.assertEqual(self.check(), 6)
        self.edit("zh-Hans", "synthetic-alpha", '<meta name="robots" content="noindex,follow">', "")  # an unreviewed page without noindex
        with self.assertRaisesRegex(ValueError, "RENDITION_INDEXING"):
            self.check()
        self.setUp()
        self.edit("zh-Hans", "synthetic-alpha", '<meta name="robots" content="noindex,follow">', f'<meta name="robots" content="noindex,follow"><link rel="alternate" hreflang="zh-Hans" href="{base}/zh-Hans/science/synthetic-alpha/">')
        with self.assertRaisesRegex(ValueError, "RENDITION_INDEXING"):  # a translation claim on a page that must not make one
            self.check()
        self.setUp()
        self.edit("en", "synthetic-alpha", '<link rel="alternate" hreflang="x-default"', f'<link rel="alternate" hreflang="zh-Hans" href="{base}/zh-Hans/science/synthetic-alpha/"><link rel="alternate" hreflang="x-default"')
        with self.assertRaisesRegex(ValueError, "RENDITION_INDEXING"):  # the English page advertises a translation that does not count
            self.check()
        self.setUp()
        self.edit("ru", "synthetic-alpha", f'<link rel="alternate" hreflang="ru" href="{base}/ru/science/synthetic-alpha/">', "")
        with self.assertRaisesRegex(ValueError, "RENDITION_INDEXING"):
            self.check()
        self.setUp()
        sitemap = self.out / "sitemap.xml"
        text = sitemap.read_text(encoding="utf-8")
        sitemap.write_text(text.replace("</urlset>", f"  <url><loc>{base}/zh-Hans/science/synthetic-alpha/</loc></url>\n</urlset>"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "RENDITION_INDEXING"):  # an unreviewed rendition listed as a translation
            self.check()
        sitemap.write_text(text.replace(f"  <url><loc>{base}/ru/science/synthetic-alpha/</loc>", "  <url><loc>x</loc>"), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "RENDITION_INDEXING"):  # the reviewed rendition missing from the sitemap
            self.check()

    def test_no_translation_url_of_a_work_without_a_counting_review_is_listed(self):
        """Whatever the pages say, the sitemap lists a /ru/ or /zh-Hans/ work URL only for a rendition with a bound internal review."""
        indexed = {(r["id"], l) for r in self.catalog["records"] if r.get("renditions") for l in ("ru", "zh-Hans") if r["renditions"][l]["state"] in RENDITION_INDEXED}
        self.assertEqual(indexed, {("synthetic-alpha", "ru")})
        listed = {(m[2], m[1]) for url in self.sitemap() if (m := re.fullmatch(r"https://contract\.place/(ru|zh-Hans)/science/(synthetic-[a-z]+)/", url))}
        self.assertEqual(listed, indexed)

    def test_the_whole_rule_is_one_switch_that_leaves_a_build_without_renditions_alone(self):
        """APPLY_FALLBACK_INDEXING_WITHOUT_RENDITIONS=false keeps the no-sidecar build as it is; true applies the same rule to it."""
        script = (ROOT / "src/prerender.mjs").read_text(encoding="utf-8")
        self.assertEqual(script.count("const APPLY_FALLBACK_INDEXING_WITHOUT_RENDITIONS=false;"), 1)
        for value, expect_noindex in (("false", False), ("true", True)):
            with tempfile.TemporaryDirectory() as temp:
                site = Path(temp) / "site"
                shutil.copytree(ROOT / "src", site / "src", ignore=shutil.ignore_patterns("node_modules"))
                for name in ("build.mjs", "roadmap-manifest.json", "publication-manifest.json"):
                    shutil.copy(ROOT / name, site / name)
                prerender = site / "src/prerender.mjs"
                prerender.write_text(script.replace("const APPLY_FALLBACK_INDEXING_WITHOUT_RENDITIONS=false;", f"const APPLY_FALLBACK_INDEXING_WITHOUT_RENDITIONS={value};"), encoding="utf-8")
                done = subprocess.run(["node", "build.mjs"], cwd=site, capture_output=True, text=True, timeout=900)
                self.assertEqual(done.returncode, 0, done.stderr)
                page = (site / "public/ru/science/constrained-transformations/index.html").read_text(encoding="utf-8")
                sitemap = (site / "public/sitemap.xml").read_text(encoding="utf-8")
                self.assertEqual('<meta name="robots" content="noindex,follow">' in page, expect_noindex)
                self.assertEqual('<link rel="alternate" hreflang="ru"' in page, not expect_noindex)
                self.assertEqual('<link rel="canonical" href="https://contract.place/ru/science/constrained-transformations/">' in page, not expect_noindex)
                self.assertEqual("https://contract.place/ru/science/constrained-transformations/" in sitemap, not expect_noindex)
                self.assertEqual("https://contract.place/en/science/constrained-transformations/" in sitemap, True)
                if not expect_noindex:  # the switch off reproduces the committed build byte for byte
                    for name in ("sitemap.xml", "ru/science/constrained-transformations/index.html", "zh-Hans/index.html", "en/science/constrained-transformations/index.html", "index.html"):
                        self.assertEqual((site / "public" / name).read_bytes(), (ROOT / "public" / name).read_bytes(), name)

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
