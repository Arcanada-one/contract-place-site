#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Integrity tests for site-local daily journal issues.

Generic checks walk every issue in src/content/journal/manifest.json.
The 2026-11-11 digests remain a separate regression pin.
Run `python3 -B scripts/test_journal.py --mutants` for the honest mutant harness.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from html.parser import HTMLParser
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[1]
JOURNAL = ROOT / "src" / "content" / "journal"
MANIFEST = JOURNAL / "manifest.json"
LANGS = ("en", "ru", "zh-Hans")
PIN_SLUG = "lesson-without-evidence-2026-11-11"
PIN_FOLDER = "2026-11-11-lesson-without-evidence"
PIN_DATE = "2026-11-11"
PIN_EXPECTED = {
    "en": "93bb988845e15bbf6f708b435975afbee7353bbeec2f0fbd5137508072f3dccd",
    "ru": "8987f7313dd5f15639fbe9583b0a6d3028b386c092917cbe8063a14a3807d029",
    "zh-Hans": "6ce4154acbf3f900732f2eb0772d307c421b22e46d74dcfbcc341bb4aefc2d83",
}
FORBIDDEN_SOURCE_HEADINGS = {"sources", "источники", "参考文献", "来源"}
HEADING_TAG = re.compile(r"<h([2-4])\b[^>]*>(.*?)</h\1>", re.I | re.S)
SYNTH_SLUG = "synthetic-probe-2099-06-01"
SYNTH_FOLDER = "2099-06-01-synthetic-probe"
SYNTH_DATE = "2099-06-01"
TMP_SITE_NAME = ".tmp-journal-mutants"


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0
        self.cells: list[str] = []
        self._cell_parts: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self._skip += 1
        if tag in {"th", "td"} and not self._skip:
            self._cell_parts.append([])

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self._skip:
            self._skip -= 1
        if tag in {"th", "td"} and self._cell_parts and not self._skip:
            self.cells.append(normalize_ws("".join(self._cell_parts.pop())))

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)
            for cell in self._cell_parts:
                cell.append(data)

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


@lru_cache(maxsize=128)
def manuscript_ast(body: str) -> dict:
    """Independent oracle: pinned Markdown reader, never the HTML writer under test.

    Cache by source text, not path, so source mutations cannot reuse old evidence.
    Missing/wrong Pandoc is an error; there is no hand-stripped Markdown fallback.
    """
    version = subprocess.run(["pandoc", "--version"], text=True, capture_output=True, check=True)
    assert version.stdout.splitlines()[0] == "pandoc 3.1.3", "Expected Pandoc 3.1.3 for journal text oracle"
    parsed = subprocess.run(
        ["pandoc", "--from=markdown+gfm_auto_identifiers+autolink_bare_uris-smart", "--to=json"],
        input=body, text=True, capture_output=True, check=True,
    )
    document = json.loads(parsed.stdout)
    assert isinstance(document.get("blocks"), list), "Invalid Pandoc journal AST"
    return document


def ast_nodes(value):
    if isinstance(value, dict):
        if "t" in value:
            yield value
        yield from ast_nodes(value.get("c"))
    elif isinstance(value, list):
        for item in value:
            yield from ast_nodes(item)


def inline_text(inlines: list[dict]) -> str:
    parts = []
    for node in inlines:
        kind, value = node["t"], node.get("c")
        if kind == "Str":
            parts.append(value)
        elif kind in {"Space", "SoftBreak", "LineBreak"}:
            parts.append(" ")
        elif kind in {"Emph", "Strong", "Underline", "Strikeout", "Superscript", "Subscript", "SmallCaps"}:
            parts.append(inline_text(value))
        elif kind == "Code":
            parts.append(value[1])
        elif kind in {"Span", "Cite"}:
            parts.append(inline_text(value[1]))
        elif kind == "Link":
            label, target = inline_text(value[1]), value[2][0]
            # The current journal decorator intentionally renders non-https
            # targets (including relative paths) as literal [label](target).
            parts.append(label if target.startswith("https://") else f"[{label}]({target})")
        elif kind == "Quoted":
            left, right = ("‘", "’") if value[0]["t"] == "SingleQuote" else ("“", "”")
            parts.append(left + inline_text(value[1]) + right)
        else:
            raise AssertionError(f"Journal text oracle does not support inline node {kind}")
    return "".join(parts)


def ast_blocks(value) -> list[str]:
    blocks = []
    for node in ast_nodes(value):
        kind, content = node["t"], node.get("c")
        if kind in {"Para", "Plain"}:
            blocks.append(inline_text(content))
        elif kind == "Header":
            blocks.append(inline_text(content[2]))
        elif kind == "CodeBlock":
            blocks.append(content[1])
        elif kind == "LineBlock":
            blocks.extend(inline_text(line) for line in content)
        elif kind == "DefinitionList":
            blocks.extend(inline_text(term) for term, _ in content)
        elif kind == "RawBlock":
            raise AssertionError("Journal text oracle does not support raw blocks")
    return [normalize_ws(block) for block in blocks if normalize_ws(block)]


def manuscript_https_links(body: str) -> list[tuple[str, str]]:
    return [
        (inline_text(node["c"][1]), node["c"][2][0])
        for node in ast_nodes(manuscript_ast(body)["blocks"])
        if node["t"] == "Link" and node["c"][2][0].startswith("https://")
    ]


def manuscript_blocks(body: str) -> list[str]:
    return ast_blocks(manuscript_ast(body)["blocks"])


