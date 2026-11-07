#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Build the publication reader from one committed, local knowledge repository.

No network access. Pandoc parses Markdown and produces HTML5/MathML; this script
resolves document links against the catalog and verifies the resulting site.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
from xml.etree import ElementTree as ET
import subprocess
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = "https://contract.place"
REPOSITORY = "Arcanada-one/knowledge-contract"
GITHUB = "https://github.com/" + REPOSITORY
PANDOC_VERSION = "3.1.3"
CC = "https://creativecommons.org/licenses/by/4.0/"
APACHE = "https://www.apache.org/licenses/LICENSE-2.0"
# Catalogue status values the site knows how to label. An unknown status stops the build (never silently shown as accepted).
STATUSES = {"research-draft"}
KINDS = {
    "paper": ("Scientific paper", "/en/science/", "Science"),
    "specification": ("Engineering specification", "/en/engineering/specifications/", "Specifications"),
    "study": ("Engineering study", "/en/engineering/studies/", "Studies"),
    "glossary": ("Reference", "/en/reference/", "Reference"),
    "bibliography": ("Reference", "/en/reference/", "Reference"),
    "appendix": ("Appendix", "/en/appendices/", "Appendices"),
}
FAMILY_INTROS = {
    "/en/science/": ("Science", "Definitions, assumptions, propositions and limits of the Knowledge Contract model. Each paper links to its engineering interpretation and supporting material."),
    "/en/engineering/specifications/": ("Engineering specifications", "Normative formats and procedures for representing, transforming, selecting and reusing knowledge. Requirements are separated from the scientific claims they operationalize."),
    "/en/engineering/studies/": ("Engineering studies", "Applications, test designs, counterexamples and observations. Each study states what was examined and how far its findings support the model."),
    "/en/reference/": ("Reference", "Shared definitions and bibliographic sources for the scientific and engineering documents."),
    "/en/appendices/": ("Appendices", "Traceability and integration details that support the main reading paths."),
}


def run(command: list[str], text: str | None = None, cwd: Path | None = None) -> str:
    result = subprocess.run(command, input=text, text=True, capture_output=True, cwd=cwd)
    if result.returncode:
        raise ValueError(f"{' '.join(command)} failed: {result.stderr.strip()}")
    return result.stdout


def e(value: object) -> str:
    return escape(str(value), quote=True)


