#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Programme reading pages: pin, language switch, nav, foundation cards, negative control."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import tempfile
import unittest

import programme
from programme import extract_foundations, verify_guide_bytes, FOUNDATION_SECTIONS, SOURCES

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
CATALOG = ROOT / "src/content/catalog.json"
LOCALES = ("en", "ru", "zh-Hans")
NAV = {"en": "Programme", "ru": "Программа", "zh-Hans": "计划"}
PIN = "46af0f06218e590e047a585ac74820f3c6336604"
BLOBS = {
    "en": "bd74b311b76cd7da1e81dff8f5d42c584d9d4b71",
    "ru": "6a7325665da20f8e728dae8637ac499981ead2b7",
    "zh-Hans": "f191fc4b4bf32f51b5b4a9bb6dab44e64d54c99b",
}


class ProgrammePageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
        cls.programme = cls.catalog.get("programme")
        if not cls.programme:
            raise unittest.SkipTest("catalogue has no programme block; rebuild first")

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
        source_root = Path("/home/dev/aup/claude-work/kcswe-site-k8/knowledge-contract")
        for locale in LOCALES:
            page = self.programme["pages"][locale]
            html = (PUBLIC / locale / "programme/index.html").read_text(encoding="utf-8")
            self.assertEqual(len(page["foundations"]), 3)
            for card in page["foundations"]:
                self.assertIn(card["title"], html)
                self.assertIn(card["visible"], html)
                self.assertEqual(card["visible"], re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", card["text"]))
            if source_root.is_dir():
                raw = (source_root / SOURCES[locale]).read_text(encoding="utf-8")
                expected = extract_foundations(raw, FOUNDATION_SECTIONS[locale])
                self.assertEqual(page["foundations"], expected)

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