def manuscript_cells(body: str) -> list[str]:
    cells = []
    for node in ast_nodes(manuscript_ast(body)["blocks"]):
        if node["t"] != "Table":
            continue
        # Pandoc Table = [attr, caption, colspecs, head, bodies, foot].
        # Row = [attr, cells]; Cell = [attr, alignment, rowspan, colspan, blocks].
        _, _, _, head, bodies, foot = node["c"]
        rows = list(head[1])
        for table_body in bodies:
            rows.extend(table_body[2])
            rows.extend(table_body[3])
        rows.extend(foot[1])
        for row in rows:
            cells.extend(normalize_ws(" ".join(ast_blocks(cell[4]))) for cell in row[1])
    return cells


def heading_text(html: str) -> str:
    return normalize_ws(re.sub(r"<[^>]+>", "", html))


class AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href is not None:
                self._href = href
                self._parts = []

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            self.links.append((self._href, normalize_ws("".join(self._parts))))
            self._href = None
            self._parts = []

    def handle_data(self, data):
        if self._href is not None:
            self._parts.append(data)


def assert_manuscript_content(body: str, page: str, label: str) -> None:
    collector = TextCollector()
    collector.feed(page)
    rendered = collector.text()
    actual_cells = Counter(collector.cells)
    # Count cells separately: a repeated number elsewhere in the article must
    # not conceal a deleted table cell or a changed value.
    for cell, count in Counter(manuscript_cells(body)).items():
        assert actual_cells[cell] >= count, f"{label}: missing table cell {cell[:100]}"
    for block in manuscript_blocks(body):
        assert block in rendered, f"{label}: missing {block[:100]}"
    anchors = AnchorCollector()
    anchors.feed(page)
    rendered_links = Counter(anchors.links)
    expected_links = Counter((href, normalize_ws(text)) for text, href in manuscript_https_links(body))
    for link, count in expected_links.items():
        assert rendered_links[link] >= count, f"{label}: missing rendered link {link[0]}"


def body_marker(body: str) -> str:
    """First manuscript paragraph/heading — locale identity without hard-coded prose."""
    blocks = manuscript_blocks(body)
    assert blocks, "manuscript body has no marker block"
    return blocks[0]


def load_manifest(path: Path = MANIFEST) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def assert_locale_page(
    issue: dict,
    lang: str,
    *,
    public_root: Path = ROOT / "public",
    journal_root: Path = JOURNAL,
) -> None:
    slug = issue["slug"]
    folder = issue["folder"]
    date = issue["date"]
    label = f"{slug}/{lang}"
    page_path = public_root / lang / "journal" / slug / "index.html"
    assert page_path.is_file(), f"{label}: missing built page"
    page = page_path.read_text(encoding="utf-8")
    meta, body = split_markdown(journal_root / folder / f"{lang}.md")
    assert f'<html lang="{lang}">' in page, f"{label}: html lang mismatch"
    assert f"<title>{meta['title']} — contract.place</title>" in page, f"{label}: title mismatch"
    assert f'content="{meta["excerpt"]}"' in page, f"{label}: excerpt mismatch"
    assert 'name="robots" content="noindex' not in page, f"{label}: page must be indexable"
    assert f'datetime="{date}"' in page, f"{label}: date mismatch"
    rendered = html_text(page)
    # Cross-locale leak checks run before this locale's body markers so a swapped
    # English body is refused as a locale identity failure, not a generic missing block.
    if lang != "en":
        en_meta, en_body = split_markdown(journal_root / folder / "en.md")
        en_marker = body_marker(en_body)
        assert en_meta["title"] not in page, f"{label}: English title on wrong locale page"
        assert en_marker not in rendered, f"{label}: English body on wrong locale page"
    marker = body_marker(body)
    assert marker in rendered, f"{label}: missing body marker from manuscript"
    assert_manuscript_content(body, page, label)
    for match in HEADING_TAG.finditer(page):
        title = heading_text(match.group(2))
        assert title.casefold() not in FORBIDDEN_SOURCE_HEADINGS, (
            f"{label}: forbidden sources heading"
        )
    index = (public_root / lang / "journal" / "index.html").read_text(encoding="utf-8")
    assert f"/journal/{slug}/" in index, f"{label}: missing from journal index"
    assert "/journal/building-a-place/" in index, f"{label}: index missing building-a-place"
    assert index.find(f"/journal/{slug}/") < index.find("/journal/building-a-place/")
    sitemap = (public_root / "sitemap.xml").read_text(encoding="utf-8")
    assert f"https://contract.place/{lang}/journal/{slug}/" in sitemap, f"{label}: missing from sitemap"


def assert_all_manifest_issues(
    *,
    manifest_path: Path = MANIFEST,
    public_root: Path = ROOT / "public",
    journal_root: Path = JOURNAL,
) -> None:
    manifest = load_manifest(manifest_path)
    assert manifest.get("schema_version") == 1
    assert isinstance(manifest.get("issues"), list) and manifest["issues"]
    for issue in manifest["issues"]:
        for lang in LANGS:
            assert_locale_page(issue, lang, public_root=public_root, journal_root=journal_root)


