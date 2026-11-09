# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Compile the trilingual Meaning Programme reading guides.

The guides are reader pages, not catalogue manuscripts and not versioned
renditions. Every visible sentence comes from the pinned knowledge repository.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re

from build_publication import Renderer, csp_table_classes, inside, plain, run

REPOSITORY = "Arcanada-one/knowledge-contract"
GITHUB = "https://github.com/" + REPOSITORY
LOCALES = ("en", "ru", "zh-Hans")
# Keep in sync with publication_checks.STATUS_LABELS (UI chrome only).
STATUS_LABELS = {
    "research-draft": {"en": "Research draft", "ru": "Исследовательский черновик", "zh-Hans": "研究草稿"},
}
SOURCES = {
    "en": "PROGRAMME.md",
    "ru": "guides/programme.ru.md",
    "zh-Hans": "guides/programme.zh-Hans.md",
}
FOUNDATION_SECTIONS = {
    "en": "Three connected foundations",
    "ru": "Три фундаментальные работы",
    "zh-Hans": "三项共同基础",
}
# Card rule: each foundation is a bold lead title plus the remainder of that
# same paragraph under the foundations section (verbatim from the guide).
FOUNDATION_CARD = re.compile(r"(?m)^\*\*(.+?)\*\*\s+(\S.*)$")
FRONT_MATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(([^)]*)\)")
OUTER_PARAGRAPH = re.compile(r"\A<p>(.*)</p>\s*\Z", re.S)
PANDOC_FROM = "markdown+gfm_auto_identifiers+pipe_tables+tex_math_dollars+tex_math_single_backslash+autolink_bare_uris"


def file_digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def git_blob(source: Path, relative: str, commit: str) -> str:
    return run(["git", "rev-parse", f"{commit}:{relative}"], cwd=source).strip()


def working_blob(path: Path) -> str:
    return run(["git", "hash-object", str(path)]).strip()


def strip_front_matter(text: str) -> str:
    return FRONT_MATTER.sub("", text, count=1)


def extract_foundations(text: str, section_title: str) -> list[dict]:
    """Return three foundation cards from the guide's foundations section."""
    body = strip_front_matter(text)
    match = re.search(r"(?m)^## " + re.escape(section_title) + r"\s*$", body)
    if not match:
        raise ValueError(f"Programme guide is missing foundations section: {section_title!r}")
    rest = body[match.end():]
    next_heading = re.search(r"(?m)^## ", rest)
    section = rest[: next_heading.start()] if next_heading else rest
    cards = []
    for line in section.splitlines():
        card = FOUNDATION_CARD.match(line.strip())
        if not card:
            continue
        title, paragraph = card[1].strip(), card[2].strip()
        if title.endswith("."):
            title = title[:-1].rstrip()
        # Verbatim source remainder for checks. Rendered card HTML is produced later
        # through the same Markdown/link path as the guide body (never raw syntax).
        visible = MARKDOWN_LINK.sub(r"\1", paragraph)
        cards.append({"title": title, "text": paragraph, "visible": visible})
    if len(cards) != 3:
        raise ValueError(f"Expected exactly three foundation cards under {section_title!r}, found {len(cards)}")
    return cards


def unwrap_single_paragraph(html: str) -> str:
    """Return the inner HTML of a single pandoc paragraph, or the original fragment."""
    match = OUTER_PARAGRAPH.fullmatch(html.strip())
    if match and "<p>" not in match.group(1):
        return match.group(1)
    return html.strip()


def render_foundation_html(
    paragraph: str,
    doc: dict,
    renderer: Renderer,
    documents: list[dict],
    locale: str,
    commit: str,
    metas: list[dict],
) -> str:
    """Render one foundation card body with the same link rules as the guide body."""
    ast = parse_markdown_text(paragraph)
    renderer.transform(ast, doc)
    html = run(
        ["pandoc", "--from=json", "--to=html5", "--mathml", "--no-highlight", "--wrap=none", "--fail-if-warnings"],
        json.dumps(ast),
    )
    html = csp_table_classes(html)
    for other in metas:
        blob_url = f"{GITHUB}/blob/{commit}/{other['path']}"
        html = html.replace(f'href="{blob_url}"', f'href="{other["route"]}"')
    html = localize_and_badge_links(html, documents, locale)
    return unwrap_single_paragraph(html)


def verify_guide_bytes(source: Path, relative: str, commit: str) -> tuple[str, str]:
    """Return (sha256, git-blob). A changed guide byte without a repin fails here."""
    path = inside(source, relative)
    if not path.is_file():
        raise ValueError(f"Programme guide missing: {relative}")
    digest = file_digest(path)
    pinned = git_blob(source, relative, commit)
    if working_blob(path) != pinned:
        raise ValueError(
            f"Programme guide {relative} working bytes differ from pinned commit {commit} "
            f"(blob {pinned}); repin before publishing"
        )
    return digest, pinned


def parse_markdown_text(text: str) -> dict:
    return json.loads(run(["pandoc", f"--from={PANDOC_FROM}", "--to=json"], text))


