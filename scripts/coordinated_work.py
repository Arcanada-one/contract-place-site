# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Render the pinned Coordinated Work proposal without admitting publications.

The programme uses the roadmap checkout, independently of the manuscript pin.
No network, task registration or execution status is inferred by this compiler.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
from urllib.parse import quote, unquote, urlsplit

from build_publication import csp_table_classes, inside, parse_markdown, plain, run

REPOSITORY = "Arcanada-one/knowledge-contract"
PREFIX = "roadmap/coordinated-work/plan/"
PAGE_PATHS = {
    "en": PREFIX + "PROGRAMME.md",
    "ru": PREFIX + "PROGRAMME.ru.md",
    "zh-Hans": PREFIX + "PROGRAMME.zh-Hans.md",
}
GRAPH_PATH = PREFIX + "execution-graph.json"
ROUTE = "roadmap/coordinated-work"


def source_url(commit: str, path: str) -> str:
    return f"https://github.com/{REPOSITORY}/blob/{commit}/{quote(path, safe='/')}"


def validate_graph(graph: dict) -> dict:
    """Count the proposed graph; never present its rows as actual task state."""
    if graph.get("schema") != "CoordinatedWorkExecutionProposal/v1":
        raise ValueError("Unsupported Coordinated Work graph schema")
    if (graph.get("status") != "proposed" or graph.get("external_task_id") is not None
            or graph.get("execution_assigned") is not False
            or graph.get("current_task_statuses_included") is not False):
        raise ValueError("Coordinated Work is a proposal, not an execution-state feed")
    tasks, epics, papers, hypotheses = (graph.get(k) for k in ("tasks", "epics", "papers", "hypotheses"))
    if any(not isinstance(items, list) or not items for items in (tasks, epics, papers, hypotheses)):
        raise ValueError("Coordinated Work graph collections must be nonempty lists")
    ids = [task.get("id") for task in tasks]
    if len(ids) != len(set(ids)) or any(not isinstance(i, str) or not i for i in ids):
        raise ValueError("Coordinated Work task identities must be unique")
    edges = 0
    for task in tasks:
        if (task.get("status") != "proposed" or task.get("external_task_id") is not None
                or task.get("execution_assigned") is not False):
            raise ValueError("Coordinated Work task rows must retain proposed status")
        dependencies = task.get("dependencies")
        if not isinstance(dependencies, list):
            raise ValueError("Coordinated Work dependencies must be explicit")
        if any(dep.get("task_id") not in ids for dep in dependencies):
            raise ValueError("Unknown Coordinated Work prerequisite")
        edges += len(dependencies)
    return {"epics": len(epics), "packages": len(tasks), "edges": edges,
            "papers": len(papers), "hypotheses": len(hypotheses)}


def render_page(source: Path, path: str, commit: str, language: str) -> dict:
    ast = parse_markdown(inside(source, path))

    def transform(node):
        if isinstance(node, list):
            for child in node:
                transform(child)
        elif isinstance(node, dict):
            kind = node.get("t")
            if kind in {"RawBlock", "RawInline"} and node["c"][0] in {"html", "html5"}:
                raise ValueError("Raw HTML is not supported in a Coordinated Work programme")
            if kind == "Image":
                raise ValueError("Coordinated Work overview supports text and source links only")
            if kind == "Link":
                target = node["c"][2][0]
                parts = urlsplit(target)
                if parts.scheme:
                    if parts.scheme != "https":
                        raise ValueError("Unsupported Coordinated Work link scheme")
                elif target.startswith("//"):
                    raise ValueError("Protocol-relative Coordinated Work link refused")
                elif parts.path:
                    relative = posixpath.normpath(str(PurePosixPath(path).parent / unquote(parts.path)))
                    if not inside(source, relative).exists():
                        raise ValueError(f"Missing Coordinated Work link target: {relative}")
                    suffix = ("?" + parts.query if parts.query else "") + ("#" + parts.fragment if parts.fragment else "")
                    target_language = next((lang for lang, candidate in PAGE_PATHS.items() if candidate == relative), None)
                    node["c"][2][0] = (f"/{target_language}/{ROUTE}/" if target_language else source_url(commit, relative)) + suffix
            for value in node.values():
                transform(value)

    transform(ast)
    blocks, toc, title, title_id = [], [], None, None
    for block in ast["blocks"]:
        if block["t"] == "Header":
            level, attrs, inlines = block["c"]
            if level == 1 and title is None:
                title, title_id = plain(inlines), attrs[0]
                continue
            if level in {2, 3}:
                toc.append({"level": level, "id": attrs[0], "title": plain(inlines)})
        blocks.append(block)
    if not title or not toc:
        raise ValueError(f"Coordinated Work page has no title or contents: {path}")
    ast["blocks"] = blocks
    html = csp_table_classes(run(["pandoc", "--from=json", "--to=html5", "--mathml", "--no-highlight", "--wrap=none", "--fail-if-warnings"], json.dumps(ast)))
    # Source diagrams remain available, while the adjacent numbered sequence is
    # the accessible reading view; no client-side diagram service is loaded.
    summary = {"en": "Dependency diagram source", "ru": "Исходный текст схемы зависимостей", "zh-Hans": "依赖图源文本"}[language]
    html = re.sub(r'(<pre class="mermaid"><code>.*?</code></pre>)',
                  lambda match: f'<details class="cw-diagram-source"><summary>{summary}</summary>{match[1]}</details>', html, flags=re.S)
    return {"path": path, "title": title, "title_id": title_id, "html": html, "toc": toc,
            "route": f"/{language}/{ROUTE}/", "source": source_url(commit, path)}


def compile_coordinated_work(source: Path, manifest_path: Path, roadmap_commit: str) -> dict | None:
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    commit = manifest.get("commit", "")
    if (manifest.get("schema_version") != 1 or manifest.get("repository") != REPOSITORY
            or not re.fullmatch(r"[0-9a-f]{40}", commit) or commit != roadmap_commit):
        raise ValueError("Coordinated Work must bind the exact roadmap source commit")
    if run(["git", "rev-parse", "HEAD"], cwd=source).strip() != commit:
        raise ValueError("Coordinated Work source checkout does not match its pin")
    if run(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=source).strip():
        raise ValueError("Coordinated Work source checkout must be clean")
    entries = manifest.get("files", [])
    expected = set(PAGE_PATHS.values()) | {GRAPH_PATH}
    if (len(entries) != len(expected) or {item.get("path") for item in entries} != expected):
        raise ValueError("Coordinated Work must pin exactly the graph and all three programme languages")
    records = {}
    for item in entries:
        path = item["path"]
        data = inside(source, path).read_bytes()
        digest = sha256(data).hexdigest()
        if digest != item.get("sha256"):
            raise ValueError(f"Coordinated Work source hash mismatch: {path}")
        records[path] = {"path": path, "sha256": digest, "url": source_url(commit, path)}
    graph = json.loads(inside(source, GRAPH_PATH).read_text(encoding="utf-8"))
    counts = validate_graph(graph)
    pages = {}
    for language, path in PAGE_PATHS.items():
        pages[language] = {**render_page(source, path, commit, language), "source_sha256": records[path]["sha256"]}
    return {"kind": "planned-research-programme", "status": "proposed", "programme_id": graph["programme_id"],
            "pin": {"repository": REPOSITORY, "commit": commit, "files": list(records.values())},
            "counts": counts, "pages": pages, "execution_state_published": False}


def provenance(programme: dict) -> dict:
    return {key: programme[key] for key in ("kind", "status", "programme_id", "pin", "counts", "execution_state_published")}
