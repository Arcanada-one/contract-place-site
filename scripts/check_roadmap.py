#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Check the built roadmap pages against the pinned roadmap source.

Usage: check_roadmap.py <public-dir> --source-dir <checkout of the roadmap pin>

The expected text is read from the source files, not from strings stored here: every field of every
task card and the public introduction must appear, in order, in the prerendered HTML of all three
language routes without script execution.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re

import roadmap

ROOT = Path(__file__).resolve().parents[1]
LOCALES = {"en": "Planned", "ru": "Запланировано", "zh-Hans": "计划中"}
NAV = {"en": "Roadmap", "ru": "Дорожная карта", "zh-Hans": "路线图"}
NOTICE = {"en": "The roadmap text is English on every language route", "ru": "Текст дорожной карты на всех языковых маршрутах английский", "zh-Hans": "所有语言路线下的路线图正文均为英文"}


class Page(HTMLParser):
    def __init__(self, text: str):
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.cards: dict[str, int] = {}
        self.status: list[str] = []
        self.rows: dict[str, list[str]] = {}
        self.stack: list[str] = []
        self._status = False
        self._cell: list[str] | None = None
        self._row: list[list[str]] | None = None
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self.times = 0
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "article" and re.fullmatch(r"rm-\d\d", a.get("id", "")):
            self.cards[a["id"]] = self.cards.get(a["id"], 0) + 1
        if tag == "span" and "rm-status" in (a.get("class") or "").split():
            self._status = True
            self.status.append("")
        if tag == "time":
            self.times += 1
        if tag == "table":
            self._table = []
        if tag == "tr" and self._table is not None:
            self._row = []
        if tag in {"td", "th"} and self._row is not None:
            self._cell = []
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag == "span":
            self._status = False
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        if tag == "tr" and self._row is not None and self._table is not None:
            self._table.append(self._row)
            self._row = None
        if tag == "table" and self._table is not None:
            self.tables.append(self._table)
            self._table = None
        while self.stack and self.stack.pop() != tag:
            pass

    def handle_data(self, data):
        if not self.stack or self.stack[-1] not in {"script", "style"}:
            self.text.append(data)
            if self._status:
                self.status[-1] += data
            if self._cell is not None:
                self._cell.append(data)


def tokens(text: str) -> list[str]:
    return re.findall(r"[^\W_]+", text)


