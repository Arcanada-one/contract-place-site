# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Source-bound roadmap localization controls, using a real temporary Git repo.

The fixture is synthetic. Passing these tests does not establish fidelity of
the authored translations, independent review, or execution/release authority.
Adverse edits are committed and their outer manifest is refreshed, so a dirty
checkout or stale outer hash cannot masquerade as the intended refusal.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
import unittest

import roadmap
import roadmap_localization as localization
from test_roadmap import INTRO, card_text, deps_json


def rendered_text(html):
    class Text(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts = []

        def handle_data(self, data):
            self.parts.append(data)

    parser = Text()
    parser.feed(html)
    return "".join(parser.parts)


class RoadmapLocalization(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        (self.source / "roadmap").mkdir(parents=True)
        self.git("init", "--quiet")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        cards = []
        for n in range(1, 26):
            card = card_text(n).replace(f"Start boundary {n}.", "Start only within reviewed scope.")
            card = card.replace(f"Gap sentence number {n} of the fixture.",
                                f"Gap sentence number {n} on 8 November 2026; previous 8 November.")
            card = card.replace("[link](../ROADMAP.md)", "[link](../ROADMAP.md#1-scope)")
            card = card.replace(f"for RM-{n:02d}.", f"for RM-{n:02d}; preserve $x=1$.")
            if n == 18:
                card = card.replace("**Deliverables.**", "**Scope separation.** Keep the baseline separate.\n\n**Deliverables.**")
            cards.append(card)
        files = {
            "ROADMAP.md": "# Roadmap\n\n## 1. Scope\n\nThe fixture overview has a [task](roadmap/TASKS.md#rm-01).\n",
            "roadmap/TASKS.md": "# Tasks\n\nIntro.\n\n" + "".join(cards),
            "roadmap/dependencies.json": json.dumps(deps_json()) + "\n",
            "roadmap/EXPERIMENTS.md": "# Experiments\n",
            "roadmap/FOUNDATIONS_RELEASE_PLAN.md": "# Foundations\n",
            "roadmap/SITE_DELIVERY.md": f"# Delivery\n\nSuggested public introduction:\n\n> {INTRO}\n",
        }
        for relative, text in files.items():
            (self.source / relative).write_text(text, encoding="utf-8")
        self.base = self.commit("English source")
        self.config = {
            "schema_version": 1, "kind": "arcanada-roadmap-localizations",
            "source": {"revision": self.base, "files": self.source_hashes()},
            "translations": {locale: {"overview": f"roadmap/ROADMAP.full.{locale}.md",
                                      "tasks": f"roadmap/TASKS.{locale}.json", "status": "author-draft"}
                             for locale in localization.LOCALES},
        }
        self.write_json(localization.INDEX, self.config)
        for locale in localization.LOCALES:
            self.write_json(f"roadmap/TASKS.{locale}.json", self.translated_cards(locale))
            overview = ("# Дорожная карта\n\n## 1. Область {#1-scope}\n\n"
                        "Обзор примера содержит [задачу](TASKS.md#rm-01).\n" if locale == "ru" else
                        "# 路线图\n\n## 1. 范围 {#1-scope}\n\n示例概述包含[任务](TASKS.md#rm-01)。\n")
            (self.source / f"roadmap/ROADMAP.full.{locale}.md").write_text(overview, encoding="utf-8")
        self.candidate = self.commit("Authored fixture translations")
        self.refresh_pin()

    def git(self, *args):
        return roadmap.run(["git", *args], cwd=self.source).strip()

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "--quiet", "--allow-empty", "-m", message)
        return self.git("rev-parse", "HEAD")

    def source_hashes(self):
        return {p: sha256((self.source / p).read_bytes()).hexdigest() for p in localization.SOURCE_FILES}

    def write_json(self, relative, value):
        (self.source / relative).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def read_json(self, relative):
        return json.loads((self.source / relative).read_text(encoding="utf-8"))

    def refresh_pin(self):
        files = dict(roadmap.FILES)
        if (self.source / localization.INDEX).exists():
            files.update(localization.FILES)
        self.pin = {"schema_version": 1, "repository": roadmap.REPOSITORY,
                    "commit": self.git("rev-parse", "HEAD"),
                    "files": [{"path": p, "role": role, "sha256": sha256((self.source / p).read_bytes()).hexdigest()}
                              for p, role in files.items()]}
        self.pin_path = self.root / "roadmap-manifest.json"
        self.pin_path.write_text(json.dumps(self.pin), encoding="utf-8")

    def reset_candidate(self):
        self.git("reset", "--quiet", "--hard", self.candidate)
        self.refresh_pin()

    def compile(self):
        return roadmap.compile_roadmap(self.source, self.pin_path, {})

    def commit_and_refuse(self, expected):
        self.commit("Adverse fixture, with valid outer pin")
        self.refresh_pin()
        self.assertEqual(self.git("status", "--porcelain"), "")
        with self.assertRaisesRegex(ValueError, "ROADMAP_LOCALIZATION: .*" + expected):
            self.compile()

    @staticmethod
    def translated_cards(locale):
        ru = locale == "ru"
        data = {
            "schema_version": 1, "language": locale,
            "introduction": ("Knowledge Contract публикует ограниченные результаты и ведёт прозрачную исследовательскую программу. Введение примера достаточно подробно для проверки компилятора." if ru else
                             "Knowledge Contract 发布有界结果并维护透明的研究计划。本示例导言足够完整，可以由编译器接受并验证。"),
            "tasks_intro": "# Задачи\n\nВведение." if ru else "# 任务\n\n导言。",
            "start": "Начинать только в пределах проверенной области." if ru else "只在已审查范围内开始。",
            "tasks": [],
        }
        for n in range(1, 26):
            ident = f"RM-{n:02d}"
            name = f"Пример задачи {n}" if ru else f"示例任务{n}"
            fields = {
                "gap": (f"Предложение о пробеле {n} от 8 ноября 2026; прежде 8 ноября." if ru else
                        f"示例的缺口段落{n}，日期为2026年11月8日；之前为11月8日。"),
                "work": (f"Работа со [ссылкой](../ROADMAP.md#1-scope) и `code` для {ident}; сохранить $x=1$." if ru else
                         f"使用[链接](../ROADMAP.md#1-scope)和 `code` 处理 {ident}；保留 $x=1$。"),
                "deliverables": f"Результат {n}." if ru else f"交付物{n}。",
                "acceptance": f"Критерий приёмки {n}." if ru else f"验收标准{n}。",
                "adversarial": f"Опровергающая проверка {n}." if ru else f"对抗检查{n}。",
            }
            if n == 18:
                fields["scope"] = "Сохранять разделение базовой области." if ru else "保持基线范围独立。"
            data["tasks"].append({"id": ident, "title": name + (": Проверить пример" if ru else ": 检查示例"),
                                  "display_name": name, "fields": fields})
        return data

    def test_valid_before_and_after_preserves_authority_graph_and_status(self):
        self.git("checkout", "--quiet", self.base)
        self.refresh_pin()
        before = self.compile()
        self.assertNotIn("translations", before)
        self.git("checkout", "--quiet", self.candidate)
        self.refresh_pin()
        after = self.compile()
        # Rendered Git URLs correctly advance to the new source pin; the
        # task definitions and authoritative graph columns do not change.
        self.assertEqual([{k: v for k, v in t.items() if k != "fields"} for t in after["tasks"]],
                         [{k: v for k, v in t.items() if k != "fields"} for t in before["tasks"]])
        for key in ("required_edges", "advisory", "execution_authority", "execution_bindings", "edge_semantics"):
            self.assertEqual(after[key], before[key])
        self.assertEqual(after["required_edges"], 24)
        self.assertEqual(set(after["translations"]), {"ru", "zh-Hans"})
        immutable = ("id", "anchor", "priority", "owner", "status", "requires", "needed_by", "informs", "informed_by")
        for locale, view in after["translations"].items():
            self.assertEqual(view["translation_state"], "unreviewed")
            self.assertEqual(len(view["tasks"]), 25)
            for original, translated in zip(after["tasks"], view["tasks"]):
                self.assertEqual({k: translated[k] for k in immutable}, {k: original[k] for k in immutable})
                self.assertEqual(translated["status"], "planned")
                self.assertEqual([f["key"] for f in translated["fields"]], [f["key"] for f in original["fields"]])
            first_work = next(f["html"] for f in view["tasks"][0]["fields"] if f["key"] == "work")
            self.assertIn(f"/blob/{self.candidate}/ROADMAP.md#1-scope", first_work)
            self.assertIn("<code>code</code>", first_work)
            self.assertIn('<span class="math inline">', first_work)
            self.assertIn("x=1", "".join(rendered_text(first_work).split()))
        evidence = after["translation_provenance"]
        self.assertEqual(evidence["source"]["revision"], self.base)
        self.assertEqual(evidence["semantic_review"], "not_verified")
        self.assertEqual(evidence["status"], "author-draft")

    def test_harmless_translation_edit_uses_new_pin_without_changing_source(self):
        data = self.read_json("roadmap/TASKS.ru.json")
        data["tasks"][0]["fields"]["acceptance"] = "Уточнённый критерий приёмки 1."
        self.write_json("roadmap/TASKS.ru.json", data)
        changed = self.commit("Harmless fixture wording")
        self.refresh_pin()
        result = self.compile()
        self.assertEqual(result["pin"]["commit"], changed)
        self.assertEqual(result["translation_provenance"]["source"]["revision"], self.base)
        field = next(f for f in result["translations"]["ru"]["tasks"][0]["fields"] if f["key"] == "acceptance")
        self.assertIn("Уточнённый", field["html"])

    def test_missing_card_or_field_and_duplicate_card(self):
        for defect, pattern in (("card", "does not contain every task"), ("field", "missing or unknown fields"), ("duplicate", "unknown or duplicate task")):
            with self.subTest(defect=defect):
                self.reset_candidate()
                data = self.read_json("roadmap/TASKS.ru.json")
                if defect == "card":
                    data["tasks"].pop()
                elif defect == "field":
                    del data["tasks"][0]["fields"]["acceptance"]
                else:
                    data["tasks"][-1] = deepcopy(data["tasks"][0])
                self.write_json("roadmap/TASKS.ru.json", data)
                self.commit_and_refuse(pattern)

    def test_translation_cannot_inject_status_owner_or_authority(self):
        for key in ("status", "owner", "execution_authority"):
            with self.subTest(key=key):
                self.reset_candidate()
                data = self.read_json("roadmap/TASKS.ru.json")
                data["tasks"][0][key] = "completed" if key == "status" else "Author"
                self.write_json("roadmap/TASKS.ru.json", data)
                self.commit_and_refuse("missing or unknown fields")

    def test_index_cannot_claim_semantic_review(self):
        data = self.read_json(localization.INDEX)
        data["translations"]["ru"]["status"] = "reviewed"
        self.write_json(localization.INDEX, data)
        self.commit_and_refuse("unexpected path or review claim")

    def test_stale_english_bytes_refused_even_with_fresh_outer_pin(self):
        path = self.source / "ROADMAP.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nChanged English context.\n", encoding="utf-8")
        self.commit_and_refuse("translation is stale")

    def test_wrong_historical_source_digest_refused(self):
        data = self.read_json(localization.INDEX)
        data["source"]["files"]["ROADMAP.md"] = "0" * 64
        self.write_json(localization.INDEX, data)
        self.commit_and_refuse("source digest does not match the historical revision")

    def test_identical_tree_on_unrelated_history_is_not_an_ancestor(self):
        tree = self.git("rev-parse", self.base + "^{tree}")
        unrelated = self.git("commit-tree", tree, "-m", "Independent root with identical English files")
        self.assertNotEqual(unrelated, self.base)
        data = self.read_json(localization.INDEX)
        data["source"]["revision"] = unrelated
        self.write_json(localization.INDEX, data)
        self.commit_and_refuse("source revision or ancestry could not be verified")

    def test_changed_rendition_link_math_and_code_refused(self):
        for old, new, pattern in (("../ROADMAP.md#1-scope", "../ROADMAP.md#other", "changed a source link"),
                                  ("$x=1$", "$x=2$", "changed opaque"),
                                  ("`code`", "код", "changed opaque")):
            with self.subTest(old=old):
                self.reset_candidate()
                data = self.read_json("roadmap/TASKS.ru.json")
                data["tasks"][0]["fields"]["work"] = data["tasks"][0]["fields"]["work"].replace(old, new)
                self.write_json("roadmap/TASKS.ru.json", data)
                self.commit_and_refuse(pattern)

    def test_new_source_binding_cannot_hide_unupdated_link_math_or_code(self):
        for old, new, pattern in (("../ROADMAP.md#1-scope", "../ROADMAP.md", "changed a source link"),
                                  ("$x=1$", "$x=2$", "changed opaque"),
                                  ("`code`", "plain code", "changed opaque")):
            with self.subTest(old=old):
                self.reset_candidate()
                path = self.source / "roadmap/TASKS.md"
                path.write_text(path.read_text(encoding="utf-8").replace(old, new, 1), encoding="utf-8")
                source_revision = self.commit("New English source")
                config = self.read_json(localization.INDEX)
                config["source"] = {"revision": source_revision, "files": self.source_hashes()}
                self.write_json(localization.INDEX, config)
                self.commit_and_refuse(pattern)

    def test_wrong_script_refused(self):
        data = self.read_json("roadmap/TASKS.ru.json")
        data["tasks"][0]["fields"]["acceptance"] = "English acceptance criterion 1."
        self.write_json("roadmap/TASKS.ru.json", data)
        self.commit_and_refuse("not in the declared language")

    def test_source_with_different_start_conditions_refused(self):
        path = self.source / "roadmap/TASKS.md"
        path.write_text(path.read_text(encoding="utf-8").replace("Start only within reviewed scope.", "Start only after special review.", 1), encoding="utf-8")
        revision = self.commit("Distinct source start condition")
        config = self.read_json(localization.INDEX)
        config["source"] = {"revision": revision, "files": self.source_hashes()}
        self.write_json(localization.INDEX, config)
        self.commit_and_refuse("shared start translation cannot cover different source conditions")


