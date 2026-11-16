# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Source-bound translations of review explanations, separate from the review.

Historical review objects and manuscript bytes remain unchanged. This optional
descriptor presents three prose fields with its own unreviewed state; it cannot
change reviewer identity, review scope, evidence or the original verdict.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

FILENAME = "publication-review-localizations.json"
REPOSITORY = "Arcanada-one/knowledge-contract"
LANGUAGES = ("ru", "zh-Hans")
FIELDS = ("independence_basis", "method", "limitations")
REVIEWED = {"reviewed", "partially-reviewed"}


def refuse(code: str, reason: str) -> None:
    raise ValueError("REVIEW_LOCALIZATION_" + code + ": " + reason)


def closed(value: object, keys: set[str], label: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        refuse("SCHEMA", label + " has missing or unknown fields")
    return value


def digest(value: object, length: int, label: str) -> str:
    if type(value) is not str or not re.fullmatch("[0-9a-f]{" + str(length) + "}", value):
        refuse("SCHEMA", label + " must be a full lowercase hexadecimal digest")
    return value


def plain(value: object, label: str) -> str:
    if (type(value) is not str or not value.strip() or value != value.strip()
            or re.search(r"[\x00-\x09\x0b-\x1f\x7f<>]", value)):
        refuse("SCHEMA", label + " must be nonempty, trimmed plain paragraph text")
    return value


def json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def review_digest(review: dict) -> str:
    return sha256(json_bytes(review)).hexdigest()


def original_fields(review: dict) -> dict:
    try:
        values = {"independence_basis": review["reviewer"]["independence_basis"],
                  "method": review["method"], "limitations": review["limitations"]}
    except (KeyError, TypeError):
        refuse("BINDING", "source review does not have the three original prose fields")
    for key, value in values.items():
        plain(value, "source review " + key)
    return values


def read_json(raw: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                refuse("SCHEMA", "duplicate JSON key: " + key)
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=pairs)
    except (UnicodeError, json.JSONDecodeError) as error:
        refuse("SCHEMA", "invalid UTF-8 JSON: " + str(error))
    if type(value) is not dict:
        refuse("SCHEMA", "expected a JSON object")
    return value


def git(source: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(source), *args], capture_output=True, check=False)
    if result.returncode:
        refuse("BINDING", "unverified committed source bytes or revision ancestry")
    return result.stdout


