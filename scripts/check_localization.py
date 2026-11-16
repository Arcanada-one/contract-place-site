#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Check source, compiled data and actual HTML for the complete locale release.

This is a publication regression check, not semantic translation review,
external acceptance, browser execution or a deployment readback. Its expected
inventory comes from the pinned knowledge JSON and site journal manifest.
It separately checks source text, compiled bodies and the rendered DOM.

Usage:
  python3 -B scripts/check_localization.py public --source-dir /path/to/knowledge \
      --roadmap-source-dir /path/to/roadmap
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from typing import Callable

SITE = Path(__file__).resolve().parents[1]
LOCALES = ("en", "ru", "zh-Hans")
TRANSLATED = ("ru", "zh-Hans")
RENDERED = {"reviewed", "partially-reviewed", "unreviewed"}
INDEXED = {"reviewed", "partially-reviewed"}
ORIGIN = "https://contract.place"
MARKDOWN = "markdown+gfm_auto_identifiers+pipe_tables+tex_math_dollars+tex_math_single_backslash+autolink_bare_uris"
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
BLOCK = {"p", "div", "section", "article", "li", "dt", "dd", "th", "td", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "blockquote"}


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    parent: Node | None = field(default=None, repr=False)

    def has(self, name: str) -> bool:
        return name in self.attrs.get("class", "").split()

    def all(self, predicate: Callable[[Node], bool]) -> list[Node]:
        result = [self] if predicate(self) else []
        for child in self.children:
            if isinstance(child, Node):
                result.extend(child.all(predicate))
        return result

    def text(self, exclude: frozenset[str] = frozenset()) -> str:
        if self.tag in {"script", "style"} or any(self.has(name) for name in exclude):
            return ""
        parts = []
        for child in self.children:
            parts.append(child.text(exclude) if isinstance(child, Node) else child)
        value = "".join(parts)
        return "\n" + value + "\n" if self.tag in BLOCK else value

    def language(self) -> str | None:
        return self.attrs.get("lang") or (self.parent.language() if self.parent else None)

    def visible(self) -> bool:
        if "hidden" in self.attrs or self.attrs.get("aria-hidden") == "true":
            return False
        if re.search(r"(?:display\s*:\s*none|visibility\s*:\s*hidden)", self.attrs.get("style", ""), re.I):
            return False
        return self.parent.visible() if self.parent else True


class Document(HTMLParser):
    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.stack = [self.root]
        self.feed(html)
        self.close()

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs), parent=self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def fingerprint(node: Node, exclude=frozenset()) -> tuple:
    """Compare actual DOM contents, including links, code, math and attributes."""
    result = []
    for child in node.children:
        if isinstance(child, str):
            if normalized(child):
                result.append(("text", normalized(child)))
        elif not any(child.has(name) for name in exclude):
            result.append((child.tag, tuple(sorted(child.attrs.items())), fingerprint(child, exclude)))
    return tuple(result)


def by_class(name: str):
    return lambda node: node.has(name)


def by_tag(name: str):
    return lambda node: node.tag == name


def has_language(text: str, locale: str) -> bool:
    # A script guard detects plain English substitution. It is not a measure
    # of meaning or translation fidelity; exact source/output checks follow.
    return bool(normalized(text)) and (locale == "en" or bool(re.search(
        r"[\u0400-\u04ff]" if locale == "ru" else r"[\u3400-\u9fff]", text)))


def unique(items: list[dict], key: str, where: str) -> dict:
    if not isinstance(items, list):
        raise ValueError(where + ": expected a list")
    values = [item[key] for item in items]
    if len(set(values)) != len(values):
        raise ValueError(where + ": duplicate " + key)
    return dict(zip(values, items))


def read_json(path: Path) -> dict:
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise ValueError(str(path) + ": duplicate JSON key " + key)
            out[key] = value
        return out
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)


def route_for(doc: dict, locale: str = "en") -> str:
    path = doc["path"]
    if path.startswith("papers/"):
        tail = "science/" + doc["slug"]
    elif path.startswith("engineering/specifications/"):
        tail = "engineering/specifications/" + doc["slug"]
    elif path.startswith("engineering/studies/"):
        tail = "engineering/studies/" + doc["slug"]
    elif path.startswith("reference/"):
        tail = "reference/" + doc["slug"]
    elif path.startswith("appendices/"):
        tail = "appendices/" + doc["slug"]
    else:
        raise ValueError("unsupported canonical source path " + path)
    return "/" + locale + "/" + tail + "/"


