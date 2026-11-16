# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Compile source-bound catalogue titles and summaries; never translate text.

The optional fixed-name source file is separate from the closed rendition v2
sidecar. Its status concerns these metadata bytes, not manuscript review. It
cannot add a work, change the publication scope, or claim semantic review.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

FILENAME = "publication-localization.json"
LANGUAGES = ("ru", "zh-Hans")


def refuse(reason: str) -> None:
    raise ValueError("LOCALIZATION_INVALID: " + reason)


def closed(value: object, keys: set[str], label: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        refuse(label + " has missing or unknown fields")
    return value


def text(value: object, label: str) -> str:
    if type(value) is not str or not value.strip() or value != value.strip():
        refuse(label + " must be a nonempty, trimmed string")
    if re.search(r"[\x00-\x1f\x7f<>]", value):
        refuse(label + " must be plain single-line text without HTML")
    return value


def git(source: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(source), *args], capture_output=True, check=False)
    if result.returncode:
        refuse("unverified source revision/ancestry")
    return result.stdout


def exact_path(root: Path, value: object, label: str) -> Path:
    name = text(value, label)
    p = PurePosixPath(name)
    resolved = (root / name).resolve()
    if p.is_absolute() or ".." in p.parts or str(p) != name or not resolved.is_relative_to(root.resolve()):
        refuse(label + " escapes the source or is not canonical")
    return resolved


def compile_localization(source: Path, manifest: dict, documents: list[dict]) -> dict | None:
    path = source / FILENAME
    if not path.exists():
        return None
    raw = path.read_bytes()

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                refuse("duplicate JSON key: " + key)
            result[key] = value
        return result

    try:
        data = json.loads(raw, object_pairs_hook=unique_pairs)
    except (UnicodeError, json.JSONDecodeError) as error:
        refuse("invalid UTF-8 JSON: " + str(error))
    closed(data, {"schema_version", "kind", "source", "entries"}, "root")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1 or data["kind"] != "arcanada-publication-localization":
        refuse("unsupported schema or kind")
    binding = closed(data["source"], {"catalog", "revision", "sha256"}, "source")
    catalog = binding["catalog"]
    if catalog != manifest.get("catalog", "publication-catalog.json"):
        refuse("source catalogue differs from the publication manifest")
    catalog_path = exact_path(source, catalog, "source.catalog")
    revision, digest = binding["revision"], binding["sha256"]
    if type(revision) is not str or not re.fullmatch(r"[0-9a-f]{40}", revision):
        refuse("source.revision must be a full commit ID")
    if type(digest) is not str or not re.fullmatch(r"[0-9a-f]{64}", digest):
        refuse("source.sha256 must be an exact digest")
    git(source, "merge-base", "--is-ancestor", revision, manifest["commit"])
    if sha256(git(source, "show", revision + ":" + catalog)).hexdigest() != digest:
        refuse("historical catalogue bytes differ from the declared digest")
    if sha256(catalog_path.read_bytes()).hexdigest() != digest:
        refuse("catalogue localization is stale for the current catalogue")
    by_work = {doc["slug"]: doc for doc in documents}
    if len(by_work) != len(documents):
        refuse("duplicate canonical work")
    if type(data["entries"]) is not list:
        refuse("entries must be a list")
    records, observed, provenance = {}, set(), []
    from renditions import script_matches
    for entry in data["entries"]:
        closed(entry, {"work", "language", "source_path", "source_sha256", "title", "summary", "status"}, "entry")
        work, language = entry["work"], entry["language"]
        if type(work) is not str or work not in by_work or type(language) is not str or language not in LANGUAGES:
            refuse("unknown work or language")
        key = work, language
        if key in observed:
            refuse("duplicate work/language entry")
        observed.add(key)
        doc = by_work[work]
        if entry["source_path"] != doc["path"]:
            refuse("metadata is bound to the wrong canonical source")
        source_bytes = exact_path(source, doc["path"], "source_path").read_bytes()
        if entry["source_sha256"] != sha256(source_bytes).hexdigest() or entry["source_sha256"] != doc["sha256"]:
            refuse("metadata source bytes are stale or inconsistent")
        if entry["status"] != "unreviewed":
            refuse("schema 1 does not confer reviewed metadata status")
        title, summary = text(entry["title"], "title"), text(entry["summary"], "summary")
        if not script_matches(language, title) or not script_matches(language, summary):
            refuse("title/summary does not match the declared language")
        records.setdefault(work, {})[language] = {"title": title, "summary": summary, "status": "unreviewed"}
        provenance.append({k: entry[k] for k in ("work", "language", "source_path", "source_sha256", "status")})
    expected = {(work, language) for work in by_work for language in LANGUAGES}
    if observed != expected:
        refuse("incomplete catalogue work/language inventory")
    return {"records": records, "provenance": {
        "schema_version": 1, "path": FILENAME, "sha256": sha256(raw).hexdigest(),
        "source": dict(binding), "entries": provenance,
        "scope": "localized catalogue metadata; no manuscript review, independent source or runtime admission",
    }}


