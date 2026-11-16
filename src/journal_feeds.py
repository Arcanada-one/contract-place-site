#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Syndicate the published daily Journal, never the research catalogue.

Input is the existing hash-verified build_journal.compile_journal result.
The authored date has day precision; feeds represent it as 00:00:00 UTC.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from email.utils import format_datetime
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.parse import urljoin, urlsplit
import xml.etree.ElementTree as ET

ORIGIN = "https://contract.place"
LANGUAGES = ("en", "ru", "zh-Hans")
LIMIT = 50
CREATED = "2026-11-16T08:30:59Z"  # Committed feed creation time, never a build clock.
ATOM = "http://www.w3.org/2005/Atom"
CONTENT = "http://purl.org/rss/1.0/modules/content/"
XML = "http://www.w3.org/XML/1998/namespace"
ET.register_namespace("atom", ATOM)
ET.register_namespace("content", CONTENT)
LABELS = {
    "en": ("Knowledge Contract Arcana — Daily journal",
           "Published daily journal issues from contract.place. Full articles and their canonical links."),
    "ru": ("Knowledge Contract Arcana — Ежедневный журнал",
           "Опубликованные выпуски ежедневного журнала contract.place: полные статьи и ссылки на них."),
    "zh-Hans": ("Knowledge Contract Arcana — 每日专栏",
                "contract.place 已发布的每日专栏：完整文章及其规范链接。"),
}


def text(value: object) -> str:
    if not isinstance(value, str) or any(
        not (ord(c) in (9, 10, 13) or 0x20 <= ord(c) <= 0xD7FF
             or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF)
        for c in value
    ):
        raise ValueError("Invalid XML text")
    return value


def issue_date(value: object) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Invalid journal date")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ValueError("Invalid journal date") from error
    if parsed.isoformat() != value:
        raise ValueError("Invalid journal date")
    return value + "T00:00:00Z"


def feed_path(language: str, kind: str) -> str:
    if language not in LANGUAGES or kind not in ("rss", "atom"):
        raise ValueError("Unsupported journal feed")
    return f"/{language}/journal/{kind}.xml"


class ArticleHTML(HTMLParser):
    """Retain public rendered article text with safe, absolute URL attributes.

    This processes the existing Pandoc output, not a second Markdown rendering.
    Active HTML is refused. Presentation classes and MathML remain available.
    """

    TAGS = set(("a abbr b bdi bdo blockquote br caption cite code col colgroup dd del "
                "details dfn div dl dt em figcaption figure h1 h2 h3 h4 h5 h6 hr i img "
                "kbd li mark ol p pre q rp rt ruby s samp section small span strong sub "
                "summary sup table tbody td tfoot th thead time tr u ul var "
                "math semantics annotation mrow mi mn mo mtext mspace ms mfrac msqrt "
                "mroot mstyle merror mpadded mphantom mfenced menclose msub msup msubsup "
                "munder mover munderover mmultiscripts mprescripts none mtable mtr mtd "
                "mlabeledtr maligngroup malignmark maction").split())
    VOID = {"br", "col", "hr", "img"}
    URLS = {"href", "src", "cite"}
    ATTRS = set(("class id title lang dir role aria-label aria-hidden alt width height "
                 "colspan rowspan scope datetime start type reversed align display "
                 "mathvariant stretchy fence separator encoding xmlns form lspace rspace "
                 "columnalign rowalign columnspacing rowspacing columnlines rowlines "
                 "linethickness notation accent accentunder displaystyle scriptlevel "
                 "mathsize mathcolor mathbackground").split())
    # Exact presentation forms emitted by the pinned Pandoc 3.1.3 HTML writer:
    # tableToHtml, colSpecListToHtml and tableCellToHtml in Writers/HTML.hs.
    # Discard these attributes; never forward CSS or parse a general style list.
    # https://github.com/jgm/pandoc/blob/3.1.3/src/Text/Pandoc/Writers/HTML.hs
    TABLE_PRESENTATION = {
        "table": re.compile(r"width:(?:100|[1-9]?[0-9])%;"),
        "col": re.compile(r"width: (?:100|[1-9]?[0-9])%"),
        "th": re.compile(r"text-align: (?:left|right|center);"),
        "td": re.compile(r"text-align: (?:left|right|center);"),
    }

    def __init__(self, canonical: str):
        super().__init__(convert_charrefs=False)
        self.canonical = canonical
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self.TAGS:
            raise ValueError(f"Unsupported active or unknown journal HTML: {tag}")
        safe = []
        seen_style = False
        for name, value in attrs:
            if name == "style":
                pattern = self.TABLE_PRESENTATION.get(tag)
                if seen_style or pattern is None or value is None or not pattern.fullmatch(value):
                    raise ValueError("Unsafe journal HTML attribute: style")
                seen_style = True
                continue
            if name.startswith("on") or name in {"srcset", "action", "formaction", "xlink:href"}:
                raise ValueError(f"Unsafe journal HTML attribute: {name}")
            if name in self.URLS:
                value = urljoin(self.canonical, value or "")
                parsed = urlsplit(value)
                if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
                    raise ValueError("Unsafe journal HTML URL")
            elif name not in self.ATTRS:
                continue
            safe.append(" " + name if value is None else f' {name}="{escape(text(value), quote=True)}"')
        self.parts.append("<" + tag + "".join(safe) + ">")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag not in self.TAGS:
            raise ValueError(f"Unsupported journal HTML: {tag}")
        if tag not in self.VOID:
            self.parts.append("</" + tag + ">")

    def handle_data(self, value: str) -> None:
        self.parts.append(escape(text(value), quote=False))

    def handle_entityref(self, name: str) -> None:
        self.parts.append("&" + name + ";")

    def handle_charref(self, name: str) -> None:
        self.parts.append("&#" + name + ";")

    def handle_decl(self, decl: str) -> None:
        raise ValueError("Declarations are not article HTML")

    def unknown_decl(self, data: str) -> None:
        raise ValueError("Declarations are not article HTML")

    def handle_pi(self, data: str) -> None:
        raise ValueError("Processing instructions are not article HTML")


