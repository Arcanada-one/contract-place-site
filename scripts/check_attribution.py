#!/usr/bin/env python3
"""Single-study attribution preflight for journal issues.

Usage: check_attribution.py --source-dir <knowledge-contract checkout at the pinned commit>
                            [--scope attribution-scope.json] [--root <site root>]

For every entry of the scope file it (1) checks that the checker, the STUDY file and each
locale file are byte-identical to their pinned git blob ids and (2) runs the pinned checker as
`python3 -I <checker> --check STUDY EN RU ZH`.

Exit: 0 all entries pass; 1/3 the checker reported DEFECT/REVIEW_REQUIRED; 2 UNKNOWN, an
unreadable or malformed scope, or a pin mismatch (a changed file must be re-pinned explicitly).
A non-zero checker code of any value fails the job.

Exit 0 means only "no bounded single-author pattern matched". It is NOT scientific acceptance,
language acceptance or a replacement for human byline review.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HEX40 = re.compile(r"[0-9a-f]{40}")
LOCALES = ("en", "ru", "zh-Hans")
CHECKER_TIMEOUT = 120


def git_blob_id(data: bytes) -> str:
    """Same id as `git hash-object` for these bytes."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _pin(obj, label):
    if not isinstance(obj, dict) or not isinstance(obj.get("path"), str) or not HEX40.fullmatch(str(obj.get("blob", ""))):
        raise ValueError(f"{label}: needs a string path and a 40-hex blob")
    path = obj["path"]
    if path.startswith("/") or ".." in Path(path).parts:
        raise ValueError(f"{label}: path must be relative and stay inside its root")
    return path, obj["blob"]


def load_scope(scope_path: Path) -> list:
    data = json.loads(scope_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError("schema_version must be 1")
    entries = data.get("entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("entries must be a non-empty list")
    out = []
    for i, entry in enumerate(entries):
        label = f"entries[{i}]"
        if entry.get("scope") != "single-study":
            raise ValueError(f"{label}: scope must be 'single-study'")
        study = entry.get("study", {})
        if not HEX40.fullmatch(str(study.get("commit", ""))) or not isinstance(study.get("repository"), str):
            raise ValueError(f"{label}.study: needs repository and a 40-hex commit")
        locales = entry.get("locales", {})
        if sorted(locales) != sorted(LOCALES):
            raise ValueError(f"{label}.locales: must be exactly {', '.join(LOCALES)}")
        out.append({
            "issue": entry.get("issue_dir", f"entries[{i}]"),
            "study": _pin(study, f"{label}.study"),
            "locales": {loc: _pin(locales[loc], f"{label}.locales.{loc}") for loc in LOCALES},
            "checker": _pin(entry.get("checker"), f"{label}.checker"),
        })
    return out


def check_entry(entry, root: Path, source_dir: Path):
    """Return (exit_code, summary_line)."""
    checker_path, checker_blob = entry["checker"]
    study_path, study_blob = entry["study"]
    files = [("checker", root / checker_path, checker_path, checker_blob),
             ("study", source_dir / study_path, study_path, study_blob)]
    files += [(f"locale {loc}", root / p, p, b) for loc, (p, b) in entry["locales"].items()]
    mismatches = []
    for kind, path, shown, pinned in files:
        try:
            actual = git_blob_id(path.read_bytes())
        except OSError as exc:
            mismatches.append(f"{kind} {shown}: unreadable ({exc.strerror})")
            continue
        if actual != pinned:
            mismatches.append(f"{kind} {shown}: blob {actual} != pinned {pinned}; re-pin explicitly after review")
    if mismatches:
        for line in mismatches:
            print("PIN MISMATCH " + line, file=sys.stderr)
        return 2, f"{entry['issue']}: FAIL pin mismatch ({len(mismatches)} file(s))"
    cmd = [sys.executable, "-I", str(root / checker_path), "--check", str(source_dir / study_path)]
    cmd += [str(root / entry["locales"][loc][0]) for loc in LOCALES]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=CHECKER_TIMEOUT)
    except subprocess.TimeoutExpired:
        print(f"checker timed out after {CHECKER_TIMEOUT}s", file=sys.stderr)
        return 2, f"{entry['issue']}: FAIL checker timeout (UNKNOWN)"
    if proc.returncode != 0:
        print(f"checker exit code {proc.returncode}")
        print(proc.stdout, end="")
        print(proc.stderr, end="", file=sys.stderr)
        names = {1: "DEFECT", 2: "UNKNOWN", 3: "REVIEW_REQUIRED"}
        return proc.returncode, f"{entry['issue']}: FAIL checker exit {proc.returncode} ({names.get(proc.returncode, 'UNEXPECTED')})"
    print(proc.stdout, end="")
    return 0, f"{entry['issue']}: pass, checker exit 0 (no bounded single-author pattern matched; not scientific or language acceptance)"


def main(argv=None) -> int:
    default_root = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source-dir", required=True, type=Path)
    ap.add_argument("--root", type=Path, default=default_root)
    ap.add_argument("--scope", type=Path)
    args = ap.parse_args(argv)
    root = args.root.resolve()
    scope = args.scope or root / "attribution-scope.json"
    try:
        entries = load_scope(scope)
    except (OSError, ValueError, AttributeError, TypeError) as exc:
        print(f"UNKNOWN: cannot use scope file {scope}: {exc}", file=sys.stderr)
        return 2
    worst = 0
    for entry in entries:
        code, summary = check_entry(entry, root, args.source_dir.resolve())
        print(summary)
        worst = max(worst, code)
    print("Note: exit 0 is a bounded single-author pattern preflight only; human byline review remains required.")
    return worst


if __name__ == "__main__":
    sys.exit(main())
