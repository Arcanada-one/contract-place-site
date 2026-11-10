# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Versioned language renditions of the published English manuscripts (K8).

A rendition is a translation of ONE exact source edition, not a new independent source. This module validates the
linked, versioned sidecar ``publication-renditions.json`` that the knowledge repository (source of truth for text)
may declare through the optional ``renditions`` key of ``publication-catalog.json``, and compiles the renditions it
describes. Nothing here writes or translates text. With no sidecar the compiler output is unchanged.

Layout: the text of a rendition lives in the knowledge repository at ``translations/<language>/<source-relative path>``,
the same relative path as its English source. Links inside a rendition are ordinary relative Markdown: they are resolved
literally from the rendition file's own directory, as GitHub renders them (see classify_link for the rules).

Every refusal is a RenditionError whose message starts with a stable code (see CODES). The design is in
docs/versioned-renditions.md.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
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
    "RENDITION_LAYOUT", "RENDITION_LINK_SCHEME", "RENDITION_LINK_ESCAPES", "RENDITION_LINK_DANGLING",
    "RENDITION_LINK_TRANSLATION", "RENDITION_LINK_FRAGMENT", "RENDITION_REVIEW_UNBOUND", "RENDITION_REVIEW_NOT_INDEPENDENT", "RENDITION_LINK_UNPINNED",
)
# Review claims that fail to bind do not refuse the build: the page is shown as unreviewed and the typed reason is recorded.
REVIEW_ISSUES = ("RENDITION_REVIEW_UNBOUND", "RENDITION_REVIEW_NOT_INDEPENDENT")
SIDECAR_SCHEMA_VERSION = 2
TRANSLATIONS_ROOT = "translations"
HEX40, HEX64 = re.compile(r"[0-9a-f]{40}"), re.compile(r"[0-9a-f]{64}")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
ANCHOR = re.compile(r"[^\s\"'<>&#/?]+")
TOP_KEYS = {"schema_version", "kind", "edition", "renditions"}
# Sidecar schema v2 identity notes (docs/versioned-renditions.md §3):
# - document_id (R3-G1-id) is the work identity: entry work + English canonical source.path; no separate document_id field.
# - Offsets are out of scope (R3-G2): sections map by anchor identity only; no source_span/unit/offset field in v2.
#   Consumers must refuse offset-based citations into renditions. Optional source_span {start,end,unit:"code_point"} is future API-G2 work.
ENTRY_KEYS = {"work", "language", "script", "source", "rendition", "review", "sections", "counts_as_independent_source", "author"}
ENTRY_REQUIRED = ENTRY_KEYS - {"review", "author"}
AUTHOR_KEYS = {"identity"}
SOURCE_KEYS = {"path", "sha256", "revision", "language"}
RENDITION_KEYS = {"path", "sha256", "revision"}
# A review is one closed object; an entry without it is an unreviewed author draft.
REVIEW_KEYS = {"reviewer", "method", "reviewed", "scope", "corrections", "reviewed_at", "limitations", "evidence"}
REVIEWER_KEYS = {"identity", "kind", "independent_of_author", "independence_basis"}
REVIEWED_KEYS = {"source_blob", "rendition_blob"}
SCOPE_KEYS = {"coverage", "sections", "claims", "proofs"}
CORRECTION_KEYS = {"section", "description"}
EVIDENCE_KEYS = {"path", "blob"}
TIME_UTC = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
REVIEWER_KINDS = ("agent",)  # KC-Brain has worded only the internal agent review; a human review needs its own label first
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


def rendition_path_for(language: str, source_path: str) -> str:
    """The only admitted location of a rendition: translations/<language>/ followed by the source-relative path."""
    return f"{TRANSLATIONS_ROOT}/{language}/{source_path}"


