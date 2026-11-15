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
from html import unescape
from html.parser import HTMLParser
import json
from pathlib import Path
import re

import roadmap
import roadmap_localization

ROOT = Path(__file__).resolve().parents[1]
LOCALES = {"en": "Planned", "ru": "Запланировано", "zh-Hans": "计划中"}
NAV = {"en": "Roadmap", "ru": "Дорожная карта", "zh-Hans": "路线图"}
NOTICE = {
    "en": "The roadmap sources and their revisions are listed below.",
    "ru": "Источники дорожной карты и их версии перечислены ниже.",
    "zh-Hans": "路线图来源及其版本列于下方。",
}
LEGACY_NOTICE = {
    "en": "The roadmap text is English on every language route",
    "ru": "Текст дорожной карты на всех языковых маршрутах английский",
    "zh-Hans": "所有语言路线下的路线图正文均为英文",
}


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


def source_tokens(text: str, cache: dict[str, list[str]]) -> list[str]:
    """Render source Markdown independently of the compiled catalogue.

    In Chinese, joining text nodes around a link differs from deleting Markdown
    delimiters in a string. Parse both sides as HTML so adjacent source words
    have the same token boundary convention. No translation or alias rewrite
    is performed here.
    """
    if text not in cache:
        html = roadmap.run(["pandoc", "--from=" + roadmap.PANDOC_FROM,
                            "--to=html5", "--mathml", "--no-highlight", "--wrap=none"], text)
        cache[text] = tokens(" ".join(Page(html).text))
    return cache[text]


