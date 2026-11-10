#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Read-only regression on four exact reviewed files, not rendition admission.

The second checkout is test input only. It never changes publication-manifest,
sidecar review states, source content, generated pages or the live index.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from hashlib import sha1
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import subprocess
import types

from build_publication import parse_markdown
from rendition_preamble import source_for_anchor_parity
from renditions import RenditionError, check_parity, sections_of

ROOT = Path(__file__).resolve().parents[1]
BASELINE_BLOB = "764227c70a6f1c02fd20ed083c54e1cbaa8e9fe1"
SOURCE_PIN = "46af0f06218e590e047a585ac74820f3c6336604"
# Phase-A bytes-import commit that carries all four current STUDY paths, including
# corrected Reuse ru f7d53ee8 (sidecar admission is a separate later pin).
RENDITION_PIN = "cad15f92f1821cf5ffe9c3d257bdbac8beba23ba"
# Prior bytes-import commit that still carries Reuse ru 7376c330 as CODE_CHANGED fixture.
CODE_REFUSAL_PIN = "64aa36781f92b1b1a376613f847c82e098720b1d"
# Prior PR76 tip that still carries the three formula-order-failing blobs.
OLD_RENDITION_PIN = "151dc8927547d27a88d0d5082b8abd1f98bd7b33"
PASS_CASES = (
    ("source-transcription-and-uncertainty", "8ca885fc3f144d89e95e4813868fd953450f1f71",
     {"ru": "8aaa8dae18a2014be6495c479e85a3e114538420",
      "zh-Hans": "9a94c63085287f59f42df75014844801f1ffca1e"}),
    ("reuse-admission-and-cost-controls", "aff97b3cda92bbb8067b1db47ce7c16ddd98c5ac",
     {"ru": "f7d53ee85bea6966c7068a0835b19ba4593a8e19",
      "zh-Hans": "f07227366731e2fb946285ec696c7199ae48565f"}),
)
# Predeclared refusal: earlier Reuse ru after formula-order fix, still two extra code spans.
EXPECTED_CODE_REFUSALS = (
    ("reuse-admission-and-cost-controls", "ru", "aff97b3cda92bbb8067b1db47ce7c16ddd98c5ac",
     "7376c33010abde5a67c9fca6c40408a8056a2500"),
)
# Old blobs that hosted CI refused with RENDITION_FORMULA_CHANGED; must stay refused.
OLD_FORMULA_REFUSALS = (
    ("source-transcription-and-uncertainty", "zh-Hans", "2f001123a165ef342b3b70e9de36389d765ff40a"),
    ("reuse-admission-and-cost-controls", "ru", "ecd4203da7ba35ad7611cd65f02e32b0c4087e17"),
    ("reuse-admission-and-cost-controls", "zh-Hans", "c2099a9aa3eb19b76a63006d5810a08e3d8d2db0"),
)


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True).stdout


def blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def checkout(variable: str, fallback: str, pin: str) -> Path:
    root = Path(os.environ.get(variable, str(ROOT / fallback))).resolve()
    require(root.is_dir(), f"required read-only test checkout missing: {variable}")
    require(git(root, "rev-parse", "HEAD").decode().strip() == pin,
            f"test checkout is not at {pin}: {root}")
    return root


