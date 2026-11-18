# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Finite source-identity and proposal-boundary controls for the CW reader."""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from coordinated_work import compile_coordinated_work, GRAPH_PATH, PAGE_PATHS, validate_graph


class CoordinatedWorkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.manifest_path = self.root / "manifest.json"
        self.graph = {
            "schema": "CoordinatedWorkExecutionProposal/v1", "programme_id": "fixture-only",
            "status": "proposed", "external_task_id": None, "execution_assigned": False,
            "current_task_statuses_included": False,
            "epics": [{"id": "EP1"}], "papers": [{"id": "P1"}], "hypotheses": [{"id": "H1"}],
            "tasks": [
                {"id": "A", "status": "proposed", "external_task_id": None, "execution_assigned": False, "dependencies": []},
                {"id": "B", "status": "proposed", "external_task_id": None, "execution_assigned": False, "dependencies": [{"task_id": "A"}]},
            ],
        }
        (self.source / GRAPH_PATH).parent.mkdir(parents=True)
        (self.source / GRAPH_PATH).write_text(json.dumps(self.graph), encoding="utf-8")
        for language, path in PAGE_PATHS.items():
            title, heading = {"en": ("Fixture programme", "Scope"), "ru": ("Программа примера", "Содержание"), "zh-Hans": ("示例计划", "范围")}[language]
            (self.source / path).write_text(f"# {title}\n\n## {heading}\n\nFixture body. [Graph](execution-graph.json).\n", encoding="utf-8")
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.pin()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.source, check=True, capture_output=True, text=True).stdout.strip()

    def pin(self):
        self.git("add", ".")
        self.git("commit", "--allow-empty", "-qm", "Synthetic compiler fixture; never published")
        self.commit = self.git("rev-parse", "HEAD")
        self.manifest = {"schema_version": 1, "repository": "Arcanada-one/knowledge-contract", "commit": self.commit,
                         "files": [{"path": path, "sha256": sha256((self.source / path).read_bytes()).hexdigest()}
                                   for path in [*PAGE_PATHS.values(), GRAPH_PATH]]}
        self.save_manifest()

    def save_manifest(self):
        self.manifest_path.write_text(json.dumps(self.manifest), encoding="utf-8")

    def compile(self):
        return compile_coordinated_work(self.source, self.manifest_path, self.commit)

    def test_three_locales_render_with_exact_source_and_no_execution_state(self):
        result = self.compile()
        self.assertEqual(result["counts"], {"epics": 1, "packages": 2, "edges": 1, "papers": 1, "hypotheses": 1})
        self.assertFalse(result["execution_state_published"])
        self.assertEqual(result["status"], "proposed")
        for language, page in result["pages"].items():
            self.assertEqual(page["route"], f"/{language}/roadmap/coordinated-work/")
            self.assertIn(f"/blob/{self.commit}/{GRAPH_PATH}", page["html"])
            self.assertEqual(len(page["toc"]), 1)

    def test_pins_cannot_be_confused_with_another_roadmap_revision(self):
        with self.assertRaisesRegex(ValueError, "exact roadmap"):
            compile_coordinated_work(self.source, self.manifest_path, "0" * 40)

    def test_missing_language_refused(self):
        self.manifest["files"] = self.manifest["files"][1:]
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "all three"):
            self.compile()

    def test_hash_mismatch_refused(self):
        self.manifest["files"][0]["sha256"] = "0" * 64
        self.save_manifest()
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.compile()

    def test_dirty_source_refused(self):
        (self.source / PAGE_PATHS["ru"]).write_text("Changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "clean"):
            self.compile()

    def test_native_task_assignment_is_not_relabelled_as_a_proposal(self):
        graph = deepcopy(self.graph)
        graph["tasks"][0]["execution_assigned"] = True
        with self.assertRaisesRegex(ValueError, "proposed status"):
            validate_graph(graph)

    def test_execution_feed_refused(self):
        graph = deepcopy(self.graph)
        graph["current_task_statuses_included"] = True
        with self.assertRaisesRegex(ValueError, "execution-state"):
            validate_graph(graph)

    def test_duplicate_identity_refused(self):
        graph = deepcopy(self.graph)
        graph["tasks"][1]["id"] = "A"
        with self.assertRaisesRegex(ValueError, "unique"):
            validate_graph(graph)

    def test_unknown_dependency_refused(self):
        graph = deepcopy(self.graph)
        graph["tasks"][1]["dependencies"][0]["task_id"] = "missing"
        with self.assertRaisesRegex(ValueError, "Unknown"):
            validate_graph(graph)

    def test_unsafe_scheme_refused_even_with_a_matching_source_hash(self):
        path = self.source / PAGE_PATHS["en"]
        path.write_text(path.read_text() + "\n[Unsafe](javascript:alert(1))\n", encoding="utf-8")
        self.pin()
        with self.assertRaisesRegex(ValueError, "link scheme"):
            self.compile()

    def test_raw_html_refused_even_with_a_matching_source_hash(self):
        path = self.source / PAGE_PATHS["en"]
        path.write_text(path.read_text() + '\n<script>alert(1)</script>\n', encoding="utf-8")
        self.pin()
        with self.assertRaisesRegex(ValueError, "Raw HTML"):
            self.compile()

    def test_missing_link_target_refused(self):
        path = self.source / PAGE_PATHS["en"]
        path.write_text(path.read_text() + "\n[Missing](missing.md)\n", encoding="utf-8")
        self.pin()
        with self.assertRaisesRegex(ValueError, "Missing Coordinated Work link"):
            self.compile()


if __name__ == "__main__":
    unittest.main(verbosity=2)