def expected_locale(locale: str, cards: dict, nodes: dict, intro: str,
                    overview: str, preamble: str, translations: dict) -> dict:
    """Expected prose comes from raw pinned locale files, never compiled HTML."""
    if locale in translations:
        raw = translations[locale]
        localized = {card["id"]: card for card in raw["tasks"]}
        if len(localized) != len(raw["tasks"]) or set(localized) != set(cards):
            raise ValueError(locale + ": source translations must contain every task exactly once")
        expected = {}
        for ident, source in cards.items():
            card = localized[ident]
            if set(card["fields"]) != set(source["fields"]) - {"start"}:
                raise ValueError(locale + "/" + ident + ": source translation fields differ from the original")
            expected[ident] = {**source, "title": card["title"],
                               "fields": {**card["fields"], "start": raw["start"]}}
        return {"cards": expected, "names": {ident: card["display_name"] for ident, card in localized.items()},
                "intro": raw["introduction"], "overview": raw["overview"], "preamble": raw["tasks_intro"],
                "language": locale, "execution": roadmap_localization.EXECUTION[locale],
                "priorities": roadmap_localization.PRIORITIES[locale]}
    names = {}
    for ident, card in cards.items():
        short, separator, _ = card["title"].partition(": ")
        name = nodes[ident].get("display_name") or (short if separator else card["title"])
        names[ident] = (nodes[ident].get("display_name_ru") or name) if locale == "ru" else name
    return {"cards": cards, "names": names, "intro": intro, "overview": overview, "preamble": preamble,
            "language": "en", "execution": roadmap.EXECUTION_BINDINGS, "priorities": roadmap.PRIORITY_LABELS}


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
    task_source = (source / "roadmap/TASKS.md").read_text(encoding="utf-8")
    cards = roadmap.split_cards(task_source)
    intro = roadmap.extract_introduction((source / "roadmap/SITE_DELIVERY.md").read_text())
    overview = (source / "ROADMAP.md").read_text()
    preamble = roadmap.tasks_preamble(task_source)
    loaded = roadmap_localization.read_sources(source, pin)
    translations = loaded[1] if loaded is not None else {}
    expected_cache: dict[str, list[str]] = {}
    if sorted(cards) != roadmap.TASK_IDS or sorted(nodes) != roadmap.TASK_IDS:
        raise SystemExit("Source does not define exactly RM-01..RM-25")

    for locale, planned in LOCALES.items():
        expected = expected_locale(locale, cards, nodes, intro, overview, preamble, translations)
        shown_cards, names = expected["cards"], expected["names"]
        if len(set(names.values())) != len(names):
            raise SystemExit(locale + ": duplicate locale task names")
        # Only names of the current locale resolve. A Russian or Chinese route
        # must not accidentally pass because an English alias was accepted.
        name_to_id = {name: ident for ident, name in names.items()}
        localized = locale in translations
        content_language = expected["language"]
        locale_overview = re.sub(r"\A---\n.*?\n---\n", "", expected["overview"], count=1, flags=re.S)
        locale_overview = roadmap.strip_editorial_markers(locale_overview)
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
        if not contains(stream, source_tokens(expected["intro"], expected_cache)):
            errors.append(where + "public introduction from the source is missing")
        for ident, card in shown_cards.items():
            rendered = re.findall(r'<article\b[^>]*\bid="' + re.escape(ident.lower()) + r'"[^>]*>(.*?)</article>', html, re.S)
            if len(rendered) != 1:
                errors.append(where + f"{ident}: cannot isolate the single task card")
                continue
            card_stream = tokens(" ".join(Page(rendered[0]).text))
            field_block = re.findall(r'<dl\b[^>]*\bclass="roadmap-fields"[^>]*>(.*?)</dl>', rendered[0], re.S)
            fields_html = re.findall(r"<dd\b[^>]*>(.*?)</dd>", field_block[0], re.S) if len(field_block) == 1 else []
            keys = [key for key, _ in roadmap.FIELD_ORDERS[1] if key in card["fields"]]
            if len(fields_html) != len(keys):
                errors.append(where + f"{ident}: field count differs from the complete source")
            if not re.search(r'<dl\b[^>]*\bclass="roadmap-fields"[^>]*\blang="' + re.escape(content_language) + r'"', rendered[0]):
                errors.append(where + f"{ident}: field language must be {content_language}")
            for key, label in roadmap.FIELD_ORDERS[1]:
                if key not in card["fields"]:
                    continue
                index = keys.index(key)
                if index >= len(fields_html):
                    continue
                actual_tokens = tokens(" ".join(Page(fields_html[index]).text))
                wanted_tokens = source_tokens(card["fields"][key], expected_cache)
                # Source prose comes first; any appended source-status links
                # follow it. A copy elsewhere on the page cannot fill this gap.
                if not wanted_tokens or actual_tokens[:len(wanted_tokens)] != wanted_tokens:
                    errors.append(where + f"{ident} {label}: complete locale source text missing from its field")
            short, sep, subtitle = card["title"].partition(": ")
            if not contains(card_stream, tokens(names[ident])):
                errors.append(where + f"{ident}: display name missing")
            if sep and subtitle and not contains(card_stream, tokens(subtitle)):
                errors.append(where + f"{ident}: title subtitle missing")
        # The TASKS.md preamble (authorship and scope statements) is rendered above the cards.
        for block in re.split(r"\n\s*\n", expected["preamble"]):
            block = block.strip()
            if block and not block.startswith("#") and not contains(stream, source_tokens(block, expected_cache)):
                errors.append(where + f"TASKS.md preamble paragraph missing: {block[:60]!r}")
        # The rendered execution-state text must be exactly the one known value (no status can ride in this field).
        shown = re.findall(r'<p lang="' + re.escape(content_language) + r'"><strong>[^<]*:</strong> ([^<]*)</p>', html)
        if [unescape(x) for x in shown] != [expected["execution"]]:
            errors.append(where + f"execution-state text must be exactly {expected['execution']!r} (found {shown})")
        # Every ROADMAP.md paragraph and list item is present (the page renders the document in full).
        for block in re.split(r"\n\s*\n", locale_overview):
            block = block.strip()
            if not block or block.startswith(("#", "|", "```")) or block.startswith("**A bounded"):
                continue
            if not contains(stream, source_tokens(block, expected_cache)):
                errors.append(where + f"overview text missing: {block[:60]!r}")
        # Dependency table equals dependencies.json, both directions and advisory links.
        deptable = next((t for t in page.tables if t and t[0] and t[0][0] == {"en": "Task", "ru": "Задача", "zh-Hans": "任务"}[locale]), None)
        if not deptable or len(deptable) != 26:
            errors.append(where + "dependency table missing or incomplete")
        else:
            needed = {i: sorted(n["id"] for n in nodes.values() if i in n["requires"]) for i in nodes}
            def resolve_names(cell):
                if cell == {"en": "none", "ru": "нет", "zh-Hans": "无"}[locale]:
                    return []
                out = []
                for part in [x.strip() for x in cell.split(",")]:
                    if part in name_to_id:
                        out.append(name_to_id[part])
                    elif not localized and re.fullmatch(r"RM-\d\d", part):
                        out.append(part)
                    else:
                        raise ValueError(part)
                return out
            for row in deptable[1:]:
                label = row[0].strip()
                ident = name_to_id.get(label) or (label.split()[0] if not localized and re.match(r"RM-\d\d", label) else None)
                if ident not in nodes:
                    errors.append(where + f"unknown dependency-table task label: {label!r}")
                    continue
                try:
                    got = resolve_names(row[4])
                    got_needed = resolve_names(row[5])
                except ValueError as err:
                    errors.append(where + f"{ident}: unresolved dependency name {err}")
                    continue
                if sorted(got) != sorted(nodes[ident]["requires"]) or sorted(got_needed) != needed[ident]:
                    errors.append(where + f"{ident}: dependency row differs from dependencies.json")
                expected_priority = expected["priorities"].get(nodes[ident]["priority"], nodes[ident]["priority"])
                if row[1] not in {nodes[ident]["priority"], expected_priority} or row[2] != nodes[ident]["content_owner"]:
                    errors.append(where + f"{ident}: priority or owner differs from dependencies.json")
        advisory = [t for t in page.tables if t and t[0] and t[0][-1] in {"Relation", "Связь", "关系"}]
        if len(advisory) != 1:
            errors.append(where + "advisory link table differs from dependencies.json")
        else:
            def adv_id(label):
                return name_to_id.get(label) or (label if not localized and re.fullmatch(r"RM-\d\d", label) else None)
            got_adv = [(adv_id(r[0]), adv_id(r[1])) for r in advisory[0][1:]]
            if any(None in pair for pair in got_adv) or sorted(got_adv) != sorted((a["from"], a["to"]) for a in deps["advisory_links"]):
                errors.append(where + "advisory link table differs from dependencies.json")
        for needle in (pin["commit"], manuscript["commit"]):
            if needle not in html:
                errors.append(where + f"missing {needle[:40]}")
        if NOTICE[locale] not in html and (translations or LEGACY_NOTICE[locale] not in html):
            errors.append(where + "source/revision notice missing")
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
    if len(catalog["records"]) != 31 or len(publication["documents"]) != 31 or "roadmap" in publication:
        errors.append("the 31-document publication changed")
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
