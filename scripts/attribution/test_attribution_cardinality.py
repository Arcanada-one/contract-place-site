#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Bounded single-author attribution preflight, NOT a linguistic proof or release gate.

Exit: 0 no bounded pattern; 1 explicit contradiction to this source's sole author;
2 UNKNOWN input/metadata; 3 REVIEW_REQUIRED ambiguous or externally attributed plural.
Both 1 and 3 require a human resolution before editorial acceptance.
"""
import json
import re
import sys
import unittest
from pathlib import Path
from typing import NamedTuple

PLURAL_NOUN = {
    # These are REVIEW candidates, not automatic proof of authorship.
    "en": re.compile(r"\b(?:authors|researchers|the\s+team)\b", re.I),
    "ru": re.compile(r"\b(?:автор(?:ы|ов|ам|ами|ах)|исследовател(?:и|ей|ям|ями|ях)|команда\s+(?:авторов|исследователей))\b", re.I),
    "zh-Hans": re.compile(r"(?:作者们|研究者们|两位作者|研究团队)"),
}
AMBIGUOUS_PRONOUN = {
    "en": re.compile(r"\bthey\s+(?:(?:explicitly|directly)\s+)?(?:say|state|write|said)\b", re.I),
    "ru": re.compile(r"\bони\s+(?:прямо\s+)?(?:пишут|говорят|сказали|указывают)\b", re.I),
    "zh-Hans": re.compile(r"他们(?:明确|直接)?(?:指出|写道|表示)"),
}
THIS_STUDY = {
    "en": re.compile(r"\bauthors\s+of\s+(?:this|the\s+present)\s+(?:study|paper)\b", re.I),
    "ru": re.compile(r"\bавтор(?:ы|ов)\s+(?:этого|данного)\s+исследования\b", re.I),
    "zh-Hans": re.compile(r"(?:本研究的?(?:作者们|两位作者)|(?:作者们|两位作者)在本研究中)"),
}
# Specific other-work byline shapes. Presence is only REVIEW evidence, never
# proof that a nearby plural refers to that other work.
OTHER_PAPER_BYLINE = {
    "en": re.compile(
        r"\b(?:paper|study|article)\b[^.!?。！？]{0,120}\bby\s+"
        r"[A-Z][A-Za-z-]+\s+and\s+[A-Z][A-Za-z-]+\b"),
    "ru": re.compile(
        r"\b(?:стат(?:ья|ьи|ье|ью|ей)|работ(?:а|е|ы|у|ой)|исследовани(?:е|я|и|ю))"
        r"\s+(?:авторов\s+)?[А-ЯЁ][А-ЯЁа-яё-]{0,24}\s+и\s+[А-ЯЁ][А-ЯЁа-яё-]{0,24}\b"),
    "zh-Hans": re.compile(
        r"[\u4e00-\u9fff]{1,8}(?:和|与)[\u4e00-\u9fff]{1,8}的(?:论文|研究|文章)"),
}
# Conservative source-metadata screen, not author-count inference.
# A scalar using visible person-list connectors is not evidence of one person;
# reject it as UNKNOWN even if the same expression could be a legal single name.
AMBIGUOUS_AUTHOR_CONNECTOR = re.compile(
    r"(?:\b(?:and|et\s+al\.?)(?=\s|$)|\bи\b|[&;/+、，；／＆和与])",
    re.I,
)

SENTENCE_END = re.compile(r"(?<=[.!?。！？])\s+|(?<=[。！？])")


class Finding(NamedTuple):
    phrase: str
    status: str     # DEFECT | REVIEW_REQUIRED | EXTERNAL_REVIEW
    reason: str


def single_author(frontmatter_source: str) -> str:
    """Read a declared byline from a deliberately narrow metadata profile.

    All header fields must be unique flat ASCII keys with double-quoted,
    single-line JSON string values. This is not a general YAML parser: other
    YAML styles return UNKNOWN, even when valid YAML. Validating every header
    line prevents a nested, merged or unterminated field from hiding a byline.
    A scalar declaration does not authenticate an author or prove uniqueness.
    """
    match = re.match(r"\A---[ \t]*\n(.*?)\n---(?:\n|\Z)", frontmatter_source, re.S)
    if not match:
        raise ValueError("missing source front matter")
    fields = {}
    for line in match.group(1).split("\n"):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        entry = re.fullmatch(
            r'([A-Za-z_][A-Za-z0-9_-]*)[ \t]*:[ \t]*("(?:[^"\\\r\n]|\\.)*")[ \t]*',
            line)
        if entry is None:
            raise ValueError("unsupported metadata; flat double-quoted string fields required")
        key, literal = entry.groups()
        if key in fields:
            raise ValueError("duplicate metadata field; manual review required")
        try:
            fields[key] = json.loads(literal)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid quoted metadata string; manual review required") from exc
    if "authors" in fields:
        raise ValueError("authors-list metadata unsupported; manual review required")
    if "author" not in fields:
        raise ValueError("exactly one scalar author required")
    value = fields["author"]
    if (not value.strip() or value.startswith("[") or "," in value
            or AMBIGUOUS_AUTHOR_CONNECTOR.search(value)
            or any(ord(ch) < 32 or 0x7F <= ord(ch) <= 0x9F
                   or 0xD800 <= ord(ch) <= 0xDFFF or ch in "\u2028\u2029"
                   for ch in value)):
        raise ValueError("ambiguous author field; manual review required")
    return value


def analyze_attribution(source: str, locale: str, manuscript: str) -> list[Finding]:
    single_author(source)
    if locale not in PLURAL_NOUN:
        raise ValueError("unsupported locale")
    findings = []
    for sentence in SENTENCE_END.split(manuscript):
        external = bool(OTHER_PAPER_BYLINE[locale].search(sentence))
        self_anchor = THIS_STUDY[locale].search(sentence)
        for pattern in (PLURAL_NOUN[locale], AMBIGUOUS_PRONOUN[locale]):
            for match in pattern.finditer(sentence):
                # A directly bounded "authors of this study" is stronger than
                # an unrelated other-paper citation in the SAME sentence.
                # Do not promote other nouns in that sentence to DEFECT.
                if (self_anchor is not None and pattern is PLURAL_NOUN[locale]
                        and self_anchor.start() <= match.start()
                        and match.end() <= self_anchor.end()):
                    findings.append(Finding(match.group(0), "DEFECT",
                                            "explicit current-study plural vs one source author"))
                elif external:
                    findings.append(Finding(match.group(0), "EXTERNAL_REVIEW",
                                            "other-paper citation; referent unverified"))
                else:
                    findings.append(Finding(match.group(0), "REVIEW_REQUIRED",
                                            "plural/pronoun referent not established lexically"))
    return findings


def flagged_phrases(source: str, locale: str, manuscript: str) -> list[str]:
    """Compatibility surface: suspected SELF attribution; external-source mentions excluded.

    A missing item is NOT a clean linguistic verdict. check_files still reports
    EXTERNAL_REVIEW findings separately, with exit code 3.
    """
    return [f.phrase for f in analyze_attribution(source, locale, manuscript)
            if f.status != "EXTERNAL_REVIEW"]


STUDY = """---
title: "Source Rule Checks"
author: "Pavel Valentov"
edition: "1.1"
---
"""
RU_R1 = "Авторы прямо пишут, что это не автоматическое извлечение смысла из произвольного текста."
RU_R2 = "В исследовании прямо указано, что это не автоматическое извлечение смысла из произвольного текста."
EN = "It is explicitly not an automatic extractor of meaning from unrestricted prose."
ZH = "研究明确说明，它不是从任意文本中自动提取含义的工具。"


class AttributionTests(unittest.TestCase):
    def test_author_from_pinned_frontmatter_excerpt(self):
        self.assertEqual(single_author(STUDY), "Pavel Valentov")

    def test_quoted_metadata_profile_preserves_supported_byline(self):
        for literal, expected in (
            ('"Pavel Valentov"', "Pavel Valentov"),
            (r'"Pavel \u0056alentov"', "Pavel Valentov"),
            (r'"Example \"Quoted\" Author"', 'Example "Quoted" Author'),
            ('"Élodie O\'Connor"', "Élodie O'Connor"),
        ):
            with self.subTest(literal=literal):
                source = ('---\n# Declared single byline, not identity verification.\n'
                          'title: "Study"\n\nauthor: ' + literal + '\n---\n')
                self.assertEqual(single_author(source), expected)

    def test_unsupported_author_syntax_is_unknown(self):
        values = (
            "null", "~", "true", "42", "[Alice, Bob]", "{name: Alice}",
            "&byline\n  - Alice\n  - Bob", '&byline "Alice"', "*byline",
            '!!str "Alice"', "|\n  Alice\n  Bob", ">\n  Alice",
            "'Alice'", "Alice", "", '"Alice', 'Alice"', '"Alice" "Bob"',
            '"Alice" # trailing comment', r'"Alice\q"', '""', '"   "',
            '"[Alice]"', '"Alice, Bob"', r'"Alice\nBob"', r'"\uD800"',
        )
        for value in values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    single_author("---\nauthor: " + value + "\n---\n")

    def test_english_two_person_scalar_is_unknown(self):
        for value in ("Lee and Kim", "Lee & Kim", "Lee; Kim",
                      "Lee / Kim", "Lee et al.", "Lee、Kim"):
            with self.subTest(byline=value):
                src = STUDY.replace('author: "Pavel Valentov"',
                                    "author: " + json.dumps(value, ensure_ascii=False))
                with self.assertRaises(ValueError):
                    single_author(src)
                with self.assertRaises(ValueError):
                    analyze_attribution(src, "en",
                                        "The authors of this study state the limit.")

    def test_russian_two_person_scalar_is_unknown(self):
        for value in ("Ли и Ким", "Ли / Ким", "Ли; Ким"):
            with self.subTest(byline=value):
                src = STUDY.replace('author: "Pavel Valentov"',
                                    "author: " + json.dumps(value, ensure_ascii=False))
                with self.assertRaises(ValueError):
                    single_author(src)
                with self.assertRaises(ValueError):
                    analyze_attribution(src, "ru",
                                        "Авторы данного исследования пишут о пределе.")

    def test_chinese_two_person_scalar_is_unknown(self):
        for value in ("李明和王芳", "李明与王芳", "李明、王芳"):
            with self.subTest(byline=value):
                src = STUDY.replace('author: "Pavel Valentov"',
                                    "author: " + json.dumps(value, ensure_ascii=False))
                with self.assertRaises(ValueError):
                    single_author(src)
                with self.assertRaises(ValueError):
                    analyze_attribution(src, "zh-Hans",
                                        "本研究的作者们指出这一限制。")

    def test_two_person_scalar_file_mode_refuses_clean_and_plural(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            base = Path(directory)
            src, en, ru, zh = (base / name for name in
                                ("study.md", "en.md", "ru.md", "zh.md"))
            src.write_text(STUDY.replace('author: "Pavel Valentov"',
                                        'author: "Lee and Kim"'), encoding="utf-8")
            ru.write_text(RU_R2, encoding="utf-8")
            zh.write_text(ZH, encoding="utf-8")
            for en_text in (EN, "The authors of this study state the limit."):
                with self.subTest(en=en_text):
                    en.write_text(en_text, encoding="utf-8")
                    self.assertEqual(check_files([str(p) for p in
                                                  (src, en, ru, zh)]), 2)

    def test_ambiguous_header_structure_is_unknown(self):
        headers = (
            'author: "Alice"\nauthor: "Alice"',
            'author: "Alice"\nauthor: "Bob"',
            '"author": "Alice"',
            ' author: "Alice"',
            'author: "Alice"\n"author": "Bob"',
            'author: "Alice"\nauthors: "Bob"',
            'author: "Alice"\n<<: *additional_authors',
            'byline:\n  author: "Bob"\nauthor: "Alice"',
            '{"author": "Alice"}',
            'title: "unterminated\nauthor: "Alice"',
            'title: |\n  author: "Bob"\nauthor: "Alice"',
            '# comment \x85author: "Alice"',
            '# comment \u2028author: "Alice"',
        )
        for header in headers:
            with self.subTest(header=header):
                with self.assertRaises(ValueError):
                    single_author("---\n" + header + "\n---\n")

    def test_file_mode_unsupported_metadata_is_unknown_before_prose(self):
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            paths = [Path(directory) / name
                     for name in ("study.md", "en.md", "ru.md", "zh.md")]
            paths[2].write_text(RU_R2, encoding="utf-8")
            paths[3].write_text(ZH, encoding="utf-8")
            for value in ("null", "{name: Alice}",
                          "&byline\n  - Alice\n  - Bob"):
                paths[0].write_text("---\nauthor: " + value + "\n---\n",
                                    encoding="utf-8")
                for prose in (EN, "The authors of this study state the limit."):
                    with self.subTest(value=value, prose=prose):
                        paths[1].write_text(prose, encoding="utf-8")
                        output, errors = StringIO(), StringIO()
                        with redirect_stdout(output), redirect_stderr(errors):
                            result = check_files([str(path) for path in paths])
                        self.assertEqual(result, 2)
                        self.assertEqual(output.getvalue(), "")
                        self.assertIn("UNKNOWN:", errors.getvalue())

    def test_historical_russian_defect_is_flagged(self):
        self.assertEqual(flagged_phrases(STUDY, "ru", RU_R1), ["Авторы"])

    def test_corrected_russian_phrase_is_not_flagged(self):
        self.assertEqual(flagged_phrases(STUDY, "ru", RU_R2), [])

    def test_english_and_chinese_current_excerpts(self):
        self.assertEqual(flagged_phrases(STUDY, "en", EN), [])
        self.assertEqual(flagged_phrases(STUDY, "zh-Hans", ZH), [])

    def test_english_and_chinese_plural_mutants(self):
        self.assertTrue(flagged_phrases(STUDY, "en", "The authors explicitly state this."))
        self.assertTrue(flagged_phrases(STUDY, "zh-Hans", "作者们明确指出这一点。"))

    def test_ru_plural_and_past_tense_are_detected(self):
        for excerpt in ("Авторы исследования прямо пишут", "Авторы пишут",
                        "Авторы прямо написали", "Авторы данного исследования пишут"):
            with self.subTest(excerpt=excerpt):
                self.assertTrue(flagged_phrases(STUDY, "ru", excerpt))

    def test_en_plain_authors_detected(self):
        self.assertTrue(flagged_phrases(STUDY, "en", "The authors state that it is not an extractor."))

    def test_zh_plain_authors_detected(self):
        self.assertTrue(flagged_phrases(STUDY, "zh-Hans", "作者们指出，这不是自动提取。"))

    def test_ambiguous_pronoun_is_review_not_defect(self):
        findings = analyze_attribution(STUDY, "en", "They explicitly say it is not an extractor.")
        self.assertEqual([f.status for f in findings], ["REVIEW_REQUIRED"])
        self.assertTrue(flagged_phrases(STUDY, "en", "They explicitly say it is not an extractor."))

    def test_other_named_paper_not_false_self_flag(self):
        text = "Of the 2025 paper by Lee and Kim, the authors explicitly state the limit."
        self.assertEqual(flagged_phrases(STUDY, "en", text), [])
        self.assertEqual([f.status for f in analyze_attribution(STUDY, "en", text)],
                         ["EXTERNAL_REVIEW"])

    def test_explicit_current_study_plural_is_defect(self):
        for locale, text in (
            ("en", "The authors of this study state the limit."),
            ("ru", "Авторы данного исследования пишут об ограничении."),
            ("zh-Hans", "本研究的作者们指出这一限制。"),
        ):
            with self.subTest(locale=locale):
                self.assertEqual([f.status for f in analyze_attribution(STUDY, locale, text)],
                                 ["DEFECT"])


    def test_external_byline_cannot_downgrade_explicit_current_study(self):
        sentence = "Unlike the paper by Lee and Kim, the authors of this study state the limit."
        self.assertEqual([f.status for f in analyze_attribution(STUDY, "en", sentence)],
                         ["DEFECT"])
        self.assertEqual(flagged_phrases(STUDY, "en", sentence), ["authors"])

    def test_researcher_and_team_nouns_are_review_candidates(self):
        for locale, sentence in (
            ("en", "The researchers state the limit."),
            ("en", "The team states the limit."),
            ("ru", "Исследователи прямо пишут, что это не извлечение."),
            ("zh-Hans", "研究者们指出，这不是自动提取。"),
            ("zh-Hans", "两位作者明确指出这一点。"),
        ):
            with self.subTest(locale=locale, sentence=sentence):
                self.assertEqual([f.status for f in analyze_attribution(STUDY, locale, sentence)],
                                 ["REVIEW_REQUIRED"])

    def test_ru_debugger_command_is_not_team_attribution(self):
        # In Russian "команда" may mean a debugger instruction, not a team.
        text = "Для отладки достаточно, чтобы была хотя бы одна команда отладчика."
        self.assertEqual(analyze_attribution(STUDY, "ru", text), [])
        self.assertEqual(flagged_phrases(STUDY, "ru", text), [])

    def test_ru_explicit_research_team_still_requires_review(self):
        for text in ("Команда авторов описывает границы.",
                     "Команда исследователей описывает пределы."):
            with self.subTest(text=text):
                found = analyze_attribution(STUDY, "ru", text)
                self.assertEqual([f.status for f in found], ["REVIEW_REQUIRED"])

    def test_ru_genitive_current_study_is_not_downgraded(self):
        sentence = "По словам авторов этого исследования, результат ограничен."
        self.assertEqual([f.status for f in analyze_attribution(STUDY, "ru", sentence)],
                         ["DEFECT"])

    def test_other_paper_byline_ru_and_zh_remains_review(self):
        for locale, sentence in (
            ("ru", "В статье Ли и Кима авторы описывают предел."),
            ("zh-Hans", "李和金的论文中，作者们指出限制。"),
        ):
            with self.subTest(locale=locale):
                self.assertEqual([f.status for f in analyze_attribution(STUDY, locale, sentence)],
                                 ["EXTERNAL_REVIEW"])

    def test_explicit_current_study_chinese_two_authors_is_defect(self):
        self.assertEqual(
            [f.status for f in analyze_attribution(STUDY, "zh-Hans",
                "本研究的两位作者明确指出这一点。")],
            ["DEFECT"])

    def test_exit_codes_separate_defect_review_external_and_clean(self):
        # Direct classification control: files on disk are tested via CLI in integration.
        for phrase, expected in (
            ("The authors of this study state the limit.", "DEFECT"),
            ("The authors state the limit.", "REVIEW_REQUIRED"),
            ("Of the 2025 paper by Lee and Kim, the authors state the limit.", "EXTERNAL_REVIEW"),
        ):
            self.assertEqual(analyze_attribution(STUDY, "en", phrase)[0].status, expected)

    def test_file_mode_all_four_exit_states(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            base = Path(directory)
            files = [base / name for name in ("study.md", "en.md", "ru.md", "zh.md")]
            files[0].write_text(STUDY, encoding="utf-8")
            files[2].write_text(RU_R2, encoding="utf-8")
            files[3].write_text(ZH, encoding="utf-8")
            def probe(en_text):
                files[1].write_text(en_text, encoding="utf-8")
                return check_files([str(p) for p in files])
            self.assertEqual(probe(EN), 0)
            self.assertEqual(probe("The authors of this study state the limit."), 1)
            self.assertEqual(probe("The authors state the limit."), 3)
            self.assertEqual(probe("Of the 2025 paper by Lee and Kim, the authors state the limit."), 3)
            files[0].write_text("---\nauthors: [Pavel, Other]\n---\n", encoding="utf-8")
            self.assertEqual(probe(EN), 2)

    def test_missing_author_is_unknown_not_pass(self):
        with self.assertRaises(ValueError):
            flagged_phrases(STUDY.replace('author: "Pavel Valentov"\n', ''), "ru", RU_R2)

    def test_unsupported_authors_list_is_unknown_not_pass(self):
        with self.assertRaises(ValueError):
            flagged_phrases("---\nauthors: [Pavel, Other]\n---\n", "ru", RU_R2)

    def test_unsupported_locale_is_unknown_not_pass(self):
        with self.assertRaises(ValueError):
            flagged_phrases(STUDY, "fr", "Les auteurs disent...")


def check_files(paths: list[str]) -> int:
    if len(paths) != 4:
        print("Usage: --check STUDY.md EN.md RU.md ZH.md", file=sys.stderr)
        return 2
    try:
        source, en, ru, zh = (Path(x).read_text(encoding="utf-8") for x in paths)
        results = {locale: analyze_attribution(source, locale, article)
                   for locale, article in (("en", en), ("ru", ru), ("zh-Hans", zh))}
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"UNKNOWN: {exc}", file=sys.stderr)
        return 2
    for locale, findings in results.items():
        print(f"{locale}: " + (str([(f.status, f.phrase) for f in findings])
                              if findings else "NO_BOUNDED_PATTERN_MATCH"))
    if any(f.status == "DEFECT" for findings in results.values() for f in findings):
        return 1
    if any(findings for findings in results.values()):
        return 3
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        sys.exit(check_files(sys.argv[2:]))
    unittest.main()
