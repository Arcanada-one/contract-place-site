# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Offline tests of the roadmap compiler: a valid fixture compiles; every defect must stop the build.

Set ROADMAP_SOURCE_DIR to a clean checkout of the pin to run the same assertions on the real source.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import roadmap
from build_publication import run

IDS = roadmap.TASK_IDS
INTRO = "Knowledge Contract publishes bounded results while maintaining a transparent research programme. This fixture introduction is long enough to be accepted by the compiler."


def requires(n: int) -> list[str]:
    return [] if n == 1 else [IDS[n - 2]]


def card_text(n: int, reqs=None, owner="KC-Brain", priority="P1", extra="") -> str:
    reqs = requires(n) if reqs is None else reqs
    ident = IDS[n - 1]
    return (f"## {ident}\n\n### Fixture task {n}\n\n**Priority:** {priority} · **Owner:** {owner} · **Required outputs:** {', '.join(reqs) if reqs else 'none'}.\n\n"
            f"**Gap.** Gap sentence number {n} of the fixture.\n\n**Work.** Work with a [link](../ROADMAP.md) and `code` for {ident}.\n\n"
            f"**Deliverables.** Deliverable {n}.\n\n**Acceptance.** Acceptance criterion {n}.\n\n**Adversarial check.** Adversarial check {n}.\n\n"
            f"{extra}**Start boundary.** Start boundary {n}.\n\n")


def deps_json(**changes) -> dict:
    nodes = [{"id": IDS[n - 1], "priority": "P1", "content_owner": "KC-Brain", "requires": requires(n)} for n in range(1, 26)]
    data = {"kind": "roadmap-dependencies", "revision": "fixture.1", "baseline_commit": "a" * 40, "execution_authority": "tracker",
            "execution_bindings": roadmap.EXECUTION_BINDINGS, "target_dates": None, "edge_semantics": "requires_output", "nodes": nodes,
            "advisory_links": [{"from": "RM-03", "to": "RM-02", "kind": "informs_not_blocks"}]}
    data.update(changes)
    return data


