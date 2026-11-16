#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""RSS/Atom source and generated-publication checks; no network is used."""
from __future__ import annotations

from copy import deepcopy
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("journal_feeds", ROOT / "src/journal_feeds.py")
feeds = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(feeds)
ATOM = {"a": feeds.ATOM}
CONTENT = "{" + feeds.CONTENT + "}encoded"


def issue(slug="example", day="2026-11-15"):
    return {
        "slug": slug, "date": day, "route": "journal/" + slug,
        "languages": {
            lang: {"title": "A & B < C — " + lang, "excerpt": 'Quotes " and \' — 摘要',
                   "sha256": "a" * 64, "html": '<p>Complete <em>article</em> &amp; evidence.</p><p>Second paragraph.</p>'}
            for lang in feeds.LANGUAGES
        },
    }


class Fragment(HTMLParser):
    def __init__(self, body):
        super().__init__(convert_charrefs=True)
        self.text = []
        self.links = []
        self.robots = []
        self.feed(body)

    def handle_data(self, value):
        if value.strip():
            self.text.append(value)

    def handle_starttag(self, tag, attrs):
        if tag == "meta" and dict(attrs).get("name") == "robots":
            self.robots.append(dict(attrs).get("content", ""))
        if tag in ("a", "link"):
            self.links.append((tag, dict(attrs)))


