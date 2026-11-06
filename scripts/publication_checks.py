# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

class Page(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.errors: list[str] = []
        self.h1 = 0
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str]]) -> None:
        attrs = dict(attrs)
        if "id" in attrs:
            if attrs["id"] in self.ids:
                self.errors.append(f'Duplicate id: {attrs["id"]}')
            self.ids.add(attrs["id"])
        if tag == "h1":
            self.h1 += 1
        for attribute in ("href", "src"):
            if attrs.get(attribute):
                self.links.append(attrs[attribute])
        for attribute in ("href", "src", "xlink:href", "action", "formaction"):
            value = attrs.get(attribute, "")
            if value and urlsplit(value).scheme.lower() not in {"", "http", "https", "mailto"}:
                self.errors.append(f"Unsupported executable/resource URL scheme in {attribute}")
        if any(k.lower().startswith("on") for k in attrs):
            self.errors.append("Inline event handler")
        if tag in {"script", "img", "iframe", "audio", "video", "source", "embed"} and attrs.get("src", "").startswith(("http:", "https:", "//")):
            self.errors.append("Remote embedded resource")
        if tag == "link" and attrs.get("rel") == "stylesheet" and attrs.get("href", "").startswith(("http:", "https:", "//")):
            self.errors.append("Remote stylesheet")


def check_site(output: Path) -> int:
    pages = {path: Page(path) for path in output.rglob("*.html")}
    errors = []
    for path, page in pages.items():
        if page.h1 != 1:
            errors.append(f"{path}: expected one h1, found {page.h1}")
        errors += [f"{path}: {error}" for error in page.errors]
        for link in page.links:
            parts = urlsplit(link)
            if parts.scheme or link.startswith("//"):
                continue
            target = output / unquote(parts.path).lstrip("/") if parts.path.startswith("/") else path.parent / unquote(parts.path) if parts.path else path
            if target.is_dir():
                target /= "index.html"
            target = target.resolve()
            if not target.is_relative_to(output.resolve()) or not target.exists():
                errors.append(f"{path.relative_to(output)}: missing target {link}")
            elif parts.fragment and target in pages and unquote(parts.fragment) not in pages[target].ids:
                errors.append(f"{path.relative_to(output)}: missing anchor {link}")
    if errors:
        raise ValueError("\n".join(errors))
    return len(pages)


# Expected public labels for catalogue statuses, independent of the site code that renders them.
STATUS_LABELS = {
    "research-draft": {"en": "Research draft", "ru": "Исследовательский черновик", "zh-Hans": "研究草稿"},
}
LOCALES = ("en", "ru", "zh-Hans")


def check_status_labels(output: Path, records: list[dict]) -> int:
    """Every page that shows a document with a catalogue status must carry its label; no page may carry a label for
    a document it does not show. Raises ValueError listing the failures; returns the number of labelled pages."""
    import re
    errors = []
    unknown = sorted({r["status"] for r in records if r.get("status")} - set(STATUS_LABELS))
    if unknown:
        raise ValueError(f"Catalogue status without a public label: {unknown}")
    drafts = [r for r in records if r.get("status")]
    badge = re.compile(r'<span class="status-badge">([^<]*)</span>')
    labelled = 0
    for locale in LOCALES:
        for page in sorted((output / locale).rglob("index.html")):
            html = page.read_text(encoding="utf-8")
            rel = page.relative_to(output).as_posix()
            shown = set()
            for record in drafts:
                route = record["route"].replace("/en/", f"/{locale}/", 1)
                label = STATUS_LABELS[record["status"]][locale]
                is_own = rel == route.strip("/") + "/index.html"
                links = html.count(f'href="{route}"')
                if is_own or links:
                    shown.add(label)
                    if f'<span class="status-badge">{label}</span>' not in html:
                        errors.append(f"{rel}: shows {record['id']} ({record['status']}) without the label {label!r}")
                if is_own and 'class="draft-notice"' not in html:
                    errors.append(f"{rel}: reading page of {record['id']} has no draft notice")
            for lead in re.findall(r'<p class="draft-notice"[^>]*><strong>([^<]*)</strong>', html):
                if locale == "zh-Hans" and not lead.endswith("。"):
                    errors.append(f"{rel}: zh-Hans notice lead {lead!r} must end with the Chinese full stop 。, not an ASCII '.'")
            extra = [text for text in badge.findall(html) if text not in shown]
            if extra:
                errors.append(f"{rel}: status label {sorted(set(extra))} on a page that shows no such document")
            labelled += bool(shown)
    if errors:
        raise ValueError("\n".join(errors))
    return labelled
