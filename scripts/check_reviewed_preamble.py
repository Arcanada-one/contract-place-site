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
RENDITION_PIN = "151dc8927547d27a88d0d5082b8abd1f98bd7b33"
CASES = (
    ("source-transcription-and-uncertainty", "8ca885fc3f144d89e95e4813868fd953450f1f71",
     {"ru": "8aaa8dae18a2014be6495c479e85a3e114538420", "zh-Hans": "2f001123a165ef342b3b70e9de36389d765ff40a"}),
    ("reuse-admission-and-cost-controls", "aff97b3cda92bbb8067b1db47ce7c16ddd98c5ac",
     {"ru": "ecd4203da7ba35ad7611cd65f02e32b0c4087e17", "zh-Hans": "c2099a9aa3eb19b76a63006d5810a08e3d8d2db0"}),
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


def main() -> None:
    source_root = checkout("PREAMBLE_SOURCE_DIR", "_knowledge-source", SOURCE_PIN)
    target_root = checkout("PREAMBLE_RENDITION_DIR", "_rendition-review-source", RENDITION_PIN)
    # Compare to the actual earlier implementation, not a reconstructed oracle.
    baseline_root = checkout("PREAMBLE_BASELINE_DIR", "_preamble-site-baseline",
                             "b1a2cb006077eea52fd09ad0b7a6fdbe5f538c65")
    baseline_bytes = (baseline_root / "scripts/renditions.py").read_bytes()
    require(blob(baseline_bytes) == BASELINE_BLOB, "unexpected baseline checker bytes")
    baseline = types.ModuleType("renditions_preamble_baseline")
    exec(compile(baseline_bytes, "pinned-baseline/renditions.py", "exec"), baseline.__dict__)
    results = []
    for work, source_blob, targets in CASES:
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
            entry = {"work": work, "language": language,
                     "source": {"path": source_path}, "rendition": {"path": target_path},
                     "sections": [{"source": anchor, "rendition": anchor} for _, anchor in source_heads]}
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
    print(json.dumps({"scope": "exact-file parity and raw Pandoc fragment regression, not publication admission",
                      "baseline_blob": BASELINE_BLOB, "source_commit": SOURCE_PIN,
                      "rendition_commit": RENDITION_PIN, "cases": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