def read_json(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return result


def inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes source repository: {relative}")
    return path


def load_inputs(source: Path, manifest_path: Path, allow_uncommitted: bool = False) -> tuple[dict, list[dict]]:
    manifest = read_json(manifest_path)
    manifest.pop("preview", None)
    if manifest.get("schema_version") != 1 or manifest.get("repository") != REPOSITORY:
        raise ValueError("Unsupported publication manifest schema or repository")
    if not re.fullmatch(r"[0-9a-f]{40}", manifest.get("commit", "")):
        raise ValueError("The publication manifest must pin a full 40-character commit")
    if not re.fullmatch(r"[0-9]+\.[0-9]+(?:\.[0-9]+)?", manifest.get("edition", "")):
        raise ValueError("The publication edition must be a numeric release identifier")
    actual = run(["git", "rev-parse", "HEAD"], cwd=source).strip()
    if actual != manifest["commit"]:
        raise ValueError(f"Source HEAD {actual} differs from manifest {manifest['commit']}")
    if run(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=source).strip() and not allow_uncommitted:
        raise ValueError("Source repository has uncommitted changes; commit the publication before building")
    if allow_uncommitted:
        manifest["preview"] = True
    catalog = read_json(inside(source, manifest.get("catalog", "publication-catalog.json")))
    if catalog.get("schema_version") != 1 or catalog.get("edition") != manifest["edition"]:
        raise ValueError("Catalog schema/edition does not match the publication manifest")
    documents = catalog.get("documents")
    if not isinstance(documents, list) or not documents:
        raise ValueError("Publication catalog has no documents")
    paths, routes = set(), set()
    for doc in documents:
        if not isinstance(doc, dict) or doc.get("type") not in KINDS:
            raise ValueError(f"Unknown document type: {doc}")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", doc.get("slug", "")):
            raise ValueError(f"Document requires a readable kebab-case slug: {doc}")
        if not isinstance(doc.get("title"), str) or not doc["title"].strip():
            raise ValueError("Document title missing")
        path = doc.get("path", "")
        if not isinstance(path, str) or not path.endswith(".md") or path.startswith("/"):
            raise ValueError(f"Invalid Markdown path: {path}")
        if not inside(source, path).is_file():
            raise ValueError(f"Catalog file missing: {path}")
        if doc.get("language", "en") != "en":
            raise ValueError(f"Reader catalog requires an English publication text: {path}")
        if "status" in doc and doc["status"] not in STATUSES:
            raise ValueError(f"Unknown catalogue status {doc['status']!r} for {path}; the site labels only {sorted(STATUSES)}")
        doc["route"] = KINDS[doc["type"]][1] + doc["slug"] + "/"
        if path in paths or doc["route"] in routes:
            raise ValueError(f"Duplicate catalog path or route: {path}")
        paths.add(path)
        routes.add(doc["route"])
        doc["sha256"] = sha256(inside(source, path).read_bytes()).hexdigest()
    return manifest, documents


def plain(node: object) -> str:
    if isinstance(node, list):
        return "".join(plain(item) for item in node)
    if not isinstance(node, dict):
        return ""
    if node.get("t") == "Str":
        return node["c"]
    if node.get("t") in {"Space", "SoftBreak", "LineBreak"}:
        return " "
    if node.get("t") in {"Code", "Math"}:
        return node["c"][-1]
    if node.get("t") in {"Link", "Image"}:
        return plain(node["c"][1])
    return plain(node.get("c", []))


def parse_markdown(path: Path) -> dict:
    return json.loads(run([
        "pandoc", "--from=markdown+gfm_auto_identifiers+pipe_tables+tex_math_dollars+tex_math_single_backslash+autolink_bare_uris",
        "--to=json", str(path),
    ]))


def node_count(value: object, kind: str) -> int:
    if isinstance(value, list):
        return sum(node_count(item, kind) for item in value)
    if isinstance(value, dict):
        return int(value.get("t") == kind) + sum(node_count(item, kind) for item in value.values())
    return 0


def csp_table_classes(content: str) -> str:
    """Retain Pandoc table alignment through local CSS, never inline style."""
    def convert(match):
        before, value, after = match.groups()
        align = re.fullmatch(r'text-align:\s*(left|center|right);?', value)
        width = re.fullmatch(r'width:\s*([0-9]{1,3})%', value)
        if align:
            name = 'table-align-' + align[1]
        elif width and before.startswith('<col') and 0 < int(width[1]) <= 100:
            name = 'table-width-' + str(int(width[1]))
        else:
            raise ValueError('Unsupported inline table style from renderer: ' + value)
        if 'class="' in before:
            before = before.replace('class="', 'class="' + name + ' ', 1)
        else:
            before += ' class="' + name + '"'
        return before + after
    return re.sub(r'(<(?:col|th|td)\b[^>]*?)\sstyle="([^"]*)"([^>]*>)', convert, content)


class Renderer:
    def __init__(self, source: Path, output: Path, manifest: dict, documents: list[dict]):
        self.source, self.output, self.manifest, self.documents = source, output, manifest, documents
        self.by_path = {doc["path"]: doc for doc in documents}
        self.site_routes: set[str] = set()

    def source_url(self, path: str, history: bool = False) -> str:
        return f"{GITHUB}/{'commits' if history else 'blob'}/{self.manifest['commit']}/{quote(path, safe='/')}"

    def resolve_link(self, target: str, doc: dict, image: bool = False) -> str:
        parts = urlsplit(target)
        if parts.scheme in {"https", "http", "mailto"} or target.startswith("//"):
            prefix = GITHUB + "/blob/"
            if not image and target.startswith(prefix):
                tail = unquote(parts.path).split("/blob/", 1)[1].split("/", 1)
                if len(tail) == 2 and tail[0] in {"main", self.manifest["commit"]} and tail[1] in self.by_path:
                    return self.by_path[tail[1]]["route"] + ("#" + parts.fragment if parts.fragment else "")
                if len(tail) == 2 and tail[0] == "main" and inside(self.source, tail[1]).exists():
                    return self.source_url(tail[1]) + ("#" + parts.fragment if parts.fragment else "")
            if image:
                raise ValueError(f"Remote image would break an offline build: {doc['path']}: {target}")
            return target
        if parts.scheme:
            raise ValueError(f"Unsupported link scheme: {doc['path']}: {target}")
        if not parts.path:
            return target
        raw_path = unquote(parts.path)
        relative = posixpath.normpath(raw_path.lstrip("/") if raw_path.startswith("/") else str(PurePosixPath(doc["path"]).parent / raw_path))
        source_path = inside(self.source, relative)
        if not source_path.exists():
            raise ValueError(f"Missing link target in {doc['path']}: {target} -> {relative}")
        suffix = ("?" + parts.query if parts.query else "") + ("#" + parts.fragment if parts.fragment else "")
        if relative in self.by_path:
            return self.by_path[relative]["route"] + suffix
        if image:
            asset_path = Path("assets/documents") / relative
            destination = self.output / asset_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, destination)
            return "/" + asset_path.as_posix() + suffix
        return self.source_url(relative) + suffix

    def transform(self, node: object, doc: dict) -> None:
        if isinstance(node, list):
            for item in node:
                self.transform(item, doc)
        elif isinstance(node, dict):
            if node.get("t") in {"Link", "Image"}:
                node["c"][2][0] = self.resolve_link(node["c"][2][0], doc, node["t"] == "Image")
            if node.get("t") in {"RawBlock", "RawInline"} and node["c"][0] in {"html", "html5"}:
                # Reader input is Markdown, not an executable HTML application.
                if re.search(r"<(?:script|iframe|object|embed)\b|\son\w+\s*=", node["c"][1], re.I):
                    raise ValueError(f"Executable raw HTML in {doc['path']}")
            for value in node.values():
                self.transform(value, doc)

    def document(self, doc: dict) -> dict:
        ast = parse_markdown(inside(self.source, doc['path']))
        self.transform(ast, doc)
        toc, blocks = [], []
        title_id = 'document-title'
        first_title = True
        for block in ast['blocks']:
            if block['t'] == 'Header':
                level, attrs, inlines = block['c']
                if level == 1 and first_title:
                    first_title = False
                    title_id = attrs[0] or title_id
                    continue
                if level in {2, 3}:
                    toc.append({'level': level, 'id': attrs[0], 'title': plain(inlines)})
            blocks.append(block)
        ast['blocks'] = blocks
        content = run(['pandoc', '--from=json', '--to=html5', '--mathml', '--no-highlight', '--wrap=none', '--fail-if-warnings'], json.dumps(ast))
        content = csp_table_classes(content)
        count = node_count(blocks, 'Math')
        if len(re.findall(r'<math(?:\s|>)', content)) != count:
            raise ValueError(f'Mathematical expressions did not render exactly: {doc["path"]}')
        return {'html': content, 'toc': toc, 'title_id': title_id, 'math_count': count}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'publication-manifest.json')
    parser.add_argument('--roadmap-source-dir', type=Path, required=True,
                        help='clean checkout of the commit pinned in roadmap-manifest.json (independent of the manuscript pin)')
    parser.add_argument('--roadmap-manifest', type=Path, default=ROOT / 'roadmap-manifest.json')
    parser.add_argument('--renditions-file', type=Path, default=None,
                        help='TEST/FIXTURE ONLY: read the renditions sidecar from this file instead of the catalogue-declared one. '
                             'The output is marked renditions_source=fixture and check_publication.py refuses it; never use it for a production build.')
    args = parser.parse_args()
    source = args.source_dir.resolve()
    version = run(['pandoc', '--version']).splitlines()[0].split()[1]
    if version != PANDOC_VERSION:
        raise ValueError(f'Expected Pandoc {PANDOC_VERSION}, found {version}')
    manifest, documents = load_inputs(source, args.manifest)
    # The roadmap is compiled and validated first: a stale pin, missing task or inconsistent graph
    # stops the build before any generated file is written.
    from roadmap import compile_roadmap
    roadmap_source = args.roadmap_source_dir.resolve()
    manuscripts = {d['path']: {'route': d['route'], 'source_sha256': d['sha256']} for d in documents}
    roadmap = compile_roadmap(roadmap_source, args.roadmap_manifest, manuscripts)
    # Generate from the source before the JS build copies the current site assets.
    from publication_catalog import write_catalog
    renderer = Renderer(source, ROOT / 'src/site', manifest, documents)
    # Language renditions (optional, versioned sidecar in the knowledge repository): validated before any file is written.
    from renditions import compile_renditions
    renditions = compile_renditions(source, manifest, documents, renderer, run, args.renditions_file.resolve() if args.renditions_file else None)
    write_catalog(source, ROOT, manifest, documents, renderer, roadmap, renditions)
    print(run(['node', 'build.mjs'], cwd=ROOT).strip())
    from publication_checks import check_site
    count = check_site(ROOT / 'public')
    from publication_checks import check_status_labels
    check_status_labels(ROOT / 'public', json.loads((ROOT / 'src/content/catalog.json').read_text())['records'])
    load_inputs(source, args.manifest)
    compile_roadmap(roadmap_source, args.roadmap_manifest, manuscripts)
    if renditions:
        print(f'Renditions: {len(renditions.entries)} work/language pairs from the {renditions.source_kind} sidecar {renditions.sidecar_path}.')
    print(f'Built {len(documents)} complete documents in three interface languages / {count} pages; edition {manifest["edition"]}; source {manifest["commit"]}; roadmap of {len(roadmap["tasks"])} planned tasks at {roadmap["pin"]["commit"]}.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, FileNotFoundError) as error:
        raise SystemExit(str(error))
