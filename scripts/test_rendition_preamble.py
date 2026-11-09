#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Bounded AST migration tests; publication/review admission is unchanged."""
from __future__ import annotations

from copy import deepcopy
import json
import subprocess
import unittest

from rendition_preamble import source_for_anchor_parity
from renditions import RenditionError, check_parity

COMMENT = '<!-- markdownlint-disable-next-line MD033 -->'
ANCHOR = '<a id="legacy-title"></a>'
ENTRY = {
    "work": "synthetic-study", "language": "ru",
    "source": {"path": "engineering/studies/synthetic-study/STUDY.md"},
    "rendition": {"path": "translations/ru/engineering/studies/synthetic-study/STUDY.md"},
    "sections": [{"source": "abstract", "rendition": "abstract"}],
}


def parse(text):
    result = subprocess.run(["pandoc", "--from=markdown+gfm_auto_identifiers+pipe_tables+tex_math_dollars+tex_math_single_backslash+autolink_bare_uris", "--to=json"],
                            input=text, text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def pair(prefix=COMMENT + '\n\n' + ANCHOR):
    source = parse(prefix + '\n\n# New English title\n\n## Abstract\n\nOriginal text.\n')
    target = parse('# Русское название {#legacy-title}\n\n## Аннотация {#abstract}\n\nПеревод.\n')
    return source, target


class AnchorPreambleTests(unittest.TestCase):
    def accepted(self, source, target):
        original_source, original_target = deepcopy(source), deepcopy(target)
        view = source_for_anchor_parity(source, target)
        self.assertIsNot(view, source)
        self.assertEqual(view["blocks"][0]["t"], "Header")
        check_parity(ENTRY, source, target)
        self.assertEqual(source, original_source)
        self.assertEqual(target, original_target)

    def refused(self, source, target):
        self.assertIs(source_for_anchor_parity(source, target), source)
        with self.assertRaises(RenditionError):
            check_parity(ENTRY, source, target)

    def test_exact_directive_and_anchor(self):
        self.accepted(*pair())

    def test_anchor_without_directive(self):
        self.accepted(*pair(ANCHOR))

    def test_html_rawblock_form(self):
        source, target = pair()
        source["blocks"][:2] = [{"t": "RawBlock", "c": ["html", COMMENT + '\n' + ANCHOR]}]
        self.accepted(source, target)

    def test_whitespace_inside_empty_anchor(self):
        self.accepted(*pair(COMMENT + '\n\n<a id="legacy-title">  </a>'))

    def test_wrong_id(self):
        source, target = pair()
        target["blocks"][0]["c"][1][0] = "wrong-title"
        self.refused(source, target)

    def test_missing_title_id(self):
        source, target = pair()
        target["blocks"][0]["c"][1][0] = ""
        self.refused(source, target)

    def test_duplicate_raw_id(self):
        source, target = pair()
        target["blocks"].append({"t": "RawBlock", "c": ["html", ANCHOR]})
        self.refused(source, target)

    def test_duplicate_span_id(self):
        source, target = pair()
        target["blocks"].append({"t": "Para", "c": [
            {"t": "Span", "c": [["legacy-title", [], []], [{"t": "Str", "c": "extra"}]]}]})
        self.refused(source, target)

    def test_duplicate_source_id(self):
        source, target = pair()
        source["blocks"].append({"t": "RawBlock", "c": ["html", ANCHOR]})
        self.refused(source, target)

    def test_source_prose_cannot_disappear(self):
        self.refused(*pair(COMMENT + '\n\n' + ANCHOR + '\n\nAn indispensable condition.'))

    def test_nonempty_anchor_is_not_ignored(self):
        self.refused(*pair('<a id="legacy-title">An indispensable condition</a>'))

    def test_arbitrary_comment_is_not_ignored(self):
        self.refused(*pair('<!-- a scientific qualification -->\n\n' + ANCHOR))

    def test_additional_attributes_are_not_ignored(self):
        self.refused(*pair('<a id="legacy-title" title="qualification"></a>'))

    def test_two_anchors_are_not_ignored(self):
        self.refused(*pair(ANCHOR + '\n\n<a id="second"></a>'))

    def test_no_heading_in_code_sample(self):
        source, target = pair()
        target = parse('```\n# Русское название {#legacy-title}\n```\n\n## Аннотация {#abstract}\n\nПеревод.\n')
        self.refused(source, target)

    def test_raw_html_heading_is_not_a_pandoc_title(self):
        source, target = pair()
        target = parse('<h1 id="legacy-title">Русское название</h1>\n\n## Аннотация {#abstract}\n\nПеревод.\n')
        self.refused(source, target)

    def test_nonhtml_raw_prefix_is_not_ignored(self):
        source, target = pair()
        source["blocks"][0]["c"][0] = "latex"
        self.refused(source, target)

    def test_no_prefix_is_unchanged(self):
        source, target = pair("")
        self.assertIs(source_for_anchor_parity(source, target), source)
        check_parity(ENTRY, source, target)

    def test_preserved_original_preamble_still_uses_old_path(self):
        source, target = pair()
        target["blocks"] = deepcopy(source["blocks"][:2]) + target["blocks"]
        target["blocks"][2]["c"][1][0] = "another-title"
        self.assertIs(source_for_anchor_parity(source, target), source)
        check_parity(ENTRY, source, target)

    def test_prose_after_h1_still_required(self):
        source, target = pair()
        idx = next(i for i, b in enumerate(source["blocks"]) if b["t"] == "Header")
        source["blocks"].insert(idx + 1, {"t": "Para", "c": [{"t": "Str", "c": "Condition"}]})
        with self.assertRaises(RenditionError) as caught:
            check_parity(ENTRY, source, target)
        self.assertEqual(caught.exception.code, "RENDITION_SECTION_MISSING")

    def test_formula_guard_survives_bridge(self):
        source, target = pair()
        source["blocks"].append({"t": "Para", "c": [{"t": "Math", "c": [{"t": "InlineMath"}, "x=1"]}]})
        target["blocks"].append({"t": "Para", "c": [{"t": "Math", "c": [{"t": "InlineMath"}, "x=2"]}]})
        with self.assertRaises(RenditionError) as caught:
            check_parity(ENTRY, source, target)
        self.assertEqual(caught.exception.code, "RENDITION_FORMULA_CHANGED")

    def test_reference_guard_survives_bridge(self):
        source, target = pair()
        source["blocks"].append({"t": "Para", "c": [
            {"t": "Link", "c": [["", [], []], [{"t": "Str", "c": "evidence"}], ["https://example.org/evidence", ""]]}]})
        with self.assertRaises(RenditionError) as caught:
            check_parity(ENTRY, source, target)
        self.assertEqual(caught.exception.code, "RENDITION_REFERENCE_DROPPED")


if __name__ == "__main__":
    unittest.main()