def validate_sidecar(sidecar: object, manifest: dict) -> list[dict]:
    """Closed-schema validation of the sidecar document; returns its entries. No file is read here."""
    closed(sidecar, TOP_KEYS, "sidecar")
    if sidecar["schema_version"] != SIDECAR_SCHEMA_VERSION or isinstance(sidecar["schema_version"], bool):
        fail("RENDITION_SIDECAR_SCHEMA", f"unsupported sidecar schema_version (expected {SIDECAR_SCHEMA_VERSION})")
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
        closed(entry, ENTRY_KEYS, where, ENTRY_REQUIRED)
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
        if source["path"] == TRANSLATIONS_ROOT or source["path"].startswith(TRANSLATIONS_ROOT + "/"):
            fail("RENDITION_LAYOUT", f"{where}: a source document cannot live under {TRANSLATIONS_ROOT}/: {source['path']}")
        expected = rendition_path_for(language, source["path"])
        if rendition["path"] != expected:
            fail("RENDITION_LAYOUT", f"{where}: the rendition path must be exactly {expected} (translations/<language>/<source path>), found {rendition['path']}")
        if "review" in entry:
            validate_review(entry, where)
        if not isinstance(entry["sections"], list) or not entry["sections"]:
            fail("RENDITION_SIDECAR_SCHEMA", f"{where}.sections must be a non-empty list")
        for pair in entry["sections"]:
            closed(pair, SECTION_KEYS, f"{where}.sections[]")
            for value in pair.values():
                if not isinstance(value, str) or not ANCHOR.fullmatch(value):
                    fail("RENDITION_SIDECAR_SCHEMA", f"{where}.sections[] holds an invalid anchor")
        entries.append(entry)
    return entries


def blob40(value: object, where: str) -> str:
    if not isinstance(value, str) or not HEX40.fullmatch(value):
        fail("RENDITION_SIDECAR_SCHEMA", f"{where} must be a full 40-character git blob id")
    return value


def text_list(value: object, where: str, allow_empty: bool) -> list:
    if not isinstance(value, list) or (not value and not allow_empty):
        fail("RENDITION_SIDECAR_SCHEMA", f"{where} must be {'a' if allow_empty else 'a non-empty'} list")
    for item in value:
        text(item, f"{where}[]")
    return value


def validate_review(entry: dict, where: str) -> None:
    """Shape of a review object. A review without every fact is a refusal (RENDITION_REVIEW_UNEVIDENCED), never a reviewed
    state; whether a complete review binds to the pinned bytes is decided later and degrades to unreviewed."""
    if "author" not in entry:
        fail("RENDITION_REVIEW_UNEVIDENCED", f"{where}: a review requires the rendition's author identity to test independence")
    closed(entry["author"], AUTHOR_KEYS, f"{where}.author")
    text(entry["author"]["identity"], f"{where}.author.identity")
    review = entry["review"]
    if not isinstance(review, dict):
        fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review must be an object")
    missing = sorted(REVIEW_KEYS - set(review))
    if missing and set(review) <= REVIEW_KEYS:
        fail("RENDITION_REVIEW_UNEVIDENCED", f"{where}.review lacks {missing}")
    closed(review, REVIEW_KEYS, f"{where}.review")
    reviewer = closed(review["reviewer"], REVIEWER_KEYS, f"{where}.review.reviewer")
    text(reviewer["identity"], f"{where}.review.reviewer.identity")
    if reviewer["kind"] not in REVIEWER_KINDS:
        fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review.reviewer.kind must be one of {REVIEWER_KINDS}")
    if not isinstance(reviewer["independent_of_author"], bool):
        fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review.reviewer.independent_of_author must be true or false")
    text(reviewer["independence_basis"], f"{where}.review.reviewer.independence_basis")
    text(review["method"], f"{where}.review.method")
    text(review["limitations"], f"{where}.review.limitations")
    reviewed = closed(review["reviewed"], REVIEWED_KEYS, f"{where}.review.reviewed")
    blob40(reviewed["source_blob"], f"{where}.review.reviewed.source_blob"), blob40(reviewed["rendition_blob"], f"{where}.review.reviewed.rendition_blob")
    scope = closed(review["scope"], SCOPE_KEYS, f"{where}.review.scope")
    if scope["coverage"] not in {"full", "partial"}:
        fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review.scope.coverage must be full or partial")
    for anchor in text_list(scope["sections"], f"{where}.review.scope.sections", False):
        if not ANCHOR.fullmatch(anchor):
            fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review.scope.sections holds an invalid anchor")
    text_list(scope["claims"], f"{where}.review.scope.claims", True), text_list(scope["proofs"], f"{where}.review.scope.proofs", True)
    if not isinstance(review["corrections"], list):
        fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review.corrections must be a list (empty when none were made)")
    for correction in review["corrections"]:
        closed(correction, CORRECTION_KEYS, f"{where}.review.corrections[]")
        if not ANCHOR.fullmatch(text(correction["section"], f"{where}.review.corrections[].section")):
            fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review.corrections[].section holds an invalid anchor")
        text(correction["description"], f"{where}.review.corrections[].description")
    stamp = text(review["reviewed_at"], f"{where}.review.reviewed_at")
    try:
        if not TIME_UTC.fullmatch(stamp):
            raise ValueError(stamp)
        datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review.reviewed_at must be a UTC time like 2026-01-31T12:00:00Z")
    evidence = closed(review["evidence"], EVIDENCE_KEYS, f"{where}.review.evidence")
    path = text(evidence["path"], f"{where}.review.evidence.path")
    if path.startswith("/") or ".." in PurePosixPath(path).parts or "\\" in path or urlsplit(path).scheme or path.endswith("/"):
        fail("RENDITION_SIDECAR_SCHEMA", f"{where}.review.evidence.path must be a repository path, not a URL or a name: {path}")
    blob40(evidence["blob"], f"{where}.review.evidence.blob")