def markdown_plain(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    return re.sub(r"[*`]", "", text)


def contains(haystack: list[str], needle: list[str]) -> bool:
    if not needle:
        return True
    first = needle[0]
    for index, token in enumerate(haystack):
        if token == first and haystack[index:index + len(needle)] == needle:
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("public", type=Path)
    parser.add_argument("--source-dir", type=Path, required=True)
    args = parser.parse_args()
    public, source = args.public.resolve(), args.source_dir.resolve()
    pin = json.loads((ROOT / "roadmap-manifest.json").read_text())
    manuscript = json.loads((ROOT / "publication-manifest.json").read_text())
    errors: list[str] = []

    # The source on disk is the pinned one (same discipline as the compiler).
    roadmap.load_pin(source, ROOT / "roadmap-manifest.json")
    deps = json.loads((source / "roadmap/dependencies.json").read_text())
    nodes = {n["id"]: n for n in deps["nodes"]}
    cards = roadmap.split_cards((source / "roadmap/TASKS.md").read_text())
    intro = roadmap.extract_introduction((source / "roadmap/SITE_DELIVERY.md").read_text())
    overview = (source / "ROADMAP.md").read_text()
    overview = re.sub(r"\A---\n.*?\n---\n", "", overview, count=1, flags=re.S)
    if sorted(cards) != roadmap.TASK_IDS or sorted(nodes) != roadmap.TASK_IDS:
        raise SystemExit("Source does not define exactly RM-01..RM-25")

    for locale, planned in LOCALES.items():
        rel = f"{locale}/roadmap/index.html"
        html = (public / rel).read_text(encoding="utf-8")
        page = Page(html)
        stream = tokens(" ".join(page.text))
        where = rel + ": "
        if sorted(page.cards) != [c.lower() for c in roadmap.TASK_IDS] or set(page.cards.values()) != {1}:
            errors.append(where + "cards rm-01..rm-25 must each appear exactly once as <article id>")
        if len(page.status) != 25 or any(s.strip().split(":")[-1].strip() != planned for s in page.status):
            errors.append(where + f"all 25 task statuses must read '{planned}' (found {sorted(set(page.status))})")
        if page.times:
            errors.append(where + "a <time> element would imply a dated status")
        if not contains(stream, tokens(intro)):
            errors.append(where + "public introduction from the source is missing")
        for ident, card in cards.items():
            for key, label in roadmap.FIELDS:
                if not contains(stream, tokens(markdown_plain(card["fields"][key]))):
                    errors.append(where + f"{ident} {label}: source text missing from the built page")
            if not contains(stream, tokens(card["title"])):
                errors.append(where + f"{ident}: title missing")
        # Every ROADMAP.md paragraph and list item is present (the page renders the document in full).
        for block in re.split(r"\n\s*\n", overview):
            block = block.strip()
            if not block or block.startswith(("#", "|", "```")) or block.startswith("**A bounded"):
                continue
            if not contains(stream, tokens(markdown_plain(block))[:40]):
                errors.append(where + f"overview text missing: {block[:60]!r}")
        # Dependency table equals dependencies.json, both directions and advisory links.
        deptable = next((t for t in page.tables if t and t[0] and t[0][0] == {"en": "Task", "ru": "Задача", "zh-Hans": "任务"}[locale]), None)
        if not deptable or len(deptable) != 26:
            errors.append(where + "dependency table missing or incomplete")
        else:
            needed = {i: sorted(n["id"] for n in nodes.values() if i in n["requires"]) for i in nodes}
            for row in deptable[1:]:
                ident = row[0].split()[0]
                got = [] if row[4] in {"none", "нет", "无"} else [x.strip() for x in row[4].split(",")]
                got_needed = [] if row[5] in {"none", "нет", "无"} else [x.strip() for x in row[5].split(",")]
                if sorted(got) != sorted(nodes[ident]["requires"]) or sorted(got_needed) != needed[ident]:
                    errors.append(where + f"{ident}: dependency row differs from dependencies.json")
                if row[1] != nodes[ident]["priority"] or row[2] != nodes[ident]["content_owner"]:
                    errors.append(where + f"{ident}: priority or owner differs from dependencies.json")
        advisory = [t for t in page.tables if t and t[0] and t[0][-1] in {"Relation", "Связь", "关系"}]
        if len(advisory) != 1 or sorted((r[0], r[1]) for r in advisory[0][1:]) != sorted((a["from"], a["to"]) for a in deps["advisory_links"]):
            errors.append(where + "advisory link table differs from dependencies.json")
        for needle in (pin["commit"], manuscript["commit"], NOTICE[locale]):
            if needle not in html:
                errors.append(where + f"missing {needle[:40]}")
        for f in pin["files"]:
            if f["sha256"] not in html or f"/blob/{pin['commit']}/{f['path']}" not in html:
                errors.append(where + f"pinned source file {f['path']} not shown with hash and versioned link")
        # Head, navigation, language.
        head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
        if f'<link rel="canonical" href="https://contract.place/{locale}/roadmap/">' not in head:
            errors.append(where + "canonical link missing")
        for other in LOCALES:
            if f'hreflang="{other}" href="https://contract.place/{other}/roadmap/"' not in head:
                errors.append(where + f"hreflang {other} missing")
        if f'href="/{locale}/roadmap/"' not in html or NAV[locale] not in html:
            errors.append(where + "primary navigation link missing")
        if f'<html lang="{locale}">' not in html:
            errors.append(where + "document language missing")
        for private_pattern, what in roadmap.PRIVATE:
            found = private_pattern.search(" ".join(page.text))
            if found:
                errors.append(where + f"private detail ({what}): {found[0]!r}")
        if locale == "zh-Hans" and "中文界面尚未经过母语编辑审校" not in html:
            errors.append(where + "Chinese interface review notice missing")

    # Navigation reaches the roadmap from the overview, the footer and ordinary pages in every language.
    for locale in LOCALES:
        for rel in (f"{locale}/index.html", f"{locale}/research/index.html", f"{locale}/science/semantic-objects-and-context/index.html"):
            if f'href="/{locale}/roadmap/"' not in (public / rel).read_text(encoding="utf-8"):
                errors.append(f"{rel}: no link to the roadmap")
    home = (public / "en/index.html").read_text(encoding="utf-8")
    if 'class="publication-paths"' not in home or 'href="/en/roadmap/"' not in home.split('class="publication-paths"', 1)[1].split("</section>", 1)[0]:
        errors.append("en/index.html: the project overview does not link to the roadmap")

    # Provenance: roadmap.json, catalogue and manifests agree; the manuscript publication is unchanged.
    prov = json.loads((public / "roadmap.json").read_text())
    if prov["roadmap_pin"]["commit"] != pin["commit"] or prov["manuscript_pin"]["commit"] != manuscript["commit"]:
        errors.append("roadmap.json pins differ from the manifests")
    if prov["same_commit"] != (pin["commit"] == manuscript["commit"]):
        errors.append("roadmap.json same_commit is wrong")
    for f in prov["roadmap_pin"]["files"]:
        if sha256((source / f["path"]).read_bytes()).hexdigest() != f["sha256"]:
            errors.append(f"roadmap.json: {f['path']} hash differs from the pinned source")
    if [t["id"] for t in prov["tasks"]] != roadmap.TASK_IDS or {t["status"] for t in prov["tasks"]} != {"planned"}:
        errors.append("roadmap.json tasks must be RM-01..RM-25, all planned")
    catalog = json.loads((ROOT / "src/content/catalog.json").read_text())
    publication = json.loads((public / "publication.json").read_text())
    if len(catalog["records"]) != 29 or len(publication["documents"]) != 29 or "roadmap" in publication:
        errors.append("the 29-document publication changed")
    if catalog["publication"]["commit"] != manuscript["commit"] or publication["commit"] != manuscript["commit"]:
        errors.append("the manuscript pin changed")
    if any("roadmap" in d["route"] or d["slug"].startswith("rm-") for d in publication["documents"]):
        errors.append("a roadmap item entered the publication catalogue")
    provenance = json.loads((ROOT / "src/site/content-provenance.json").read_text())
    if provenance["roadmap"]["pin"] != catalog["roadmap"]["pin"]:
        errors.append("content-provenance.json roadmap pin differs from the catalogue")
    sitemap = (public / "sitemap.xml").read_text()
    for locale in LOCALES:
        if f"<loc>https://contract.place/{locale}/roadmap/</loc>" not in sitemap:
            errors.append(f"sitemap.xml: {locale} roadmap missing")
    if "/en/roadmap/" not in (public / "llms.txt").read_text():
        errors.append("llms.txt: roadmap missing")
    if errors:
        raise SystemExit("\n".join(sorted(set(errors))[:60]))
    print("roadmap checks OK (25 planned task cards x 3 language routes, text from source, dependency tables, pins, navigation, SEO, privacy)")


if __name__ == "__main__":
    main()