def compile_article_localizations(site: Path, articles: list[dict]) -> tuple[list[dict], dict | None]:
    """Bind localized legacy excerpts to the complete retained English record.

    Here ``status`` is the translated publication-status prose, not a review
    enum. These translated excerpts do not recover the canonical Russian v1
    source or claim a fresh check of the historical observations they report.
    """
    relative = "src/content/article-localizations.json"
    path = site / relative
    originals = [{k: v for k, v in article.items() if k != "translations"} for article in articles]
    if not path.exists():
        return originals, None
    raw = path.read_bytes()

    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                refuse("duplicate article JSON key: " + key)
            result[key] = value
        return result

    try:
        data = json.loads(raw, object_pairs_hook=unique_pairs)
    except (UnicodeError, json.JSONDecodeError) as error:
        refuse("invalid article UTF-8 JSON: " + str(error))
    closed(data, {"schema_version", "kind", "articles"}, "article root")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1 or data["kind"] != "arcanada-article-localizations":
        refuse("unsupported article schema or kind")
    if type(data["articles"]) is not list:
        refuse("articles must be a list")
    by_id = {article["id"]: article for article in originals}
    if len(by_id) != len(originals):
        refuse("duplicate retained article ID")
    observed, bindings = set(), []
    from renditions import script_matches
    for entry in data["articles"]:
        closed(entry, {"id", "source_sha256", "translations"}, "article entry")
        identity = entry["id"]
        if type(identity) is not str or identity not in by_id or identity in observed:
            refuse("unknown or duplicate article ID")
        observed.add(identity)
        original = by_id[identity]
        digest = sha256(json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        if entry["source_sha256"] != digest:
            refuse("article source record is stale")
        closed(entry["translations"], set(LANGUAGES), "article translations")
        translated = {}
        for language in LANGUAGES:
            fields = closed(entry["translations"][language], {"title", "description", "status", "abstract"}, "article language")
            for key, value in fields.items():
                if key in {"title", "description"}:
                    text(value, "article " + key)
                elif type(value) is not str or not value.strip() or value != value.strip() or re.search(r"[\x00-\x09\x0b-\x1f\x7f<>]", value):
                    refuse("article " + key + " must be plain paragraph text without HTML")
            if not all(script_matches(language, fields[key]) for key in ("title", "description", "abstract")):
                refuse("article text does not match the declared language")
            translated[language] = dict(fields)
        # Add only after hashing the unmodified original English record.
        original["translations"] = translated
        bindings.append({"id": identity, "source_sha256": digest})
    if observed != set(by_id):
        refuse("incomplete retained article inventory")
    return originals, {"schema_version": 1, "path": relative, "sha256": sha256(raw).hexdigest(),
                       "articles": bindings,
                       "scope": "unreviewed translations of retained English excerpts; no recovered Russian v1 original, fresh empirical check or independent review"}