def git_bytes(source: Path, *args: str) -> bytes | None:
    result = subprocess.run(["git", *args], cwd=source, capture_output=True)
    return result.stdout if result.returncode == 0 else None


def tree_paths(source: Path, revision: str) -> frozenset[str]:
    """Every file and directory path of the pinned commit (plus "." for the root): what a link can resolve to."""
    listing = git_bytes(source, "ls-tree", "-r", "-t", "--name-only", "-z", revision)
    if listing is None:
        fail("RENDITION_SOURCE_PIN", f"cannot list the tree of {revision}")
    return frozenset(["."] + [p.decode("utf-8") for p in listing.split(b"\0") if p])


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


def classify_link(target: str, rendition_path: str, language: str, tree: frozenset[str], by_path: dict,
                  pinned: frozenset[str]) -> tuple[str, str | None]:
    """Deterministic class of one link of a rendition. Relative targets are resolved LITERALLY from the directory of the
    rendition file (ordinary Markdown semantics, as GitHub renders it). Returns (class, canonical path):

    * external: http(s) or mailto outside the repository, unchanged;
    * fragment: a same-document ``#anchor``;
    * peer: a path under ``translations/<this language>/`` that is the rendition of a catalogue document AND is itself a
      pinned entry of the sidecar; the canonical path is the document's source path (the link goes to the document's
      route in the same interface language, carrying its state);
    * document: a catalogue document at its canonical (English) path; same route rule, the state of the target decides
      whether the English fallback is explicit;
    * invariant: any other file or directory that exists at the pinned commit (schema, example, code, data, image).

    Refused, nothing guessed: a target that leaves the repository root, a target under ``translations/`` that is not a
    pinned rendition of this language (another language, the coverage file, an uncatalogued path), a same-language
    translation that is not a pinned sidecar entry, an unsupported scheme, and a path that does not exist at the pinned
    commit (which is what catches links written from the source's directory depth)."""
    from build_publication import GITHUB
    parts = urlsplit(target)
    if parts.scheme in {"https", "http", "mailto"} or target.startswith("//"):
        prefix = GITHUB + "/blob/"
        if target.startswith(prefix):
            tail = unquote(parts.path).split("/blob/", 1)[1].split("/", 1)
            if len(tail) == 2 and tail[1] in by_path:
                return "document", tail[1]
        return "external", None
    if parts.scheme:
        fail("RENDITION_LINK_SCHEME", f"{rendition_path}: unsupported link scheme in {target!r}")
    if not parts.path:
        return "fragment", None
    raw = unquote(parts.path)
    relative = posixpath.normpath(raw.lstrip("/") if raw.startswith("/") else str(PurePosixPath(rendition_path).parent / raw))
    if relative == ".." or relative.startswith("../"):
        fail("RENDITION_LINK_ESCAPES", f"{rendition_path}: {target!r} leaves the repository root")
    if relative == TRANSLATIONS_ROOT or relative.startswith(TRANSLATIONS_ROOT + "/"):
        own = f"{TRANSLATIONS_ROOT}/{language}/"
        source_path = relative[len(own):] if relative.startswith(own) else None
        if source_path is None or source_path not in by_path:
            fail("RENDITION_LINK_TRANSLATION", f"{rendition_path}: {target!r} resolves to {relative}, which is not a {language} rendition of a catalogue document")
        if source_path not in pinned:
            fail("RENDITION_LINK_UNPINNED", f"{rendition_path}: {target!r} links to {relative}, which is not a pinned entry of the sidecar (no link to an unpinned draft)")
        if relative not in tree:
            fail("RENDITION_LINK_DANGLING", f"{rendition_path}: {target!r} resolves to {relative}, which does not exist at the pinned commit")
        return "peer", source_path
    if relative not in tree:
        fail("RENDITION_LINK_DANGLING", f"{rendition_path}: {target!r} resolves to {relative}, which does not exist at the pinned commit")
    return ("document" if relative in by_path else "invariant"), relative