class JournalFeedTests(unittest.TestCase):
    def test_all_languages_are_valid_xml_with_full_content_and_stable_links(self):
        for lang in feeds.LANGUAGES:
            with self.subTest(lang=lang):
                source = issue()
                output = feeds.render([source], lang)
                rss = ET.fromstring(output["rss"])
                atom = ET.fromstring(output["atom"])
                canonical = f"https://contract.place/{lang}/journal/example/"
                item = rss.find("channel/item")
                entry = atom.find("a:entry", ATOM)
                self.assertEqual(rss.tag, "rss")
                self.assertEqual(rss.findtext("channel/language"), lang)
                self.assertEqual(item.findtext("title"), source["languages"][lang]["title"])
                self.assertEqual(item.findtext("description"), source["languages"][lang]["excerpt"])
                self.assertEqual(item.findtext("guid"), canonical)
                self.assertEqual(item.find("guid").attrib["isPermaLink"], "true")
                self.assertEqual(item.findtext("pubDate"), "Sun, 15 Nov 2026 00:00:00 GMT")
                self.assertIn("<em>article</em>", item.findtext(CONTENT))
                self.assertIn("Second paragraph.", item.findtext(CONTENT))
                self.assertEqual(entry.findtext("a:id", namespaces=ATOM), canonical)
                self.assertEqual(entry.findtext("a:content", namespaces=ATOM), item.findtext(CONTENT))
                self.assertEqual(entry.find("a:content", ATOM).attrib["type"], "html")
                self.assertEqual(entry.findtext("a:updated", namespaces=ATOM), "2026-11-15T00:00:00Z")
                self.assertEqual(atom.find("a:link[@rel='self']", ATOM).attrib["href"],
                                 f"https://contract.place/{lang}/journal/atom.xml")

    def test_relative_urls_and_fragments_are_absolute_without_changing_link_text(self):
        canonical = "https://contract.place/ru/journal/example/"
        source = '<p><a href="../older/?a=1&amp;b=2">Source &amp; scope</a><a href="#result">Result</a></p><img src="/assets/chart.png" alt="a &amp; b">'
        html = feeds.article_html(source, canonical)
        self.assertIn('href="https://contract.place/ru/journal/older/?a=1&amp;b=2"', html)
        self.assertIn('href="https://contract.place/ru/journal/example/#result"', html)
        self.assertIn('src="https://contract.place/assets/chart.png"', html)
        self.assertEqual(Fragment(html).text, Fragment(source).text)

    def test_mathml_and_code_text_survive(self):
        source = '<p><code>&lt;key&gt;</code></p><math xmlns="http://www.w3.org/1998/Math/MathML"><mrow><mi>x</mi><mspace width="1em"/><mo>&lt;</mo><mn>2</mn></mrow></math>'
        html = feeds.article_html(source, "https://contract.place/en/journal/example/")
        self.assertIn("<code>&lt;key&gt;</code>", html)
        self.assertIn('<mspace width="1em"></mspace>', html)
        self.assertEqual(Fragment(html).text, Fragment(source).text)

    def test_active_content_and_unsafe_urls_refused(self):
        for html in (
            '<script>alert(1)</script>', '<iframe src="/private"></iframe>',
            '<p onclick="alert(1)">Text</p>', '<img src="javascript:alert(1)">',
            '<a href="data:text/html,hello">x</a>', '<a href="https://name:secret@example.org/">x</a>',
            '<img srcset="/a 1x, /b 2x">', '<p style="background:url(/track)">x</p>',
            '<!DOCTYPE html>', '<?xml version="1.0"?>',
        ):
            with self.subTest(html=html), self.assertRaises(ValueError):
                feeds.article_html(html, "https://contract.place/en/journal/example/")

    def test_invalid_dates_and_xml_control_characters_refused(self):
        for day in ("2026-02-30", "2026-1-01", "2026-11-15T10:00:00Z", "", None):
            with self.subTest(day=day), self.assertRaises(ValueError):
                feeds.render([issue(day=day)], "en")
        for value in ("bad\x00text", "bad\x1ftext", "\ud800"):
            source = issue()
            source["languages"]["en"]["title"] = value
            with self.subTest(value=repr(value)), self.assertRaises(ValueError):
                feeds.render([source], "en")

    def test_duplicates_wrong_routes_and_missing_language_refused(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            feeds.render([issue(), issue()], "en")
        for mutation in ("route", "slug", "language", "sha", "body"):
            source = issue()
            if mutation == "route":
                source["route"] = "science/example"
            elif mutation == "slug":
                source["slug"] = "../private"
            elif mutation == "language":
                del source["languages"]["ru"]
            elif mutation == "sha":
                source["languages"]["ru"]["sha256"] = "unknown"
            else:
                source["languages"]["ru"]["html"] = ""
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                feeds.render([source], "ru")
        with self.assertRaisesRegex(ValueError, "Invalid journal identity"):
            feeds.render([issue("building-a-place")], "en")
        with self.assertRaisesRegex(ValueError, "Invalid journal feed input"):
            feeds.render([issue()], "xx")

    def test_identity_survives_article_correction(self):
        first = issue()
        second = deepcopy(first)
        second["languages"]["en"]["title"] = "Corrected title"
        second["languages"]["en"]["html"] = "<p>Corrected article</p>"
        before = ET.fromstring(feeds.render([first], "en")["atom"])
        after = ET.fromstring(feeds.render([second], "en")["atom"])
        self.assertEqual(before.findtext("a:entry/a:id", namespaces=ATOM),
                         after.findtext("a:entry/a:id", namespaces=ATOM))
        self.assertNotEqual(before.findtext("a:entry/a:content", namespaces=ATOM),
                            after.findtext("a:entry/a:content", namespaces=ATOM))

    def test_sort_limit_and_validation_outside_window(self):
        sources = [issue(f"entry-{index:03}", "2026-11-14") for index in range(60)]
        sources.append(issue("newest", "2026-11-15"))
        result = feeds.entries(sources, "en")
        self.assertEqual(len(result), 50)
        self.assertEqual(result[0]["slug"], "newest")
        self.assertEqual(result[1]["slug"], "entry-000")
        self.assertEqual(feeds.render(sources, "en"), feeds.render(list(reversed(sources)), "en"))
        sources[-2]["languages"]["en"]["sha256"] = "invalid"
        with self.assertRaises(ValueError):
            feeds.render(sources, "en")

    def test_empty_feed_uses_fixed_creation_timestamp(self):
        first = feeds.render([], "en")
        second = feeds.render([], "en")
        self.assertEqual(first, second)
        root = ET.fromstring(first["atom"])
        self.assertEqual(root.findtext("a:updated", namespaces=ATOM), "2026-11-16T08:30:59Z")
        self.assertEqual(root.findall("a:entry", ATOM), [])


class GeneratedJournalFeeds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "src/content/journal/manifest.json").read_text())
        cls.catalogue = json.loads((ROOT / "src/content/catalog.json").read_text())
        cls.issues = cls.catalogue["journal_issues"]

    def test_committed_feeds_match_only_manifest_daily_issues_in_each_locale(self):
        expected = sorted(self.manifest["issues"], key=lambda row: (-date_ordinal(row["date"]), row["slug"]))[:50]
        for lang in feeds.LANGUAGES:
            with self.subTest(lang=lang):
                paths = {kind: ROOT / "public" / lang / "journal" / (kind + ".xml") for kind in ("rss", "atom")}
                self.assertTrue(all(path.is_file() for path in paths.values()), "Build feeds before testing")
                rss = ET.fromstring(paths["rss"].read_text())
                atom = ET.fromstring(paths["atom"].read_text())
                expected_ids = [f"https://contract.place/{lang}/journal/{row['slug']}/" for row in expected]
                self.assertEqual([node.findtext("guid") for node in rss.findall("channel/item")], expected_ids)
                self.assertEqual([node.findtext("a:id", namespaces=ATOM) for node in atom.findall("a:entry", ATOM)], expected_ids)
                by_slug = {row["slug"]: row for row in self.issues}
                for row, rss_item, atom_item in zip(expected, rss.findall("channel/item"), atom.findall("a:entry", ATOM)):
                    source = by_slug[row["slug"]]["languages"][lang]
                    self.assertEqual(rss_item.findtext("title"), source["title"])
                    self.assertEqual(rss_item.findtext("description"), source["excerpt"])
                    self.assertEqual(Fragment(rss_item.findtext(CONTENT)).text, Fragment(source["html"]).text)
                    self.assertEqual(atom_item.findtext("a:content", namespaces=ATOM), rss_item.findtext(CONTENT))
                    self.assertTrue((ROOT / "public" / lang / "journal" / row["slug"] / "index.html").is_file())

    def test_prerendered_discovery_and_visible_subscription_links(self):
        for lang in feeds.LANGUAGES:
            for route in ("", "journal"):
                with self.subTest(lang=lang, route=route):
                    html = (ROOT / "public" / lang / route / "index.html").read_text()
                    page = Fragment(html)
                    for kind in ("rss", "atom"):
                        url = f"https://contract.place/{lang}/journal/{kind}.xml"
                        self.assertTrue(any(tag == "link" and attrs.get("rel") == "alternate"
                                            and attrs.get("type") == f"application/{kind}+xml"
                                            and attrs.get("href") == url for tag, attrs in page.links))
                        self.assertTrue(any(tag == "a" and attrs.get("href") == url for tag, attrs in page.links))
                    if route == "journal":
                        self.assertIn("journal-subscriptions", html)


    def test_discovery_is_confined_to_indexable_home_and_manifest_journal_pages(self):
        allowed = {"index.html"}
        for lang in feeds.LANGUAGES:
            allowed.update({f"{lang}/index.html", f"{lang}/journal/index.html"})
            allowed.update(f"{lang}/journal/{row['slug']}/index.html" for row in self.manifest["issues"])
        seen = set()
        excluded = 0
        for path in (ROOT / "public").rglob("*.html"):
            relative = path.relative_to(ROOT / "public").as_posix()
            page = Fragment(path.read_text())
            discovery = [attrs for tag, attrs in page.links if tag == "link"
                         and attrs.get("rel") == "alternate"
                         and attrs.get("type") in ("application/rss+xml", "application/atom+xml")]
            noindex = any("noindex" in value.lower().split(",") for value in page.robots)
            if relative in allowed and not noindex:
                self.assertEqual(len(discovery), 2, relative)
                seen.add(relative)
            else:
                self.assertEqual(discovery, [], relative + ": unexpected feed discovery")
                excluded += 1
        self.assertEqual(seen, allowed)
        self.assertGreater(excluded, 0, "Exercise noindex, aliases, readers and other sections")


def date_ordinal(value):
    from datetime import date
    return date.fromisoformat(value).toordinal()


if __name__ == "__main__":
    unittest.main()

