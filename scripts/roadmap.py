# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Compile the Knowledge Contract research roadmap from its own pinned source.

The roadmap pin (`roadmap-manifest.json`) is independent of the manuscript pin in
`publication-manifest.json`. The compiler refuses a pin that is not a full commit,
a source checkout at a different commit or with uncommitted changes, any source file
whose bytes differ from the recorded SHA-256, and any inconsistency between the task
cards and the dependency definition. A roadmap is planned work: no task status other
than "planned" can be produced without execution evidence, and this delivery has none.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
from urllib.parse import quote, unquote, urlsplit

from roadmap_names import (normalize_tasks, strip_editorial_markers, DISPLAY_NAME_KEYS,
                           validate_display_names, check_card_display_name,
                           EDITORIAL_METADATA, validate_editorial_metadata)

REPOSITORY = "Arcanada-one/knowledge-contract"
GITHUB = "https://github.com/" + REPOSITORY
SCHEMA = 1
# role -> path. "rendered" files become page content; "linked" files are only linked at the pin;
# "introduction" supplies the public introduction text and is never rendered as a page.
FILES = {
    "ROADMAP.md": "rendered",
    "roadmap/TASKS.md": "rendered",
    "roadmap/dependencies.json": "rendered",
    "roadmap/EXPERIMENTS.md": "linked",
    "roadmap/FOUNDATIONS_RELEASE_PLAN.md": "linked",
    "roadmap/SITE_DELIVERY.md": "introduction",
}
TASK_IDS = ["RM-%02d" % n for n in range(1, 26)]
PRIORITIES = ("P0", "P1", "P2")
NODE_KEYS = {"id", "priority", "content_owner", "requires"} | DISPLAY_NAME_KEYS
STATUS_KEYS = {"status", "state", "progress", "completed", "started", "execution_status", "percent", "due", "date", "eta"}
FIELDS = [
    ("gap", "Gap"), ("work", "Work"), ("deliverables", "Deliverables"),
    ("acceptance", "Acceptance"), ("adversarial", "Adversarial check"), ("start", "Start boundary"),
]
# One optional field (RM-18 "Scope separation", source revision fb410a84) may follow Work; nothing else is tolerated.
OPTIONAL_FIELD = ("scope", "Scope separation")
OPTIONAL_FIELD_CARD = "RM-18"
FIELD_ORDERS = (FIELDS, FIELDS[:2] + [OPTIONAL_FIELD] + FIELDS[2:])
PANDOC_FROM = "markdown+gfm_auto_identifiers+pipe_tables+tex_math_dollars+tex_math_single_backslash+autolink_bare_uris"
# Private or internal details never belong on the public page.
PRIVATE = [
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "UUID (work-item identifier)"),
    (re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"), "IPv4 address"),
    (re.compile(r"/home/|/Users/|arcanada-inbox|\.claude/|\bwss?://|\.internal\b|\.local\b"), "internal path or host"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "e-mail address"),
    (re.compile(r"\barcana-[a-z]+|dev-ai|\binbox/|kc-mail|\.ts\.net", re.I), "internal host name or mailbox path"),
]
# Known value of the only free-text execution field; anything else could publish a task state.
EXECUTION_BINDINGS = "unverified; RM labels are not work-item IDs"
TOP_LEVEL_KEYS = {"kind", "revision", "baseline_commit", "execution_authority", "execution_bindings", "target_dates",
                  "edge_semantics", "preparation_sequence_policy", "nodes", "advisory_links"} | set(EDITORIAL_METADATA)
CARD_LABEL = re.compile(r"(?m)^\*\*([^*\n]+?)(?:[.:]\*\*|\*\*\s*[.:])")


def run(command: list[str], text: str | None = None, cwd: Path | None = None) -> str:
    result = subprocess.run(command, input=text, text=True, capture_output=True, cwd=cwd)
    if result.returncode:
        raise ValueError(f"{' '.join(command)} failed: {result.stderr.strip()}")
    return result.stdout


def e(value: object) -> str:
    return escape(str(value), quote=True)