class JournalTests(unittest.TestCase):
    def test_ast_oracle_emphasis_and_relative_link_labels(self) -> None:
        body = (
            "## *Heading*\n\n**Correction**: Read [*the follow-up*](/en/journal/follow-up/) "
            "and [**primary source**](https://example.org/source).\n"
        )
        # Authored expected HTML is independent of the HTML writer/helper.
        # Relative links retain the decorator's existing visible-literal policy.
        page = (
            '<h2><em>Heading</em></h2>\n<p><strong>Correction</strong>: Read '
            '[the follow-up](/en/journal/follow-up/) and '
            '<a href="https://example.org/source"><strong>primary source</strong></a>.</p>'
        )
        self.assertEqual(manuscript_blocks(body), [
            "Heading", "Correction: Read [the follow-up](/en/journal/follow-up/) and primary source.",
        ])
        self.assertEqual(manuscript_https_links(body), [("primary source", "https://example.org/source")])
        assert_manuscript_content(body, page, "fixture/en")
        flattened = page.replace('<a href="https://example.org/source"><strong>primary source</strong></a>',
                                 '<strong>primary source</strong>')
        with self.assertRaisesRegex(AssertionError, "missing rendered link https://example.org/source"):
            assert_manuscript_content(body, flattened, "fixture/en")

    def test_ast_oracle_refuses_changed_or_deleted_table_cell_despite_repeated_values(self) -> None:
        body = (
            "The value 23 also appears outside the table.\n\n"
            "| Rule | Unknown |\n| --- | --- |\n| alpha | 23 |\n| beta | 23 |\n"
        )
        page = (
            '<p>The value 23 also appears outside the table.</p>\n<table>'
            '<thead><tr><th>Rule</th><th>Unknown</th></tr></thead><tbody>'
            '<tr><td>alpha</td><td>23</td></tr><tr><td>beta</td><td>23</td></tr>'
            '</tbody></table>'
        )
        self.assertEqual(manuscript_cells(body), ["Rule", "Unknown", "alpha", "23", "beta", "23"])
        assert_manuscript_content(body, page, "fixture/en")
        for replacement in ("<td>24</td>", ""):
            with self.subTest(replacement=replacement), self.assertRaisesRegex(AssertionError, "missing table cell 23"):
                assert_manuscript_content(body, page.replace("<td>23</td>", replacement, 1), "fixture/en")

    def test_pin_2026_11_11_hash_regressions(self) -> None:
        """Fixed digests for the live 2026-11-11 issue — regression pin, not the generic check."""
        manifest = load_manifest()
        issue = next(item for item in manifest["issues"] if item["slug"] == PIN_SLUG)
        self.assertEqual(issue["date"], PIN_DATE)
        self.assertEqual(issue["folder"], PIN_FOLDER)
        for lang in LANGS:
            recorded = issue["languages"][lang]["sha256"]
            self.assertEqual(recorded, PIN_EXPECTED[lang], lang)
            path = JOURNAL / PIN_FOLDER / issue["languages"][lang]["file"]
            self.assertEqual(digest(path), PIN_EXPECTED[lang], str(path))

    def test_compile_binds_manifest(self) -> None:
        from build_journal import compile_journal

        issues = compile_journal(ROOT)
        issue = next(item for item in issues if item["slug"] == PIN_SLUG)
        for lang in LANGS:
            self.assertEqual(issue["languages"][lang]["sha256"], PIN_EXPECTED[lang])
            self.assertTrue(issue["languages"][lang]["html"])
        catalog = json.loads((ROOT / "src/content/catalog.json").read_text(encoding="utf-8"))
        self.assertTrue(any(item["slug"] == PIN_SLUG for item in catalog.get("journal_issues", [])))

    def test_journal_content_cache_identity(self) -> None:
        """Journal edits change the catalog cache key without changing the source pin."""
        def assert_html_identity(html: str, expected: str, label: str) -> None:
            urls = re.findall(r'src="(/content\.js(?:\?[^"]*)?)"', html)
            self.assertEqual(urls, ["/content.js?v=" + expected], label)

        def assert_public_identity(public_root: Path) -> tuple[bytes, str]:
            content = (public_root / "content.js").read_bytes()
            expected = sha256(content).hexdigest()
            pages = list(public_root.rglob("*.html"))
            self.assertTrue(pages, "No generated HTML pages")
            for page in pages:
                assert_html_identity(page.read_text(encoding="utf-8"), expected, str(page))
            return content, expected

        _, baseline_hash = assert_public_identity(ROOT / "public")
        source_manifest = (ROOT / "publication-manifest.json").read_bytes()
        source_pin = json.loads(source_manifest)["commit"]

        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory) / "site"
            public_root, _, _ = prepare_temp_site(site)
            self.assertEqual((site / "publication-manifest.json").read_bytes(), source_manifest)
            changed_content, changed_hash = assert_public_identity(public_root)
            self.assertNotEqual(changed_hash, baseline_hash, "New journal issue reused the old cache key")
            self.assertNotEqual(changed_hash, source_pin)
            for lang in LANGS:
                self.assertTrue((public_root / lang / "journal" / SYNTH_SLUG / "index.html").is_file())

            # A source-pin-only URL is stale even when the manuscript revision is correct.
            home = (public_root / "en" / "index.html").read_text(encoding="utf-8")
            stale = home.replace("/content.js?v=" + changed_hash, "/content.js?v=" + source_pin)
            self.assertNotEqual(stale, home)
            with self.assertRaises(AssertionError):
                assert_html_identity(stale, changed_hash, "old source-pin cache key")

            result = subprocess.run(
                ["node", "build.mjs"], cwd=site, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            rebuilt_content, rebuilt_hash = assert_public_identity(public_root)
            self.assertEqual(rebuilt_content, changed_content, "Unchanged inputs changed catalog bytes")
            self.assertEqual(rebuilt_hash, changed_hash)
            self.assertEqual((site / "publication-manifest.json").read_bytes(), source_manifest)

    def test_rendered_locale_pages_for_every_issue(self) -> None:
        assert_all_manifest_issues()

    def test_native_compiled_journal_tables_preserve_semantics_without_inline_style(self) -> None:
        from build_journal import compile_journal

        # A long row makes pinned Pandoc emit col widths; equal-width separators
        # also exercise all three alignments without relying on hand-made HTML.
        body = (
            "| Rule | Known | Unknown | Result |\n"
            "| :---- | ----: | :---: | ----- |\n"
            "| Verification | 9/10 | 23 | Not established under the study's threshold; "
            "retain the unknown cases and [Source](https://example.org/evidence). |\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            site = Path(directory)
            journal = site / "src/content/journal"
            folder = journal / "2026-11-16-table-fixture"
            folder.mkdir(parents=True)
            languages = {}
            for lang in LANGS:
                content = (
                    "---\nsite: contract.place\nsection: journal\n"
                    "slug: table-fixture\ndate: 2026-11-16\n"
                    f"lang: {lang}\ntitle: Table fixture {lang}\nexcerpt: Table evidence {lang}\n"
                    "---\n\n" + body
                )
                path = folder / f"{lang}.md"
                path.write_text(content, encoding="utf-8")
                languages[lang] = {"file": path.name, "sha256": digest(path)}
            manifest = {"schema_version": 1, "issues": [{
                "slug": "table-fixture", "date": "2026-11-16",
                "folder": folder.name, "languages": languages,
            }]}
            (journal / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            compiled = compile_journal(site)
            self.assertEqual(len(compiled), 1)
            for lang in LANGS:
                with self.subTest(lang=lang):
                    html = compiled[0]["languages"][lang]["html"]
                    self.assertIn("<table>", html)
                    self.assertIn("<colgroup>", html)
                    self.assertIn("<thead>", html)
                    self.assertIn("<tbody>", html)
                    self.assertRegex(html, r'class="table-width-[0-9]+"')
                    for alignment in ("left", "right", "center"):
                        self.assertIn(f'table-align-{alignment}', html)
                    visible = html_text(html)
                    for value in ("Rule", "Known", "Unknown", "Result", "Verification", "9/10", "23"):
                        self.assertIn(value, visible)
                    self.assertIn("Not established under the study's threshold", visible)
                    self.assertIn('<a href="https://example.org/evidence" rel="noopener noreferrer">Source</a>', html)
                    self.assertNotRegex(html, r"\bstyle\s*=")

    def test_native_journal_unsupported_table_css_is_refused(self) -> None:
        from build_journal import render_body, require_pandoc

        require_pandoc()
        for cell in (
            '<td style="background:url(https://example.org/track)">Cell</td>',
            '<td style="text-align: left; display:none;">Cell</td>',
            '<td style="width: 25%">Cell</td>',
        ):
            with self.subTest(cell=cell), self.assertRaisesRegex(ValueError, "Unsupported inline table style from renderer"):
                render_body("<table><tbody><tr>" + cell + "</tr></tbody></table>")


@dataclass
class MutantOutcome:
    name: str
    expected_refusal: str
    observed_refusal: str
    verdict: str  # KILLED | SURVIVED | INFRA_ERROR


def _print_outcome(outcome: MutantOutcome) -> None:
    print(
        f"MUTANT {outcome.name}: expected={outcome.expected_refusal!r} "
        f"observed={outcome.observed_refusal!r} verdict={outcome.verdict}"
    )


def _refusal_from_exc(exc: BaseException) -> str:
    return str(exc).strip() or type(exc).__name__


def _subprocess_refusal(result: subprocess.CompletedProcess[str]) -> str:
    text = (result.stderr or result.stdout or "").strip()
    if not text:
        return f"exit:{result.returncode}"
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else f"exit:{result.returncode}"


_INFRA_MARKERS = (
    "No such file or directory",
    "not found",
    "MODULE_NOT_FOUND",
    "Cannot find module",
    "pandoc: command not found",
    "missing script:",
)


def _looks_like_infra(observed: str) -> bool:
    lower = observed.lower()
    return any(marker.lower() in lower for marker in _INFRA_MARKERS)


def run_subprocess_mutant(
    name: str,
    expected_refusal: str,
    *,
    baseline_cmd: list[str],
    mutate: Callable[[], None],
    probe_cmd: list[str],
    restore: Callable[[], None],
    mutation_target: Path,
    env: dict[str, str] | None = None,
    cwd: Path = ROOT,
) -> MutantOutcome:
    run_env = {**os.environ, **(env or {})}

    def run_cmd(cmd: list[str]) -> subprocess.CompletedProcess[str]:
        if cmd[0] == "python3" and len(cmd) >= 3 and cmd[2].endswith(".py"):
            script = Path(cmd[2]) if Path(cmd[2]).is_absolute() else cwd / cmd[2]
            if not script.is_file():
                raise FileNotFoundError(f"missing script: {script}")
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=run_env)

    def baseline() -> None:
        result = run_cmd(baseline_cmd)
        if result.returncode != 0:
            raise RuntimeError(_subprocess_refusal(result) or f"exit:{result.returncode}")

    try:
        baseline()
    except FileNotFoundError as exc:
        outcome = MutantOutcome(name, expected_refusal, f"infra: {_refusal_from_exc(exc)}", "INFRA_ERROR")
        _print_outcome(outcome)
        return outcome
    except BaseException as exc:
        outcome = MutantOutcome(name, expected_refusal, f"baseline-before: {_refusal_from_exc(exc)}", "INFRA_ERROR")
        _print_outcome(outcome)
        return outcome

    if not mutation_target.is_file():
        outcome = MutantOutcome(name, expected_refusal, f"infra: missing mutation target {mutation_target}", "INFRA_ERROR")
        _print_outcome(outcome)
        return outcome
    before = digest(mutation_target)
    try:
        mutate()
        after = digest(mutation_target)
        if before == after:
            outcome = MutantOutcome(name, expected_refusal, "mutation-not-applied: digest unchanged", "INFRA_ERROR")
            _print_outcome(outcome)
        else:
            result = run_cmd(probe_cmd)
            if result.returncode == 0:
                outcome = MutantOutcome(name, expected_refusal, "accepted", "SURVIVED")
            else:
                observed = _subprocess_refusal(result)
                if expected_refusal in observed:
                    outcome = MutantOutcome(name, expected_refusal, observed, "KILLED")
                elif _looks_like_infra(observed):
                    outcome = MutantOutcome(name, expected_refusal, f"infra: {observed}", "INFRA_ERROR")
                else:
                    outcome = MutantOutcome(
                        name, expected_refusal, f"infra: unexpected refusal: {observed}", "INFRA_ERROR"
                    )
            _print_outcome(outcome)
    except FileNotFoundError as exc:
        outcome = MutantOutcome(name, expected_refusal, f"infra: {_refusal_from_exc(exc)}", "INFRA_ERROR")
        _print_outcome(outcome)
    except BaseException as exc:
        outcome = MutantOutcome(name, expected_refusal, f"infra: {_refusal_from_exc(exc)}", "INFRA_ERROR")
        _print_outcome(outcome)
    try:
        restore()
        baseline()
    except BaseException as exc:
        outcome = MutantOutcome(name, expected_refusal, f"baseline-after: {_refusal_from_exc(exc)}", "INFRA_ERROR")
        _print_outcome(outcome)
    return outcome


def run_assertion_mutant(
    name: str,
    expected_refusal: str,
    *,
    baseline: Callable[[], None],
    mutate: Callable[[], None],
    probe: Callable[[], None],
    restore: Callable[[], None],
    mutation_target: Path,
) -> MutantOutcome:
    try:
        baseline()
    except BaseException as exc:
        outcome = MutantOutcome(name, expected_refusal, f"baseline-before: {_refusal_from_exc(exc)}", "INFRA_ERROR")
        _print_outcome(outcome)
        return outcome

    if not mutation_target.is_file():
        outcome = MutantOutcome(name, expected_refusal, f"infra: missing mutation target {mutation_target}", "INFRA_ERROR")
        _print_outcome(outcome)
        return outcome
    before = digest(mutation_target)
    try:
        mutate()
        after = digest(mutation_target)
        if before == after:
            outcome = MutantOutcome(name, expected_refusal, "mutation-not-applied: digest unchanged", "INFRA_ERROR")
            _print_outcome(outcome)
        else:
            try:
                probe()
                outcome = MutantOutcome(name, expected_refusal, "accepted", "SURVIVED")
                _print_outcome(outcome)
            except AssertionError as exc:
                observed = _refusal_from_exc(exc)
                verdict = "KILLED" if expected_refusal in observed else "SURVIVED"
                outcome = MutantOutcome(name, expected_refusal, observed, verdict)
                _print_outcome(outcome)
            except BaseException as exc:
                outcome = MutantOutcome(name, expected_refusal, f"infra: {_refusal_from_exc(exc)}", "INFRA_ERROR")
                _print_outcome(outcome)
    except BaseException as exc:
        outcome = MutantOutcome(name, expected_refusal, f"infra: {_refusal_from_exc(exc)}", "INFRA_ERROR")
        _print_outcome(outcome)
    try:
        restore()
        baseline()
    except BaseException as exc:
        outcome = MutantOutcome(name, expected_refusal, f"baseline-after: {_refusal_from_exc(exc)}", "INFRA_ERROR")
        _print_outcome(outcome)
    return outcome


def synthetic_markdown(lang: str, title: str, excerpt: str, body: str) -> str:
    return (
        "---\n"
        "site: contract.place\n"
        "section: journal\n"
        f"slug: {SYNTH_SLUG}\n"
        f"date: {SYNTH_DATE}\n"
        f"lang: {lang}\n"
        f'title: "{title}"\n'
        f'excerpt: "{excerpt}"\n'
        "---\n\n"
        f"{body}\n"
    )


def write_synthetic_issue(journal_root: Path) -> dict:
    folder = journal_root / SYNTH_FOLDER
    folder.mkdir(parents=True, exist_ok=True)
    files = {
        "en": synthetic_markdown(
            "en",
            "Synthetic probe issue for journal checks",
            "Temporary second issue used only inside the mutant harness.",
            "SYNTHETIC_EN_MARKER_ALPHA unique English probe paragraph for journal mutant coverage.\n\n"
            "## Synthetic English section\n\n"
            "Second English paragraph stays locale-specific.",
        ),
        "ru": synthetic_markdown(
            "ru",
            "Синтетический выпуск для проверок журнала",
            "Временный второй выпуск только для мутантного стенда.",
            "SYNTHETIC_RU_MARKER_BETA уникальный русский абзац для проверки мутантов журнала.\n\n"
            "## Синтетический русский раздел\n\n"
            "Второй русский абзац остаётся привязанным к локали.",
        ),
        "zh-Hans": synthetic_markdown(
            "zh-Hans",
            "用于期刊检查的合成期号",
            "仅用于突变体支架的临时第二期。",
            "SYNTHETIC_ZH_MARKER_GAMMA 用于期刊突变体覆盖的唯一中文段落。\n\n"
            "## 合成中文小节\n\n"
            "第二段中文保持与语言绑定。",
        ),
    }
    languages = {}
    for lang, text in files.items():
        path = folder / f"{lang}.md"
        path.write_text(text, encoding="utf-8")
        languages[lang] = {"file": f"{lang}.md", "sha256": digest(path)}
    return {
        "slug": SYNTH_SLUG,
        "date": SYNTH_DATE,
        "folder": SYNTH_FOLDER,
        "languages": languages,
    }


def prepare_temp_site(tmp_root: Path) -> tuple[Path, Path, dict]:
    """Copy a minimal buildable tree and add a second valid journal issue. Never touches public/."""
    if tmp_root.exists():
        shutil.rmtree(tmp_root)
    tmp_root.mkdir(parents=True)
    for name in ("build.mjs", "publication-manifest.json", "roadmap-manifest.json"):
        shutil.copy2(ROOT / name, tmp_root / name)
    shutil.copytree(ROOT / "scripts", tmp_root / "scripts", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(ROOT / "src", tmp_root / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    journal_root = tmp_root / "src" / "content" / "journal"
    synth = write_synthetic_issue(journal_root)
    manifest = load_manifest(journal_root / "manifest.json")
    manifest["issues"].append(synth)
    (journal_root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    result = subprocess.run(["node", "build.mjs"], cwd=tmp_root, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "temp site build failed: " + (result.stderr or result.stdout or f"exit:{result.returncode}")
        )
    return tmp_root / "public", journal_root, synth


def inject_english_body(page_path: Path, catalog_issue: dict, lang: str = "ru") -> None:
    original = page_path.read_text(encoding="utf-8")
    english_html = catalog_issue["languages"]["en"]["html"]
    mutated = re.sub(
        rf'(<div lang="{lang}" class="journal-body">).*?(</div>\s*<a class="text-link" href="/{lang}/journal/")',
        lambda m: m.group(1) + english_html + m.group(2),
        original,
        count=1,
        flags=re.S,
    )
    if mutated == original:
        raise RuntimeError(f"failed to inject English body into {page_path}")
    page_path.write_text(mutated, encoding="utf-8")


def run_infra_self_test() -> MutantOutcome:
    """Deliberately broken harness environment must yield INFRA_ERROR, not KILLED."""
    missing = "scripts/does-not-exist-build_journal.py"
    expected = "Journal file digest mismatch"
    target = JOURNAL / PIN_FOLDER / "en.md"
    original = target.read_bytes()

    def mutate() -> None:
        target.write_bytes(original + b"x")

    def restore() -> None:
        target.write_bytes(original)

    return run_subprocess_mutant(
        "infra-self-test",
        expected,
        baseline_cmd=["python3", "-B", "scripts/build_journal.py"],
        mutate=mutate,
        probe_cmd=["python3", "-B", missing],
        restore=restore,
        mutation_target=target,
    )


def run_mutants() -> int:
    """Apply each required mutant; require exact refusal; never count infra as killed."""
    outcomes: list[MutantOutcome] = []

    # --- (a) one byte changed in a committed .md → digest mismatch ---
    target_a = JOURNAL / PIN_FOLDER / "en.md"
    original_a = target_a.read_bytes()
    expected_a = "Journal file digest mismatch"

    outcomes.append(
        run_subprocess_mutant(
            "a",
            expected_a,
            baseline_cmd=["python3", "-B", "scripts/build_journal.py"],
            mutate=lambda: target_a.write_bytes(original_a + b"x"),
            probe_cmd=["python3", "-B", "scripts/build_journal.py"],
            restore=lambda: target_a.write_bytes(original_a),
            mutation_target=target_a,
        )
    )

    pin_issue = next(item for item in load_manifest()["issues"] if item["slug"] == PIN_SLUG)
    catalog = json.loads((ROOT / "src/content/catalog.json").read_text(encoding="utf-8"))
    catalog_pin = next(item for item in catalog["journal_issues"] if item["slug"] == PIN_SLUG)

    # --- (b) ru route rendering the English body (pin issue) ---
    page_b = ROOT / "public/ru/journal" / PIN_SLUG / "index.html"
    original_b = page_b.read_text(encoding="utf-8")
    expected_b = f"{PIN_SLUG}/ru: English body on wrong locale page"
    outcomes.append(
        run_assertion_mutant(
            "b",
            expected_b,
            baseline=lambda: assert_locale_page(pin_issue, "ru"),
            mutate=lambda: inject_english_body(page_b, catalog_pin, "ru"),
            probe=lambda: assert_locale_page(pin_issue, "ru"),
            restore=lambda: page_b.write_text(original_b, encoding="utf-8"),
            mutation_target=page_b,
        )
    )

    # --- (c) article missing from the journal index ---
    index_c = ROOT / "public/en/journal/index.html"
    original_c = index_c.read_text(encoding="utf-8")
    expected_c = f"{PIN_SLUG}/en: missing from journal index"

    def mutate_c() -> None:
        mutated = original_c.replace(f"/journal/{PIN_SLUG}/", "/journal/not-present/")
        if mutated == original_c:
            raise RuntimeError("index mutation did not change bytes")
        index_c.write_text(mutated, encoding="utf-8")

    outcomes.append(
        run_assertion_mutant(
            "c",
            expected_c,
            baseline=lambda: assert_locale_page(pin_issue, "en"),
            mutate=mutate_c,
            probe=lambda: assert_locale_page(pin_issue, "en"),
            restore=lambda: index_c.write_text(original_c, encoding="utf-8"),
            mutation_target=index_c,
        )
    )

    # --- (d) article route marked noindex ---
    page_d = ROOT / "public/en/journal" / PIN_SLUG / "index.html"
    original_d = page_d.read_text(encoding="utf-8")
    expected_d = f"{PIN_SLUG}/en: page must be indexable"

    def mutate_d() -> None:
        mutated = original_d.replace("</title>", '</title><meta name="robots" content="noindex,follow">', 1)
        if mutated == original_d:
            raise RuntimeError("noindex mutation did not change bytes")
        page_d.write_text(mutated, encoding="utf-8")

    outcomes.append(
        run_assertion_mutant(
            "d",
            expected_d,
            baseline=lambda: assert_locale_page(pin_issue, "en"),
            mutate=mutate_d,
            probe=lambda: assert_locale_page(pin_issue, "en"),
            restore=lambda: page_d.write_text(original_d, encoding="utf-8"),
            mutation_target=page_d,
        )
    )

    # --- (e) fake unbuilt issue on a temp manifest → check_page refuses ---
    fake_slug = "mutant-missing-issue-2099-01-01"
    mutated_manifest = load_manifest()
    mutated_manifest["issues"].append(
        {
            "slug": fake_slug,
            "date": "2099-01-01",
            "folder": "2099-01-01-mutant-missing-issue",
            "languages": {
                "en": {"file": "en.md", "sha256": "0" * 64},
                "ru": {"file": "ru.md", "sha256": "0" * 64},
                "zh-Hans": {"file": "zh-Hans.md", "sha256": "0" * 64},
            },
        }
    )
    # check_page walks sitemap membership before the page-file check.
    expected_e = f"sitemap.xml missing journal issue https://contract.place/en/journal/{fake_slug}/"
    with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
        temp_manifest = Path(tmp) / "manifest.json"
        baseline_bytes = (json.dumps(mutated_manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        temp_manifest.write_bytes(baseline_bytes)

        def baseline_e() -> None:
            env = {**os.environ}
            env.pop("JOURNAL_MANIFEST", None)
            result = subprocess.run(
                ["python3", "-B", "scripts/check_page.py", "public"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                env=env,
            )
            if result.returncode != 0:
                raise RuntimeError(_subprocess_refusal(result))

        def mutate_e() -> None:
            temp_manifest.write_bytes(baseline_bytes + b"\n")

        try:
            baseline_e()
        except BaseException as exc:
            outcome = MutantOutcome("e", expected_e, f"baseline-before: {_refusal_from_exc(exc)}", "INFRA_ERROR")
            _print_outcome(outcome)
            outcomes.append(outcome)
        else:
            before = digest(temp_manifest)
            mutate_e()
            after = digest(temp_manifest)
            if before == after:
                outcome = MutantOutcome("e", expected_e, "mutation-not-applied: digest unchanged", "INFRA_ERROR")
            else:
                result = subprocess.run(
                    ["python3", "-B", "scripts/check_page.py", "public"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    env={**os.environ, "JOURNAL_MANIFEST": str(temp_manifest)},
                )
                if result.returncode == 0:
                    outcome = MutantOutcome("e", expected_e, "accepted", "SURVIVED")
                else:
                    observed = _subprocess_refusal(result)
                    if expected_e in observed:
                        outcome = MutantOutcome("e", expected_e, observed, "KILLED")
                    elif _looks_like_infra(observed):
                        outcome = MutantOutcome("e", expected_e, f"infra: {observed}", "INFRA_ERROR")
                    else:
                        outcome = MutantOutcome(
                            "e", expected_e, f"infra: unexpected refusal: {observed}", "INFRA_ERROR"
                        )
            _print_outcome(outcome)
            outcomes.append(outcome)
            try:
                temp_manifest.write_bytes(baseline_bytes)
                os.environ.pop("JOURNAL_MANIFEST", None)
                baseline_e()
            except BaseException as exc:
                failed = MutantOutcome("e", expected_e, f"baseline-after: {_refusal_from_exc(exc)}", "INFRA_ERROR")
                _print_outcome(failed)
                outcomes.append(failed)

    # --- temp site with a second valid issue for (f)/(g) ---
    tmp_site = ROOT / TMP_SITE_NAME
    try:
        public_tmp, journal_tmp, synth = prepare_temp_site(tmp_site)
        assert_all_manifest_issues(
            manifest_path=journal_tmp / "manifest.json",
            public_root=public_tmp,
            journal_root=journal_tmp,
        )
        spec = importlib.util.spec_from_file_location(
            "build_journal_tmp", tmp_site / "scripts" / "build_journal.py"
        )
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        synth_compiled = next(item for item in mod.compile_journal(tmp_site) if item["slug"] == SYNTH_SLUG)

        # --- (f) English body on the second issue's ru page ---
        page_f = public_tmp / "ru/journal" / SYNTH_SLUG / "index.html"
        original_f = page_f.read_text(encoding="utf-8")
        expected_f = f"{SYNTH_SLUG}/ru: English body on wrong locale page"
        outcomes.append(
            run_assertion_mutant(
                "f",
                expected_f,
                baseline=lambda: assert_locale_page(
                    synth, "ru", public_root=public_tmp, journal_root=journal_tmp
                ),
                mutate=lambda: inject_english_body(page_f, synth_compiled, "ru"),
                probe=lambda: assert_locale_page(
                    synth, "ru", public_root=public_tmp, journal_root=journal_tmp
                ),
                restore=lambda: page_f.write_text(original_f, encoding="utf-8"),
                mutation_target=page_f,
            )
        )

        # --- (g) remove only the second issue from the journal index ---
        index_g = public_tmp / "en/journal/index.html"
        original_g = index_g.read_text(encoding="utf-8")
        expected_g = f"{SYNTH_SLUG}/en: missing from journal index"

        def mutate_g() -> None:
            mutated = original_g.replace(f"/journal/{SYNTH_SLUG}/", "/journal/not-present/")
            if mutated == original_g:
                raise RuntimeError("synth index mutation did not change bytes")
            if f"/journal/{PIN_SLUG}/" not in mutated:
                raise RuntimeError("synth index mutation removed the pin issue")
            index_g.write_text(mutated, encoding="utf-8")

        outcomes.append(
            run_assertion_mutant(
                "g",
                expected_g,
                baseline=lambda: assert_locale_page(
                    synth, "en", public_root=public_tmp, journal_root=journal_tmp
                ),
                mutate=mutate_g,
                probe=lambda: assert_locale_page(
                    synth, "en", public_root=public_tmp, journal_root=journal_tmp
                ),
                restore=lambda: index_g.write_text(original_g, encoding="utf-8"),
                mutation_target=index_g,
            )
        )
    except BaseException as exc:
        for name, expected in (
            ("f", f"{SYNTH_SLUG}/ru: English body on wrong locale page"),
            ("g", f"{SYNTH_SLUG}/en: missing from journal index"),
        ):
            outcome = MutantOutcome(name, expected, f"infra: {exc}", "INFRA_ERROR")
            _print_outcome(outcome)
            outcomes.append(outcome)
        traceback.print_exc()
    finally:
        if tmp_site.exists():
            shutil.rmtree(tmp_site, ignore_errors=True)

    # --- (h) one manuscript https link rendered as plain text ---
    page_h = ROOT / "public/en/journal" / PIN_SLUG / "index.html"
    original_h = page_h.read_text(encoding="utf-8")
    _, pin_body_en = split_markdown(JOURNAL / PIN_FOLDER / "en.md")
    pin_links = manuscript_https_links(pin_body_en)
    assert pin_links, "pin English manuscript must declare https source links"
    link_text_h, href_h = pin_links[0]
    expected_h = f"{PIN_SLUG}/en: missing rendered link {href_h}"

    def mutate_h() -> None:
        pattern = re.compile(
            rf'<a href="{re.escape(href_h)}"[^>]*>{re.escape(link_text_h)}</a>'
        )
        mutated, count = pattern.subn(link_text_h, original_h, count=1)
        if count != 1 or mutated == original_h:
            raise RuntimeError(f"failed to flatten source link {href_h}")
        page_h.write_text(mutated, encoding="utf-8")

    outcomes.append(
        run_assertion_mutant(
            "h",
            expected_h,
            baseline=lambda: assert_locale_page(pin_issue, "en"),
            mutate=mutate_h,
            probe=lambda: assert_locale_page(pin_issue, "en"),
            restore=lambda: page_h.write_text(original_h, encoding="utf-8"),
            mutation_target=page_h,
        )
    )

    # --- (i) closing Sources heading reintroduced on a built page ---
    page_i = ROOT / "public/en/journal" / PIN_SLUG / "index.html"
    original_i = page_i.read_text(encoding="utf-8")
    expected_i = f"{PIN_SLUG}/en: forbidden sources heading"

    def mutate_i() -> None:
        needle = f'<div lang="en" class="journal-body">'
        insertion = needle + "<h2>Sources</h2>"
        if needle not in original_i:
            raise RuntimeError("journal body marker missing for sources-heading mutant")
        mutated = original_i.replace(needle, insertion, 1)
        if mutated == original_i:
            raise RuntimeError("sources-heading mutation did not change bytes")
        page_i.write_text(mutated, encoding="utf-8")

    outcomes.append(
        run_assertion_mutant(
            "i",
            expected_i,
            baseline=lambda: assert_locale_page(pin_issue, "en"),
            mutate=mutate_i,
            probe=lambda: assert_locale_page(pin_issue, "en"),
            restore=lambda: page_i.write_text(original_i, encoding="utf-8"),
            mutation_target=page_i,
        )
    )

    outcomes.append(run_infra_self_test())

    killed = [o for o in outcomes if o.verdict == "KILLED"]
    survived = [o for o in outcomes if o.verdict == "SURVIVED"]
    infra = [o for o in outcomes if o.verdict == "INFRA_ERROR"]
    print(
        f"MUTANT SUMMARY: killed={len(killed)} survived={len(survived)} "
        f"infra_error={len(infra)} total={len(outcomes)}"
    )

    required = {o.name: o for o in outcomes if o.name in list("abcdefghi")}
    failures = 0
    for name in "abcdefghi":
        outcome = required.get(name)
        if outcome is None:
            print(f"MUTANT {name}: missing from harness")
            failures += 1
        elif outcome.verdict != "KILLED":
            failures += 1
    self_test = next((o for o in outcomes if o.name == "infra-self-test"), None)
    if self_test is None or self_test.verdict != "INFRA_ERROR":
        print("INFRA self-test did not report INFRA_ERROR")
        failures += 1
    return failures


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--mutants":
        raise SystemExit(run_mutants())
    unittest.main()
