# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Versioned language renditions of the published English manuscripts (K8).

A rendition is a translation of ONE exact source edition, not a new independent source. This module validates the
linked, versioned sidecar ``publication-renditions.json`` that the knowledge repository (source of truth for text)
may declare through the optional ``renditions`` key of ``publication-catalog.json``, and compiles the renditions it
describes. Nothing here writes or translates text. With no sidecar the compiler output is unchanged.

Every refusal is a RenditionError whose message starts with a stable code (see CODES). The design is in
docs/versioned-renditions.md.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
from urllib.parse import unquote, urlsplit

SIDECAR_KIND = "arcanada-publication-renditions"
SOURCE_LANGUAGE = "en"
# Interface locales other than the English source language, with the script each declares.
RENDITION_LANGUAGES = {"ru": "Cyrl", "zh-Hans": "Hans"}
STATES_RENDERED = ("reviewed", "partially-reviewed", "unreviewed")
STATES_FALLBACK = ("stale", "missing")
STATES = STATES_RENDERED + STATES_FALLBACK
CODES = (
    "RENDITION_SIDECAR_SCHEMA", "RENDITION_LANGUAGE", "RENDITION_SOURCE_PIN", "RENDITION_REVISION_PIN",
    "RENDITION_DIGEST", "RENDITION_UNKNOWN_WORK", "RENDITION_DUPLICATE", "RENDITION_REVIEW_UNEVIDENCED",
    "RENDITION_SECTION_MISSING", "RENDITION_SECTION_DRIFT", "RENDITION_SECTION_UNRESOLVED",
    "RENDITION_STRUCTURE_MISMATCH", "RENDITION_FORMULA_CHANGED", "RENDITION_CODE_CHANGED",
    "RENDITION_REFERENCE_DROPPED", "RENDITION_REFERENCE_CHANGED", "RENDITION_FIXTURE_ONLY",
    "RENDITION_SILENT_FALLBACK", "RENDITION_STATE_LABEL", "RENDITION_SOURCE_AUTHORITY",
)
HEX40, HEX64 = re.compile(r"[0-9a-f]{40}"), re.compile(r"[0-9a-f]{64}")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
ANCHOR = re.compile(r"[^\s\"'<>&#/?]+")
TOP_KEYS = {"schema_version", "kind", "edition", "renditions"}
ENTRY_KEYS = {"work", "language", "script", "source", "rendition", "review", "sections", "counts_as_independent_source"}
SOURCE_KEYS = {"path", "sha256", "revision", "language"}
RENDITION_KEYS = {"path", "sha256", "revision"}
REVIEW_KEYS = {"status", "scope", "reviewed_sections", "method", "reviewers", "evidence", "limits"}
REVIEWER_KEYS = {"kind", "ref"}
SECTION_KEYS = {"source", "rendition"}
FIXTURE_SOURCE, REPOSITORY_SOURCE = "fixture", "knowledge-repository"
STRUCTURAL_BLOCKS = ("Table", "BulletList", "OrderedList", "DefinitionList", "BlockQuote", "CodeBlock", "HorizontalRule", "Figure", "RawBlock")


class RenditionError(ValueError):
    def __init__(self, code: str, detail: str):
        assert code in CODES, code
        self.code = code
        super().__init__(f"{code}: {detail}")


def fail(code: str, detail: str):
    raise RenditionError(code, detail)


def closed(value: object, keys: set[str], where: str, required: set[str] | None = None) -> dict:
    if not isinstance(value, dict):
        fail("RENDITION_SIDECAR_SCHEMA", f"{where} must be an object")
    unknown = sorted(set(value) - keys)
    if unknown:
        fail("RENDITION_SIDECAR_SCHEMA", f"{where} has unknown fields {unknown}")
    missing = sorted((required if required is not None else keys) - set(value))
    if missing:
        fail("RENDITION_SIDECAR_SCHEMA", f"{where} lacks fields {missing}")
    return value


