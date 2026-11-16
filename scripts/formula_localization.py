# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Source-bound presentation of formula prose; canonical mathematics is opaque.

Only explicitly registered, visible MathML mtext contents may change. The
source and rendition Math AST parity check still runs before this layer. The
complete source MathML tree, including its exact TeX annotation, is checked
before replacement; every other HTML byte is retained. This is not semantic
translation review or a permission to rename mathematical identifiers.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from html import escape, unescape
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
from xml.etree import ElementTree as ET

FILENAME = "publication-formula-localizations.json"
REPOSITORY = "Arcanada-one/knowledge-contract"
LANGUAGES = ("ru", "zh-Hans")
NS = "{http://www.w3.org/1998/Math/MathML}"
MATH = re.compile(r"<math\b[^>]*>.*?</math>", re.S)
MTEXT = re.compile(r"(<mtext\b[^>]*>)([^<>]*)(</mtext>)", re.S)
ANNOTATION_FIELDS = {"math_index", "math_type", "tex_sha256", "mtext_index", "source_text", "translations"}


def refuse(code: str, reason: str) -> None:
    raise ValueError("FORMULA_LOCALIZATION_" + code + ": " + reason)


def closed(value: object, keys: set[str], label: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        refuse("SCHEMA", label + " has missing or unknown fields")
    return value


def digest(value: object, size: int, label: str) -> str:
    if type(value) is not str or not re.fullmatch("[0-9a-f]{" + str(size) + "}", value):
        refuse("SCHEMA", label + " must be a full lowercase hexadecimal digest")
    return value


def plain(value: object, label: str) -> str:
    # Boundary spaces are part of the original formula's prose and are kept.
    if type(value) is not str or not value.strip() or re.search(r"[\x00-\x1f\x7f<>]", value):
        refuse("SCHEMA", label + " must be nonempty single-line plain text")
    return value


def boundary_spaces(value: str) -> tuple[str, str]:
    return value[:len(value) - len(value.lstrip())], value[len(value.rstrip()):]


def git(source: Path, *args: str) -> bytes:
    process = subprocess.run(["git", "-C", str(source), *args], capture_output=True, check=False)
    if process.returncode:
        refuse("BINDING", "unverified committed source bytes or revision ancestry")
    return process.stdout


def path_at(root: Path, value: object) -> Path:
    if type(value) is not str or not value or value != value.strip():
        refuse("SCHEMA", "document path must be a canonical relative path")
    name = PurePosixPath(value)
    result = (root / value).resolve()
    if name.is_absolute() or ".." in name.parts or str(name) != value or not result.is_relative_to(root.resolve()):
        refuse("SCHEMA", "document path escapes its source or is not canonical")
    return result


def math_parts(html: str) -> list[dict]:
    """Read generated MathML without serializing or changing its HTML bytes."""
    matches = list(MATH.finditer(html))
    if len(re.findall(r"<math\b", html)) != len(matches):
        refuse("STRUCTURE", "malformed or incomplete MathML")
    parts = []
    for match in matches:
        raw = match.group()
        try:
            tree = ET.fromstring(raw)
        except ET.ParseError as error:
            refuse("STRUCTURE", "invalid generated MathML: " + str(error))
        if tree.tag != NS + "math":
            refuse("STRUCTURE", "unexpected MathML namespace")
        annotations = list(tree.iter(NS + "annotation"))
        if (len(annotations) != 1 or annotations[0].get("encoding") != "application/x-tex"
                or len(annotations[0]) or list(tree.iter(NS + "annotation-xml"))):
            refuse("STRUCTURE", "expected one unchanged plain TeX annotation")
        nodes = list(tree.iter(NS + "mtext"))
        spans = list(MTEXT.finditer(raw))
        if len(nodes) != len(spans) or any(len(node) for node in nodes):
            refuse("STRUCTURE", "mtext must contain plain text, not nested markup")
        for node, span in zip(nodes, spans):
            if (node.text or "") != unescape(span[2]):
                refuse("STRUCTURE", "ambiguous mtext encoding")
        parts.append({"start": match.start(), "end": match.end(), "raw": raw, "tree": tree,
                      "tex": annotations[0].text or "", "mtext": nodes, "spans": spans})
    return parts


def source_math(source: Path, relative: str) -> tuple[list[tuple[str, str]], list[dict]]:
    from build_publication import parse_markdown, run
    ast = parse_markdown(path_at(source, relative))
    # The reader consumes the first H1 as its separate title. Its body is the
    # source of the one-based formula indices, exactly as in Renderer.document.
    first = next((index for index, block in enumerate(ast["blocks"])
                  if block.get("t") == "Header" and block["c"][0] == 1), None)
    if first is not None:
        del ast["blocks"][first]
    formulas = []

    def walk(value):
        if isinstance(value, dict):
            if value.get("t") == "Math":
                formulas.append((value["c"][0]["t"], value["c"][1]))
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(ast["blocks"])
    rendered = run(["pandoc", "--from=json", "--to=html5", "--mathml", "--no-highlight",
                    "--wrap=none", "--fail-if-warnings"], json.dumps(ast))
    parts = math_parts(rendered)
    if len(formulas) != len(parts):
        refuse("STRUCTURE", "source formula count does not match rendered MathML")
    for (kind, tex), part in zip(formulas, parts):
        expected_mode = {"InlineMath": "inline", "DisplayMath": "block"}.get(kind)
        if part["tex"] != tex or part["tree"].get("display") != expected_mode:
            refuse("STRUCTURE", "source TeX or display mode changed during rendering")
    return formulas, parts


class FormulaLocalizations:
    def __init__(self, source: Path, manifest: dict, documents: list[dict]):
        self.source, self.manifest = source, manifest
        self.entries: dict[str, dict] = {}
        self.canonical: dict[str, list[dict]] = {}
        self._provenance = None
        path = source / FILENAME
        if not path.exists():
            # Deleting an already pinned descriptor must not disable the gate.
            if subprocess.run(["git", "-C", str(source), "cat-file", "-e", manifest["commit"] + ":" + FILENAME],
                              capture_output=True, check=False).returncode == 0:
                refuse("BINDING", "pinned formula descriptor is missing from the checkout")
            return
        raw = path.read_bytes()

        def pairs(items):
            result = {}
            for key, value in items:
                if key in result:
                    refuse("SCHEMA", "duplicate JSON key: " + key)
                result[key] = value
            return result

        try:
            data = json.loads(raw, object_pairs_hook=pairs)
        except (UnicodeError, json.JSONDecodeError) as error:
            refuse("SCHEMA", "invalid UTF-8 JSON: " + str(error))
        closed(data, {"schema_version", "repository", "source_revision", "review_state", "documents"}, "root")
        if (type(data["schema_version"]) is not int or data["schema_version"] != 1
                or data["repository"] != REPOSITORY or data["review_state"] != "unreviewed"):
            refuse("SCHEMA", "unsupported schema/repository or unearned formula review state")
        revision = digest(data["source_revision"], 40, "source_revision")
        current = digest(manifest["commit"], 40, "publication commit")
        git(source, "merge-base", "--is-ancestor", revision, current)
        if git(source, "show", current + ":" + FILENAME) != raw:
            refuse("BINDING", "formula descriptor differs from the selected publication commit")
        by_path = {doc["path"]: doc for doc in documents}
        if len(by_path) != len(documents):
            refuse("SCHEMA", "duplicate canonical document path")
        if type(data["documents"]) is not list or not data["documents"]:
            refuse("SCHEMA", "documents must be a nonempty list")
        from renditions import script_matches
        for entry in data["documents"]:
            closed(entry, {"path", "source_sha256", "annotations"}, "document")
            relative = entry["path"]
            file = path_at(source, relative)
            if relative not in by_path or relative in self.entries:
                refuse("SCHEMA", "unknown or duplicate canonical document")
            expected = digest(entry["source_sha256"], 64, "source_sha256")
            if sha256(git(source, "show", revision + ":" + relative)).hexdigest() != expected:
                refuse("BINDING", "historical manuscript bytes differ from the declared source digest")
            if (sha256(file.read_bytes()).hexdigest() != expected
                    or sha256(git(source, "show", current + ":" + relative)).hexdigest() != expected
                    or by_path[relative].get("sha256", expected) != expected):
                refuse("BINDING", "formula localization is stale for current manuscript bytes")
            formulas, canonical = source_math(source, relative)
            if type(entry["annotations"]) is not list or not entry["annotations"]:
                refuse("SCHEMA", "annotations must be a nonempty list")
            observed = set()
            for annotation in entry["annotations"]:
                closed(annotation, ANNOTATION_FIELDS, "annotation")
                mi, ti = annotation["math_index"], annotation["mtext_index"]
                if (type(mi) is not int or type(ti) is not int or mi < 1 or ti < 1
                        or mi > len(formulas) or ti > len(canonical[mi - 1]["mtext"])):
                    refuse("BINDING", "formula/mtext index is outside the exact source")
                if (mi, ti) in observed:
                    refuse("SCHEMA", "duplicate formula/mtext binding")
                observed.add((mi, ti))
                kind, tex = formulas[mi - 1]
                if annotation["math_type"] != kind or digest(annotation["tex_sha256"], 64, "tex_sha256") != sha256(tex.encode()).hexdigest():
                    refuse("BINDING", "formula TeX or display type differs from its binding")
                original = plain(annotation["source_text"], "source_text")
                if original != (canonical[mi - 1]["mtext"][ti - 1].text or ""):
                    refuse("BINDING", "visible mtext differs from its exact source_text")
                closed(annotation["translations"], set(LANGUAGES), "translations")
                for language in LANGUAGES:
                    value = plain(annotation["translations"][language], language + " translation")
                    if not script_matches(language, value):
                        refuse("LANGUAGE", "mtext translation does not match " + language)
                    if boundary_spaces(value) != boundary_spaces(original):
                        refuse("STRUCTURE", "mtext translation changes boundary spacing")
            actual = {(mi, ti) for mi, part in enumerate(canonical, 1)
                      for ti, node in enumerate(part["mtext"], 1) if (node.text or "").strip()}
            if observed != actual:
                refuse("COVERAGE", "all nonempty source mtext must be registered exactly once")
            self.entries[relative] = deepcopy(entry)
            self.canonical[relative] = canonical
        self._provenance = {
            "schema_version": 1, "path": FILENAME, "sha256": sha256(raw).hexdigest(),
            "repository": REPOSITORY, "source_revision": revision, "review_state": "unreviewed",
            "documents": [{"path": entry["path"], "source_sha256": entry["source_sha256"],
                           "annotations": [{key: annotation[key] for key in sorted(ANNOTATION_FIELDS - {"translations"})}
                                           for annotation in entry["annotations"]]}
                          for entry in data["documents"]],
            "scope": "visible formula prose only; canonical TeX and source math parity unchanged; no independent review",
        }

    def provenance(self) -> dict | None:
        return deepcopy(self._provenance)

    def for_document(self, relative: str, language: str) -> dict | None:
        entry = self.entries.get(relative)
        if entry is None:
            return None
        if language not in LANGUAGES:
            refuse("LANGUAGE", "unknown formula presentation locale")
        return {"path": FILENAME, "sha256": self._provenance["sha256"],
                "source_path": relative, "source_sha256": entry["source_sha256"],
                "source_revision": self._provenance["source_revision"],
                "language": language, "review_state": "unreviewed",
                "annotations": [{key: annotation[key] for key in ("math_index", "mtext_index", "tex_sha256")}
                                for annotation in entry["annotations"]]}

    def _expected(self, relative: str, language: str) -> list[str]:
        replacements = {(item["math_index"], item["mtext_index"]): item["translations"][language]
                        for item in self.entries[relative]["annotations"]}
        result = []
        for mi, part in enumerate(self.canonical[relative], 1):
            raw = part["raw"]
            for ti, span in reversed(list(enumerate(part["spans"], 1))):
                if (mi, ti) in replacements:
                    raw = raw[:span.start(2)] + escape(replacements[(mi, ti)], quote=False) + raw[span.end(2):]
            result.append(raw)
        return result

    def _inventory(self, relative: str, language: str, html: str) -> list[dict]:
        if language not in LANGUAGES:
            refuse("LANGUAGE", "unknown formula presentation locale")
        parts = math_parts(html)
        if relative not in self.entries:
            if any((node.text or "").strip() for part in parts for node in part["mtext"]):
                refuse("COVERAGE", "localized reader has nonempty mtext without a source-bound descriptor: " + relative)
        elif len(parts) != len(self.canonical[relative]):
            refuse("STRUCTURE", "localized formula count differs from the exact source")
        return parts

    def localize(self, relative: str, language: str, html: str) -> str:
        if language == "en":
            return html
        parts = self._inventory(relative, language, html)
        if relative not in self.entries:
            return html
        for actual, canonical in zip(parts, self.canonical[relative]):
            # Raw equality also refuses entity re-encoding, comments or
            # whitespace edits which an XML tree comparison can normalize.
            if actual["raw"] != canonical["raw"]:
                refuse("STRUCTURE", "input formula tree or TeX annotation differs from the exact source")
        # Replace only the inner text spans in the caller's bytes. Even the
        # whitespace/attribute spelling outside those spans remains unchanged.
        replacements = {(item["math_index"], item["mtext_index"]): item["translations"][language]
                        for item in self.entries[relative]["annotations"]}
        for mi, part in reversed(list(enumerate(parts, 1))):
            for ti, span in reversed(list(enumerate(part["spans"], 1))):
                if (mi, ti) in replacements:
                    start, end = part["start"] + span.start(2), part["start"] + span.end(2)
                    html = html[:start] + escape(replacements[(mi, ti)], quote=False) + html[end:]
        self.validate_localized(relative, language, html)
        return html

    def validate_localized(self, relative: str, language: str, html: str) -> None:
        """Validate compiled MathML independently of the actual replacement."""
        parts = self._inventory(relative, language, html)
        if relative not in self.entries:
            return
        expected = self._expected(relative, language)
        for part, raw in zip(parts, expected):
            if part["raw"] != raw:
                refuse("STRUCTURE", "localized formula differs outside the declared exact mtext presentation")