class ReviewLocalizations:
    def __init__(self, source: Path, manifest: dict, documents: list[dict]):
        self.entries: dict[tuple[str, str], dict] = {}
        self.originals: dict[tuple[str, str], dict] = {}
        self._provenance = None
        self._source = None
        file = source / FILENAME
        if not file.exists():
            if subprocess.run(["git", "-C", str(source), "cat-file", "-e", manifest["commit"] + ":" + FILENAME],
                              capture_output=True, check=False).returncode == 0:
                refuse("BINDING", "pinned review descriptor is missing from the checkout")
            return  # Named older snapshots retain their original review view.
        raw = file.read_bytes()
        data = read_json(raw)
        closed(data, {"schema_version", "repository", "source_revision", "source_path", "source_sha256",
                      "review_state", "entries"}, "root")
        if (type(data["schema_version"]) is not int or data["schema_version"] != 1
                or data["repository"] != REPOSITORY or data["review_state"] != "unreviewed"):
            refuse("SCHEMA", "unsupported schema/repository or unearned presentation review state")
        revision = digest(data["source_revision"], 40, "source_revision")
        current = digest(manifest["commit"], 40, "publication commit")
        expected = digest(data["source_sha256"], 64, "source_sha256")
        relative = plain(data["source_path"], "source_path")
        path = PurePosixPath(relative)
        resolved = (source / relative).resolve()
        if path.is_absolute() or ".." in path.parts or str(path) != relative or not resolved.is_relative_to(source.resolve()):
            refuse("SCHEMA", "source_path escapes the checkout or is not canonical")
        catalog = read_json((source / manifest.get("catalog", "publication-catalog.json")).read_bytes())
        if catalog.get("renditions") != relative:
            refuse("BINDING", "descriptor is not bound to the catalogue-declared rendition sidecar")
        git(source, "merge-base", "--is-ancestor", revision, current)
        if git(source, "show", current + ":" + FILENAME) != raw:
            refuse("BINDING", "review descriptor differs from the selected publication commit")
        sidecar_raw = resolved.read_bytes()
        if (sha256(git(source, "show", revision + ":" + relative)).hexdigest() != expected
                or sha256(git(source, "show", current + ":" + relative)).hexdigest() != expected
                or sha256(sidecar_raw).hexdigest() != expected):
            refuse("BINDING", "historical/current rendition sidecar differs from the exact source digest")
        sidecar = read_json(sidecar_raw)
        if type(sidecar.get("renditions")) is not list:
            refuse("BINDING", "source rendition sidecar has no record inventory")
        published = {doc["slug"] for doc in documents}
        for entry in sidecar["renditions"]:
            if type(entry) is not dict:
                refuse("BINDING", "invalid source rendition record")
            review = entry.get("review")
            if review is None:
                continue
            work, language = entry.get("work"), entry.get("language")
            if type(work) is not str or work not in published or type(language) is not str or language not in LANGUAGES:
                refuse("BINDING", "review belongs to an unknown work or language")
            key = work, language
            if key in self.originals or type(review) is not dict:
                refuse("BINDING", "duplicate or invalid original review")
            original_fields(review)
            self.originals[key] = deepcopy(review)
        if type(data["entries"]) is not list:
            refuse("SCHEMA", "entries must be a list")
        from renditions import script_matches
        for entry in data["entries"]:
            closed(entry, {"work", "language", "review_sha256", "fields"}, "entry")
            work, language = entry["work"], entry["language"]
            if type(work) is not str or type(language) is not str or language not in LANGUAGES:
                refuse("SCHEMA", "invalid review work/language")
            key = work, language
            if key not in self.originals or key in self.entries:
                refuse("COVERAGE", "unknown or duplicate review work/language")
            if digest(entry["review_sha256"], 64, "review_sha256") != review_digest(self.originals[key]):
                refuse("BINDING", "original review JSON differs from the entry binding")
            closed(entry["fields"], set(FIELDS), "translated review fields")
            for name, value in entry["fields"].items():
                plain(value, "translated " + name)
                if not script_matches(language, value):
                    refuse("LANGUAGE", "review prose does not match its declared locale")
            self.entries[key] = deepcopy(entry)
        if set(self.entries) != set(self.originals):
            refuse("COVERAGE", "review explanations must cover every source review exactly once")
        self._source = {
            "path": FILENAME, "sha256": sha256(raw).hexdigest(), "revision": current,
            "sidecar_path": relative, "sidecar_sha256": expected, "sidecar_revision": revision,
        }
        self._provenance = {
            "schema_version": 1, "repository": REPOSITORY, "review_state": "unreviewed",
            "source": deepcopy(self._source),
            "entries": [{key: entry[key] for key in ("work", "language", "review_sha256")} for entry in data["entries"]],
            "scope": "translated explanations only; original review, identity, scope and verdict unchanged; no new review",
        }

    def provenance(self) -> dict | None:
        return deepcopy(self._provenance)

    def validate_inventory(self, active_reviews: set[tuple[str, str]]) -> None:
        if self._provenance is not None and set(active_reviews) != set(self.entries):
            refuse("COVERAGE", "descriptor does not match the currently verified review inventory")

    def for_review(self, work: str, language: str, original: dict | None = None) -> dict | None:
        if self._provenance is None:
            return None
        key = work, language
        if key not in self.entries:
            refuse("COVERAGE", "verified review has no bound localized explanation")
        entry = self.entries[key]
        if original is not None and review_digest(original) != entry["review_sha256"]:
            refuse("BINDING", "review changed between validation and compilation")
        return {"review_state": "unreviewed", "language": language, "fields": deepcopy(entry["fields"]),
                "source": dict(self._source, review_sha256=entry["review_sha256"])}