class CalendarParity(unittest.TestCase):
    def test_full_and_yearless_dates_match_across_three_languages(self):
        source = "On 8 November 2026 and 8 November, retain 31 records."
        translations = ("На 8 ноября 2026 и 8 ноября сохранить 31 запись.",
                        "于2026年11月8日和11月8日，保留31项记录。",
                        "于2026年十一月8日和十一月8日，保留31项记录。")
        expected = (Counter({"31": 1}), Counter({(2026, 11, 8): 1, (None, 11, 8): 1}))
        for text in (source, *translations):
            with self.subTest(text=text):
                self.assertEqual(localization.numeric_facts(text), expected)
                localization.parity(source, text, "ROADMAP.md", "ROADMAP.md", "calendar")

    def test_changed_day_month_and_added_year_refused(self):
        for changed in ("于2026年11月9日和11月8日，保留31项记录。",
                        "于2026年12月8日和11月8日，保留31项记录。",
                        "于2026年11月8日和2026年11月8日，保留31项记录。"):
            with self.subTest(changed=changed), self.assertRaisesRegex(ValueError, "changed dates"):
                localization.parity("On 8 November 2026 and 8 November, retain 31 records.", changed,
                                    "ROADMAP.md", "ROADMAP.md", "calendar")

    def test_non_date_numbers_stay_exact_and_invalid_dates_refuse(self):
        with self.assertRaisesRegex(ValueError, "changed numbers"):
            localization.parity("On 8 November 2026 retain 31 records.", "于2026年11月8日保留32项记录。",
                                "ROADMAP.md", "ROADMAP.md", "count")
        for text in ("31 November 2026", "31 ноября 2026", "2026年11月31日"):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, "invalid calendar date"):
                localization.numeric_facts(text)

    def test_month_names_cannot_be_parsed_as_partial_tokens(self):
        # 十三 is thirteen, not the suffix 三 (three); 二十一 is twenty-one,
        # not its suffix 十一 (eleven). A partial-token parse changes the date.
        for source, invalid in (("On 8 March.", "于十三月8日。"),
                                ("On 8 November.", "于二十一月8日。"),
                                ("On 8 March.", "On 8 Marching."),
                                ("На 8 марта.", "На 8 мартаневерно.")):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                localization.parity(source, invalid, "ROADMAP.md", "ROADMAP.md", "calendar")


if __name__ == "__main__":
    unittest.main()