def anchors_of(ast: dict) -> set[str]:
    """Every explicit or generated identifier that a same-document fragment can name."""
    found: set[str] = set()

    def visit(node: dict) -> None:
        kind = node.get("t")
        if kind == "Header":
            found.add(node["c"][1][0])
        elif kind in {"Div", "Span", "CodeBlock", "Code", "Link", "Image"}:
            found.add(node["c"][0][0])
    walk(ast["blocks"], visit)
    found.discard("")
    return found


def title_id(ast: dict) -> str | None:
    for block in ast["blocks"]:
        if block["t"] == "Header" and block["c"][0] == 1:
            return block["c"][1][0] or None
    return None


def analyse_links(ast: dict, rendition_path: str, language: str, tree: frozenset[str], by_path: dict, pinned: frozenset[str],
                  fragment_map: dict[str, str], own_anchors: set[str], source_anchors: set[str], errors: list | None = None) -> list[tuple[str, str | None, str]]:
    """Classify every link and image of a rendition (see classify_link). A same-document fragment must be a mapped section
    anchor of the rendition or an identifier that the source and the rendition both carry; a guessed fragment is refused.
    Returns (class, path, target) per link. With ``errors`` given, refusals are collected there instead of raised."""
    results: list[tuple[str, str | None, str]] = []

    def visit(node: dict) -> None:
        if node.get("t") not in {"Link", "Image"}:
            return
        target = node["c"][2][0]
        try:
            kind, path = classify_link(target, rendition_path, language, tree, by_path, pinned)
            if kind == "fragment":
                fragment = unquote(urlsplit(target).fragment)
                if fragment and fragment not in fragment_map and not (fragment in own_anchors and fragment in source_anchors):
                    fail("RENDITION_LINK_FRAGMENT", f"{rendition_path}: same-document fragment #{fragment} is not a mapped section anchor and not an anchor of both texts")
        except RenditionError as error:
            if errors is None:
                raise
            errors.append(error)
            return
        results.append((kind, path, target))
    walk(ast["blocks"], visit)
    return results


def normalize_target(target: str, base_path: str, fragment_map: dict[str, str], language: str | None = None,
                     peer_maps: dict | None = None) -> str:
    """Comparable identity of a link target: the canonical repository path (plus fragment). Relative paths are resolved
    literally from ``base_path`` (the source document for the source, the rendition file for a rendition); a target under
    ``translations/<language>/`` is the same target as the document at the remaining (source) path, and a fragment into
    such a peer is mapped through that peer's section mapping to the source anchor."""
    parts = urlsplit(target)
    if parts.scheme or target.startswith("//"):
        return target
    fragment = unquote(parts.fragment)
    if not parts.path:
        return "#" + fragment_map.get(fragment, "\0unmapped:" + fragment)
    raw = unquote(parts.path)
    relative = posixpath.normpath(raw.lstrip("/") if raw.startswith("/") else str(PurePosixPath(base_path).parent / raw))
    own = f"{TRANSLATIONS_ROOT}/{language}/"
    if language and relative.startswith(own):
        relative = relative[len(own):]
        fragment = (peer_maps or {}).get((language, relative), {}).get(fragment, fragment)
    return relative + ("#" + fragment if fragment else "")


