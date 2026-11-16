#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Synthetic localization refusal controls; no external review or live service."""
from html import escape
import json
from pathlib import Path
import tempfile
import unittest

from check_localization import Audit, LOCALES, ORIGIN


def page(title, description, locale, route, body, indexed=True, alternate_languages=LOCALES):
    if indexed:
        tail = route.split("/", 2)[2]
        seo = '<link rel="canonical" href="' + ORIGIN + route + '">'
        for lang in (*alternate_languages, "x-default"):
            target = "en" if lang == "x-default" else lang
            seo += f'<link rel="alternate" hreflang="{lang}" href="{ORIGIN}/{target}/{tail}">'
    else:
        seo = '<meta name="robots" content="noindex,follow">'
    return (f'<html lang="{locale}"><head><title>{escape(title)} — contract.place</title>'
            f'<meta name="description" content="{escape(description, quote=True)}">{seo}</head><body>'
            f'<main><div class="page-head"><h1 lang="{locale}">{escape(title)}</h1>'
            f'<p class="lead" lang="{locale}">{escape(description)}</p></div>{body}</main></body></html>')


class ReaderControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.public = Path(self.temp.name)
        self.documents, self.metadata, self.sidecar = [], [], []
        self.catalog = {"records": []}
        self.files = {}
        for index, slug in enumerate(("alpha", "beta")):
            digest = str(index + 1) * 64
            doc = {"slug": slug, "path": f"papers/{slug}/PAPER.md",
                   "title": "Synthetic " + slug, "summary": "Source description " + slug}
            self.documents.append(doc)
            texts = {
                "en": (doc["title"], doc["summary"], "<p>Source condition: retain the exception.</p><p>Unknown is not false.</p>"),
                "ru": ("Пример " + slug, "Описание примера " + slug, "<p>Исходное условие: сохранить исключение.</p><p>Неизвестное не означает ложное.</p>"),
                "zh-Hans": ("示例" + slug, "示例说明" + slug, "<p>来源条件：保留例外。</p><p>未知不等于假。</p>"),
            }
            states = {"ru": "reviewed" if index == 0 else "partially-reviewed",
                      "zh-Hans": "unreviewed" if index == 0 else "reviewed"}
            record = {"id": slug, "path": doc["path"], "route": f"/en/science/{slug}/",
                      "source_sha256": digest, "html": texts["en"][2], "renditions": {}, "localization": {}}
            allowed = ["en", "ru"] + (["zh-Hans"] if index else [])
            for locale, (title, summary, html) in texts.items():
                route = f"/{locale}/science/{slug}/"
                state = states.get(locale)
                if state:
                    self.metadata.append({"work": slug, "language": locale, "source_path": doc["path"],
                                          "source_sha256": digest, "title": title, "summary": summary, "status": "unreviewed"})
                    self.sidecar.append({"work": slug, "language": locale, "source": {"path": doc["path"], "sha256": digest}})
                    record["renditions"][locale] = {"state": state, "language": locale, "title": title, "html": html,
                                                     "source": {"sha256": digest}}
                    record["localization"][locale] = {"title": title, "summary": summary, "status": "unreviewed"}
                label = (f'<aside class="rendition-state" data-state="{state}" data-body-language="{locale}" '
                         'data-independent-source="false">Declared state</aside>') if state else ""
                body = label + f'<div class="source-body prose" lang="{locale}">{html}</div>'
                path = self.public / route.lstrip("/") / "index.html"
                path.parent.mkdir(parents=True)
                path.write_text(page(title, summary, locale, route, body, state != "unreviewed", allowed), encoding="utf-8")
                self.files[slug, locale] = path
            self.catalog["records"].append(record)

    def audit(self):
        result = Audit(self.public)
        result.readers(self.catalog, self.documents, self.metadata, self.sidecar)
        return result

    def codes(self):
        return {error["code"] for error in self.audit().errors}

    def test_positive_multiple_works_and_mixed_review_states(self):
        result = self.audit()
        self.assertEqual(result.errors, [])
        self.assertEqual(result.counts["reader_pages"], 6)

    def test_missing_body_is_not_replaced_by_source_file_count(self):
        self.catalog["records"][1]["renditions"]["ru"].pop("html")
        self.assertIn("BODY_EMPTY", self.codes())
        self.assertIn("BODY_CONTENT", self.codes())

    def test_missing_registered_work_is_not_hidden_by_duplicate_count(self):
        self.catalog["records"].pop()
        self.assertIn("INVENTORY", self.codes())

    def test_missing_metadata_field_refused(self):
        self.catalog["records"][0]["localization"]["ru"].pop("summary")
        self.assertIn("METADATA_SOURCE", self.codes())

    def test_actual_wrong_body_language_refused(self):
        path = self.files["alpha", "ru"]
        path.write_text(path.read_text().replace('class="source-body prose" lang="ru"',
                                                 'class="source-body prose" lang="en"'))
        self.assertIn("BODY_LANGUAGE", self.codes())

    def test_actual_missing_paragraph_refused(self):
        path = self.files["beta", "zh-Hans"]
        path.write_text(path.read_text().replace("<p>未知不等于假。</p>", ""))
        self.assertIn("BODY_CONTENT", self.codes())

    def test_wrong_locale_head_and_description_refused(self):
        path = self.files["alpha", "ru"]
        value = path.read_text().replace("<title>Пример alpha", "<title>Synthetic alpha")
        value = value.replace('name="description" content="Описание примера alpha"',
                              'name="description" content="Source description alpha"')
        path.write_text(value)
        codes = self.codes()
        self.assertIn("PAGE_TITLE", codes)
        self.assertIn("META_DESCRIPTION", codes)

    def test_declared_draft_title_suffix_does_not_allow_arbitrary_status(self):
        self.documents[0]["status"] = "research-draft"
        path = self.files["alpha", "en"]
        path.write_text(path.read_text().replace("<title>Synthetic alpha —", "<title>Synthetic alpha (Research draft) —"))
        self.assertEqual(self.audit().errors, [])
        path.write_text(path.read_text().replace("(Research draft)", "(Accepted)"))
        self.assertIn("PAGE_TITLE", self.codes())

    def test_compiled_and_actual_english_fallback_still_refused(self):
        record = self.catalog["records"][0]
        rd = record["renditions"]["ru"]
        path = self.files["alpha", "ru"]
        path.write_text(path.read_text().replace(rd["html"], record["html"]))
        rd["html"] = record["html"]
        codes = self.codes()
        self.assertIn("ENGLISH_FALLBACK", codes)
        self.assertIn("BODY_SCRIPT", codes)

    def test_unreviewed_canonical_promotion_refused(self):
        path = self.files["alpha", "zh-Hans"]
        path.write_text(path.read_text().replace('<meta name="robots" content="noindex,follow">',
                                                f'<link rel="canonical" href="{ORIGIN}/zh-Hans/science/alpha/">'))
        self.assertIn("INDEXING_STATE", self.codes())

    def test_hidden_translation_refused(self):
        path = self.files["beta", "ru"]
        path.write_text(path.read_text().replace('<div class="source-body prose"', '<div hidden class="source-body prose"'))
        self.assertIn("BODY_HIDDEN", self.codes())

    def test_route_replacement_does_not_preserve_inventory(self):
        result = Audit(self.public)
        old = self.files["beta", "ru"]
        old.rename(old.parent / "replacement.html")
        result.retained_routes({"routes": ["/ru/science/beta/", "/en/science/alpha/"]})
        self.assertIn("ROUTE_LOST", {error["code"] for error in result.errors})

    def test_old_html_cannot_mask_work_removed_from_both_catalogues(self):
        retained = {"canonical_readers": [{"id": "beta", "path": "papers/beta/PAPER.md", "route": "/en/science/beta/"}],
                    "journal_slugs": [], "article_ids": [], "roadmap_task_ids": []}
        self.catalog["records"].pop()
        self.documents.pop()
        result = Audit(self.public)
        result.retained_content(self.catalog, self.documents, retained)
        self.assertTrue(self.files["beta", "ru"].exists())
        self.assertIn("CONTENT_LOST", {error["code"] for error in result.errors})

    def test_source_to_compiled_omission_refused_even_if_dom_matches(self):
        result = Audit(self.public)
        source = "# Source title\n\nRetain the exception.\n\nUnknown is not false.\n"
        result.source_body(source, "<p>Retain the exception.</p><p>Unknown is not false.</p>", "positive")
        self.assertEqual(result.errors, [])
        result.source_body(source, "<p>Retain the exception.</p>", "negative")
        self.assertEqual(result.errors[-1]["code"], "SOURCE_BODY")

    def test_programme_badge_projection_preserves_chinese_adjacency(self):
        result = Audit(self.public)
        source = "# 指南\n\n从[意义桥梁](paper.md)发展；这不是普遍理解理论。\n"
        compiled = '<p>从<a href="/zh-Hans/science/example/">意义桥梁</a> <span class="status-badge">研究草稿</span>发展；这不是普遍理解理论。</p>'
        result.source_body(source, compiled, "positive", ignore_status_badges=True)
        self.assertEqual(result.errors, [])
        result.source_body(source, compiled.replace("这不是", "这是"), "negative", ignore_status_badges=True)
        self.assertEqual(result.errors[-1]["code"], "SOURCE_BODY")


class RoadmapControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source, self.public = root / "source", root / "public"
        (self.source / "roadmap").mkdir(parents=True)
        (self.source / "roadmap/dependencies.json").write_text(json.dumps({"nodes": [{"id": "RM-01"}]}))
        fields = ("gap", "work", "deliverables", "acceptance", "adversarial", "start")
        labels = ("Gap", "Work", "Deliverables", "Acceptance", "Adversarial check", "Start boundary")
        english_fields = {key: "Synthetic " + key + ". Keep the declared limit." for key in fields}
        title = "Synthetic Task: Preserve a condition"
        english_preamble = "# Task definitions\n\nThese are planned synthetic tasks, not completed evidence."
        original = english_preamble + "\n\n## RM-01\n\n### " + title
        original += "\n\n**Priority:** P0 · **Owner:** Example · **Required outputs:** none.\n\n"
        original += "\n\n".join(f"**{label}:** {english_fields[key]}" for key, label in zip(fields, labels))
        (self.source / "roadmap/TASKS.md").write_text(original + "\n")
        intro = "This is a synthetic roadmap introduction. It describes a bounded plan and does not claim that its experiments have been executed."
        (self.source / "roadmap/SITE_DELIVERY.md").write_text("Suggested public introduction:\n\n> " + intro + "\n")
        self.catalog = {"records": [], "roadmap": {"translations": {}}}
        for locale in LOCALES:
            if locale == "en":
                texts = english_fields
                heading, overview, preamble, introduction = title, "A synthetic source overview.", english_preamble, intro
            elif locale == "ru":
                texts = {key: "Синтетический пример " + key + ". Сохранить указанное ограничение." for key in fields}
                heading, overview = "Пример задачи: Сохранить условие", "Синтетический обзор исходника."
                preamble, introduction = "# Определения задач\n\nЭто планы, не выполненные свидетельства.", "Синтетическое вступление."
            else:
                texts = {key: "合成示例" + key + "。保留已声明的限制。" for key in fields}
                heading, overview = "示例任务: 保留条件", "合成来源概述。"
                preamble, introduction = "# 任务定义\n\n这是计划，不是已完成证据。", "合成介绍。"
            overview_file = self.source / ("ROADMAP.md" if locale == "en" else f"roadmap/ROADMAP.full.{locale}.md")
            overview_file.write_text("# Overview\n\n" + overview + "\n")
            preamble_body = preamble.split("\n\n", 1)[1]
            view = {"language": locale, "translation_state": "unreviewed", "introduction": introduction,
                    "overview_html": "<p>" + overview + "</p>",
                    "tasks_intro_html": "<p>" + preamble_body + "</p>",
                    "tasks": [{"id": "RM-01", "title": heading, "status": "planned",
                               "fields": [{"key": key, "html": "<p>" + texts[key] + "</p>"} for key in fields]}]}
            if locale == "en":
                self.catalog["roadmap"].update(view)
            else:
                self.catalog["roadmap"]["translations"][locale] = view
                raw = {"language": locale, "introduction": introduction, "tasks_intro": preamble, "start": texts["start"],
                       "tasks": [{"id": "RM-01", "title": heading, "display_name": heading.split(":")[0],
                                  "fields": {key: value for key, value in texts.items() if key != "start"}}]}
                (self.source / f"roadmap/TASKS.{locale}.json").write_text(json.dumps(raw, ensure_ascii=False))
            short, _, subtitle = heading.partition(": ")
            card = ('<article class="roadmap-card" data-task-id="RM-01"><h3><a class="rm-name" lang="' + locale + '">'
                    + short + '</a><span class="rm-subtitle" lang="' + locale + '">' + subtitle + '</span></h3>'
                    + '<dl class="roadmap-fields" lang="' + locale + '">')
            card += "".join("<div><dt>" + key + "</dt><dd><p>" + texts[key] + "</p></dd></div>" for key in fields)
            card += "</dl></article>"
            body = ('<section id="roadmap-section-overview"><div class="source-body" lang="' + locale + '">'
                    + view["overview_html"] + '</div></section><section aria-labelledby="roadmap-tasks">'
                    + '<div class="source-body" lang="' + locale + '">' + view["tasks_intro_html"] + "</div>"
                    + card + "</section>")
            route = "/" + locale + "/roadmap/"
            path = self.public / locale / "roadmap/index.html"
            path.parent.mkdir(parents=True)
            path.write_text(page(heading, introduction, locale, route, body))

    def audit(self):
        result = Audit(self.public)
        result.roadmaps(self.catalog, self.source)
        return result

    def test_source_json_and_actual_all_fields_positive(self):
        result = self.audit()
        self.assertEqual(result.errors, [])
        self.assertEqual(result.counts["roadmap_cards"], 3)
        self.assertEqual(result.counts["roadmap_fields"], 18)

    def test_removed_compiled_field_refused_against_source_json(self):
        self.catalog["roadmap"]["translations"]["ru"]["tasks"][0]["fields"].pop(3)
        self.assertIn("INVENTORY", {e["code"] for e in self.audit().errors})

    def test_changed_actual_field_language_refused(self):
        path = self.public / "zh-Hans/roadmap/index.html"
        path.write_text(path.read_text().replace('class="roadmap-fields" lang="zh-Hans"', 'class="roadmap-fields" lang="en"'))
        self.assertIn("BODY_LANGUAGE", {e["code"] for e in self.audit().errors})

    def test_missing_task_refused_against_dependency_identity(self):
        self.catalog["roadmap"]["translations"]["ru"]["tasks"] = []
        self.assertIn("INVENTORY", {e["code"] for e in self.audit().errors})

    def test_field_omission_in_source_text_projection_refused(self):
        self.catalog["roadmap"]["translations"]["zh-Hans"]["tasks"][0]["fields"][3]["html"] = "<p>合成示例acceptance。</p>"
        self.assertIn("SOURCE_BODY", {e["code"] for e in self.audit().errors})


if __name__ == "__main__":
    unittest.main()
