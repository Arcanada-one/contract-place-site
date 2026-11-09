#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Programme reading pages: pin, language switch, nav, foundation cards, negative control."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import posixpath
import re
import tempfile
import unittest
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from programme import (
    FOUNDATION_SECTIONS,
    GITHUB,
    MARKDOWN_LINK,
    SOURCES,
    extract_foundations,
    verify_guide_bytes,
)

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
CATALOG = ROOT / "src/content/catalog.json"
SOURCE_ROOT = Path(os.environ.get("PROGRAMME_SOURCE_DIR", str(ROOT / "_knowledge-source"))).resolve()
LOCALES = ("en", "ru", "zh-Hans")
NAV = {"en": "Programme", "ru": "Программа", "zh-Hans": "计划"}
PIN = "899564575085e2eb69c43c2bc4f4164e5dd39a7e"
BLOBS = {
    "en": "bd74b311b76cd7da1e81dff8f5d42c584d9d4b71",
    "ru": "6a7325665da20f8e728dae8637ac499981ead2b7",
    "zh-Hans": "f191fc4b4bf32f51b5b4a9bb6dab44e64d54c99b",
}
# Raw Markdown tokens that must never appear in rendered programme surfaces.
RAW_MARKDOWN = re.compile(r"\]\(|\*\*|`")
CARD_HTML = re.compile(r'<article class="foundation-card"[^>]*>(.*?)</article>', re.S)
MAIN_HTML = re.compile(r"<main\b[^>]*>(.*?)</main>", re.S)
HREF = re.compile(r'href="([^"]+)"')


class ProgrammePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        cls.programme = cls.catalog.get("programme")
        if not cls.programme:
            raise AssertionError("catalogue has no programme block; rebuild first")
        if not SOURCE_ROOT.is_dir():
            raise AssertionError("pinned knowledge-contract checkout required; set PROGRAMME_SOURCE_DIR")
        for locale, relative in SOURCES.items():
            digest, blob = verify_guide_bytes(SOURCE_ROOT, relative, PIN)
            if blob != BLOBS[locale] or digest != cls.programme["pages"][locale]["source_sha256"]:
                raise AssertionError(f"programme source identity mismatch: {relative}")

    def test_three_programme_pages_exist_with_pin(self):
        self.assertEqual(self.programme["pin"]["commit"], PIN)
        self.assertEqual(self.catalogue_publication_commit(), PIN)
        for locale in LOCALES:
            rel = f"{locale}/programme/index.html"
            html = (PUBLIC / rel).read_text(encoding="utf-8")
            self.assertTrue((PUBLIC / rel).is_file(), rel)
            self.assertIn(PIN, html)
            self.assertIn(BLOBS[locale], html)
            self.assertIn(SOURCES[locale], html)
            self.assertIn(f'<html lang="{locale}">', html)
            page = self.programme["pages"][locale]
            self.assertIn(page["html"], html)
            self.assertIn(page["source_sha256"], html)

    def catalogue_publication_commit(self):
        return self.catalog["publication"]["commit"]

    def test_language_switch_and_hreflang(self):
        for locale in LOCALES:
            html = (PUBLIC / locale / "programme/index.html").read_text(encoding="utf-8")
            head = re.search(r"<head>(.*?)</head>", html, re.S).group(1)
            for other in LOCALES:
                self.assertIn(f'hreflang="{other}" href="https://contract.place/{other}/programme/"', head)
                self.assertIn(f'href="/{other}/programme/"', html)
            self.assertNotIn("data-fallback=", html)
            self.assertNotIn('data-target-state="', html)

    def test_nav_link_in_all_locales(self):
        for locale in LOCALES:
            for rel in (f"{locale}/index.html", f"{locale}/programme/index.html", f"{locale}/roadmap/index.html"):
                html = (PUBLIC / rel).read_text(encoding="utf-8")
                self.assertIn(f'href="/{locale}/programme/"', html, rel)
                self.assertIn(NAV[locale], html, rel)

    def test_foundation_cards_equal_source_text(self):
        for locale in LOCALES:
            page = self.programme["pages"][locale]
            html = (PUBLIC / locale / "programme/index.html").read_text(encoding="utf-8")
            self.assertEqual(len(page["foundations"]), 3)
            for card in page["foundations"]:
                self.assertIn(card["title"], html)
                self.assertTrue(card.get("html"), "foundation card must carry rendered HTML")
                self.assertIn(card["html"], html)
                self.assertEqual(card["visible"], MARKDOWN_LINK.sub(r"\1", card["text"]))
                # Card HTML is the Markdown path, not escaped source syntax.
                self.assertNotRegex(card["html"], RAW_MARKDOWN)
            raw = (SOURCE_ROOT / SOURCES[locale]).read_text(encoding="utf-8")
            expected = extract_foundations(raw, FOUNDATION_SECTIONS[locale])
            for got, want in zip(page["foundations"], expected, strict=True):
                self.assertEqual(got["title"], want["title"])
                self.assertEqual(got["text"], want["text"])
                self.assertEqual(got["visible"], want["visible"])
                self.assertTrue(got["html"])

    def test_rendered_programme_has_no_raw_markdown_and_card_links_resolve(self):
        """Fails on ad6adce: cards showed labels only / or raw Markdown, without resolved anchors."""
        self.assertTrue(SOURCE_ROOT.is_dir(), "pinned knowledge-contract checkout required")
        published_routes = {
            f"/{locale}/{family}/{slug}/"
            for family in ("science", "engineering", "reference", "appendices")
            for locale in LOCALES
            for slug_dir in (PUBLIC / locale / family).glob("*")
            if slug_dir.is_dir()
            for slug in [slug_dir.name]
        }
        # Also accept exact files under public for non-manuscript routes.
        for locale in LOCALES:
            published_routes.add(f"/{locale}/programme/")
            published_routes.add(f"/{locale}/roadmap/")

        for locale in LOCALES:
            page_html = (PUBLIC / locale / "programme/index.html").read_text(encoding="utf-8")
            main = MAIN_HTML.search(page_html)
            self.assertIsNotNone(main, locale)
            main_html = main.group(1)
            self.assertNotRegex(main_html, RAW_MARKDOWN, f"raw Markdown leaked in <main> for {locale}")

            cards = CARD_HTML.findall(page_html)
            self.assertEqual(len(cards), 3, locale)
            raw = (SOURCE_ROOT / SOURCES[locale]).read_text(encoding="utf-8")
            source_cards = extract_foundations(raw, FOUNDATION_SECTIONS[locale])
            for card_html, source in zip(cards, source_cards, strict=True):
                self.assertNotRegex(card_html, RAW_MARKDOWN, f"raw Markdown in card ({locale})")
                plain = re.sub(r"<[^>]+>", "", card_html)
                self.assertIn(source["title"], page_html)
                # Labels survive rendering; status badges may sit beside links.
                for label, target in MARKDOWN_LINK.findall(source["text"]):
                    self.assertIn(label, plain)
                    expected = self.resolve_card_href(SOURCES[locale], target, locale)
                    hrefs = HREF.findall(card_html)
                    self.assertIn(
                        expected,
                        hrefs,
                        f"{locale}: missing resolved card link for {target} -> {expected}; have {hrefs}",
                    )
                    self.assert_href_resolves(expected, published_routes)
                if not MARKDOWN_LINK.search(source["text"]):
                    self.assertIn(source["visible"][:48], plain)

            # Body links inside <main> must also resolve when present.
            body = re.search(r'class="source-body prose"[^>]*>(.*?)</div>', main_html, re.S)
            self.assertIsNotNone(body, locale)
            for href in HREF.findall(body.group(1)):
                if href.startswith("#"):
                    continue
                self.assert_href_resolves(href, published_routes)

    def resolve_card_href(self, guide_path: str, target: str, locale: str) -> str:
        """Map a guide-relative Markdown target to the site or GitHub URL the renderer emits."""
        parts = urlsplit(target)
        raw_path = unquote(parts.path)
        relative = posixpath.normpath(str(PurePosixPath(guide_path).parent / raw_path))
        for record in self.catalog.get("records", []):
            if record.get("path") == relative:
                return record["route"].replace("/en/", f"/{locale}/", 1)
        return f"{GITHUB}/blob/{PIN}/{relative}"

    def assert_href_resolves(self, href: str, published_routes: set[str]) -> None:
        parts = urlsplit(href)
        if href.startswith("/") and not href.startswith("//"):
            path = parts.path if parts.path.endswith("/") else parts.path + "/"
            if path.endswith("/index.html"):
                path = path[: -len("index.html")]
            self.assertTrue(
                path in published_routes or (PUBLIC / parts.path.lstrip("/")).exists(),
                f"site route missing for {href}",
            )
            return
        prefix = f"{GITHUB}/blob/{PIN}/"
        self.assertTrue(href.startswith(prefix), f"unexpected external href {href}")
        rel = unquote(href[len(prefix):].split("#", 1)[0].split("?", 1)[0])
        self.assertTrue((SOURCE_ROOT / rel).exists(), f"GitHub blob target missing at pin: {rel}")

    def test_english_fallback_is_not_labelled_translation(self):
        for locale in LOCALES:
            html = (PUBLIC / locale / "programme/index.html").read_text(encoding="utf-8")
            self.assertNotIn("data-target-state=", html)
            self.assertNotIn('data-fallback="en"', html)
            body_lang = re.search(r'class="source-body prose" lang="([^"]+)"', html)
            self.assertIsNotNone(body_lang)
            self.assertEqual(body_lang.group(1), locale)