def facts(ast: dict, doc_path: str, fragment_map: dict[str, str], language: str | None = None, peer_maps: dict | None = None) -> dict:
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
            references[(kind, normalize_target(node["c"][2][0], doc_path, fragment_map, language, peer_maps))] += 1
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


def check_parity(entry: dict, source_ast: dict, rendition_ast: dict, before_references=None, peer_maps: dict | None = None) -> dict[str, str]:
    """Structural parity between a source and its rendition. Returns the rendition-to-source anchor map.
    ``before_references`` runs after the section and structure checks and before formulas, code and references are
    compared, so that a link that cannot be resolved is reported as such and not as a dropped reference."""
    from rendition_preamble import source_for_anchor_parity
    source_ast = source_for_anchor_parity(source_ast, rendition_ast)
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
    structure_pairs = [("", "")] + pairs
    for s, r in structure_pairs:
        a, b = src_structure[s], rnd_structure[r]
        if a["text"] and not b["text"]:
            fail("RENDITION_SECTION_MISSING", f"{work}/{language}: section {s or '(preamble)'} has text in the source but none in the rendition")
        if {k: v for k, v in a.items() if k != "text"} != {k: v for k, v in b.items() if k != "text"}:
            fail("RENDITION_STRUCTURE_MISMATCH", f"{work}/{language}: tables, lists, quotations or code blocks of section {s or '(preamble)'} differ from the source")
    if before_references is not None:
        before_references()
    reverse = {r: s for s, r in pairs}
    base = entry["source"]["path"]  # links resolve literally from each file's own directory; the targets are compared canonically
    source_title, rendition_title = title_id(source_ast), title_id(rendition_ast)
    if source_title and rendition_title:
        reverse[rendition_title] = source_title
    source_facts = facts(source_ast, base, {**{i: i for i in src_ids}, **({source_title: source_title} if source_title else {})})
    rendition_facts = facts(rendition_ast, entry["rendition"]["path"], reverse, language, peer_maps)
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