def article_html(value: object, canonical: str) -> str:
    source = text(value)
    if not source.strip():
        raise ValueError("Missing journal article body")
    parser = ArticleHTML(canonical)
    parser.feed(source)
    parser.close()
    return "".join(parser.parts)


def entries(issues: object, language: str) -> list[dict]:
    if language not in LANGUAGES or not isinstance(issues, list):
        raise ValueError("Invalid journal feed input")
    seen: set[str] = set()
    result = []
    # Validate the whole declared set before truncating. A stale old source must not be hidden by LIMIT.
    for issue in issues:
        if not isinstance(issue, dict):
            raise ValueError("Invalid journal identity")
        slug = issue.get("slug")
        if not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError("Invalid journal identity")
        if issue.get("route") != "journal/" + slug or slug == "building-a-place":
            raise ValueError("Invalid journal identity")
        if slug in seen:
            raise ValueError("Duplicate journal identity")
        seen.add(slug)
        languages = issue.get("languages")
        if not isinstance(languages, dict):
            raise ValueError("Missing bound journal language")
        page = languages.get(language)
        if not isinstance(page, dict) or not re.fullmatch(r"[0-9a-f]{64}", page.get("sha256", "")):
            raise ValueError("Missing bound journal language")
        title, summary = text(page.get("title")), text(page.get("excerpt"))
        if not title.strip() or not summary.strip():
            raise ValueError("Missing journal metadata")
        published = issue_date(issue.get("date"))
        updated = issue_date(issue["updated"]) if "updated" in issue else published
        if updated < published:
            raise ValueError("Journal updated date precedes publication")
        canonical = ORIGIN + "/" + language + "/journal/" + slug + "/"
        result.append({"id": canonical, "slug": slug, "title": title, "summary": summary,
                       "published": published, "updated": updated,
                       "html": article_html(page.get("html"), canonical)})
    result.sort(key=lambda item: (-date.fromisoformat(item["published"][:10]).toordinal(), item["slug"]))
    return result[:LIMIT]


def child(parent: ET.Element, name: str, value: str | None = None, **attrs: str) -> ET.Element:
    node = ET.SubElement(parent, name, attrs)
    if value is not None:
        node.text = text(value)
    return node


def serialized(root: ET.Element) -> str:
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def rfc822(iso: str) -> str:
    return format_datetime(datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc), usegmt=True)


def render(issues: object, language: str) -> dict[str, str]:
    items = entries(issues, language)
    title, description = LABELS[language]
    home = ORIGIN + "/" + language + "/journal/"
    updated = max((entry["updated"] for entry in items), default=CREATED)

    rss = ET.Element("rss", {"version": "2.0"})
    channel = child(rss, "channel")
    child(channel, "title", title)
    child(channel, "link", home)
    child(channel, "description", description)
    child(channel, "language", language)
    child(channel, "copyright", "Pavel Valentov and Knowledge Contract Arcana contributors; CC BY 4.0")
    child(channel, f"{{{ATOM}}}link", href=ORIGIN + feed_path(language, "rss"),
          rel="self", type="application/rss+xml")
    child(channel, "lastBuildDate", rfc822(updated))
    for entry in items:
        item = child(channel, "item")
        child(item, "title", entry["title"])
        child(item, "link", entry["id"])
        child(item, "guid", entry["id"], isPermaLink="true")
        child(item, "pubDate", rfc822(entry["published"]))
        child(item, "description", entry["summary"])
        child(item, f"{{{CONTENT}}}encoded", entry["html"])

    atom = ET.Element("feed", {"xmlns": ATOM, f"{{{XML}}}lang": language})
    child(atom, "id", ORIGIN + feed_path(language, "atom"))
    child(atom, "title", title)
    child(atom, "subtitle", description)
    child(atom, "link", href=ORIGIN + feed_path(language, "atom"), rel="self", type="application/atom+xml")
    child(atom, "link", href=home, rel="alternate", type="text/html")
    child(atom, "link", href="https://creativecommons.org/licenses/by/4.0/", rel="license")
    author = child(atom, "author")
    child(author, "name", "Knowledge Contract Arcana")
    child(author, "uri", ORIGIN + "/")
    child(atom, "updated", updated)
    for entry in items:
        item = child(atom, "entry")
        child(item, "id", entry["id"])
        child(item, "title", entry["title"])
        child(item, "link", href=entry["id"], rel="alternate", type="text/html")
        child(item, "published", entry["published"])
        child(item, "updated", entry["updated"])
        child(item, "summary", entry["summary"], type="text")
        child(item, "content", entry["html"], type="html")
    return {"rss": serialized(rss), "atom": serialized(atom)}


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: journal_feeds.py <public-directory>; compiled issues on stdin")
    issues = json.load(sys.stdin)
    # Validate every language and construct all six feeds before writing any of them.
    feeds = {language: render(issues, language) for language in LANGUAGES}
    output = Path(sys.argv[1]).resolve()
    for language, formats in feeds.items():
        folder = output / language / "journal"
        folder.mkdir(parents=True, exist_ok=True)
        for kind, content in formats.items():
            (folder / (kind + ".xml")).write_text(content, encoding="utf-8")
    print("Generated daily Journal RSS and Atom for en, ru and zh-Hans.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError) as error:
        raise SystemExit(str(error))