class ProgrammeSourceTests(unittest.TestCase):
    def test_extract_foundations_rule(self):
        sample = """# Title\n\n## Three connected foundations\n\n**Meaning Theory: One.** First paragraph one.\n\n**Meaning Algebra: Two.** First paragraph two.\n\n**Meaning Geometry: Three.** First paragraph three.\n\n## Next\n"""
        cards = extract_foundations(sample, FOUNDATION_SECTIONS["en"])
        self.assertEqual(
            [c["title"] for c in cards],
            ["Meaning Theory: One", "Meaning Algebra: Two", "Meaning Geometry: Three"],
        )
        self.assertEqual(cards[0]["text"], "First paragraph one.")

    def test_changed_guide_byte_without_repin_fails(self):
        """Negative control: mutated guide bytes must not verify against the pin blob."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "guides").mkdir()
            relative = "PROGRAMME.md"
            original = b"# Knowledge Contract\n\noriginal bytes\n"
            (root / relative).write_bytes(original)
            # Fake a git repo at a synthetic commit that records the original blob.
            import subprocess
            subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "config", "user.name", "test"], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "add", relative], cwd=root, check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", "seed"], cwd=root, check=True, capture_output=True)
            commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
            digest, blob = verify_guide_bytes(root, relative, commit)
            self.assertEqual(digest, sha256(original).hexdigest())
            self.assertTrue(blob)
            (root / relative).write_bytes(original + b"mutated\n")
            with self.assertRaises(ValueError) as ctx:
                verify_guide_bytes(root, relative, commit)
            self.assertIn("differ from pinned commit", str(ctx.exception))


class RoadmapCompatAnchorTests(unittest.TestCase):
    def test_rm01_compatibility_anchor_resolves(self):
        for locale in LOCALES:
            html = (PUBLIC / locale / "roadmap/index.html").read_text(encoding="utf-8")
            self.assertRegex(html, r'<article class="roadmap-card" id="rm-01"[^>]*data-task-id="RM-01"')
            self.assertIn('href="#rm-01"', html)
            # Names are shown; internal codes remain available as compatibility targets.
            self.assertIn("Claim Atlas", html)


if __name__ == "__main__":
    unittest.main()