def compile_programme(source: Path, commit: str, renderer: Renderer) -> dict:
    """Compile the three programme guides against the publication pin."""
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Programme compilation requires the full publication commit")
    actual = run(["git", "rev-parse", "HEAD"], cwd=source).strip()
    if actual != commit:
        raise ValueError(f"Programme source HEAD {actual} differs from publication pin {commit}")
    if run(["git", "status", "--porcelain", "--untracked-files=normal"], cwd=source).strip():
        raise ValueError("Programme source repository has uncommitted changes; use a clean checkout of the pin")

    routes = {locale: f"/{locale}/programme/" for locale in LOCALES}
    metas: list[dict] = []
    for locale, relative in SOURCES.items():
        digest, blob = verify_guide_bytes(source, relative, commit)
        metas.append({
            "path": relative,
            "route": routes[locale],
            "language": locale,
            "sha256": digest,
            "blob": blob,
            "source": f"{GITHUB}/blob/{commit}/{relative}",
            "history": f"{GITHUB}/commits/{commit}/{relative}",
        })

    # Link resolution: manuscripts already on the renderer, plus programme peers and roadmap pages.
    extra = [
        {"path": m["path"], "route": m["route"], "slug": "programme", "title": "Programme", "type": "glossary", "sha256": m["sha256"]}
        for m in metas
    ]
    if (source / "ROADMAP.md").is_file():
        extra.append({
            "path": "ROADMAP.md", "route": "/en/roadmap/", "slug": "roadmap", "title": "Roadmap",
            "type": "glossary", "sha256": file_digest(source / "ROADMAP.md"),
        })
    if (source / "roadmap/ROADMAP.ru.md").is_file():
        extra.append({
            "path": "roadmap/ROADMAP.ru.md", "route": "/ru/roadmap/", "slug": "roadmap-ru", "title": "Roadmap",
            "type": "glossary", "sha256": file_digest(source / "roadmap/ROADMAP.ru.md"),
        })
    programme_renderer = Renderer(source, renderer.output, renderer.manifest, list(renderer.documents) + extra)

    pages = {}
    for meta in metas:
        locale = meta["language"]
        raw = inside(source, meta["path"]).read_text(encoding="utf-8")
        foundations = extract_foundations(raw, FOUNDATION_SECTIONS[locale])
        body = strip_front_matter(raw)
        temp = {
            "path": meta["path"],
            "route": meta["route"],
            "slug": "programme",
            "title": "Programme",
            "type": "glossary",
            "sha256": meta["sha256"],
        }
        for card in foundations:
            card["html"] = render_foundation_html(
                card["text"], temp, programme_renderer, renderer.documents, locale, commit, metas
            )
        ast = parse_markdown_text(body)
        programme_renderer.transform(ast, temp)
        toc, blocks = [], []
        title_id = "document-title"
        title_text = None
        first_title = True
        for block in ast["blocks"]:
            if block["t"] == "Header":
                level, attrs, inlines = block["c"]
                if level == 1 and first_title:
                    first_title = False
                    title_id = attrs[0] or title_id
                    title_text = plain(inlines)
                    continue
                if level in {2, 3}:
                    toc.append({"level": level, "id": attrs[0], "title": plain(inlines)})
            blocks.append(block)
        if not title_text:
            raise ValueError(f"Programme guide has no H1 title: {meta['path']}")
        ast["blocks"] = blocks
        html = run(["pandoc", "--from=json", "--to=html5", "--mathml", "--no-highlight", "--wrap=none", "--fail-if-warnings"], json.dumps(ast))
        html = csp_table_classes(html)
        for other in metas:
            blob_url = f"{GITHUB}/blob/{commit}/{other['path']}"
            html = html.replace(f'href="{blob_url}"', f'href="{other["route"]}"')
        # UI chrome: keep the reader in the current locale and badge linked drafts.
        html = localize_and_badge_links(html, renderer.documents, locale)
        pages[locale] = {
            "language": locale,
            "path": meta["path"],
            "route": meta["route"],
            "title": title_text,
            "title_id": title_id,
            "html": html,
            "toc": toc,
            "foundations": foundations,
            "source": meta["source"],
            "history": meta["history"],
            "source_sha256": meta["sha256"],
            "blob": meta["blob"],
            "revision": commit,
        }

    return {
        "kind": "programme-guide",
        "pin": {
            "repository": REPOSITORY,
            "commit": commit,
            "files": [
                {
                    "path": pages[locale]["path"],
                    "sha256": pages[locale]["source_sha256"],
                    "blob": pages[locale]["blob"],
                    "url": pages[locale]["source"],
                }
                for locale in LOCALES
            ],
        },
        "routes": routes,
        "pages": pages,
        "foundation_card_rule": (
            "Card title is the bold lead title of each foundation paragraph under the "
            "foundations section; card text is the remainder of that same paragraph, "
            "verbatim from the guide, rendered through the same Markdown/link path as the body."
        ),
    }


def localize_and_badge_links(html: str, documents: list[dict], locale: str) -> str:
    """Point manuscript links at the current UI locale and badge catalogue drafts."""
    for doc in documents:
        en_route = doc["route"]
        local_route = en_route.replace("/en/", f"/{locale}/", 1)
        if locale != "en":
            html = html.replace(f'href="{en_route}"', f'href="{local_route}"')
        status = doc.get("status")
        if not status or status not in STATUS_LABELS:
            continue
        label = STATUS_LABELS[status][locale]
        badge = f'<span class="status-badge">{label}</span>'
        pattern = re.compile(rf'(href="{re.escape(local_route)}"[^>]*>.*?</a>)(?!\s*<span class="status-badge">)')
        html = pattern.sub(rf'\1 {badge}', html)
    return html


def provenance(record: dict) -> dict:
    return {
        "kind": record["kind"],
        "pin": record["pin"],
        "routes": record["routes"],
        "foundation_card_rule": record["foundation_card_rule"],
        "pages": {
            locale: {
                "path": page["path"],
                "source_sha256": page["source_sha256"],
                "blob": page["blob"],
                "title": page["title"],
                "foundations": page["foundations"],
            }
            for locale, page in record["pages"].items()
        },
    }
