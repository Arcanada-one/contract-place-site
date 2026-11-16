#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Compile site-local daily journal Markdown into catalogue data.

Source of record: src/content/journal/<folder>/{en,ru,zh-Hans}.md plus
src/content/journal/manifest.json (slug, date, per-language file + sha256).
Bodies are converted with Pandoc 3.1.3. A daily issue is added by placing three
language files, appending a manifest entry, and rebuilding.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape, unescape
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
JOURNAL_ROOT = ROOT / "src" / "content" / "journal"
MANIFEST_PATH = JOURNAL_ROOT / "manifest.json"
LANGS = ("en", "ru", "zh-Hans")
PANDOC_VERSION = "3.1.3"
FRONT_MATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", re.S)
ANCHOR_TAG = re.compile(r"<a\s+([^>]*?)>(.*?)</a>", re.I | re.S)


def run(command: list[str], text: str | None = None) -> str:
    result = subprocess.run(command, input=text, text=True, capture_output=True)
    if result.returncode:
        raise ValueError(f"{' '.join(command)} failed: {result.stderr.strip()}")
    return result.stdout


def require_pandoc() -> None:
    version = run(["pandoc", "--version"]).splitlines()[0].split()[1]
    if version != PANDOC_VERSION:
        raise ValueError(f"Expected Pandoc {PANDOC_VERSION}, found {version}")


def parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    match = FRONT_MATTER.match(text)
    if not match:
        raise ValueError("Journal Markdown must start with YAML front matter")
    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise ValueError(f"Invalid front-matter line: {line}")
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"')
    return meta, match.group(2).lstrip("\n")


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def decorate_inline_links(html: str) -> str:
    """Keep https Markdown/autolink anchors clickable; leave other schemes as plain text.

    https targets become <a href="...">…</a> with rel="noopener noreferrer".
    Any other scheme is flattened to an HTML-escaped [text](url) literal so the
    brackets stay visible and are never executable.
    """

    def replace(match: re.Match[str]) -> str:
        attrs = match.group(1)
        inner = match.group(2)
        href_match = re.search(r'\bhref="([^"]*)"', attrs)
        if not href_match:
            return match.group(0)
        href = href_match.group(1)
        if href.startswith("https://"):
            return f'<a href="{escape(href, quote=True)}" rel="noopener noreferrer">{inner}</a>'
        text = unescape(re.sub(r"<[^>]+>", "", inner))
        return escape(f"[{text}]({href})")

    return ANCHOR_TAG.sub(replace, html)


def render_body(body: str) -> str:
    # Match the publication renderer: GFM identifiers and bare URLs become ordinary links.
    html = run(
        [
            "pandoc",
            # Disable smart typography so manuscript apostrophes and dashes stay literal.
            "--from=markdown+gfm_auto_identifiers+autolink_bare_uris-smart",
            "--to=html5",
            "--mathml",
            "--no-highlight",
            "--wrap=none",
        ],
        body,
    ).strip()
    return decorate_inline_links(html)


def compile_journal(site: Path | None = None) -> list[dict]:
    """Verify the manifest against committed files and return compiled issues (newest first)."""
    require_pandoc()
    root = (site or ROOT) / "src" / "content" / "journal"
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("issues"), list):
        raise ValueError("Unsupported journal manifest")
    issues: list[dict] = []
    seen_slugs: set[str] = set()
    for entry in manifest["issues"]:
        slug = entry["slug"]
        date = entry["date"]
        folder = entry["folder"]
        if slug in seen_slugs:
            raise ValueError(f"Duplicate journal slug: {slug}")
        seen_slugs.add(slug)
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError(f"Invalid journal slug: {slug}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
            raise ValueError(f"Invalid journal date: {date}")
        languages = entry.get("languages") or {}
        if set(languages) != set(LANGS):
            raise ValueError(f"Journal issue {slug} must declare en, ru and zh-Hans")
        compiled_langs: dict[str, dict] = {}
        for lang in LANGS:
            info = languages[lang]
            rel = info["file"]
            expected = info["sha256"]
            path = root / folder / rel
            if not path.is_file():
                raise ValueError(f"Missing journal file: {path}")
            actual = digest(path)
            if actual != expected:
                raise ValueError(
                    f"Journal file digest mismatch for {path}: expected {expected}, found {actual}"
                )
            text = path.read_text(encoding="utf-8")
            meta, body = parse_front_matter(text)
            for key in ("site", "section", "slug", "date", "lang", "title", "excerpt"):
                if key not in meta:
                    raise ValueError(f"Missing front-matter key {key} in {path}")
            if meta["site"] != "contract.place" or meta["section"] != "journal":
                raise ValueError(f"Unexpected site/section in {path}")
            if meta["slug"] != slug or meta["date"] != date or meta["lang"] != lang:
                raise ValueError(f"Front matter identity mismatch in {path}")
            compiled_langs[lang] = {
                "file": f"{folder}/{rel}",
                "sha256": actual,
                "title": meta["title"],
                "excerpt": meta["excerpt"],
                "html": render_body(body),
            }
        issues.append(
            {
                "slug": slug,
                "date": date,
                "folder": folder,
                "route": f"journal/{slug}",
                "languages": compiled_langs,
            }
        )
    issues.sort(key=lambda item: item["date"], reverse=True)
    return issues


def main() -> None:
    issues = compile_journal(ROOT)
    json.dump(issues, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError, KeyError) as error:
        raise SystemExit(str(error))