def normalized_identity(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().casefold()


def blob_id(source: Path, revision: str, path: str) -> str | None:
    found = git_bytes(source, "rev-parse", "--verify", "--quiet", f"{revision}:{path}")
    return found.decode().strip() if found else None


def evaluate_review(source: Path, manifest: dict, doc: dict, entry: dict) -> tuple[str, dict | None]:
    """The review state of a rendition whose source is current: ("reviewed" | "partially-reviewed" | "unreviewed", issue).

    No review object: an unreviewed author draft, no issue. A review object counts only when it is independently
    inspectable and bound to exactly what is published: the reviewer is independent of the author (stated, with a basis,
    and not the same identity), the reviewed source and rendition blobs equal the pinned ones, the evidence file exists
    at its pinned blob in the publication commit, and the scope names real sections of the source (full coverage names
    all of them). Anything else leaves the rendition unreviewed with a typed issue; the build is not refused."""
    review = entry.get("review")
    if review is None:
        return "unreviewed", None

    def degraded(code: str, detail: str) -> tuple[str, dict]:
        return "unreviewed", {"code": code, "detail": detail}
    reviewer = review["reviewer"]
    if reviewer["independent_of_author"] is not True:
        return degraded("RENDITION_REVIEW_NOT_INDEPENDENT", "the reviewer states that the review is not independent of the author")
    if normalized_identity(reviewer["identity"]) == normalized_identity(entry["author"]["identity"]):
        return degraded("RENDITION_REVIEW_NOT_INDEPENDENT", "the reviewer identity equals the author identity")
    for name, pin in (("source", entry["source"]), ("rendition", entry["rendition"])):
        pinned = blob_id(source, pin["revision"], pin["path"])
        if pinned is None or review["reviewed"][name + "_blob"] != pinned:
            return degraded("RENDITION_REVIEW_UNBOUND", f"the reviewed {name} blob {review['reviewed'][name + '_blob']} is not the pinned {name} blob {pinned}")
    evidence = review["evidence"]
    found = blob_id(source, manifest["commit"], evidence["path"])
    if found is None or found != evidence["blob"]:
        return degraded("RENDITION_REVIEW_UNBOUND", f"the evidence {evidence['path']} is not at the pinned blob {evidence['blob']} in the publication commit")
    from build_publication import inside, parse_markdown
    headings = [anchor for _, anchor in sections_of(parse_markdown(inside(source, doc["path"])))[0]]
    scope = review["scope"]
    unknown = [a for a in scope["sections"] + [c["section"] for c in review["corrections"]] if a not in headings]
    if unknown:
        return degraded("RENDITION_REVIEW_UNBOUND", f"the review names sections that are not in the source: {sorted(set(unknown))}")
    if len(set(scope["sections"])) != len(scope["sections"]):
        return degraded("RENDITION_REVIEW_UNBOUND", "the review scope repeats a section")
    if scope["coverage"] == "full" and set(scope["sections"]) != set(headings):
        return degraded("RENDITION_REVIEW_UNBOUND", f"full coverage is claimed but the scope omits {sorted(set(headings) - set(scope['sections']))}")
    return ("reviewed" if scope["coverage"] == "full" else "partially-reviewed"), None


def resolve_state(source: Path, manifest: dict, doc: dict, entry: dict) -> tuple[str, dict | None]:
    """(state, review issue). A source that changed after the pin is stale whatever the review says."""
    if entry["source"]["sha256"] != doc["sha256"]:
        return "stale", None
    return evaluate_review(source, manifest, doc, entry)


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


def review_for_page(renderer, entry: dict) -> dict:
    """The review exactly as the sidecar states it, plus the author and the pinned link to the evidence file."""
    review = json.loads(json.dumps(entry["review"]))
    review["evidence"]["url"] = renderer.source_url(review["evidence"]["path"])
    review["author"] = entry["author"]["identity"]
    return review


def link_context(entries: list[dict]) -> tuple[dict, dict]:
    """(pinned, peer_maps): for each language the source paths that are pinned sidecar entries (the only translated peers a
    rendition may link to), and for each (language, source path) the rendition-anchor to source-anchor section mapping."""
    pinned: dict[str, set] = {language: set() for language in RENDITION_LANGUAGES}
    peer_maps: dict[tuple, dict] = {}
    for entry in entries:
        pinned[entry["language"]].add(entry["source"]["path"])
        peer_maps[(entry["language"], entry["source"]["path"])] = {p["rendition"]: p["source"] for p in entry["sections"]}
    return {language: frozenset(paths) for language, paths in pinned.items()}, peer_maps


def link_hooks(language: str, states: dict, by_path: dict, tree: frozenset[str], rendition_path: str, pinned: frozenset[str], peer_maps: dict) -> dict:
    """Renderer hooks for one rendition. Relative links resolve literally from the rendition file's directory (the renderer's
    default for a document whose path is the rendition path); a translated peer is mapped to its source document, and a
    fragment into it to the source anchor, which the rendered page keeps resolvable. A link to a catalogue document goes to
    that document's route in the same interface language. The target's state is explicit on the link: a shown rendition is
    linked as such; a stale or missing one is linked with an explicit English-fallback state."""
    from publication_checks import RENDITION_FALLBACK, RENDITION_LABELS
    own = f"{TRANSLATIONS_ROOT}/{language}/"

    def route(relative: str) -> str:
        return by_path[relative]["route"].replace("/en/", f"/{language}/", 1)

    def resolve(relative: str, fragment: str) -> tuple[str, str]:
        if relative.startswith(own):
            canonical = relative[len(own):]
            return canonical, peer_maps.get((language, canonical), {}).get(unquote(fragment), fragment) if fragment else fragment
        return relative, fragment

    def note(node: dict, original: str) -> None:
        kind, path = classify_link(original, rendition_path, language, tree, by_path, pinned)
        if kind not in {"document", "peer"}:
            return
        state = states.get((by_path[path]["slug"], language), "missing")
        shown = state in STATES_RENDERED
        attrs = node["c"][0][2]
        attrs.extend([["hreflang", language if shown else SOURCE_LANGUAGE], ["data-target-state", state]])
        if not shown:
            attrs.append(["data-fallback", SOURCE_LANGUAGE])
            if not node["c"][2][1]:
                node["c"][2][1] = f"{RENDITION_LABELS[state][language]} {RENDITION_FALLBACK[language]}"
    return {"link_resolve": resolve, "link_route": route, "link_note": note}


def link_class_counts(links: list[tuple[str, str | None, str]], language: str, states: dict, by_path: dict) -> dict:
    counts = Counter(kind for kind, _, _ in links)
    counts.update(
        "document_shown" if states.get((by_path[path]["slug"], language), "missing") in STATES_RENDERED else "document_fallback"
        for kind, path, _ in links if kind in {"document", "peer"})
    return dict(sorted(counts.items()))


def compile_entry(source: Path, manifest: dict, doc: dict, entry: dict, states: dict, ctx: dict, report: dict | None = None) -> tuple[dict, dict]:
    """Verify and compile one rendition. Raises RenditionError at the first failure, or, when ``report`` is given (the
    read-only dry run), records every failing stage in report["failures"] and carries on."""
    from build_publication import inside, parse_markdown
    renderer, by_path, tree = ctx["renderer"], ctx["by_path"], ctx["tree"]
    work, language = entry["work"], entry["language"]
    label = f"{work}/{language}"
    rendition_path = entry["rendition"]["path"]

    def attempt(stage: str, function):
        if report is None:
            return function()
        try:
            return function()
        except RenditionError as error:
            report["failures"].append((stage, error.code, str(error)))
            return None

    def pins() -> None:
        if entry["source"]["path"] != doc["path"]:
            fail("RENDITION_SOURCE_PIN", f"{label}: source path {entry['source']['path']} is not the catalogued {doc['path']}")
        verify_pin(source, manifest, label + " source", entry["source"], "RENDITION_SOURCE_PIN")
        verify_pin(source, manifest, label + " rendition", entry["rendition"], "RENDITION_REVISION_PIN")
        if git_bytes(source, "merge-base", "--is-ancestor", entry["source"]["revision"], entry["rendition"]["revision"]) is None:
            fail("RENDITION_REVISION_PIN", f"{label}: the rendition revision predates the source revision it claims to render (mixed source/rendition pins)")
        if rendition_path in by_path or rendition_path == doc["path"]:
            fail("RENDITION_SOURCE_PIN", f"{label}: a rendition cannot be a catalogued source document")
    attempt("pins", pins)
    file = inside(source, rendition_path)

    def digest() -> None:
        if not file.is_file():
            fail("RENDITION_DIGEST", f"{label}: rendition file is missing: {rendition_path}")
        found = sha256(file.read_bytes()).hexdigest()
        if found != entry["rendition"]["sha256"]:
            fail("RENDITION_DIGEST", f"{label}: rendition bytes {found} differ from the pinned {entry['rendition']['sha256']}")
    attempt("digest", digest)
    state = states[(work, language)]
    issue = ctx["issues"].get((work, language))
    record = {
        "language": language, "script": entry["script"], "state": state,
        "source": dict(entry["source"], url=renderer.source_url(doc["path"])),
        "current_source_sha256": doc["sha256"],
        "rendition": dict(entry["rendition"], url=renderer.source_url(rendition_path), history=renderer.source_url(rendition_path, True)),
        "review": review_for_page(renderer, entry) if state in ("reviewed", "partially-reviewed") else None,
        "review_issue": issue, "sections": entry["sections"], "counts_as_independent_source": False,
    }
    if state != "stale" and file.is_file():
        source_ast, rendition_ast = parse_markdown(inside(source, doc["path"])), parse_markdown(file)

        def language_checks() -> None:
            declared_language = meta_value(rendition_ast, "language")
            if declared_language != language:
                fail("RENDITION_LANGUAGE", f"{label}: the rendition's own front matter declares language {declared_language!r}")
            if not script_matches(language, body_text(rendition_ast)):
                fail("RENDITION_LANGUAGE", f"{label}: the rendition text is not in the declared script {entry['script']}")
        attempt("language", language_checks)
        pairs = [(p["source"], p["rendition"]) for p in entry["sections"]]
        fragment_map = {r: s for s, r in pairs}
        source_title, rendition_title = title_id(source_ast), title_id(rendition_ast)
        if source_title and rendition_title:
            fragment_map[rendition_title] = source_title
        found: dict = {}

        def links(errors: list | None) -> None:
            found["links"] = analyse_links(rendition_ast, rendition_path, language, tree, by_path, ctx["pinned"][language], fragment_map, anchors_of(rendition_ast), anchors_of(source_ast), errors)
        if report is None:
            check_parity(entry, source_ast, rendition_ast, before_references=lambda: links(None), peer_maps=ctx["peer_maps"])
        else:
            link_errors: list = []
            links(link_errors)
            report["failures"].extend(("links", error.code, str(error)) for error in link_errors)
            report["links"] = found["links"]
            attempt("parity", lambda: check_parity(entry, source_ast, rendition_ast, peer_maps=ctx["peer_maps"]))
        record["link_classes"] = link_class_counts(found["links"], language, states, by_path)

        def render() -> None:
            hooks = link_hooks(language, states, by_path, tree, rendition_path, ctx["pinned"][language], ctx["peer_maps"])
            fragment = renderer.document(dict({"path": rendition_path, "slug": work}, **hooks))
            title = next((plain_title(block) for block in rendition_ast["blocks"] if block["t"] == "Header" and block["c"][0] == 1), None)
            if not title:
                fail("RENDITION_SECTION_MISSING", f"{label}: the rendition has no title heading")
            record.update({
                "title": title, "title_id": fragment["title_id"], "html": annotate_sections(fragment["html"], pairs),
                "toc": fragment["toc"], "math_count": fragment["math_count"],
            })
        if report is None or not report["failures"]:
            attempt("render", render)
    provenance = {
        "work": work, "language": language, "state": state, "script": entry["script"],
        "source_path": doc["path"], "source_sha256": entry["source"]["sha256"], "current_source_sha256": doc["sha256"],
        "source_revision": entry["source"]["revision"], "rendition_path": rendition_path,
        "rendition_sha256": entry["rendition"]["sha256"], "rendition_revision": entry["rendition"]["revision"],
        "review_status": "internal-agent-review" if state in ("reviewed", "partially-reviewed") else "unreviewed",
        "review_scope": {"reviewed": "full", "partially-reviewed": "partial"}.get(state, "none"),
        "review_issue": issue["code"] if issue else None,
        "counts_as_independent_source": False,
    }
    return record, provenance


def compile_renditions(source: Path, manifest: dict, documents: list[dict], renderer, run, fixture_file: Path | None = None) -> Compiled | None:
    """Validate and compile the declared renditions. Returns None when none are declared (output stays unchanged)."""
    from build_publication import inside, read_json
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
    for entry in entries:
        if entry["work"] not in by_slug:
            fail("RENDITION_UNKNOWN_WORK", f"{entry['work']} is not in the publication catalogue")
    # First pass: the state of every work/language pair. A link from one rendition to another document depends on it.
    resolved = {(e["work"], e["language"]): resolve_state(source, manifest, by_slug[e["work"]], e) for e in entries}
    states = {key: state for key, (state, _) in resolved.items()}
    issues = {key: issue for key, (_, issue) in resolved.items() if issue}
    pinned, peer_maps = link_context(entries)
    ctx = {"renderer": renderer, "by_path": by_path, "tree": tree_paths(source, manifest["commit"]), "issues": issues, "pinned": pinned, "peer_maps": peer_maps}
    result: dict[str, dict] = {}
    provenance_entries = []
    for doc in documents:
        result[doc["slug"]] = {}
        for language in RENDITION_LANGUAGES:
            if (doc["slug"], language) not in declared_pairs:
                # C6: a missing page must still carry a resolvable source URL (never href="undefined").
                pin = {"path": doc["path"], "sha256": doc["sha256"], "revision": manifest["commit"], "language": SOURCE_LANGUAGE,
                       "url": renderer.source_url(doc["path"])}
                result[doc["slug"]][language] = {"language": language, "script": RENDITION_LANGUAGES[language], "state": "missing", "source": pin}
                provenance_entries.append({"work": doc["slug"], "language": language, "state": "missing", "source_sha256": doc["sha256"]})
    for entry in entries:
        record, provenance = compile_entry(source, manifest, by_slug[entry["work"]], entry, states, ctx)
        result[entry["work"]][entry["language"]] = record
        provenance_entries.append(provenance)
    provenance_entries.sort(key=lambda e: (e["work"], e["language"]))
    return Compiled(kind, sidecar_path, sha256(raw).hexdigest(), result, provenance_entries)


def plain_title(block: dict) -> str:
    from build_publication import plain
    return plain(block["c"][2])