class Ids(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.counts = Counter()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == "id" and value:
                self.counts[value] += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def entry_for(work: str, language: str, source_path: str, target_path: str, source_heads):
    return {"work": work, "language": language,
            "source": {"path": source_path}, "rendition": {"path": target_path},
            "sections": [{"source": anchor, "rendition": anchor} for _, anchor in source_heads]}


def swap_first_two_math(ast: dict) -> bool:
    """One-token reorder: swap the first two Math nodes in document order. Returns True if swapped."""
    nodes = []

    def visit(node):
        if isinstance(node, dict):
            if node.get("t") == "Math":
                nodes.append(node)
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(ast["blocks"])
    if len(nodes) < 2:
        return False
    nodes[0]["c"], nodes[1]["c"] = nodes[1]["c"], nodes[0]["c"]
    return True


def readd_one_fail_code_span(ast: dict) -> bool:
    """Mutant: wrap the bare fail token of a fail/unknown Str as one inline Code span."""

    def visit(node) -> bool:
        if isinstance(node, list):
            for index, item in enumerate(node):
                if isinstance(item, dict) and item.get("t") == "Str" and item.get("c") == "fail/unknown":
                    node[index:index + 1] = [
                        {"t": "Code", "c": [["", [], []], "fail"]},
                        {"t": "Str", "c": "/unknown"},
                    ]
                    return True
                if visit(item):
                    return True
            return False
        if isinstance(node, dict):
            for value in node.values():
                if visit(value):
                    return True
        return False

    return visit(ast["blocks"])


def refuse_with_code(entry, source_ast, target_ast, expected_code: str) -> str:
    try:
        check_parity(entry, source_ast, target_ast)
    except RenditionError as error:
        require(error.code == expected_code,
                f"expected {expected_code}, got {error.code}: {entry['work']}/{entry['language']}")
        return error.code
    raise AssertionError(f"expected refusal {expected_code}: {entry['work']}/{entry['language']}")


def main() -> None:
    # Dedicated English pin: do not reuse the publication-manifest `_knowledge-source` checkout,
    # which advances independently of this exact-file regression.
    source_root = checkout("PREAMBLE_SOURCE_DIR", "_preamble-english-source", SOURCE_PIN)
    target_root = checkout("PREAMBLE_RENDITION_DIR", "_rendition-review-source", RENDITION_PIN)
    code_refusal_root = checkout("PREAMBLE_CODE_REFUSAL_DIR", "_rendition-code-refusal-source",
                                 CODE_REFUSAL_PIN)
    old_root = checkout("PREAMBLE_OLD_RENDITION_DIR", "_rendition-old-review-source", OLD_RENDITION_PIN)
    # Compare to the actual earlier implementation, not a reconstructed oracle.
    baseline_root = checkout("PREAMBLE_BASELINE_DIR", "_preamble-site-baseline",
                             "b1a2cb006077eea52fd09ad0b7a6fdbe5f538c65")
    baseline_bytes = (baseline_root / "scripts/renditions.py").read_bytes()
    require(blob(baseline_bytes) == BASELINE_BLOB, "unexpected baseline checker bytes")
    baseline = types.ModuleType("renditions_preamble_baseline")
    exec(compile(baseline_bytes, "pinned-baseline/renditions.py", "exec"), baseline.__dict__)
    results = []
    reorder_refusals = []
    code_span_mutant_refusals = []
    for work, source_blob, targets in PASS_CASES:
        source_path = f"engineering/studies/{work}/STUDY.md"
        raw_source = (source_root / source_path).read_bytes()
        require(blob(raw_source) == source_blob, f"source bytes changed: {work}")
        source_ast = parse_markdown(source_root / source_path)
        for language, target_blob in targets.items():
            target_path = f"translations/{language}/{source_path}"
            raw_target = (target_root / target_path).read_bytes()
            require(blob(raw_target) == target_blob, f"reviewed rendition bytes changed: {work}/{language}")
            target_ast = parse_markdown(target_root / target_path)
            source_heads, _ = sections_of(source_ast)
            target_heads, _ = sections_of(target_ast)
            require(source_heads == target_heads, f"expected exact section anchors: {work}/{language}")
            entry = entry_for(work, language, source_path, target_path, source_heads)
            before = None
            try:
                baseline.check_parity(entry, source_ast, target_ast)
            except baseline.RenditionError as error:
                before = error.code
            require(before == "RENDITION_SECTION_MISSING", f"expected baseline refusal: {work}/{language}: {before}")
            source_copy, target_copy = deepcopy(source_ast), deepcopy(target_ast)
            check_parity(entry, source_ast, target_ast)
            require(source_ast == source_copy and target_ast == target_copy, "input AST was mutated")
            require(source_for_anchor_parity(source_ast, target_ast) is not source_ast, "bridge not exercised")
            for name, src, dst in (
                ("prose-preserved", deepcopy(source_ast), deepcopy(target_ast)),
                ("missing-anchor", deepcopy(source_ast), deepcopy(target_ast)),
            ):
                if name == "prose-preserved":
                    src["blocks"].insert(0, {"t": "Para", "c": [{"t": "Str", "c": "Required condition."}]})
                else:
                    dst["blocks"][0]["c"][1][0] = "not-the-reviewed-anchor"
                refused = False
                try:
                    check_parity(entry, src, dst)
                except RenditionError:
                    refused = True
                require(refused, f"negative control passed: {work}/{language}/{name}")
            mutated = deepcopy(target_ast)
            require(swap_first_two_math(mutated), f"need two math tokens to reorder: {work}/{language}")
            code = refuse_with_code(entry, deepcopy(source_ast), mutated, "RENDITION_FORMULA_CHANGED")
            reorder_refusals.append({"work": work, "language": language, "reason": code})
            if work == "reuse-admission-and-cost-controls" and language == "ru":
                code_mutant = deepcopy(target_ast)
                require(readd_one_fail_code_span(code_mutant),
                        "need bare fail/unknown Str to re-add one code span")
                code = refuse_with_code(entry, deepcopy(source_ast), code_mutant, "RENDITION_CODE_CHANGED")
                code_span_mutant_refusals.append({
                    "work": work, "language": language, "rendition_blob": target_blob, "reason": code,
                    "mutation": "re-add one inline code span around fail",
                })
            rendered = subprocess.run(
                ["pandoc", "--from=json", "--to=html5", "--mathml", "--wrap=none"],
                input=json.dumps(target_ast), text=True, check=True, capture_output=True).stdout
            ids = Ids()
            ids.feed(rendered)
            ids.close()
            title_anchor = target_ast["blocks"][0]["c"][1][0]
            require(ids.counts[title_anchor] == 1, f"legacy title anchor not unique: {work}/{language}")
            require(all(n == 1 for n in ids.counts.values()), f"duplicate rendered ids: {work}/{language}")
            results.append({"work": work, "language": language, "source_blob": source_blob,
                            "rendition_blob": target_blob, "before": before, "after": "parity-pass",
                            "negative_controls_refused": 2, "rendered_ids_unique": True})

    code_refusals = []
    for work, language, source_blob, target_blob in EXPECTED_CODE_REFUSALS:
        source_path = f"engineering/studies/{work}/STUDY.md"
        target_path = f"translations/{language}/{source_path}"
        raw_source = (source_root / source_path).read_bytes()
        require(blob(raw_source) == source_blob, f"source bytes changed: {work}")
        raw_target = (code_refusal_root / target_path).read_bytes()
        require(blob(raw_target) == target_blob, f"code-refusal fixture bytes changed: {work}/{language}")
        source_ast = parse_markdown(source_root / source_path)
        target_ast = parse_markdown(code_refusal_root / target_path)
        source_heads, _ = sections_of(source_ast)
        entry = entry_for(work, language, source_path, target_path, source_heads)
        code = refuse_with_code(entry, source_ast, target_ast, "RENDITION_CODE_CHANGED")
        code_refusals.append({
            "work": work, "language": language, "rendition_blob": target_blob, "reason": code,
            "disposition": "refused: predeclared code-span parity negative for 7376c330",
        })

    old_refusals = []
    for work, language, old_blob in OLD_FORMULA_REFUSALS:
        source_path = f"engineering/studies/{work}/STUDY.md"
        target_path = f"translations/{language}/{source_path}"
        source_ast = parse_markdown(source_root / source_path)
        raw_old = (old_root / target_path).read_bytes()
        require(blob(raw_old) == old_blob, f"old refusal fixture bytes changed: {work}/{language}")
        target_ast = parse_markdown(old_root / target_path)
        source_heads, _ = sections_of(source_ast)
        entry = entry_for(work, language, source_path, target_path, source_heads)
        code = refuse_with_code(entry, source_ast, target_ast, "RENDITION_FORMULA_CHANGED")
        old_refusals.append({"work": work, "language": language, "rendition_blob": old_blob, "reason": code})

    print(json.dumps({
        "scope": "exact-file parity and raw Pandoc fragment regression, not publication admission",
        "baseline_blob": BASELINE_BLOB,
        "source_commit": SOURCE_PIN,
        "rendition_commit": RENDITION_PIN,
        "code_refusal_commit": CODE_REFUSAL_PIN,
        "old_rendition_commit": OLD_RENDITION_PIN,
        "cases": results,
        "expected_code_refusals": code_refusals,
        "code_span_mutant_refusals": code_span_mutant_refusals,
        "old_formula_refusals": old_refusals,
        "reorder_mutation_refusals": reorder_refusals,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
