#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Read-only dry run of the rendition validator and link resolver over a knowledge-repository checkout (K8).

It reads ``translations/<language>/...`` of a clean checkout, treats EVERY file as an unreviewed author draft, derives a
positional section mapping (a real sidecar declares it explicitly) and runs the same stages as the compiler: layout,
pins, digest, language, literal link resolution from the rendition's directory and structural parity. It prints counts per language. It writes nothing into the
checkout or the site, nothing it prints is a publication, and it never marks anything reviewed, deployed or indexed.

Usage: renditions_dry_run.py --source-dir CHECKOUT --source-revision PINNED_SOURCE_COMMIT
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import tempfile

from build_publication import Renderer, inside, load_inputs, parse_markdown, read_json, run
from renditions import (RENDITION_LANGUAGES, SIDECAR_SCHEMA_VERSION, TRANSLATIONS_ROOT, RenditionError, compile_entry, git_bytes, link_context, meta_value,
                        rendition_path_for, resolve_state, sections_of, tree_paths, validate_sidecar)


def audit(source: Path, source_revision: str) -> dict:
    head = run(["git", "rev-parse", "HEAD"], cwd=source).strip()
    with tempfile.TemporaryDirectory() as temp:
        catalog = read_json(inside(source, "publication-catalog.json"))
        manifest_file = Path(temp) / "manifest.json"
        manifest_file.write_text(json.dumps({"schema_version": 1, "edition": catalog["edition"], "repository": "Arcanada-one/knowledge-contract",
                                             "commit": head, "catalog": "publication-catalog.json"}))
        manifest, documents = load_inputs(source, manifest_file)  # also refuses an unclean checkout
        renderer = Renderer(source, Path(temp) / "out", manifest, documents)
        tree = tree_paths(source, head)
        ctx = {"renderer": renderer, "by_path": {d["path"]: d for d in documents}, "tree": tree, "issues": {}}
        report: dict = {"source_revision": source_revision, "publication_commit": head, "documents": len(documents), "languages": {}, "files": []}
        for language in RENDITION_LANGUAGES:
            prefix = f"{TRANSLATIONS_ROOT}/{language}/"
            found = sorted(p for p in tree if p.startswith(prefix) and p.endswith(".md") and p in tree and (source / p).is_file())
            expected = {rendition_path_for(language, d["path"]): d for d in documents}
            matched = [p for p in found if p in expected]
            summary = {"files_found": len(found), "path_matches": len(matched), "unmatched_paths": [p for p in found if p not in expected],
                       "absent_documents": len(expected) - len(matched), "states": Counter(), "front_matter_pin_agrees": 0,
                       "link_classes": Counter(), "unresolved_links": Counter(),
                       "parity_failures": Counter(), "other_failures": Counter(), "files_with_a_failure": 0, "files_clean": 0}
            entries = []
            for path in matched:
                doc = expected[path]
                original = git_bytes(source, "show", f"{source_revision}:{doc['path']}")
                if original is None:
                    raise ValueError(f"{doc['path']} does not exist at the source revision {source_revision}")
                latest = git_bytes(source, "log", "-1", "--format=%H", head, "--", path).decode().strip()
                entries.append((doc, {
                    "work": doc["slug"], "language": language, "script": RENDITION_LANGUAGES[language], "counts_as_independent_source": False,
                    "source": {"path": doc["path"], "sha256": sha256(original).hexdigest(), "revision": source_revision, "language": "en"},
                    "rendition": {"path": path, "sha256": sha256((source / path).read_bytes()).hexdigest(), "revision": latest},
                    "sections": positional_sections(source, doc, path)}))
            validate_sidecar({"schema_version": SIDECAR_SCHEMA_VERSION, "kind": "arcanada-publication-renditions", "edition": manifest["edition"],
                              "renditions": [e for _, e in entries]}, manifest)  # a layout violation cannot get past this
            states = {(e["work"], e["language"]): resolve_state(source, manifest, d, e)[0] for d, e in entries}
            pinned, peer_maps = link_context([e for _, e in entries])
            language_ctx = dict(ctx, pinned=pinned, peer_maps=peer_maps)  # a translated peer must be a pinned entry of this audit
            for doc, entry in entries:
                file_report: dict = {"failures": []}
                compile_entry(source, manifest, doc, entry, states, language_ctx, file_report)
                state = states[(entry["work"], language)]
                summary["states"][state] += 1
                ast = parse_markdown(source / entry["rendition"]["path"])
                blob = git_bytes(source, "rev-parse", f"{source_revision}:{doc['path']}").decode().strip()
                if (meta_value(ast, "translation_of"), meta_value(ast, "source_commit"), meta_value(ast, "source_git_blob")) == (doc["path"], source_revision, blob):
                    summary["front_matter_pin_agrees"] += 1
                for kind, path_, target in file_report.get("links", []):
                    summary["link_classes"][kind] += 1
                    if kind in {"document", "peer"}:
                        shown = states.get((doc_slug(ctx, path_), language), "missing") in ("reviewed", "partially-reviewed", "unreviewed")
                        summary["link_classes"]["document_shown" if shown else "document_fallback"] += 1
                for stage, code, _ in file_report["failures"]:
                    bucket = "unresolved_links" if code.startswith("RENDITION_LINK_") else "parity_failures" if stage == "parity" else "other_failures"
                    summary[bucket][code] += 1
                    report["files"].append({"language": language, "path": entry["rendition"]["path"], "stage": stage, "code": code})
                summary["files_with_a_failure" if file_report["failures"] else "files_clean"] += 1
            report["languages"][language] = {k: dict(sorted(v.items())) if isinstance(v, Counter) else v for k, v in summary.items()}
        report["files"].sort(key=lambda f: (f["language"], f["path"], f["stage"], f["code"]))
        return report


def doc_slug(ctx: dict, path: str) -> str:
    return ctx["by_path"][path]["slug"]


def positional_sections(source: Path, doc: dict, rendition_path: str) -> list[dict]:
    """Pair the source and rendition headings by position. Only for the dry run: a real sidecar declares the mapping."""
    src, rnd = sections_of(parse_markdown(inside(source, doc["path"])))[0], sections_of(parse_markdown(inside(source, rendition_path)))[0]
    pairs = [{"source": a[1], "rendition": b[1]} for a, b in zip(src, rnd)]
    return pairs or [{"source": "none", "rendition": "none"}]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(audit(args.source_dir.resolve(), args.source_revision), indent=2, ensure_ascii=False, sort_keys=True))
    except (ValueError, RenditionError) as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    main()
