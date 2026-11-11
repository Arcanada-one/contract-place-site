#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Integrity tests for site-local daily journal issues."""
from __future__ import annotations

from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "src" / "content" / "journal"
MANIFEST = JOURNAL / "manifest.json"
SLUG = "lesson-without-evidence-2026-11-11"
FOLDER = "2026-11-11-lesson-without-evidence"
LANGS = ("en", "ru", "zh-Hans")
EXPECTED = {
    "en": "0ceb36b39e2ae5f16c92b81b27b98bd6ade9f3feb7d724a5ee05bb0e9abbe3e9",
    "ru": "34e68420285319ca847d516cf6eec8e75cdc9d2852f441b15b49a2fd60ed96ff",
    "zh-Hans": "70743391332427237afd8fe11810764283d6e9cc9b3cfa6d1fd0a1106377074c",
}


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)

    def text(self) -> str:
        return normalize_ws("".join(self.parts))


def html_text(html: str) -> str:
    parser = TextCollector()
    parser.feed(html)
    return parser.text()


def split_markdown(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", text, re.S)
    assert match, path
    meta = {}
    for line in match.group(1).splitlines():
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"')
    return meta, match.group(2)


def manuscript_blocks(body: str) -> list[str]:
    blocks: list[str] = []
    for raw in re.split(r"\n\s*\n", body.strip()):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("## "):
            blocks.append(normalize_ws(line[3:]))
        elif line.startswith("- "):
            for item in line.splitlines():
                blocks.append(normalize_ws(item[2:] if item.startswith("- ") else item))
        else:
            blocks.append(normalize_ws(line))
    return blocks


def assert_locale_page(lang: str) -> None:
    page = (ROOT / "public" / lang / "journal" / SLUG / "index.html").read_text(encoding="utf-8")
    meta, body = split_markdown(JOURNAL / FOLDER / f"{lang}.md")
    assert f'<html lang="{lang}">' in page, lang
    assert f"<title>{meta['title']} — contract.place</title>" in page, lang
    assert f'content="{meta["excerpt"]}"' in page, lang
    assert 'name="robots" content="noindex' not in page, lang + " must be indexable"
    assert 'datetime="2026-11-11"' in page, lang
    rendered = html_text(page)
    for block in manuscript_blocks(body):
        assert normalize_ws(block) in rendered, f"{lang}: missing {block[:100]}"
    if lang != "en":
        en_title = split_markdown(JOURNAL / FOLDER / "en.md")[0]["title"]
        assert en_title not in page, lang + " must not render the English title"
        en_heading = "Memory helps as long as you can go back to the source"
        assert en_heading not in rendered, lang + " must not render the English body"
    index = (ROOT / "public" / lang / "journal" / "index.html").read_text(encoding="utf-8")
    assert f"/journal/{SLUG}/" in index, lang + " index missing issue"
    assert "/journal/building-a-place/" in index, lang + " index missing building-a-place"
    assert index.find(f"/journal/{SLUG}/") < index.find("/journal/building-a-place/")
    sitemap = (ROOT / "public" / "sitemap.xml").read_text(encoding="utf-8")
    assert f"https://contract.place/{lang}/journal/{SLUG}/" in sitemap, lang


class JournalTests(unittest.TestCase):
    def test_manifest_records_expected_digests(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 1)
        issue = next(item for item in manifest["issues"] if item["slug"] == SLUG)
        self.assertEqual(issue["date"], "2026-11-11")
        self.assertEqual(issue["folder"], FOLDER)
        for lang in LANGS:
            recorded = issue["languages"][lang]["sha256"]
            self.assertEqual(recorded, EXPECTED[lang], lang)
            path = JOURNAL / FOLDER / issue["languages"][lang]["file"]
            self.assertEqual(digest(path), EXPECTED[lang], str(path))

    def test_compile_binds_manifest(self) -> None:
        from build_journal import compile_journal

        issues = compile_journal(ROOT)
        issue = next(item for item in issues if item["slug"] == SLUG)
        for lang in LANGS:
            self.assertEqual(issue["languages"][lang]["sha256"], EXPECTED[lang])
            self.assertTrue(issue["languages"][lang]["html"])
        catalog = json.loads((ROOT / "src/content/catalog.json").read_text(encoding="utf-8"))
        self.assertTrue(any(item["slug"] == SLUG for item in catalog.get("journal_issues", [])))

    def test_rendered_locale_pages(self) -> None:
        for lang in LANGS:
            assert_locale_page(lang)


def run_mutants() -> int:
    """Apply each required mutant and require the corresponding check to fail."""
    failures = 0

    # (a) one byte changed in a committed .md
    target = JOURNAL / FOLDER / "en.md"
    original = target.read_bytes()
    try:
        target.write_bytes(original + b"x")
        result = subprocess.run(
            ["python3", "-B", "scripts/build_journal.py"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print("MUTANT a FAILED TO FAIL: digest check accepted a changed byte")
            failures += 1
        else:
            print("MUTANT a OK: digest mismatch refused")
    finally:
        target.write_bytes(original)

    # (b) ru route rendering the English body
    page_path = ROOT / "public/ru/journal" / SLUG / "index.html"
    original_page = page_path.read_text(encoding="utf-8")
    catalog = json.loads((ROOT / "src/content/catalog.json").read_text(encoding="utf-8"))
    issue = next(item for item in catalog["journal_issues"] if item["slug"] == SLUG)
    english_html = issue["languages"]["en"]["html"]
    mutated = re.sub(
        r'(<div lang="ru" class="journal-body">).*?(</div>\s*<a class="text-link" href="/ru/journal/")',
        lambda m: m.group(1) + english_html + m.group(2),
        original_page,
        count=1,
        flags=re.S,
    )
    assert mutated != original_page
    try:
        page_path.write_text(mutated, encoding="utf-8")
        try:
            assert_locale_page("ru")
            print("MUTANT b FAILED TO FAIL: English body on /ru/ was accepted")
            failures += 1
        except AssertionError:
            print("MUTANT b OK: English body on /ru/ refused")
    finally:
        page_path.write_text(original_page, encoding="utf-8")

    # (c) article missing from the journal index
    index_path = ROOT / "public/en/journal/index.html"
    original_index = index_path.read_text(encoding="utf-8")
    mutated_index = original_index.replace(f"/journal/{SLUG}/", "/journal/not-present/")
    assert mutated_index != original_index
    try:
        index_path.write_text(mutated_index, encoding="utf-8")
        try:
            assert_locale_page("en")
            print("MUTANT c FAILED TO FAIL: missing index entry was accepted")
            failures += 1
        except AssertionError:
            print("MUTANT c OK: missing index entry refused")
    finally:
        index_path.write_text(original_index, encoding="utf-8")

    # (d) article route marked noindex
    en_page = ROOT / "public/en/journal" / SLUG / "index.html"
    original_en = en_page.read_text(encoding="utf-8")
    mutated_en = original_en.replace("</title>", '</title><meta name="robots" content="noindex,follow">', 1)
    assert mutated_en != original_en
    try:
        en_page.write_text(mutated_en, encoding="utf-8")
        try:
            assert_locale_page("en")
            print("MUTANT d FAILED TO FAIL: noindex article was accepted")
            failures += 1
        except AssertionError:
            print("MUTANT d OK: noindex article refused")
    finally:
        en_page.write_text(original_en, encoding="utf-8")

    return failures


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--mutants":
        raise SystemExit(run_mutants())
    unittest.main()
