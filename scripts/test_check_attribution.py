#!/usr/bin/env python3
"""Tests for scripts/check_attribution.py. Stdlib only; temp dirs only.

The real pinned study is read from ATTRIBUTION_SOURCE_DIR (default: _attribution-source), a
checkout of the knowledge repository at the commit pinned in attribution-scope.json.
The historical Russian text is a byte-exact fixture of src/content/.../ru.md at commit 49fcebbc (PR 50),
kept as a file because CI checks out a shallow clone without history.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCOPE = json.loads((ROOT / "attribution-scope.json").read_text(encoding="utf-8"))
ENTRY = SCOPE["entries"][0]
SOURCE = Path(os.environ.get("ATTRIBUTION_SOURCE_DIR", ROOT / "_attribution-source"))
HISTORICAL_RU = ROOT / "scripts" / "fixtures" / "attribution" / "ru-be2047af7955-pr50.md"  # file at commit 49fcebbc (PR 50)
HISTORICAL_RU_BLOB = "be2047af7955d56425665d84ce63989b56f28bd3"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_attribution import git_blob_id  # noqa: E402


def run_check(root: Path, source: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-B", str(ROOT / "scripts" / "check_attribution.py"),
                           "--root", str(root), "--source-dir", str(source)],
                          capture_output=True, text=True, timeout=300)


def run_checker(root: Path, entry: dict, source: Path) -> subprocess.CompletedProcess:
    study = source / entry["study"]["path"]
    cmd = [sys.executable, "-I", str(root / entry["checker"]["path"]), "--check", str(study)]
    cmd += [str(root / entry["locales"][k]["path"]) for k in ("en", "ru", "zh-Hans")]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)


class Sandbox:
    """A temp copy of the pinned inputs with a scope file written beside them."""

    def __init__(self, test):
        self.tmp = Path(tempfile.mkdtemp(prefix="attribution-test-"))
        test.addCleanup(shutil.rmtree, self.tmp, True)
        self.root, self.source = self.tmp / "root", self.tmp / "source"
        self.entry = json.loads(json.dumps(ENTRY))
        for rel in [self.entry["checker"]["path"]] + [v["path"] for v in self.entry["locales"].values()]:
            (self.root / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, self.root / rel)
        study = self.source / self.entry["study"]["path"]
        study.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SOURCE / self.entry["study"]["path"], study)

    def write_scope(self):
        data = {"schema_version": 1, "entries": [self.entry]}
        (self.root / "attribution-scope.json").write_text(json.dumps(data), encoding="utf-8")

    def repin(self, kind_path, entry_obj):
        entry_obj["blob"] = git_blob_id(kind_path.read_bytes())

    def study_path(self):
        return self.source / self.entry["study"]["path"]

    def locale_path(self, loc):
        return self.root / self.entry["locales"][loc]["path"]


class AttributionPreflight(unittest.TestCase):
    def test_a_real_pinned_entry_passes(self):
        proc = run_check(ROOT, SOURCE)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("not scientific or language acceptance", proc.stdout)

    def test_b_historical_ru_is_review_required(self):
        old = HISTORICAL_RU.read_bytes()
        self.assertEqual(git_blob_id(old), HISTORICAL_RU_BLOB)
        box = Sandbox(self)
        box.locale_path("ru").write_bytes(old)
        box.repin(box.locale_path("ru"), box.entry["locales"]["ru"])
        box.write_scope()
        self.assertEqual(run_checker(box.root, box.entry, box.source).returncode, 3)
        proc = run_check(box.root, box.source)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("checker exit code 3", proc.stdout)

    def test_c_unpinned_locale_change_is_pin_mismatch(self):
        box = Sandbox(self)
        path = box.locale_path("zh-Hans")
        path.write_bytes(path.read_bytes() + b" ")
        box.write_scope()
        proc = run_check(box.root, box.source)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("PIN MISMATCH", proc.stderr)
        self.assertIn("zh-Hans.md", proc.stderr)

    def test_d_unpinned_checker_change_is_pin_mismatch(self):
        box = Sandbox(self)
        path = box.root / box.entry["checker"]["path"]
        path.write_bytes(path.read_bytes() + b"\n")
        box.write_scope()
        proc = run_check(box.root, box.source)
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("PIN MISMATCH checker", proc.stderr)

    def test_e_multi_author_study_is_unknown(self):
        box = Sandbox(self)
        path = box.study_path()
        text = path.read_text(encoding="utf-8")
        self.assertIn('author: "Pavel Valentov"', text)
        path.write_text(text.replace('author: "Pavel Valentov"', 'author: "Lee and Kim"'), encoding="utf-8")
        box.repin(path, box.entry["study"])
        box.write_scope()
        proc = run_check(box.root, box.source)
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(run_checker(box.root, box.entry, box.source).returncode, 2)
        self.assertIn("checker exit code 2", proc.stdout)

    def test_scope_must_be_single_study(self):
        box = Sandbox(self)
        box.entry["scope"] = "multi-study"
        box.write_scope()
        self.assertEqual(run_check(box.root, box.source).returncode, 2)


if __name__ == "__main__":
    unittest.main()
