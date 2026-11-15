# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Compile pinned roadmap translations without changing the work graph.

Closed shapes, exact source bindings and structural controls do not constitute
semantic review. All translated prose is authored in the knowledge repository.
"""
from __future__ import annotations
from collections import Counter
from datetime import date
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
from urllib.parse import unquote, urlsplit

INDEX = "roadmap/localizations.json"
LOCALES = ("ru", "zh-Hans")
SOURCE_FILES = ("ROADMAP.md", "roadmap/TASKS.md", "roadmap/SITE_DELIVERY.md", "roadmap/dependencies.json")
FILES = {
    INDEX: "rendition-manifest",
    "roadmap/ROADMAP.full.ru.md": "rendition",
    "roadmap/ROADMAP.full.zh-Hans.md": "rendition",
    "roadmap/TASKS.ru.json": "rendition",
    "roadmap/TASKS.zh-Hans.json": "rendition",
}
FIELD_LABELS = {
    "ru": {"gap": "Пробел", "work": "Работа", "deliverables": "Результаты",
           "acceptance": "Приёмка", "adversarial": "Опровергающая проверка",
           "start": "Граница начала", "scope": "Разделение областей"},
    "zh-Hans": {"gap": "缺口", "work": "工作", "deliverables": "交付物",
                "acceptance": "验收", "adversarial": "对抗检查",
                "start": "启动边界", "scope": "范围分离"},
}
PRIORITIES = {
    "ru": {"P0": "Немедленно", "P1": "Далее", "P2": "Расширение"},
    "zh-Hans": {"P0": "立即", "P1": "下一步", "P2": "扩展"},
}
EXECUTION = {
    "ru": "не проверено; метки RM не являются идентификаторами рабочих единиц",
    "zh-Hans": "未经验证；RM 标签不是工作项标识符",
}


def refuse(message: str) -> None:
    raise ValueError("ROADMAP_LOCALIZATION: " + message)


def closed(value: object, keys: set[str], label: str) -> dict:
    if type(value) is not dict or set(value) != keys:
        refuse(label + " has missing or unknown fields")
    return value


def read_json(path: Path) -> dict:
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                refuse("duplicate JSON member " + key)
            result[key] = value
        return result
    try:
        value = json.loads(path.read_bytes(), object_pairs_hook=pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        refuse("cannot read " + str(path) + ": " + str(error))
    if type(value) is not dict:
        refuse("expected a JSON object")
    return value


def prose(value: object, locale: str, label: str, single_line: bool = False) -> str:
    if type(value) is not str or not value.strip():
        refuse(label + " is empty or not text")
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", value):
        refuse(label + " has control characters")
    if single_line and ("\n" in value or "<" in value or ">" in value):
        refuse(label + " must be plain single-line text")
    from renditions import script_matches
    if not script_matches(locale, value):
        refuse(label + " is not in the declared language")
    return value


def git(source: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(source), *args], capture_output=True, check=False)
    if result.returncode:
        refuse("source revision or ancestry could not be verified")
    return result.stdout


def strip_front_matter(text: str) -> str:
    return re.sub(r"\A---\n.*?\n---\n", "", text, count=1, flags=re.S)


def ast(text: str) -> dict:
    from roadmap import PANDOC_FROM, run, strip_editorial_markers
    return json.loads(run(["pandoc", "--from=" + PANDOC_FROM, "--to=json"],
                          strip_editorial_markers(strip_front_matter(text))))


def canonical_link(target: str, origin: str) -> str:
    parts = urlsplit(target)
    if parts.scheme or target.startswith("//"):
        return target
    path = (posixpath.normpath(str(PurePosixPath(origin).parent / unquote(parts.path)))
            if parts.path else origin)
    return path + ("?" + parts.query if parts.query else "") + ("#" + parts.fragment if parts.fragment else "")


def numeric_facts(text: str) -> tuple[Counter, Counter]:
    """Compare calendar dates by value, and other Arabic numerals literally.

    November, ноября and 11月 name one month. A translation must not change a
    date merely to satisfy a literal count of digits. Yearless dates stay
    yearless; no year is inferred from surrounding editorial history.
    """
    dates = Counter()
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
        "января": 1, "февраля": 2, "марта": 3, "апреля": 4, "мая": 5, "июня": 6,
        "июля": 7, "августа": 8, "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
    }
    chinese = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
               "七": 7, "八": 8, "九": 9, "十": 10, "十一": 11, "十二": 12}

    def retain(year, month, day):
        try:
            date(int(year) if year else 2000, int(month), int(day))
        except ValueError:
            refuse("invalid calendar date")
        dates[(int(year) if year else None, int(month), int(day))] += 1
        return " "

    names = "|".join(sorted(months, key=len, reverse=True))
    text = re.sub(r"(?<!\w)([0-9]{1,2})\s+(" + names + r")(?!\w)(?:\s+([0-9]{4})(?!\w))?",
                  lambda m: retain(m[3], months[m[2].lower()], m[1]), text, flags=re.I)
    text = re.sub(r"(?<![0-9一二三四五六七八九十百千万〇零])(?:([0-9]{4})\s*年\s*)?([0-9]{1,2}|十一|十二|[一二三四五六七八九十])\s*月\s*([0-9]{1,2})\s*日",
                  lambda m: retain(m[1], int(m[2]) if m[2].isascii() else chinese[m[2]], m[3]), text)
    return Counter(re.findall(r"[0-9]+(?:[.,][0-9]+)*", text)), dates


def facts(text: str, origin: str) -> dict:
    result = {"opaque": [], "links": [], "structure": Counter(), "headings": [], "numbers": Counter(), "dates": Counter()}
    words = []
    structural = {"Table", "BulletList", "OrderedList", "BlockQuote", "HorizontalRule", "Image", "CodeBlock", "Note"}
    def visit(node):
        if isinstance(node, list):
            for item in node:
                visit(item)
        elif isinstance(node, dict):
            kind, content = node.get("t"), node.get("c")
            if kind in structural:
                result["structure"][kind] += 1
            if kind in {"Code", "CodeBlock", "Math"}:
                result["opaque"].append((kind, content[0] if kind == "Math" else None, content[-1]))
                return
            if kind in {"RawBlock", "RawInline"} and content[0] in {"html", "html5"}:
                refuse("raw HTML is not a translated roadmap block")
            if kind in {"Link", "Image"}:
                result["links"].append((kind, canonical_link(content[2][0], origin)))
            if kind == "Header":
                result["headings"].append((content[0], content[1][0] if content[0] != 1 else "title"))
            if kind == "Str":
                words.append(content)
            for value in node.values():
                visit(value)
    visit(ast(text)["blocks"])
    result["numbers"], result["dates"] = numeric_facts(" ".join(words))
    return result


def parity(original: str, translated: str, origin: str, translation_origin: str, label: str) -> None:
    left, right = facts(original, origin), facts(translated, translation_origin)
    for key in ("opaque", "structure", "headings", "numbers", "dates"):
        if left[key] != right[key]:
            refuse(label + " changed " + key)
    if Counter(left["links"]) != Counter(right["links"]):
        refuse(label + " changed a source link or fragment")


def read_sources(source: Path, pin: dict) -> tuple[dict, dict] | None:
    """Return bound raw locale payloads, also used by source-to-output checks."""
    listed = {f["path"] for f in pin["files"]}
    if INDEX not in listed:
        if (source / INDEX).exists():
            refuse("existing localization inputs are not pinned by the roadmap manifest")
        return None
    if not set(FILES).issubset(listed):
        refuse("the complete translation input set must be pinned")
    config = read_json(source / INDEX)
    closed(config, {"schema_version", "kind", "source", "translations"}, "index")
    if type(config["schema_version"]) is not int or config["schema_version"] != 1 or config["kind"] != "arcanada-roadmap-localizations":
        refuse("unsupported index schema")
    binding = closed(config["source"], {"revision", "files"}, "source binding")
    revision = binding["revision"]
    if type(revision) is not str or not re.fullmatch(r"[0-9a-f]{40}", revision):
        refuse("the source revision is not a full commit ID")
    hashes = closed(binding["files"], set(SOURCE_FILES), "source file bindings")
    git(source, "merge-base", "--is-ancestor", revision, pin["commit"])
    for relative, digest in hashes.items():
        if type(digest) is not str or not re.fullmatch(r"[0-9a-f]{64}", digest):
            refuse("invalid source digest")
        if sha256(git(source, "show", revision + ":" + relative)).hexdigest() != digest:
            refuse("source digest does not match the historical revision: " + relative)
        if sha256((source / relative).read_bytes()).hexdigest() != digest:
            refuse("translation is stale for " + relative)
    closed(config["translations"], set(LOCALES), "translations")
    raw = {}
    for locale in LOCALES:
        entry = closed(config["translations"][locale], {"overview", "tasks", "status"}, locale)
        if entry != {"overview": f"roadmap/ROADMAP.full.{locale}.md",
                     "tasks": f"roadmap/TASKS.{locale}.json", "status": "author-draft"}:
            refuse(locale + " has an unexpected path or review claim")
        data = read_json(source / entry["tasks"])
        closed(data, {"schema_version", "language", "introduction", "tasks_intro", "start", "tasks"}, locale + " tasks")
        if type(data["schema_version"]) is not int or data["schema_version"] != 1 or data["language"] != locale:
            refuse(locale + " has an unsupported task schema or language")
        raw[locale] = {**data, "overview": (source / entry["overview"]).read_text(encoding="utf-8"),
                       "overview_path": entry["overview"], "tasks_path": entry["tasks"]}
    return config, raw


def compile_translations(source: Path, pin: dict, cards: dict, engine, record: dict) -> tuple[dict, dict] | None:
    loaded = read_sources(source, pin)
    if loaded is None:
        return None
    config, raw = loaded
    from roadmap import TASK_IDS, EXECUTION_BINDINGS, tasks_preamble, extract_introduction
    if record["execution_bindings"] != EXECUTION_BINDINGS:
        refuse("unknown execution state cannot be translated")
    original_overview = (source / "ROADMAP.md").read_text(encoding="utf-8")
    original_intro = extract_introduction((source / "roadmap/SITE_DELIVERY.md").read_text(encoding="utf-8"))
    original_preamble = tasks_preamble((source / "roadmap/TASKS.md").read_text(encoding="utf-8"))
    starts = {c["fields"]["start"] for c in cards.values()}
    if len(starts) != 1:
        refuse("a shared start translation cannot cover different source conditions")
    views = {}
    for locale, data in raw.items():
        for key in ("introduction", "tasks_intro", "start", "overview"):
            prose(data[key], locale, locale + " " + key)
        parity(original_intro, data["introduction"], "roadmap/SITE_DELIVERY.md", data["tasks_path"], locale + " introduction")
        parity(original_preamble, data["tasks_intro"], "roadmap/TASKS.md", data["tasks_path"], locale + " preamble")
        parity(next(iter(starts)), data["start"], "roadmap/TASKS.md", data["tasks_path"], locale + " start boundary")
        parity(original_overview, data["overview"], "ROADMAP.md", data["overview_path"], locale + " overview")
        if type(data["tasks"]) is not list or len(data["tasks"]) != len(TASK_IDS):
            refuse(locale + " does not contain every task")
        seen, names, tasks = set(), set(), []
        for item in data["tasks"]:
            closed(item, {"id", "title", "display_name", "fields"}, locale + " task")
            ident = item["id"]
            if type(ident) is not str or ident not in cards or ident in seen:
                refuse(locale + " has an unknown or duplicate task")
            seen.add(ident)
            title = prose(item["title"], locale, ident + " title", True)
            name = prose(item["display_name"], locale, ident + " name", True)
            if name in names or not title.startswith(name + ": ") or not title[len(name) + 2:].strip():
                refuse(locale + " has a duplicate name or an unbound subtitle")
            names.add(name)
            source_card = cards[ident]
            fields = closed(item["fields"], set(source_card["fields"]) - {"start"}, ident + " fields")
            base = next(task for task in record["tasks"] if task["id"] == ident)
            translated_fields = []
            for source_field in base["fields"]:
                key = source_field["key"]
                text = data["start"] if key == "start" else prose(fields[key], locale, ident + " " + key)
                parity(source_card["fields"][key], text, "roadmap/TASKS.md", data["tasks_path"], locale + " " + ident + " " + key)
                html, _ = engine.markdown(text, data["tasks_path"])
                translated_fields.append({"key": key, "label": FIELD_LABELS[locale][key], "html": html})
            tasks.append({**base, "title": title, "display_name": name,
                          "display_name_ru": name if locale == "ru" else base["display_name_ru"],
                          "subtitle": title[len(name) + 2:], "priority_label": PRIORITIES[locale][base["priority"]],
                          "fields": translated_fields})
        if seen != set(TASK_IDS):
            refuse(locale + " is missing a task")
        tasks.sort(key=lambda item: item["id"])
        overview_html, overview_toc = engine.markdown(strip_front_matter(data["overview"]), data["overview_path"],
                                                     shift=1, prefix="src-", drop_title=True)
        preamble_html, _ = engine.markdown(data["tasks_intro"], data["tasks_path"], shift=1, prefix="tasks-", drop_title=True)
        views[locale] = {"language": locale, "translation_state": "unreviewed",
                         "introduction": data["introduction"], "tasks_intro": data["tasks_intro"],
                         "tasks_intro_html": preamble_html, "overview_html": overview_html,
                         "overview_toc": overview_toc, "tasks": tasks,
                         "names": {t["id"]: t["display_name"] for t in tasks},
                         "priority_labels": PRIORITIES[locale], "execution_bindings": EXECUTION[locale]}
    provenance = {"source": config["source"], "status": "author-draft",
                  "semantic_review": "not_verified",
                  "files": [{**f} for f in pin["files"] if f["path"] in FILES]}
    return views, provenance