def text(value: object, where: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        fail("RENDITION_SIDECAR_SCHEMA", f"{where} must be a non-empty trimmed string")
    return value


def safe_path(value: object, where: str) -> str:
    path = text(value, where)
    parts = PurePosixPath(path).parts
    if path.startswith("/") or ".." in parts or "\\" in path or not path.endswith(".md"):
        fail("RENDITION_SIDECAR_SCHEMA", f"{where} must be a relative Markdown path inside the repository: {path}")
    return path


def sha(value: object, where: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        fail("RENDITION_SIDECAR_SCHEMA", f"{where} must be a lowercase SHA-256")
    return value


def commit(value: object, where: str) -> str:
    if not isinstance(value, str) or not HEX40.fullmatch(value):
        fail("RENDITION_SIDECAR_SCHEMA", f"{where} must be a full 40-character commit")
    return value


def validate_sidecar(sidecar: object, manifest: dict) -> list[dict]:
    """Closed-schema validation of the sidecar document; returns its entries. No file is read here."""
    closed(sidecar, TOP_KEYS, "sidecar")
    if sidecar["schema_version"] != 1 or isinstance(sidecar["schema_version"], bool):
        fail("RENDITION_SIDECAR_SCHEMA", "unsupported sidecar schema_version")
    if sidecar["kind"] != SIDECAR_KIND:
        fail("RENDITION_SIDECAR_SCHEMA", f"kind must be {SIDECAR_KIND!r}")
    if sidecar["edition"] != manifest["edition"]:
        fail("RENDITION_SIDECAR_SCHEMA", "sidecar edition differs from the publication edition")
    if not isinstance(sidecar["renditions"], list):
        fail("RENDITION_SIDECAR_SCHEMA", "renditions must be a list")
    seen = set()
    entries = []
    for index, entry in enumerate(sidecar["renditions"]):
        where = f"renditions[{index}]"
        closed(entry, ENTRY_KEYS, where)
        work = entry["work"]
        if not isinstance(work, str) or not SLUG.fullmatch(work):
            fail("RENDITION_SIDECAR_SCHEMA", f"{where}.work must be a catalogue slug")
        language = entry["language"]
        if language == SOURCE_LANGUAGE:
            fail("RENDITION_LANGUAGE", f"{where}: a rendition cannot be declared in the source language")
        if language not in RENDITION_LANGUAGES:
            fail("RENDITION_LANGUAGE", f"{where}: language {language!r} is not an interface locale {sorted(RENDITION_LANGUAGES)}")
        if entry["script"] != RENDITION_LANGUAGES[language]:
            fail("RENDITION_LANGUAGE", f"{where}: script {entry['script']!r} does not belong to {language}")
        if (work, language) in seen:
            fail("RENDITION_DUPLICATE", f"{where}: second rendition of {work} in {language}")
        seen.add((work, language))
        if entry["counts_as_independent_source"] is not False:
            fail("RENDITION_SIDECAR_SCHEMA", f"{where}: a rendition is never an independent source (counts_as_independent_source must be false)")
        source = closed(entry["source"], SOURCE_KEYS, f"{where}.source")
        safe_path(source["path"], f"{where}.source.path"), sha(source["sha256"], f"{where}.source.sha256")
        commit(source["revision"], f"{where}.source.revision")
        if source["language"] != SOURCE_LANGUAGE:
            fail("RENDITION_LANGUAGE", f"{where}: only an English source edition is supported, found {source['language']!r}")
        rendition = closed(entry["rendition"], RENDITION_KEYS, f"{where}.rendition")
        safe_path(rendition["path"], f"{where}.rendition.path"), sha(rendition["sha256"], f"{where}.rendition.sha256")
        commit(rendition["revision"], f"{where}.rendition.revision")
        review = closed(entry["review"], REVIEW_KEYS, f"{where}.review", REVIEW_KEYS - {"reviewed_sections"})
        if review["status"] not in {"reviewed", "unreviewed"}:
            fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review.status must be reviewed or unreviewed")
        if review["scope"] not in {"full", "sections"}:
            fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review.scope must be full or sections")
        if (review["scope"] == "sections") != ("reviewed_sections" in review):
            fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review: reviewed_sections is required exactly when scope is sections")
        if not isinstance(review["method"], str) or not isinstance(review["limits"], str):
            fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review.method and limits must be strings")
        if not isinstance(review["reviewers"], list) or not isinstance(review["evidence"], list):
            fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review.reviewers and evidence must be lists")
        for reviewer in review["reviewers"]:
            closed(reviewer, REVIEWER_KEYS, f"{where}.review.reviewers[]")
            if reviewer["kind"] not in {"agent", "human"}:
                fail("RENDITION_SIDECAR_SCHEMA", f"{where}: reviewer kind must be agent or human")
            text(reviewer["ref"], f"{where}.review.reviewers[].ref")
        for item in review["evidence"]:
            text(item, f"{where}.review.evidence[]")
        if "reviewed_sections" in review:
            if not isinstance(review["reviewed_sections"], list) or not review["reviewed_sections"]:
                fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review.reviewed_sections must be a non-empty list")
            for item in review["reviewed_sections"]:
                if not isinstance(item, str) or not ANCHOR.fullmatch(item):
                    fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review.reviewed_sections holds an invalid anchor")
        if review["status"] == "reviewed" and not (review["method"].strip() and review["reviewers"] and review["evidence"] and review["limits"].strip()):
            fail("RENDITION_REVIEW_UNEVIDENCED", f"{where}: status reviewed requires method, reviewers, evidence references and declared limits")
        if review["status"] == "unreviewed" and (review["reviewers"] or review["evidence"] or review["scope"] != "full"):
            fail("RENDITION_REVIEW_UNEVIDENCED", f"{where}: an unreviewed rendition cannot carry reviewers, evidence or a partial scope")
        if not isinstance(entry["sections"], list) or not entry["sections"]:
            fail("RENDITION_SIDECAR_SCHEMA", f"{where}.sections must be a non-empty list")
        for pair in entry["sections"]:
            closed(pair, SECTION_KEYS, f"{where}.sections[]")
            for value in pair.values():
                if not isinstance(value, str) or not ANCHOR.fullmatch(value):
                    fail("RENDITION_SIDECAR_SCHEMA", f"{where}.sections[] holds an invalid anchor")
        entries.append(entry)
    return entries


def git_bytes(source: Path, *args: str) -> bytes | None:
    import subprocess
    result = subprocess.run(["git", *args], cwd=source, capture_output=True)
    return result.stdout if result.returncode == 0 else None


def verify_pin(source: Path, manifest: dict, label: str, pin: dict, code: str) -> None:
    """A pin names the commit that authored exact bytes. It must be reachable from the publication commit (the sidecar
    itself lives in that commit, so it cannot name it) and the blob there must be the pinned bytes."""
    if git_bytes(source, "merge-base", "--is-ancestor", pin["revision"], manifest["commit"]) is None:
        fail(code, f"{label}: revision {pin['revision']} is not an ancestor of the publication commit {manifest['commit']}")
    blob = git_bytes(source, "show", f"{pin['revision']}:{pin['path']}")
    if blob is None or sha256(blob).hexdigest() != pin["sha256"]:
        fail(code, f"{label}: the bytes of {pin['path']} at {pin['revision']} are not the pinned {pin['sha256']}")


def walk(node: object, visit) -> None:
    if isinstance(node, list):
        for item in node:
            walk(item, visit)
    elif isinstance(node, dict):
        visit(node)
        for value in node.values():
            walk(value, visit)


def normalize_target(target: str, doc_path: str, fragment_map: dict[str, str]) -> str:
    parts = urlsplit(target)
    if parts.scheme or target.startswith("//"):
        return target
    fragment = unquote(parts.fragment)
    if not parts.path:
        return "#" + fragment_map.get(fragment, "\0unmapped:" + fragment)
    relative = posixpath.normpath(str(PurePosixPath(doc_path).parent / unquote(parts.path)))
    return relative + ("#" + fragment if fragment else "")


def facts(ast: dict, doc_path: str, fragment_map: dict[str, str]) -> dict:
    formulas, code, references, notes = [], [], Counter(), [0]

    def visit(node: dict) -> None:
        kind = node.get("t")
        if kind == "Math":
            formulas.append((node["c"][0]["t"], node["c"][1]))
        elif kind == "CodeBlock":
            code.append(("block", tuple(node["c"][0][1]), node["c"][1]))
        elif kind == "Code":
            code.append(("inline", tuple(node["c"][0][1]), node["c"][1]))
        elif kind in {"Link", "Image"}:
            references[(kind, normalize_target(node["c"][2][0], doc_path, fragment_map))] += 1
        elif kind == "Cite":
            for citation in node["c"][0]:
                references[("Cite", citation["citationId"])] += 1
        elif kind == "Note":
            notes[0] += 1

    walk(ast["blocks"], visit)
    return {"formulas": formulas, "code": code, "references": references, "notes": notes[0]}


def sections_of(ast: dict) -> tuple[list[tuple[int, str]], dict[str, Counter]]:
    """Headings (level 2/3, as the reader's contents list) and per-section structural block counts."""
    headings, structure, current, first_title = [], {"": Counter()}, "", True
    for block in ast["blocks"]:
        if block["t"] == "Header":
            level, attrs, _ = block["c"]
            if level == 1 and first_title:
                first_title = False
                continue
            if level in {2, 3}:
                headings.append((level, attrs[0]))
                current = attrs[0]
                structure[current] = Counter()
                continue
        structure[current][block["t"] if block["t"] in STRUCTURAL_BLOCKS else "text"] += 1
    return headings, structure


def body_text(ast: dict) -> str:
    pieces: list[str] = []

    def visit(node: dict) -> None:
        if node.get("t") == "Str":
            pieces.append(node["c"])

    walk(ast["blocks"], visit)
    return " ".join(pieces)


def script_matches(language: str, sample: str) -> bool:
    letters = [c for c in sample if c.isalpha()]
    if not letters:
        return False
    if language == "ru":
        return sum("Ѐ" <= c <= "ӿ" for c in letters) / len(letters) >= 0.5
    return sum("一" <= c <= "鿿" for c in letters) / len(letters) >= 0.3


def meta_value(ast: dict, key: str) -> str | None:
    value = ast.get("meta", {}).get(key)
    if value is None:
        return None
    if value["t"] == "MetaString":
        return value["c"]
    if value["t"] == "MetaInlines":
        from build_publication import plain
        return plain(value["c"])
    return None


def check_parity(entry: dict, source_ast: dict, rendition_ast: dict) -> dict[str, str]:
    """Structural parity between a source and its rendition. Returns the rendition-to-source anchor map."""
    work, language = entry["work"], entry["language"]
    pairs = [(p["source"], p["rendition"]) for p in entry["sections"]]
    src_heads, src_structure = sections_of(source_ast)
    rnd_heads, rnd_structure = sections_of(rendition_ast)
    src_ids, rnd_ids = [i for _, i in src_heads], [i for _, i in rnd_heads]
    mapped_src, mapped_rnd = [s for s, _ in pairs], [r for _, r in pairs]
    if len(set(mapped_src)) != len(mapped_src) or len(set(mapped_rnd)) != len(mapped_rnd):
        fail("RENDITION_SECTION_DRIFT", f"{work}/{language}: the section mapping repeats an anchor")
    if len(set(src_ids)) != len(src_ids) or len(set(rnd_ids)) != len(rnd_ids):
        fail("RENDITION_SECTION_DRIFT", f"{work}/{language}: duplicate heading anchors; use explicit stable anchors")
    missing = [s for s in src_ids if s not in mapped_src]
    if missing:
        fail("RENDITION_SECTION_MISSING", f"{work}/{language}: source sections without a mapped rendition section: {missing}")
    unknown = [s for s in mapped_src if s not in src_ids]
    if unknown:
        fail("RENDITION_SECTION_DRIFT", f"{work}/{language}: mapping names source sections that no longer exist: {unknown}")
    unresolved = [r for r in mapped_rnd if r not in rnd_ids]
    if unresolved:
        fail("RENDITION_SECTION_UNRESOLVED", f"{work}/{language}: mapped rendition anchors are absent from the rendition: {unresolved}")
    extra = [r for r in rnd_ids if r not in mapped_rnd]
    if extra:
        fail("RENDITION_SECTION_DRIFT", f"{work}/{language}: rendition sections absent from the mapping: {extra}")
    if [dict(pairs)[s] for s in src_ids] != rnd_ids:
        fail("RENDITION_SECTION_DRIFT", f"{work}/{language}: the rendition's section order differs from the source")
    levels_src, levels_rnd = dict((i, l) for l, i in src_heads), dict((i, l) for l, i in rnd_heads)
    for s, r in pairs:
        if levels_src[s] != levels_rnd[r]:
            fail("RENDITION_SECTION_DRIFT", f"{work}/{language}: heading level of {s} differs from {r}")
    reviewed = entry["review"].get("reviewed_sections")
    if reviewed is not None and any(s not in src_ids for s in reviewed):
        fail("RENDITION_SECTION_DRIFT", f"{work}/{language}: reviewed_sections names a section that is not in the source")
    structure_pairs = [("", "")] + pairs
    for s, r in structure_pairs:
        a, b = src_structure[s], rnd_structure[r]
        if a["text"] and not b["text"]:
            fail("RENDITION_SECTION_MISSING", f"{work}/{language}: section {s or '(preamble)'} has text in the source but none in the rendition")
        if {k: v for k, v in a.items() if k != "text"} != {k: v for k, v in b.items() if k != "text"}:
            fail("RENDITION_STRUCTURE_MISMATCH", f"{work}/{language}: tables, lists, quotations or code blocks of section {s or '(preamble)'} differ from the source")
    reverse = {r: s for s, r in pairs}
    source_facts = facts(source_ast, entry["source"]["path"], {i: i for i in src_ids})
    rendition_facts = facts(rendition_ast, entry["rendition"]["path"], reverse)
    if [f for f in source_facts["formulas"]] != rendition_facts["formulas"]:
        fail("RENDITION_FORMULA_CHANGED", f"{work}/{language}: formulas differ from the source (exact LaTeX and display mode must be identical, in order)")
    if source_facts["code"] != rendition_facts["code"]:
        fail("RENDITION_CODE_CHANGED", f"{work}/{language}: code blocks or code identifiers differ from the source (exact text, in order)")
    dropped = source_facts["references"] - rendition_facts["references"]
    if dropped or source_facts["notes"] > rendition_facts["notes"]:
        fail("RENDITION_REFERENCE_DROPPED", f"{work}/{language}: references or footnotes of the source are missing: {sorted(map(str, dropped))[:5]}, footnotes {source_facts['notes']} -> {rendition_facts['notes']}")
    if rendition_facts["references"] != source_facts["references"] or rendition_facts["notes"] != source_facts["notes"]:
        fail("RENDITION_REFERENCE_CHANGED", f"{work}/{language}: the rendition adds or retargets references: {sorted(map(str, rendition_facts['references'] - source_facts['references']))[:5]}")
    return reverse


def state_of(entry: dict, current_source_sha: str) -> str:
    if entry["source"]["sha256"] != current_source_sha:
        return "stale"
    review = entry["review"]
    if review["status"] == "unreviewed":
        return "unreviewed"
    return "reviewed" if review["scope"] == "full" else "partially-reviewed"


def annotate_sections(html: str, pairs: list[tuple[str, str]]) -> str:
    """Bind each rendition heading to its source section; keep the source anchor resolvable when the ids differ."""
    for source_id, rendition_id in pairs:
        pattern = re.compile(r'<h([23]) id="' + re.escape(rendition_id) + r'"')
        alias = f'<span id="{source_id}" class="source-anchor"></span>' if source_id != rendition_id else ""
        html, count = pattern.subn(lambda m: f'{alias}<h{m.group(1)} id="{rendition_id}" data-source-section="{source_id}"', html)
        if count != 1:
            fail("RENDITION_SECTION_UNRESOLVED", f"rendition heading {rendition_id} did not render exactly once")
    return html


def sidecar_reference(source: Path, catalog: dict) -> str | None:
    reference = catalog.get("renditions")
    if reference is None:
        return None
    return safe_json_path(reference)


def safe_json_path(value: object) -> str:
    if not isinstance(value, str) or not value.endswith(".json") or value.startswith("/") or ".." in PurePosixPath(value).parts or "\\" in value:
        fail("RENDITION_SIDECAR_SCHEMA", "the catalogue renditions key must be a relative JSON path inside the repository")
    return value


class Compiled:
    def __init__(self, source_kind: str, sidecar_path: str, sidecar_sha256: str, by_work: dict, entries: list[dict]):
        self.source_kind, self.sidecar_path, self.sidecar_sha256 = source_kind, sidecar_path, sidecar_sha256
        self.by_work, self.entries = by_work, entries

    def for_work(self, work: str) -> dict:
        return self.by_work[work]

    def provenance(self) -> dict:
        return {
            "schema_version": 1, "kind": SIDECAR_KIND, "renditions_source": self.source_kind,
            "sidecar": self.sidecar_path, "sidecar_sha256": self.sidecar_sha256,
            "entries": self.entries,
        }


def compile_renditions(source: Path, manifest: dict, documents: list[dict], renderer, run, fixture_file: Path | None = None) -> Compiled | None:
    """Validate and compile the declared renditions. Returns None when none are declared (output stays unchanged)."""
    from build_publication import inside, parse_markdown, read_json
    catalog = read_json(inside(source, manifest.get("catalog", "publication-catalog.json")))
    declared = sidecar_reference(source, catalog)
    if declared is not None and fixture_file is not None:
        fail("RENDITION_SOURCE_AUTHORITY", "the catalogue already declares a sidecar; a fixture sidecar must not override the knowledge repository")
    if declared is None and fixture_file is None:
        return None
    if fixture_file is not None:
        sidecar_path, kind, raw = "(fixture) " + fixture_file.name, FIXTURE_SOURCE, fixture_file.read_bytes()
    else:
        file = inside(source, declared)
        if not file.is_file():
            fail("RENDITION_SIDECAR_SCHEMA", f"declared sidecar is missing: {declared}")
        run(["git", "ls-files", "--error-unmatch", declared], cwd=source)
        sidecar_path, kind, raw = declared, REPOSITORY_SOURCE, file.read_bytes()
    try:
        sidecar = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        fail("RENDITION_SIDECAR_SCHEMA", f"the sidecar is not valid UTF-8 JSON: {error}")
    entries = validate_sidecar(sidecar, manifest)
    by_path = {doc["path"]: doc for doc in documents}
    by_slug = {doc["slug"]: doc for doc in documents}
    declared_pairs = {(e["work"], e["language"]): e for e in entries}
    result: dict[str, dict] = {}
    provenance_entries = []
    for doc in documents:
        result[doc["slug"]] = {}
        for language in RENDITION_LANGUAGES:
            entry = declared_pairs.get((doc["slug"], language))
            pin = {"path": doc["path"], "sha256": doc["sha256"], "revision": manifest["commit"], "language": SOURCE_LANGUAGE}
            if entry is None:
                result[doc["slug"]][language] = {"language": language, "script": RENDITION_LANGUAGES[language], "state": "missing", "source": pin}
                provenance_entries.append({"work": doc["slug"], "language": language, "state": "missing", "source_sha256": doc["sha256"]})
    for entry in entries:
        work, language = entry["work"], entry["language"]
        doc = by_slug.get(work)
        if doc is None:
            fail("RENDITION_UNKNOWN_WORK", f"{work} is not in the publication catalogue")
        if entry["source"]["path"] != doc["path"]:
            fail("RENDITION_SOURCE_PIN", f"{work}/{language}: source path {entry['source']['path']} is not the catalogued {doc['path']}")
        rendition_path = entry["rendition"]["path"]
        label = f"{work}/{language}"
        verify_pin(source, manifest, label + " source", entry["source"], "RENDITION_SOURCE_PIN")
        verify_pin(source, manifest, label + " rendition", entry["rendition"], "RENDITION_REVISION_PIN")
        if git_bytes(source, "merge-base", "--is-ancestor", entry["source"]["revision"], entry["rendition"]["revision"]) is None:
            fail("RENDITION_REVISION_PIN", f"{label}: the rendition revision predates the source revision it claims to render (mixed source/rendition pins)")
        if rendition_path in by_path or rendition_path == doc["path"]:
            fail("RENDITION_SOURCE_PIN", f"{work}/{language}: a rendition cannot be a catalogued source document")
        file = inside(source, rendition_path)
        if not file.is_file():
            fail("RENDITION_DIGEST", f"{work}/{language}: rendition file is missing: {rendition_path}")
        digest = sha256(file.read_bytes()).hexdigest()
        if digest != entry["rendition"]["sha256"]:
            fail("RENDITION_DIGEST", f"{work}/{language}: rendition bytes {digest} differ from the pinned {entry['rendition']['sha256']}")
        state = state_of(entry, doc["sha256"])
        record = {
            "language": language, "script": entry["script"], "state": state,
            "source": dict(entry["source"], url=renderer.source_url(doc["path"])),
            "current_source_sha256": doc["sha256"],
            "rendition": dict(entry["rendition"], url=renderer.source_url(rendition_path), history=renderer.source_url(rendition_path, True)),
            "review": entry["review"], "sections": entry["sections"], "counts_as_independent_source": False,
        }
        if state != "stale":
            source_ast, rendition_ast = parse_markdown(inside(source, doc["path"])), parse_markdown(file)
            declared_language = meta_value(rendition_ast, "language")
            if declared_language != language:
                fail("RENDITION_LANGUAGE", f"{work}/{language}: the rendition's own front matter declares language {declared_language!r}")
            if not script_matches(language, body_text(rendition_ast)):
                fail("RENDITION_LANGUAGE", f"{work}/{language}: the rendition text is not in the declared script {entry['script']}")
            check_parity(entry, source_ast, rendition_ast)
            fragment = renderer.document({"path": rendition_path, "slug": work})
            title = next((plain_title(block) for block in rendition_ast["blocks"] if block["t"] == "Header" and block["c"][0] == 1), None)
            if not title:
                fail("RENDITION_SECTION_MISSING", f"{work}/{language}: the rendition has no title heading")
            pairs = [(p["source"], p["rendition"]) for p in entry["sections"]]
            record.update({
                "title": title, "title_id": fragment["title_id"], "html": annotate_sections(fragment["html"], pairs),
                "toc": fragment["toc"], "math_count": fragment["math_count"],
            })
        result[work][language] = record
        provenance_entries.append({
            "work": work, "language": language, "state": state, "script": entry["script"],
            "source_path": doc["path"], "source_sha256": entry["source"]["sha256"], "current_source_sha256": doc["sha256"],
            "source_revision": entry["source"]["revision"], "rendition_path": rendition_path,
            "rendition_sha256": entry["rendition"]["sha256"], "rendition_revision": entry["rendition"]["revision"],
            "review_status": entry["review"]["status"], "review_scope": entry["review"]["scope"],
            "counts_as_independent_source": False,
        })
    provenance_entries.sort(key=lambda e: (e["work"], e["language"]))
    return Compiled(kind, sidecar_path, sha256(raw).hexdigest(), result, provenance_entries)


def plain_title(block: dict) -> str:
    from build_publication import plain
    return plain(block["c"][2])