class RoadmapCompiler(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        (self.source / "roadmap").mkdir(parents=True)
        run(["git", "init", "--quiet"], cwd=self.source)
        self.write()

    def tearDown(self):
        self.temp.cleanup()

    def write(self, tasks=None, deps=None, roadmap_md=None, delivery=None, remove=()):
        files = {
            "ROADMAP.md": roadmap_md or "---\ntitle: x\n---\n\n# Roadmap\n\n## 1. Scope\n\nThe roadmap fixture overview.\n",
            "roadmap/TASKS.md": tasks or "# Tasks\n\nIntro.\n\n" + "".join(card_text(n) for n in range(1, 26)),
            "roadmap/dependencies.json": json.dumps(deps or deps_json(), indent=2) + "\n",
            "roadmap/EXPERIMENTS.md": "# Experiments\n",
            "roadmap/FOUNDATIONS_RELEASE_PLAN.md": "# Foundations\n",
            "roadmap/SITE_DELIVERY.md": delivery or f"# Delivery\n\nSuggested public introduction:\n\n> {INTRO}\n",
        }
        for path, text in files.items():
            (self.source / path).write_text(text, encoding="utf-8")
        for path in remove:
            (self.source / path).unlink()
        run(["git", "add", "-A"], cwd=self.source)
        run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "--quiet", "--allow-empty", "-m", "fixture"], cwd=self.source)
        self.commit = run(["git", "rev-parse", "HEAD"], cwd=self.source).strip()
        self.manifest = {"schema_version": 1, "repository": roadmap.REPOSITORY, "commit": self.commit, "files": [
            {"path": p, "role": r, "sha256": sha256((self.source / p).read_bytes()).hexdigest()} for p, r in roadmap.FILES.items()]}
        self.save_manifest()

    def save_manifest(self):
        self.path = self.root / "roadmap-manifest.json"
        self.path.write_text(json.dumps(self.manifest))

    def compile(self):
        return roadmap.compile_roadmap(self.source, self.path, {})

    def fails(self, pattern):
        with self.assertRaisesRegex(ValueError, pattern):
            self.compile()

    def test_valid_roadmap_compiles_as_planned_work(self):
        record = self.compile()
        self.assertEqual([t["id"] for t in record["tasks"]], IDS)
        self.assertEqual({t["status"] for t in record["tasks"]}, {"planned"})
        self.assertEqual(record["required_edges"], 24)
        self.assertEqual(record["tasks"][1]["requires"], ["RM-01"])
        self.assertEqual(record["tasks"][0]["needed_by"], ["RM-02"])
        self.assertEqual(record["tasks"][1]["informed_by"], ["RM-03"])
        self.assertEqual(record["introduction"], INTRO)
        self.assertEqual(record["pin"]["commit"], self.commit)
        self.assertIn("Gap sentence number 7", record["tasks"][6]["fields"][0]["html"])
        self.assertIn(f"/blob/{self.commit}/ROADMAP.md", record["tasks"][0]["fields"][1]["html"])

    # --- the pin -----------------------------------------------------------------------------
    def test_pin_must_be_a_full_commit(self):
        for value in ("main", self.commit[:12], self.commit.upper(), ""):
            self.manifest["commit"] = value
            self.save_manifest()
            self.fails("40-character commit")

    def test_stale_pin_hash_mismatch_rejected(self):
        self.manifest["files"][1]["sha256"] = "0" * 64
        self.save_manifest()
        self.fails("stale roadmap pin")

    def test_source_at_another_commit_rejected(self):
        self.write(tasks="# Tasks\n\n" + "".join(card_text(n) for n in range(1, 26)) + "\nChanged.\n")
        self.manifest["commit"] = "f" * 40
        self.save_manifest()
        self.fails("differs from roadmap manifest")

    def test_uncommitted_source_rejected(self):
        (self.source / "ROADMAP.md").write_text("Changed after the pin")
        self.fails("uncommitted changes")

    def test_edit_after_pin_changes_the_hash(self):
        self.write(tasks="# Tasks\n\n" + "".join(card_text(n) for n in range(1, 26)) + "Edited after pinning.\n")
        stale = self.manifest  # re-pinned to the new commit, but the old recorded hashes
        stale["files"][1]["sha256"] = sha256(b"old").hexdigest()
        self.save_manifest()
        self.fails("stale roadmap pin")

    def test_file_list_must_be_exact(self):
        self.manifest["files"].pop()
        self.save_manifest()
        self.fails("must list exactly")

    # --- cards and graph ---------------------------------------------------------------------
    def test_missing_task_rejected(self):
        self.write(tasks="# Tasks\n\n" + "".join(card_text(n) for n in range(1, 25)))
        self.fails("RM-01..RM-25 once each .*missing \\['RM-25'\\]")

    def test_duplicate_task_rejected(self):
        self.write(tasks="# Tasks\n\n" + "".join(card_text(n) for n in range(1, 26)) + card_text(3))
        self.fails("RM-03 appears more than once")

    def test_missing_graph_node_rejected(self):
        deps = deps_json()
        deps["nodes"].pop()
        self.write(deps=deps)
        self.fails("exactly RM-01..RM-25")

    def test_changed_dependency_rejected(self):
        deps = deps_json()
        deps["nodes"][4]["requires"] = ["RM-01"]  # the RM-05 card still names RM-04
        self.write(deps=deps)
        self.fails("RM-05: card required outputs")

    def test_changed_priority_and_owner_rejected(self):
        deps = deps_json()
        deps["nodes"][2]["priority"] = "P0"
        self.write(deps=deps)
        self.fails("RM-03: card priority P1 differs")
        deps = deps_json()
        deps["nodes"][2]["content_owner"] = "Someone-Else"
        self.write(deps=deps)
        self.fails("RM-03: card owner")

    def test_dangling_required_edge_rejected(self):
        deps = deps_json()
        deps["nodes"][1]["requires"] = ["RM-99"]
        tasks = "# Tasks\n\n" + "".join(card_text(n, reqs=["RM-99"] if n == 2 else None) for n in range(1, 26))
        self.write(tasks=tasks, deps=deps)
        self.fails("dangling required dependency RM-99")

    def test_cycle_rejected_with_diagnostic(self):
        deps = deps_json()
        deps["nodes"][0]["requires"] = ["RM-25"]
        tasks = "# Tasks\n\n" + "".join(card_text(n, reqs=["RM-25"] if n == 1 else None) for n in range(1, 26))
        self.write(tasks=tasks, deps=deps)
        self.fails("Cyclic required dependency: RM-01 -> RM-25 -> .* -> RM-01")

    def test_self_dependency_and_bad_advisory_rejected(self):
        deps = deps_json()
        deps["nodes"][3]["requires"] = ["RM-04"]
        tasks = "# Tasks\n\n" + "".join(card_text(n, reqs=["RM-04"] if n == 4 else None) for n in range(1, 26))
        self.write(tasks=tasks, deps=deps)
        self.fails("depends on itself")
        self.write(deps=deps_json(advisory_links=[{"from": "RM-03", "to": "RM-77", "kind": "informs_not_blocks"}]))
        self.fails("Dangling advisory link")
        self.write(deps=deps_json(advisory_links=[{"from": "RM-03", "to": "RM-02", "kind": "requires_output"}]))
        self.fails("must be informs_not_blocks")

    def test_card_with_unexpected_field_rejected(self):
        tasks = "# Tasks\n\n" + "".join(card_text(n, extra="**Status.** completed\n\n" if n == 6 else "") for n in range(1, 26))
        self.write(tasks=tasks)
        self.fails("RM-06: card fields")

    def test_optional_scope_separation_field_only_after_work(self):
        def tasks(move_after_acceptance):
            out = []
            for n in range(1, 26):
                text = card_text(n)
                if n == 18:
                    scope = "**Scope separation.** Scope separation sentence.\n\n"
                    marker = "**Acceptance.**" if move_after_acceptance else "**Deliverables.**"
                    text = text.replace(marker, scope + marker)
                out.append(text)
            return "# Tasks\n\n" + "".join(out)
        self.write(tasks=tasks(False))
        card = next(t for t in self.compile()["tasks"] if t["id"] == "RM-18")
        self.assertEqual([f["label"] for f in card["fields"]][:4], ["Gap", "Work", "Scope separation", "Deliverables"])
        self.write(tasks=tasks(True))
        self.fails("RM-18: card fields")

    def test_execution_bindings_accepts_only_the_known_value(self):
        for text in ("RM-03 completed; RM-05 active, 60% done", "unverified", roadmap.EXECUTION_BINDINGS + " ", "", None, ["x"]):
            self.write(deps=deps_json(execution_bindings=text))
            self.fails("execution_bindings must be exactly")
        self.write(deps=deps_json())
        self.assertEqual(self.compile()["execution_bindings"], roadmap.EXECUTION_BINDINGS)  # negative control

    def test_unknown_top_level_key_rejected(self):
        self.write(deps=deps_json(task_states={"RM-03": "completed"}))
        self.fails("unexpected top-level key")

    def test_colon_label_cannot_bypass_the_field_set(self):
        for label in ("**Status:** active", "**Progress:** 60%", "**Status**: done"):
            tasks = "# Tasks\n\n" + "".join(
                card_text(n).replace("**Acceptance.**", label + "\n\n**Acceptance.**") if n == 5 else card_text(n) for n in range(1, 26))
            self.write(tasks=tasks)
            self.fails("RM-05: card fields")
        self.write()  # negative control: the unmodified cards compile
        self.compile()

    def test_scope_separation_allowed_only_on_rm18(self):
        scope = "**Scope separation.** Scope sentence.\n\n"
        tasks = "# Tasks\n\n" + "".join(
            card_text(n).replace("**Deliverables.**", scope + "**Deliverables.**") if n == 7 else card_text(n) for n in range(1, 26))
        self.write(tasks=tasks)
        self.fails("RM-07: card fields")

    def test_text_between_header_and_first_field_rejected(self):
        tasks = "# Tasks\n\n" + "".join(
            card_text(n).replace("**Gap.**", "Authored by somebody; status active.\n\n**Gap.**") if n == 4 else card_text(n) for n in range(1, 26))
        self.write(tasks=tasks)
        self.fails("RM-04: unexpected text between the card header")

    def test_tasks_preamble_is_kept_for_rendering(self):
        self.write(tasks="---\ntitle: t\n---\n\n# Tasks\n\nPreamble statement of authorship.\n\n" + "".join(card_text(n) for n in range(1, 26)))
        record = self.compile()
        self.assertIn("Preamble statement of authorship", record["tasks_intro_html"])

    def test_internal_host_and_mailbox_names_rejected(self):
        for leak in ("see arcana-devs host", "the dev-ai box", "file in inbox/contract-place", "via kc-mail", "node.tail1234.ts.net"):
            self.write(roadmap_md=f"---\ntitle: x\n---\n\n# Roadmap\n\n## 1. Scope\n\nText: {leak}.\n")
            self.fails("internal host name or mailbox path|private")

    # --- status and privacy ------------------------------------------------------------------
    def test_non_planned_status_without_evidence_rejected(self):
        for key, value in (("status", "completed"), ("status", "active"), ("progress", 40), ("started", "2026-11-07")):
            deps = deps_json()
            deps["nodes"][6][key] = value
            self.write(deps=deps)
            self.fails("no execution evidence")
        self.write(deps=deps_json(status="completed"))
        self.fails("carries execution state")

    def test_dates_are_not_published(self):
        self.write(deps=deps_json(target_dates={"RM-01": "2026-12-01"}))
        self.fails("no target dates")

    def test_private_identifiers_rejected(self):
        for leak in ("task 3f2b8c1e-9d4a-4e6f-8a1b-2c3d4e5f6a7b", "host 10.1.2.3", "/home/dev/inbox/x", "mail someone@example.org"):
            tasks = "# Tasks\n\n" + "".join(card_text(n) for n in range(1, 26))
            tasks = tasks.replace("Gap sentence number 9 of the fixture.", f"Gap sentence number 9 of the fixture. {leak}.")
            self.write(tasks=tasks)
            self.fails("private or internal detail")

    def test_introduction_is_taken_from_the_source(self):
        self.write(delivery="# Delivery\n\nNo suggested block here.\n")
        self.fails("Suggested public introduction")

    def test_raw_html_and_images_rejected(self):
        tasks = "# Tasks\n\n" + "".join(card_text(n) for n in range(1, 26)).replace("Deliverable 4.", "Deliverable <script>alert(1)</script>.")
        self.write(tasks=tasks)
        self.fails("Raw HTML")

    def test_missing_link_target_rejected(self):
        tasks = "# Tasks\n\n" + "".join(card_text(n) for n in range(1, 26)).replace("(../ROADMAP.md)", "(../NOPE.md)", 1)
        self.write(tasks=tasks)
        self.fails("Missing or escaping link target")

    def test_manuscript_link_uses_site_route_only_for_identical_bytes(self):
        (self.source / "papers").mkdir()
        (self.source / "papers/p.md").write_text("# P\n")
        roadmap_md = "# Roadmap\n\n## 1. Scope\n\nSee [the paper](papers/p.md).\n"
        self.write(roadmap_md=roadmap_md)
        digest = sha256((self.source / "papers/p.md").read_bytes()).hexdigest()
        same = roadmap.compile_roadmap(self.source, self.path, {"papers/p.md": {"route": "/en/science/p/", "source_sha256": digest}})
        self.assertIn('href="/en/science/p/"', same["overview_html"])
        other = roadmap.compile_roadmap(self.source, self.path, {"papers/p.md": {"route": "/en/science/p/", "source_sha256": "0" * 64}})
        self.assertIn(f"/blob/{self.commit}/papers/p.md", other["overview_html"])

    def test_card_prose_draft_link_gets_status_badge_in_each_locale(self):
        """Linked-status line is last child inside the field <dd>; Gap prose stays contiguous for check_roadmap."""
        from html.parser import HTMLParser
        from programme import (
            catalogue_title_for_locale,
            localize_catalogue_links,
            roadmap_linked_status,
            STATUS_LABELS,
            LOCALES,
        )
        from publication_checks import check_status_labels
        import check_roadmap as cr

        class DlChildCheck(HTMLParser):
            def __init__(self):
                super().__init__()
                self.stack = []
                self.bad = []
                self.status_parents = []

            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                parent = self.stack[-1] if self.stack else None
                if tag == "p" and parent == "dl":
                    self.bad.append("p-under-dl")
                if attrs.get("class") == "rm-linked-status":
                    self.status_parents.append(parent)
                self.stack.append(tag)

            def handle_endtag(self, tag):
                if self.stack and self.stack[-1] == tag:
                    self.stack.pop()
                elif tag in self.stack:
                    while self.stack and self.stack[-1] != tag:
                        self.stack.pop()
                    if self.stack:
                        self.stack.pop()

        (self.source / "papers").mkdir()
        (self.source / "papers/draft.md").write_text("# Draft\n")
        digest = sha256((self.source / "papers/draft.md").read_bytes()).hexdigest()
        gap = "See the [draft manuscript](../papers/draft.md) in source."
        tasks = "# Tasks\n\n" + "".join(
            card_text(n).replace(f"Gap sentence number {n} of the fixture.", gap, 1) if n == 1 else card_text(n)
            for n in range(1, 26)
        )
        self.write(tasks=tasks)
        manuscripts = {"papers/draft.md": {"route": "/en/science/draft/", "source_sha256": digest}}
        record = roadmap.compile_roadmap(self.source, self.path, manuscripts)
        field_html = record["tasks"][0]["fields"][0]["html"]
        self.assertIn('href="/en/science/draft/"', field_html)
        documents = [{
            "id": "draft",
            "route": "/en/science/draft/",
            "status": "research-draft",
            "title": "Draft Catalogue Title",
            "titleRu": "Черновик каталога",
            # no titleZhHans: zh-Hans must fall back to English catalogue title, never link text
        }]
        public = self.root / "public"
        gap_source = gap  # markdown form of the replaced Gap sentence
        expected_titles = {
            "en": "Draft Catalogue Title",
            "ru": "Черновик каталога",
            "zh-Hans": "Draft Catalogue Title",
        }
        # Fixture declares en + ru catalogue titles; zh-Hans falls back to English.
        localized_title_locales = [
            locale for locale in LOCALES if catalogue_title_for_locale(documents[0], locale)
        ]
        self.assertEqual(localized_title_locales, ["en", "ru"])
        for locale in LOCALES:
            body = localize_catalogue_links(field_html, documents, locale)
            status_line = roadmap_linked_status(field_html, documents, locale)
            label = STATUS_LABELS["research-draft"][locale]
            self.assertIn(f'href="/{locale}/science/draft/"', body)
            self.assertNotIn("status-badge", body)
            self.assertIn('class="rm-linked-status"', status_line)
            self.assertIn(f'<span class="status-badge">{label}</span>', status_line)
            self.assertIn(f">{expected_titles[locale]}</a>", status_line)
            self.assertNotIn(">draft manuscript</a>", status_line)
            # Mirror prerender placement: linked-status is last child inside the same <dd>.
            fragment = (
                f'<dl class="roadmap-fields"><div><dt>Gap</dt>'
                f'<dd class="source-body prose">{body}{status_line}</dd></div></dl>'
            )
            checker = DlChildCheck()
            checker.feed(f"<main>{fragment}</main>")
            self.assertEqual(checker.bad, [], f"{locale}: <p> must not be a direct child of <dl>")
            self.assertEqual(checker.status_parents, ["dd"], f"{locale}: rm-linked-status must sit inside <dd>")
            stream = cr.tokens(" ".join(cr.Page(f"<main>{fragment}</main>").text))
            self.assertTrue(
                cr.contains(stream, cr.tokens(cr.markdown_plain(gap_source))),
                f"{locale}: Gap source tokens must stay contiguous; badge tokens follow field text",
            )
            page = public / locale / "roadmap" / "index.html"
            page.parent.mkdir(parents=True, exist_ok=True)
            page.write_text(f"<main>{fragment}</main>", encoding="utf-8")
        # Parse every written roadmap page: no <p> direct child of <dl>.
        for locale in LOCALES:
            page_html = (public / locale / "roadmap" / "index.html").read_text(encoding="utf-8")
            checker = DlChildCheck()
            checker.feed(page_html)
            self.assertEqual(checker.bad, [], f"{locale} roadmap page has <p> under <dl>")
            self.assertEqual(checker.status_parents, ["dd"])
        self.assertGreaterEqual(check_status_labels(public, documents), 3)

    def test_card_prose_link_without_status_has_no_badge(self):
        from programme import localize_catalogue_links, roadmap_linked_status, LOCALES

        (self.source / "papers").mkdir()
        (self.source / "papers/accepted.md").write_text("# Accepted\n")
        digest = sha256((self.source / "papers/accepted.md").read_bytes()).hexdigest()
        gap = "See the [accepted manuscript](../papers/accepted.md) in source."
        tasks = "# Tasks\n\n" + "".join(
            card_text(n).replace(f"Gap sentence number {n} of the fixture.", gap, 1) if n == 1 else card_text(n)
            for n in range(1, 26)
        )
        self.write(tasks=tasks)
        manuscripts = {"papers/accepted.md": {"route": "/en/science/accepted/", "source_sha256": digest}}
        record = roadmap.compile_roadmap(self.source, self.path, manuscripts)
        field_html = record["tasks"][0]["fields"][0]["html"]
        documents = [{"id": "accepted", "route": "/en/science/accepted/", "title": "Accepted"}]
        for locale in LOCALES:
            body = localize_catalogue_links(field_html, documents, locale)
            sibling = roadmap_linked_status(field_html, documents, locale)
            self.assertIn(f'href="/{locale}/science/accepted/"', body)
            self.assertNotIn("status-badge", body)
            self.assertEqual(sibling, "")


@unittest.skipUnless(os.environ.get("ROADMAP_SOURCE_DIR"), "ROADMAP_SOURCE_DIR not set")
class RealSource(unittest.TestCase):
    def test_pinned_source_compiles(self):
        root = Path(__file__).resolve().parents[1]
        record = roadmap.compile_roadmap(Path(os.environ["ROADMAP_SOURCE_DIR"]).resolve(), root / "roadmap-manifest.json", {})
        self.assertEqual([t["id"] for t in record["tasks"]], IDS)
        self.assertEqual({t["status"] for t in record["tasks"]}, {"planned"})
        self.assertEqual(record["required_edges"], 45)
        self.assertEqual(len(record["advisory"]), 4)
        deps = json.loads((Path(os.environ["ROADMAP_SOURCE_DIR"]) / "roadmap/dependencies.json").read_text())
        for node, task in zip(deps["nodes"], record["tasks"]):
            self.assertEqual((node["id"], node["priority"], node["content_owner"], sorted(node["requires"])), (task["id"], task["priority"], task["owner"], task["requires"]))


if __name__ == "__main__":
    unittest.main()