class Audit:
    def __init__(self, public: Path):
        self.public = public
        self.errors: list[dict] = []
        self.counts: Counter = Counter()
        self.cache: dict[str, Node | None] = {}

    def require(self, condition: bool, code: str, where: str, detail: str):
        if not condition:
            self.errors.append({"code": code, "where": where, "detail": detail})
        return condition

    def one(self, node: Node, predicate, where: str, label: str) -> Node | None:
        found = node.all(predicate)
        if self.require(len(found) == 1, "DOM_CARDINALITY", where, f"{label}: expected one, found {len(found)}"):
            return found[0]
        return None

    def page(self, route: str) -> Node | None:
        if route in self.cache:
            return self.cache[route]
        relative = route.lstrip("/") + ("index.html" if route.endswith("/") else "")
        path = self.public / relative
        if not self.require(path.is_file(), "ROUTE_MISSING", route, "expected generated HTML file"):
            self.cache[route] = None
        else:
            self.cache[route] = Document(path.read_text(encoding="utf-8")).root
        return self.cache[route]

    def inventory(self, actual: set, expected: set, where: str):
        self.require(actual == expected, "INVENTORY", where,
                     f"missing={sorted(expected - actual)!r}; unexpected={sorted(actual - expected)!r}")

    def head(self, page: Node, route: str, locale: str, title: str | None,
             description: str | None, indexed: bool = True, alternates=LOCALES,
             metadata_title: str | None = None):
        html = self.one(page, by_tag("html"), route, "html")
        if html:
            self.require(html.attrs.get("lang") == locale, "PAGE_LANGUAGE", route, f"expected html lang={locale}")
        head = self.one(page, by_tag("head"), route, "head")
        if not head:
            return
        if title is not None:
            element = self.one(head, by_tag("title"), route, "head title")
            if element:
                actual = normalized(element.text()).removesuffix(" — contract.place")
                expected_title = metadata_title if metadata_title is not None else title
                self.require(actual == normalized(expected_title), "PAGE_TITLE", route, f"expected source/status title {expected_title!r}; got {actual!r}")
            h1 = self.one(page, by_tag("h1"), route, "h1")
            if h1:
                self.require(normalized(h1.text()) == normalized(title), "VISIBLE_TITLE", route, "H1 differs from source locale title")
                self.require(h1.language() == locale, "TITLE_LANGUAGE", route, f"expected H1 language {locale}")
        meta = head.all(lambda n: n.tag == "meta" and n.attrs.get("name") == "description")
        self.require(len(meta) == 1 and bool(meta[0].attrs.get("content")), "META_DESCRIPTION", route, "missing or duplicate description")
        if len(meta) == 1:
            content = meta[0].attrs.get("content", "")
            if description is not None:
                self.require(content == description, "META_DESCRIPTION", route, "description differs from source locale metadata")
            self.require(has_language(content, locale), "METADATA_LANGUAGE", route, f"description has no {locale} content")
        canonical = [n.attrs.get("href") for n in head.all(lambda n: n.tag == "link" and n.attrs.get("rel") == "canonical")]
        alternate_nodes = head.all(lambda n: n.tag == "link" and n.attrs.get("rel") == "alternate" and "hreflang" in n.attrs)
        alternate = {n.attrs["hreflang"]: n.attrs.get("href") for n in alternate_nodes}
        robots = [n.attrs.get("content", "") for n in head.all(lambda n: n.tag == "meta" and n.attrs.get("name") == "robots")]
        if indexed:
            self.require(canonical == [ORIGIN + route], "CANONICAL", route, "indexable page needs its exact locale canonical")
            tail = route.split("/", 2)[2]
            expected = {lang: ORIGIN + "/" + lang + "/" + tail for lang in alternates}
            expected["x-default"] = ORIGIN + "/en/" + tail
            self.require(alternate == expected and len(alternate_nodes) == len(expected), "HREFLANG", route, "alternates disagree with reviewed-state indexing policy")
            self.require(not any("noindex" in value for value in robots), "INDEXING_STATE", route, "indexable page is noindex")
        else:
            self.require(not canonical and not alternate_nodes and any("noindex" in value for value in robots),
                         "INDEXING_STATE", route, "unreviewed manuscript must be noindex without canonical/hreflang")

    def body(self, page: Node, predicate, expected_html: str, route: str, locale: str,
             exclude=frozenset()) -> Node | None:
        element = self.one(page, predicate, route, "localized body")
        self.require(isinstance(expected_html, str) and bool(expected_html.strip()),
                     "BODY_EMPTY", route, "compiled body missing or empty")
        if not element:
            return None
        self.require(element.language() == locale, "BODY_LANGUAGE", route,
                     f"expected body language {locale}; found {element.language()!r}")
        self.require(element.visible(), "BODY_HIDDEN", route, "localized body is hidden")
        self.require(has_language(element.text(exclude), locale), "BODY_SCRIPT", route,
                     f"empty body or no {locale} text; script presence is not semantic review")
        if isinstance(expected_html, str):
            expected = Document(expected_html).root
            self.require(fingerprint(element, exclude) == fingerprint(expected), "BODY_CONTENT", route,
                         "actual body differs from the complete compiled locale body")
        return element

    def source_body(self, markdown: str, compiled_html: str, where: str,
                    drop_title: bool = True, journal: bool = False, ignore_status_badges: bool = False,
                    formula_localizations=None, source_path: str | None = None, language: str | None = None):
        """Independent Markdown render, compared as text without rewritten URLs.

        Unlike a file-existence check this refuses a shortened compiled body.
        URL/DOM identity is checked separately between compiled and actual HTML.
        The existing source compiler remains responsible for link resolution.
        """
        parser = "markdown+gfm_auto_identifiers+autolink_bare_uris-smart" if journal else MARKDOWN
        process = subprocess.run(["pandoc", "--from=" + parser, "--to=html5", "--mathml",
                                  "--no-highlight", "--wrap=none"],
                                 input=markdown, capture_output=True, text=True, check=False)
        if process.returncode:
            raise ValueError(where + ": source Markdown render failed: " + process.stderr.strip())
        source_html = process.stdout
        if formula_localizations is not None:
            source_html = formula_localizations.localize(source_path, language, source_html)
            formula_localizations.validate_localized(source_path, language, compiled_html)
        root = Document(source_html).root
        if drop_title:
            first = next((n for n in root.children if isinstance(n, Node) and n.tag == "h1"), None)
            if first:
                root.children.remove(first)
        expected = normalized(root.text())
        # Programme decoration adds exactly one space and a plain status span
        # after selected links. Remove that whole addition for source-text
        # comparison, including its space (Chinese source text may be adjacent).
        # Actual compiled→DOM comparison still requires the badge unchanged.
        if ignore_status_badges:
            compiled_html = re.sub(r' <span class="status-badge">[^<>]*</span>', "", compiled_html)
        actual = normalized(Document(compiled_html).root.text())
        self.require(bool(expected) and expected == actual, "SOURCE_BODY", where,
                     "compiled text differs from source Markdown (excluding first H1 and added status badges)")

    def hash(self, root: Path, relative: str, expected: str, where: str) -> str:
        path = (root / relative).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError(where + ": source path escapes its checkout")
        raw = path.read_bytes()
        self.require(sha256(raw).hexdigest() == expected, "SOURCE_DIGEST", where, "source file differs from its recorded SHA-256")
        return raw.decode("utf-8")

    def retained_routes(self, baseline: dict):
        expected = set(baseline["routes"])
        actual = {"/" + path.relative_to(self.public).as_posix().removesuffix("index.html")
                  for path in self.public.rglob("*.html")}
        self.require(len(expected) == len(baseline["routes"]), "BASELINE_SCHEMA", "route baseline", "duplicate baseline route")
        for route in sorted(expected - actual):
            self.require(False, "ROUTE_LOST", route, "route retained in the named pre-change baseline is absent")
        self.counts["baseline_routes"] = len(expected)
        self.counts["actual_html_routes"] = len(actual)

    def retained_content(self, catalog: dict, documents: list[dict], baseline: dict):
        """Old files alone cannot mask a work dropped from both catalogues."""
        source_docs = unique(documents, "slug", "knowledge catalogue")
        compiled = unique(catalog.get("records", []), "id", "compiled records")
        for old in baseline["canonical_readers"]:
            doc, record = source_docs.get(old["id"]), compiled.get(old["id"])
            self.require(bool(doc) and doc.get("path") == old["path"]
                         and bool(record) and record.get("route") == old["route"],
                         "CONTENT_LOST", old["id"], "baseline source identity/reader route was dropped or changed")
        for label, retained, actual in (
            ("journal issues", baseline["journal_slugs"], [x["slug"] for x in catalog.get("journal_issues", [])]),
            ("article excerpts", baseline["article_ids"], [x["id"] for x in catalog.get("articles", [])]),
            ("roadmap tasks", baseline["roadmap_task_ids"], [x["id"] for x in catalog.get("roadmap", {}).get("tasks", [])]),
        ):
            self.require(set(retained).issubset(actual), "CONTENT_LOST", label,
                         "baseline identities absent: " + repr(sorted(set(retained) - set(actual))))

    def review_prose(self, page: Node, rendition: dict, expected: dict, original: dict,
                     locale: str, where: str):
        """Translated presentation and verbatim source review are separate."""
        from review_localization import FIELDS, original_fields
        self.require(rendition.get("review_localization") == expected, "REVIEW_PROVENANCE", where,
                     "compiled review explanation differs from its source-bound descriptor")
        actual_review = json.loads(json.dumps(rendition.get("review")))
        if self.require(type(actual_review) is dict, "REVIEW_ORIGINAL", where, "original review object is absent"):
            actual_review.pop("author", None)  # Added by the pre-existing compiler.
            if type(actual_review.get("evidence")) is dict:
                actual_review["evidence"].pop("url", None)
            self.require(actual_review == original, "REVIEW_ORIGINAL", where,
                         "original review facts changed under the localized presentation")
        facts_nodes = page.all(lambda node: node.tag == "script" and node.has("rendition-facts"))
        if self.require(len(facts_nodes) == 1, "REVIEW_FACTS", where, "expected exactly one rendition facts record"):
            try:
                facts = json.loads("".join(child for child in facts_nodes[0].children if isinstance(child, str)))
            except (ValueError, TypeError):
                facts = None
            self.require(type(facts) is dict and facts.get("review") == rendition.get("review")
                         and facts.get("review_localization") == {key: expected[key] for key in ("review_state", "language", "source")},
                         "REVIEW_FACTS", where, "machine-readable original review or presentation state/pin differs from its bound record")

        def shown(node):
            parent = node
            while parent is not None:
                if parent.tag == "details" and "open" not in parent.attrs:
                    return False
                parent = parent.parent
            return node.visible()

        translated = page.all(lambda node: "data-review-localization-field" in node.attrs)
        self.require(len(translated) == len(FIELDS)
                     and {node.attrs["data-review-localization-field"] for node in translated} == set(FIELDS),
                     "REVIEW_FIELDS", where, "expected exactly the three localized explanation fields")
        for node in translated:
            field = node.attrs["data-review-localization-field"]
            if field in FIELDS:
                self.require(normalized(node.text()) == normalized(expected["fields"][field])
                             and node.language() == locale and shown(node),
                             "REVIEW_FIELD_TEXT", where + "/" + field,
                             "visible review prose differs from the exact locale text or language")
        notices = page.all(lambda node: "data-review-localization-state" in node.attrs)
        self.require(len(notices) == 1 and notices[0].attrs["data-review-localization-state"] == "unreviewed"
                     and notices[0].language() == locale and shown(notices[0]) and bool(normalized(notices[0].text())),
                     "REVIEW_PRESENTATION_STATE", where, "localized explanations need their own visible unreviewed state")
        containers = page.all(lambda node: node.attrs.get("data-review-original") == "true")
        if self.require(len(containers) == 1 and containers[0].tag == "details"
                        and "open" not in containers[0].attrs and containers[0].language() == "en",
                        "REVIEW_ORIGINAL_VIEW", where, "original review prose needs a separately labelled closed English details view"):
            originals = containers[0].all(lambda node: "data-review-original-field" in node.attrs)
            self.require(len(originals) == len(FIELDS)
                         and {node.attrs["data-review-original-field"] for node in originals} == set(FIELDS),
                         "REVIEW_ORIGINAL_VIEW", where, "original view must retain the three source prose fields")
            values = original_fields(original)
            for node in originals:
                field = node.attrs["data-review-original-field"]
                if field in FIELDS:
                    self.require(normalized(node.text()) == normalized(values[field]) and node.language() == "en",
                                 "REVIEW_ORIGINAL_TEXT", where + "/" + field, "historical English review prose changed or disappeared")

    def readers(self, catalog: dict, documents: list[dict], metadata: list[dict],
                sidecar: list[dict], source: Path | None = None):
        formula_localizations = None
        review_localizations = None
        if source:
            from formula_localization import FormulaLocalizations
            from review_localization import ReviewLocalizations
            formula_localizations = FormulaLocalizations(source, catalog["publication"], documents)
            review_localizations = ReviewLocalizations(source, catalog["publication"], documents)
            self.require(catalog.get("formula_localization_source") == formula_localizations.provenance(),
                         "FORMULA_PROVENANCE", "readers", "compiled formula presentation is not bound to its exact source descriptor")
            self.require(catalog.get("review_localization_source") == review_localizations.provenance(),
                         "REVIEW_PROVENANCE", "readers", "compiled review explanations are not bound to their exact source descriptor")
        docs = unique(documents, "slug", "knowledge catalogue")
        records = unique(catalog["records"], "id", "compiled records")
        if review_localizations is not None:
            review_localizations.validate_inventory({
                (record["id"], language) for record in records.values()
                for language, view in record.get("renditions", {}).items() if view.get("state") in INDEXED
            })
        self.inventory(set(records), set(docs), "canonical works")
        metas, renditions = {}, {}
        for key, items, target in (("metadata", metadata, metas), ("renditions", sidecar, renditions)):
            for item in items:
                ident = (item["work"], item["language"])
                self.require(ident not in target, "INVENTORY", key, "duplicate work/language " + repr(ident))
                target[ident] = item
            self.inventory(set(target), {(slug, lang) for slug in docs for lang in TRANSLATED}, key)
        for slug, doc in docs.items():
            record = records.get(slug)
            if record is None:
                continue
            self.require(record.get("route") == route_for(doc), "READER_ROUTE", slug, "route disagrees with canonical source family")
            self.require(record.get("path") == doc["path"], "SOURCE_PATH", slug, "compiled record is bound to another source")
            source_digest = record.get("source_sha256")
            if source:
                raw = self.hash(source, doc["path"], source_digest, slug)
                self.source_body(raw, record.get("html", ""), slug + "/en")
            allowed = ["en"] + [lang for lang in TRANSLATED if record.get("renditions", {}).get(lang, {}).get("state") in INDEXED]
            for locale in LOCALES:
                route = route_for(doc, locale)
                title, summary, html, state = doc["title"], doc["summary"], record.get("html", ""), "source"
                if locale != "en":
                    rd = record.get("renditions", {}).get(locale, {})
                    entry = renditions.get((slug, locale))
                    meta = metas.get((slug, locale))
                    if not self.require(bool(rd) and rd.get("state") in RENDERED, "RENDITION_STATE", route,
                                        "expected reviewed, partially-reviewed or unreviewed body; no missing/stale/English fallback"):
                        continue
                    if not entry or not meta:
                        continue
                    title, summary, html, state = meta["title"], meta["summary"], rd.get("html", ""), rd["state"]
                    # The historical compiler may render an older source
                    # without this optional descriptor. A complete locale
                    # release must not claim coverage for English review
                    # explanations after the descriptor is removed/repinned.
                    if state in INDEXED and rd.get("review"):
                        self.require(type(rd.get("review_localization")) is dict,
                                     "REVIEW_LOCALIZATION_MISSING", route,
                                     "a displayed source review needs bound localized explanations in a complete locale release")
                    localized = record.get("localization", {}).get(locale, {})
                    self.require(localized.get("title") == title and localized.get("summary") == summary,
                                 "METADATA_SOURCE", route, "compiled title/summary differ from source localization JSON")
                    self.require(meta.get("source_path") == doc["path"] and meta.get("source_sha256") == source_digest,
                                 "METADATA_BINDING", route, "localized metadata is not bound to this source")
                    self.require(rd.get("title") == title, "RENDITION_TITLE", route, "rendition H1 and localized catalogue title disagree")
                    self.require(rd.get("language") == locale and entry["language"] == locale, "RENDITION_LANGUAGE", route, "wrong registered language")
                    self.require(entry.get("source", {}).get("path") == doc["path"]
                                 and entry.get("source", {}).get("sha256") == source_digest
                                 and rd.get("source", {}).get("sha256") == source_digest,
                                 "RENDITION_SOURCE", route, "sidecar/compiled rendition does not bind the current English source bytes")
                    self.require(all(has_language(value, locale) for value in (title, summary)),
                                 "METADATA_LANGUAGE", route, "title or summary is empty or in another script")
                    self.require(normalized(Document(html).root.text()) != normalized(Document(record.get("html", "")).root.text()),
                                 "ENGLISH_FALLBACK", route, "compiled locale body equals the English body")
                    if source:
                        pin = entry["rendition"]
                        raw = self.hash(source, pin["path"], pin["sha256"], route)
                        self.require(rd.get("rendition", {}).get("sha256") == pin["sha256"], "RENDITION_BINDING", route, "compiled rendition digest differs from sidecar")
                        self.require(rd.get("formula_localization") == formula_localizations.for_document(doc["path"], locale),
                                     "FORMULA_PROVENANCE", route, "rendition formula presentation binding differs from the source descriptor")
                        self.source_body(raw, html, route, formula_localizations=formula_localizations,
                                         source_path=doc["path"], language=locale)
                page = self.page(route)
                if not page:
                    continue
                # The English reader retains the catalogue draft suffix in its
                # head title. The rendition wrapper uses its exact localized
                # manuscript title; scientific status remains a separate badge.
                metadata_title = title
                if locale == "en" and doc.get("status"):
                    from publication_checks import STATUS_LABELS
                    metadata_title += " (" + STATUS_LABELS[doc["status"]][locale] + ")"
                self.head(page, route, locale, title, summary, locale == "en" or state in INDEXED, allowed,
                          metadata_title=metadata_title)
                self.body(page, by_class("source-body"), html, route, locale)
                if source and locale != "en":
                    projection = review_localizations.for_review(slug, locale, entry.get("review")) if state in INDEXED else None
                    self.require(rd.get("review_localization") == projection, "REVIEW_PROVENANCE", route,
                                 "review presentation is missing, stale or applied outside a verified review")
                    if projection is not None:
                        self.review_prose(page, rd, projection, entry["review"], locale, route)
                        self.counts["localized_review_fields"] += len(projection["fields"])
                lead = self.one(page, by_class("lead"), route, "reader summary")
                if lead:
                    self.require(normalized(lead.text()) == normalized(summary), "VISIBLE_SUMMARY", route, "lead differs from source locale summary")
                    self.require(lead.language() == locale, "SUMMARY_LANGUAGE", route, "lead carries another language")
                if locale != "en":
                    labels = page.all(by_class("rendition-state"))
                    self.require(len(labels) == 1 and labels[0].attrs.get("data-state") == state
                                 and labels[0].attrs.get("data-body-language") == locale
                                 and labels[0].attrs.get("data-independent-source") == "false",
                                 "STATE_LABEL", route, "actual page does not retain its explicit state, body language and source relation")
                self.counts["reader_pages"] += 1

    def journals(self, catalog: dict, site: Path):
        manifest = read_json(site / "src/content/journal/manifest.json")
        expected = unique(manifest["issues"], "slug", "journal manifest")
        records = unique(catalog.get("journal_issues", []), "slug", "compiled journal")
        self.inventory(set(records), set(expected), "journal issues")
        from build_journal import parse_front_matter
        for slug, entry in expected.items():
            record = records.get(slug)
            if not record:
                continue
            self.inventory(set(entry.get("languages", {})), set(LOCALES), slug + " source journal languages")
            self.inventory(set(record.get("languages", {})), set(LOCALES), slug + " journal languages")
            for locale in LOCALES:
                pin, view = entry["languages"][locale], record.get("languages", {}).get(locale)
                if view is None:
                    continue
                relative = entry["folder"] + "/" + pin["file"]
                raw = self.hash(site / "src/content/journal", relative, pin["sha256"], slug + "/" + locale)
                meta, markdown = parse_front_matter(raw)
                self.require(view.get("sha256") == pin["sha256"] and view.get("file") == relative,
                             "JOURNAL_BINDING", slug, "compiled journal is not bound to this locale source")
                self.require(meta.get("lang") == locale and view.get("title") == meta["title"] and view.get("excerpt") == meta["excerpt"],
                             "JOURNAL_METADATA", slug, "locale title, excerpt or language differs from Markdown front matter")
                self.source_body(markdown, view.get("html", ""), slug + "/" + locale, False, True)
                route = "/" + locale + "/journal/" + slug + "/"
                page = self.page(route)
                if page:
                    self.head(page, route, locale, meta["title"], meta["excerpt"])
                    self.body(page, by_class("journal-body"), view.get("html", ""), route, locale)
                    self.counts["journal_pages"] += 1

    def programmes(self, catalog: dict, source: Path):
        programme = catalog.get("programme", {})
        expected = {"en": "PROGRAMME.md", "ru": "guides/programme.ru.md", "zh-Hans": "guides/programme.zh-Hans.md"}
        self.inventory(set(programme.get("pages", {})), set(expected), "programme languages")
        for locale, relative in expected.items():
            view = programme.get("pages", {}).get(locale)
            if not view:
                continue
            route = "/" + locale + "/programme/"
            self.require(view.get("path") == relative and view.get("language") == locale, "PROGRAMME_BINDING", route, "wrong guide source or language")
            raw = self.hash(source, relative, view.get("source_sha256"), route)
            self.source_body(raw, view.get("html", ""), route, ignore_status_badges=True)
            page = self.page(route)
            if page:
                self.head(page, route, locale, view.get("title"), None)
                self.body(page, by_class("source-body"), view.get("html", ""), route, locale)
                self.counts["programme_pages"] += 1

    def articles(self, catalog: dict, localized: dict):
        expected = unique(localized["articles"], "id", "article localization source")
        records = unique(catalog.get("articles", []), "id", "compiled articles")
        self.inventory(set(records), set(expected), "retained article excerpts")
        for ident, entry in expected.items():
            article = records.get(ident)
            if not article:
                continue
            original = {k: v for k, v in article.items() if k != "translations"}
            digest = sha256(json.dumps(original, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            self.require(digest == entry["source_sha256"], "ARTICLE_BINDING", ident, "retained English record differs from the translation binding")
            for locale in LOCALES:
                view = original if locale == "en" else entry["translations"].get(locale, {})
                if locale != "en":
                    self.require(article.get("translations", {}).get(locale) == view, "ARTICLE_TRANSLATION", ident + "/" + locale,
                                 "compiled excerpt differs from its source JSON")
                for key in ("title", "description", "status", "abstract"):
                    self.require(has_language(view.get(key, ""), locale), "ARTICLE_FIELD", ident + "/" + locale, "missing/wrong-language " + key)
                route = "/" + locale + "/journal/" + ident + "/"
                page = self.page(route)
                if not page:
                    continue
                self.head(page, route, locale, view.get("title"), view.get("description"))
                body = self.one(page, by_class("publication-body"), route, "retained excerpt")
                if body:
                    status = body.all(by_class("publication-status"))
                    status_parts = view.get("status", "").split("\n\n")[1:]
                    actual_status = status[0].all(by_tag("p")) if len(status) == 1 else []
                    self.require([normalized(n.text()) for n in actual_status] == [normalized(x) for x in status_parts],
                                 "ARTICLE_STATUS", route, "historical status prose changed or disappeared")
                    abstract_boxes = [n for n in body.children if isinstance(n, Node) and n.tag == "div" and "lang" in n.attrs]
                    expected_parts = [normalized(x) for x in view.get("abstract", "").split("\n\n")]
                    actual_parts = [normalized(n.text()) for box in abstract_boxes for n in box.all(by_tag("p"))]
                    self.require(actual_parts == expected_parts, "ARTICLE_ABSTRACT", route, "complete retained abstract differs or is missing")
                    visible_boxes = body.all(lambda n: n.tag == "div" and "lang" in n.attrs)
                    self.require(bool(visible_boxes) and all(n.language() == locale and n.visible() for n in visible_boxes),
                                 "ARTICLE_LANGUAGE", route, "status/abstract language or visibility differs")
                self.counts["article_pages"] += 1

    def roadmaps(self, catalog: dict, source: Path):
        from roadmap import split_cards, tasks_preamble, extract_introduction
        road = catalog.get("roadmap", {})
        dependency_ids = {n["id"] for n in read_json(source / "roadmap/dependencies.json")["nodes"]}
        original = (source / "roadmap/TASKS.md").read_text(encoding="utf-8")
        source_cards = split_cards(original)
        self.inventory(set(source_cards), dependency_ids, "English roadmap source")
        for locale in LOCALES:
            if locale == "en":
                view = road
                expected_cards = source_cards
                intro = extract_introduction((source / "roadmap/SITE_DELIVERY.md").read_text(encoding="utf-8"))
                preamble = tasks_preamble(original)
                overview = (source / "ROADMAP.md").read_text(encoding="utf-8")
            else:
                raw = read_json(source / f"roadmap/TASKS.{locale}.json")
                expected_cards = unique(raw["tasks"], "id", locale + " roadmap source")
                expected_cards = {key: {**value, "fields": {**value["fields"], "start": raw["start"]}} for key, value in expected_cards.items()}
                intro, preamble = raw["introduction"], raw["tasks_intro"]
                overview = (source / f"roadmap/ROADMAP.full.{locale}.md").read_text(encoding="utf-8")
                view = road.get("translations", {}).get(locale, {})
                self.require(view.get("language") == locale, "ROADMAP_LANGUAGE", locale, "compiled roadmap translation absent or wrong language")
                self.require(view.get("translation_state") == "unreviewed", "ROADMAP_REVIEW", locale, "author draft must not be promoted to reviewed")
            self.inventory(set(expected_cards), dependency_ids, locale + " roadmap source cards")
            cards = unique(view.get("tasks", []), "id", locale + " compiled roadmap cards")
            self.inventory(set(cards), dependency_ids, locale + " compiled roadmap cards")
            self.require(view.get("introduction") == intro, "ROADMAP_INTRO", locale, "introduction differs from source locale")
            self.source_body(overview, view.get("overview_html", ""), locale + " roadmap overview")
            self.source_body(preamble, view.get("tasks_intro_html", ""), locale + " roadmap preamble")
            route = "/" + locale + "/roadmap/"
            page = self.page(route)
            if not page:
                continue
            self.head(page, route, locale, None, None)
            introduction = self.one(page, by_class("lead"), route, "roadmap introduction")
            if introduction:
                self.require(normalized(introduction.text()) == normalized(intro) and introduction.language() == locale,
                             "ROADMAP_INTRO", route, "actual introduction differs from the locale source or has wrong language")
            actual_cards = page.all(by_class("roadmap-card"))
            actual_ids = [node.attrs.get("data-task-id") for node in actual_cards]
            self.require(set(actual_ids) == dependency_ids and len(actual_ids) == len(dependency_ids),
                         "ROADMAP_CARDS", route, "actual cards have missing/duplicate/unknown task identities")
            for ident, expected in expected_cards.items():
                card = cards.get(ident)
                actual = next((node for node in actual_cards if node.attrs.get("data-task-id") == ident), None)
                if card is None or actual is None:
                    continue
                self.require(card.get("title") == expected["title"] and card.get("status") == "planned",
                             "ROADMAP_TITLE_STATE", route + "#" + ident, "source title differs or task is promoted beyond planned")
                short, separator, subtitle = expected["title"].partition(": ")
                name_node = self.one(actual, by_class("rm-name"), route + "#" + ident, "roadmap name")
                subtitle_node = self.one(actual, by_class("rm-subtitle"), route + "#" + ident, "roadmap subtitle")
                if name_node and subtitle_node:
                    self.require(bool(separator) and normalized(name_node.text()) == normalized(short)
                                 and normalized(subtitle_node.text()) == normalized(subtitle)
                                 and name_node.language() == locale and subtitle_node.language() == locale,
                                 "ROADMAP_VISIBLE_TITLE", route + "#" + ident, "actual name/subtitle differs from translated source title or language")
                fields = unique(card.get("fields", []), "key", locale + "/" + ident + " fields")
                self.inventory(set(fields), set(expected["fields"]), locale + "/" + ident + " field inventory")
                boxes = actual.all(by_class("roadmap-fields"))
                dds = boxes[0].all(by_tag("dd")) if len(boxes) == 1 else []
                self.require(len(dds) == len(card.get("fields", [])), "ROADMAP_FIELDS", route + "#" + ident,
                             "actual field count differs from complete source fields")
                for index, record in enumerate(card.get("fields", [])):
                    key = record["key"]
                    if key not in expected["fields"]:
                        continue
                    self.source_body(expected["fields"][key], record.get("html", ""), locale + "/" + ident + "/" + key, False)
                    if index < len(dds):
                        holder = Node("wrapper", children=[dds[index]])
                        expected_html = record.get("html", "")
                        for source_record in catalog["records"]:
                            expected_html = expected_html.replace('href="' + source_record["route"] + '"',
                                                                  'href="' + source_record["route"].replace("/en/", "/" + locale + "/", 1) + '"')
                        self.body(holder, by_tag("dd"), expected_html, route + "#" + ident + "/" + key, locale,
                                  frozenset({"rm-linked-status"}))
                        self.counts["roadmap_fields"] += 1
                self.counts["roadmap_cards"] += 1
            # Check whole overview and preamble bodies independently of the cards.
            overview_section = page.all(lambda n: n.attrs.get("id") == "roadmap-section-overview")
            tasks_section = page.all(lambda n: n.tag == "section" and n.attrs.get("aria-labelledby") == "roadmap-tasks")
            if len(overview_section) == 1:
                self.body(overview_section[0], by_class("source-body"), view.get("overview_html", ""), route + "#overview", locale)
            else:
                self.require(False, "ROADMAP_OVERVIEW", route, "overview section absent or duplicated")
            if len(tasks_section) == 1:
                preambles = [n for n in tasks_section[0].children if isinstance(n, Node) and n.has("source-body")]
                if len(preambles) == 1:
                    self.body(Node("wrapper", children=preambles), by_class("source-body"), view.get("tasks_intro_html", ""), route + "#preamble", locale)
                else:
                    self.require(False, "ROADMAP_PREAMBLE", route, "task preamble absent or duplicated")
            else:
                self.require(False, "ROADMAP_PREAMBLE", route, "task section absent or duplicated")
            self.counts["roadmap_pages"] += 1


def run_audit(public: Path, site: Path, source: Path, roadmap_source: Path, baseline: Path) -> Audit:
    audit = Audit(public)
    catalog = read_json(site / "src/content/catalog.json")
    served = (public / "content.js").read_text(encoding="utf-8").split("=", 1)[1].strip().removesuffix(";")
    served_data = json.loads(served)
    # build.mjs adds only the route compatibility map; all compiled content
    # fields must survive unchanged into the publicly served data.
    audit.require({key: served_data.get(key) for key in catalog} == catalog
                  and set(served_data) - set(catalog) <= {"reader_aliases"},
                  "CATALOGUE_OUTPUT", "content.js", "served catalogue differs from compiled source catalogue")
    for name, root, filename, actual in (
        ("publication", source, "publication-manifest.json", catalog.get("publication", {})),
        ("roadmap", roadmap_source, "roadmap-manifest.json", catalog.get("roadmap", {}).get("pin", {})),
    ):
        pin = read_json(site / filename)
        process = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=False)
        audit.require(process.returncode == 0 and process.stdout.strip() == pin["commit"] == actual.get("commit"),
                      "CHECKOUT_PIN", name, "source checkout, site manifest and compiled commit must agree")
        clean = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=normal"],
                               capture_output=True, text=True, check=False)
        audit.require(clean.returncode == 0 and not clean.stdout.strip(), "CHECKOUT_DIRTY", name,
                      "source checkout has uncommitted changes; local drafts cannot establish a pinned release")
        if name == "roadmap":
            for entry in pin["files"]:
                audit.hash(root, entry["path"], entry["sha256"], "roadmap pin/" + entry["path"])
    docs = read_json(source / "publication-catalog.json")
    retained = read_json(baseline)
    stages = (
        ("routes", lambda: audit.retained_routes(retained)),
        ("retained content", lambda: audit.retained_content(catalog, docs["documents"], retained)),
        ("readers", lambda: audit.readers(catalog, docs["documents"], read_json(source / "publication-localization.json")["entries"],
                                          read_json(source / docs["renditions"])["renditions"], source)),
        ("journal", lambda: audit.journals(catalog, site)),
        ("programme", lambda: audit.programmes(catalog, source)),
        ("articles", lambda: audit.articles(catalog, read_json(site / "src/content/article-localizations.json"))),
        ("roadmap", lambda: audit.roadmaps(catalog, roadmap_source)),
    )
    for name, stage in stages:
        try:
            stage()
        except (OSError, ValueError, KeyError, TypeError) as error:
            audit.require(False, "INPUT_INVALID", name, str(error))
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("public", nargs="?", type=Path, default=SITE / "public")
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--roadmap-source-dir", type=Path, required=True)
    parser.add_argument("--site-dir", type=Path, default=SITE)
    parser.add_argument("--baseline", type=Path, default=SITE / "scripts/fixtures/localization-routes.json")
    parser.add_argument("--json-report", type=Path)
    args = parser.parse_args()
    try:
        audit = run_audit(args.public, args.site_dir, args.source_dir, args.roadmap_source_dir, args.baseline)
        report = {"schema_version": 1, "status": "FAIL" if audit.errors else "PASS",
                  "checked": dict(audit.counts), "errors": audit.errors,
                  "scope": "local source/compiled/HTML regression; no independent semantic review, browser or deployment claim"}
    except (OSError, ValueError, KeyError, TypeError) as error:
        report = {"schema_version": 1, "status": "FAIL", "checked": {},
                  "errors": [{"code": "INPUT_INVALID", "where": "initialization", "detail": str(error)}]}
    if args.json_report:
        args.json_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for error in report["errors"]:
        print(f"{error['code']} {error['where']}: {error['detail']}")
    print("Localization " + report["status"] + ": " + json.dumps(report["checked"], sort_keys=True))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