def read_json(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return result


def load_pin(source: Path, manifest_path: Path) -> dict:
    """Validate the roadmap pin against an exact, clean source checkout and the recorded file hashes."""
    pin = read_json(manifest_path)
    if pin.get("schema_version") != SCHEMA or pin.get("repository") != REPOSITORY:
        raise ValueError("Unsupported roadmap manifest schema or repository")
    if not isinstance(pin.get("commit"), str) or not re.fullmatch(r"[0-9a-f]{40}", pin["commit"]):
        raise ValueError("The roadmap manifest must pin a full 40-character commit")
    files = pin.get("files")
    if not isinstance(files, list) or {f.get("path") for f in files if isinstance(f, dict)} != set(FILES) or len(files) != len(FILES):
        raise ValueError("The roadmap manifest must list exactly: " + ", ".join(FILES))
    for item in files:
        if item.get("role") != FILES[item["path"]]:
            raise ValueError(f"Roadmap file {item['path']} must have role {FILES[item['path']]}")
        if not isinstance(item.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise ValueError(f"Roadmap file {item['path']} needs a SHA-256 digest")
    actual = run(["git", "rev-parse", "HEAD"], cwd=source).strip()
    if actual != pin["commit"]:
        raise ValueError(f"Roadmap source HEAD {actual} differs from roadmap manifest {pin['commit']}")
    if run(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=source).strip():
        raise ValueError("Roadmap source repository has uncommitted changes; use a clean checkout of the pin")
    for item in files:
        path = (source / item["path"]).resolve()
        if not path.is_relative_to(source.resolve()) or not path.is_file():
            raise ValueError(f"Roadmap source file missing: {item['path']}")
        digest = sha256(path.read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"Roadmap source file {item['path']} has SHA-256 {digest}, expected {item['sha256']} (stale roadmap pin)")
    return pin


def check_graph(deps: dict) -> dict[str, dict]:
    """Return nodes by id after verifying ids, priorities, owners, edges and the absence of cycles or status."""
    nodes = deps.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("dependencies.json has no node list")
    validate_display_names(nodes)
    by_id: dict[str, dict] = {}
    for node in nodes:
        if not isinstance(node, dict) or not isinstance(node.get("id"), str):
            raise ValueError(f"Malformed dependency node: {node!r}")
        if node["id"] in by_id:
            raise ValueError(f"Duplicate dependency node {node['id']}")
        extra = set(node) - NODE_KEYS
        if extra & STATUS_KEYS:
            raise ValueError(f"{node['id']}: execution state {sorted(extra & STATUS_KEYS)} has no execution evidence in this delivery; only planned work is published")
        if extra:
            raise ValueError(f"{node['id']}: unexpected dependency field(s) {sorted(extra)}")
        if node.get("priority") not in PRIORITIES:
            raise ValueError(f"{node['id']}: priority must be one of {PRIORITIES}")
        if not isinstance(node.get("content_owner"), str) or not node["content_owner"].strip():
            raise ValueError(f"{node['id']}: content owner missing")
        if not isinstance(node.get("requires"), list):
            raise ValueError(f"{node['id']}: requires must be a list")
        by_id[node["id"]] = node
    if sorted(by_id) != TASK_IDS:
        missing = sorted(set(TASK_IDS) - set(by_id))
        extra = sorted(set(by_id) - set(TASK_IDS))
        raise ValueError(f"Dependency graph must contain exactly RM-01..RM-25 once each (missing {missing}, unexpected {extra})")
    if deps.get("execution_bindings") != EXECUTION_BINDINGS:
        raise ValueError(f"dependencies.json execution_bindings must be exactly {EXECUTION_BINDINGS!r}; any other text could publish a task state")
    if deps.get("target_dates") is not None:
        raise ValueError("The roadmap defines no target dates; a dated promise cannot be published without accepted estimates")
    if set(deps) & STATUS_KEYS:
        raise ValueError("dependencies.json carries execution state; this delivery publishes planned work only")
    validate_editorial_metadata(deps)
    unknown_keys = set(deps) - TOP_LEVEL_KEYS
    if unknown_keys:
        raise ValueError(f"dependencies.json has unexpected top-level key(s) {sorted(unknown_keys)}; only planned-work fields are published")
    for node in by_id.values():
        if len(set(node["requires"])) != len(node["requires"]):
            raise ValueError(f"{node['id']}: duplicate required dependency")
        for target in node["requires"]:
            if target not in by_id:
                raise ValueError(f"{node['id']}: dangling required dependency {target}")
            if target == node["id"]:
                raise ValueError(f"{node['id']}: depends on itself")
    # Required edges must be acyclic (depth-first search with an explicit path for the diagnostic).
    state: dict[str, int] = {}
    def visit(task: str, path: list[str]) -> None:
        if task not in by_id:
            raise ValueError(f"Cycle search reached unknown task {task!r}")
        if state.get(task) == 2:
            return
        if state.get(task) == 1:
            raise ValueError("Cyclic required dependency: " + " -> ".join(path[path.index(task):] + [task]))
        state[task] = 1
        for target in by_id[task]["requires"]:
            visit(target, path + [task])
        state[task] = 2
    for task in TASK_IDS:
        visit(task, [])
    return by_id


def check_advisory(deps: dict, by_id: dict[str, dict]) -> list[dict]:
    links = deps.get("advisory_links")
    if not isinstance(links, list):
        raise ValueError("dependencies.json has no advisory_links list")
    seen = set()
    for link in links:
        if not isinstance(link, dict) or set(link) != {"from", "to", "kind"}:
            raise ValueError(f"Malformed advisory link: {link!r}")
        if link["kind"] != "informs_not_blocks":
            raise ValueError(f"Advisory link {link['from']} -> {link['to']} must be informs_not_blocks")
        for end in (link["from"], link["to"]):
            if end not in by_id:
                raise ValueError(f"Dangling advisory link {link['from']} -> {link['to']}: unknown {end}")
        if link["from"] == link["to"] or (link["from"], link["to"]) in seen:
            raise ValueError(f"Invalid or repeated advisory link {link['from']} -> {link['to']}")
        seen.add((link["from"], link["to"]))
    return links


def split_cards(text: str) -> dict[str, dict]:
    """Parse TASKS.md strictly: one `## RM-nn` section per card with a fixed field set."""
    text = normalize_tasks(text)
    sections = re.split(r"(?m)^## (?=RM-)", text)[1:]
    cards: dict[str, dict] = {}
    for section in sections:
        head, _, body = section.partition("\n")
        ident = head.strip()
        if not re.fullmatch(r"RM-\d\d", ident):
            raise ValueError(f"Malformed task heading: {head!r}")
        if ident in cards:
            raise ValueError(f"Task {ident} appears more than once in TASKS.md")
        title = re.match(r"\s*### (.+)\n", body)
        header = re.search(r"(?m)^\*\*Priority:\*\* (P\d) · \*\*Owner:\*\* ([^·\n]+?) · \*\*Required outputs:\*\* (.+?)\.\s*$", body)
        if not title or not header:
            raise ValueError(f"{ident}: title or priority/owner/required-output header missing")
        required = [] if header[3].strip() == "none" else [x.strip() for x in header[3].split(",")]
        rest = body[header.end():]
        found = list(CARD_LABEL.finditer(rest))
        labels = [m[1].strip() for m in found]
        before = rest[:found[0].start()] if found else rest
        if before.strip():
            raise ValueError(f"{ident}: unexpected text between the card header and the first field: {before.strip()[:80]!r}")
        between = body[title.end():header.start()]
        if between.strip():
            raise ValueError(f"{ident}: unexpected text between the title and the card header: {between.strip()[:80]!r}")
        allowed = FIELD_ORDERS if ident == OPTIONAL_FIELD_CARD else FIELD_ORDERS[:1]
        order = next((o for o in allowed if labels == [label for _, label in o]), None)
        if order is None:
            raise ValueError(f"{ident}: card fields {labels} differ from the expected {[label for _, label in FIELDS]}")
        fields = {}
        for index, match in enumerate(found):
            end = found[index + 1].start() if index + 1 < len(found) else len(rest)
            fields[order[index][0]] = rest[match.end():end].strip()
        cards[ident] = {"id": ident, "title": title[1].strip(), "priority": header[1], "owner": header[2].strip(), "requires": required, "fields": fields}
    return cards


def tasks_preamble(text: str) -> str:
    """The TASKS.md text before the first card (front matter and the H1 title removed); it is rendered, never dropped."""
    text = normalize_tasks(text)
    head = re.split(r"(?m)^## (?=RM-)", text, maxsplit=1)[0]
    return re.sub(r"\A---\n.*?\n---\n", "", head, count=1, flags=re.S).strip()


def extract_introduction(text: str) -> str:
    match = re.search(r"Suggested public introduction:\s*\n\s*\n((?:>.*\n?)+)", text)
    if not match:
        raise ValueError("SITE_DELIVERY.md has no 'Suggested public introduction' block quote")
    intro = " ".join(re.sub(r"^>\s?", "", line).strip() for line in match[1].splitlines()).strip()
    if len(intro) < 80:
        raise ValueError("Roadmap introduction is implausibly short")
    return intro


class Roadmap:
    def __init__(self, source: Path, pin: dict, manuscripts: dict[str, dict]):
        self.source, self.pin, self.manuscripts = source, pin, manuscripts
        self.commit = pin["commit"]

    def blob(self, path: str, fragment: str = "") -> str:
        return f"{GITHUB}/blob/{self.commit}/{quote(path, safe='/')}" + ("#" + fragment if fragment else "")

    def resolve_link(self, target: str, origin: str) -> str:
        parts = urlsplit(target)
        if parts.scheme in {"https", "http", "mailto"}:
            return target
        if parts.scheme or target.startswith("//"):
            raise ValueError(f"Unsupported link in {origin}: {target}")
        if not parts.path:
            return target
        relative = posixpath.normpath(str(PurePosixPath(origin).parent / unquote(parts.path)))
        path = (self.source / relative).resolve()
        if relative.startswith("..") or not path.is_relative_to(self.source.resolve()) or not path.exists():
            raise ValueError(f"Missing or escaping link target in {origin}: {target}")
        fragment = parts.fragment
        doc = self.manuscripts.get(relative)
        # A manuscript link reaches the site's reading page only when its bytes at the roadmap pin
        # equal the published text; otherwise the pinned source is the honest destination.
        if doc and path.is_file() and sha256(path.read_bytes()).hexdigest() == doc["source_sha256"]:
            return doc["route"] + ("#" + fragment if fragment else "")
        return self.blob(relative, fragment)

    def markdown(self, text: str, origin: str, shift: int = 0, prefix: str = "", drop_title: bool = False) -> tuple[str, list[dict]]:
        text = strip_editorial_markers(text)
        ast = json.loads(run(["pandoc", "--from=" + PANDOC_FROM, "--to=json"], text))
        toc: list[dict] = []
        blocks = []
        first = True

        def transform(node: object) -> None:
            if isinstance(node, list):
                for item in node:
                    transform(item)
            elif isinstance(node, dict):
                if node.get("t") in {"Link", "Image"}:
                    if node["t"] == "Image":
                        raise ValueError(f"Images are not part of the roadmap reading surface: {origin}")
                    node["c"][2][0] = self.resolve_link(node["c"][2][0], origin)
                if node.get("t") in {"RawBlock", "RawInline"} and node["c"][0] in {"html", "html5"}:
                    raise ValueError(f"Raw HTML is not accepted in roadmap source: {origin}")
                for value in node.values():
                    transform(value)

        transform(ast["blocks"])
        for block in ast["blocks"]:
            if block["t"] == "Header":
                level, attrs, inlines = block["c"]
                if level == 1 and first and drop_title:
                    first = False
                    continue
                block["c"][0] = level + shift
                if level == 2:
                    toc.append({"level": 3, "id": prefix + attrs[0], "title": plain(inlines)})
            blocks.append(block)
        ast["blocks"] = blocks
        html = run(["pandoc", "--from=json", "--to=html5", "--no-highlight", "--wrap=none", "--fail-if-warnings", "--id-prefix=" + prefix], json.dumps(ast))
        from build_publication import csp_table_classes  # shared CSP-safe table presentation
        html = csp_table_classes(html)
        if re.search(r"<(?:script|iframe|object|embed)\b|\son\w+\s*=|\sstyle=", html, re.I):
            raise ValueError(f"Executable or inline-styled markup rendered from {origin}")
        return html, toc


def plain(node: object) -> str:
    if isinstance(node, list):
        return "".join(plain(item) for item in node)
    if not isinstance(node, dict):
        return ""
    if node.get("t") == "Str":
        return node["c"]
    if node.get("t") in {"Space", "SoftBreak", "LineBreak"}:
        return " "
    if node.get("t") in {"Code", "Math"}:
        return node["c"][-1]
    if node.get("t") in {"Link", "Image"}:
        return plain(node["c"][1])
    return plain(node.get("c", []))


def scan_private(label: str, text: str) -> None:
    for pattern, what in PRIVATE:
        found = pattern.search(text)
        if found:
            raise ValueError(f"{label}: private or internal detail ({what}) must not be published: {found[0]!r}")


def compile_roadmap(source: Path, manifest_path: Path, manuscripts: dict[str, dict]) -> dict:
    """Return the generated roadmap record. Raises ValueError before anything is written."""
    pin = load_pin(source, manifest_path)
    deps = read_json(source / "roadmap/dependencies.json")
    nodes = check_graph(deps)
    advisory = check_advisory(deps, nodes)
    cards = split_cards((source / "roadmap/TASKS.md").read_text(encoding="utf-8"))
    if sorted(cards) != TASK_IDS:
        raise ValueError(f"TASKS.md must define exactly RM-01..RM-25 once each (missing {sorted(set(TASK_IDS) - set(cards))}, unexpected {sorted(set(cards) - set(TASK_IDS))})")
    for ident in TASK_IDS:
        card, node = cards[ident], nodes[ident]
        check_card_display_name(card, node)
        if card["priority"] != node["priority"]:
            raise ValueError(f"{ident}: card priority {card['priority']} differs from dependencies.json {node['priority']}")
        if card["owner"] != node["content_owner"]:
            raise ValueError(f"{ident}: card owner {card['owner']} differs from dependencies.json {node['content_owner']}")
        if sorted(card["requires"]) != sorted(node["requires"]):
            raise ValueError(f"{ident}: card required outputs {card['requires']} differ from dependencies.json {node['requires']}")
    roadmap = Roadmap(source, pin, manuscripts)
    introduction = extract_introduction((source / "roadmap/SITE_DELIVERY.md").read_text(encoding="utf-8"))
    overview_text = (source / "ROADMAP.md").read_text(encoding="utf-8")
    overview_text = re.sub(r"\A---\n.*?\n---\n", "", overview_text, count=1, flags=re.S)
    preamble = tasks_preamble((source / "roadmap/TASKS.md").read_text(encoding="utf-8"))
    preamble_html, _ = roadmap.markdown(preamble, "roadmap/TASKS.md", shift=1, prefix="tasks-", drop_title=True)
    overview_html, overview_toc = roadmap.markdown(overview_text, "ROADMAP.md", shift=1, prefix="src-", drop_title=True)
    needed_by = {ident: [] for ident in TASK_IDS}
    for ident in TASK_IDS:
        for target in nodes[ident]["requires"]:
            needed_by[target].append(ident)
    informs = {ident: [] for ident in TASK_IDS}
    informed_by = {ident: [] for ident in TASK_IDS}
    for link in advisory:
        informs[link["from"]].append(link["to"])
        informed_by[link["to"]].append(link["from"])
    tasks = []
    for ident in TASK_IDS:
        card = cards[ident]
        fields = []
        for key, label in FIELD_ORDERS[1]:
            if key not in card["fields"]:
                continue
            html, _ = roadmap.markdown(card["fields"][key], "roadmap/TASKS.md")
            fields.append({"key": key, "label": label, "html": html})
        tasks.append({
            "id": ident, "anchor": ident.lower(), "title": card["title"], "priority": card["priority"], "owner": card["owner"],
            "status": "planned", "requires": sorted(nodes[ident]["requires"]), "needed_by": sorted(needed_by[ident]),
            "informs": sorted(informs[ident]), "informed_by": sorted(informed_by[ident]), "fields": fields,
        })
    record = {
        "pin": {"repository": pin["repository"], "commit": pin["commit"], "files": [
            {"path": f["path"], "role": f["role"], "sha256": f["sha256"], "url": roadmap.blob(f["path"])} for f in pin["files"]]},
        "revision": deps.get("revision"), "baseline_commit": deps.get("baseline_commit"),
        "execution_authority": deps.get("execution_authority"), "execution_bindings": deps.get("execution_bindings"),
        "edge_semantics": deps.get("edge_semantics"),
        "introduction": introduction, "tasks_intro": preamble, "tasks_intro_html": preamble_html, "overview_html": overview_html, "overview_toc": overview_toc,
        "tasks": tasks, "advisory": advisory,
        "required_edges": sum(len(n["requires"]) for n in nodes.values()),
    }
    scan_private("roadmap", json.dumps(record, ensure_ascii=False))
    for key in ("revision", "baseline_commit"):
        if not isinstance(record[key], str) or not record[key]:
            raise ValueError(f"dependencies.json {key} missing")
    return record


def provenance(record: dict) -> dict:
    return {
        "pin": record["pin"], "revision": record["revision"], "baseline_commit": record["baseline_commit"],
        "tasks": [{k: t[k] for k in ("id", "priority", "owner", "status", "requires")} for t in record["tasks"]],
        "advisory": record["advisory"],
    }
