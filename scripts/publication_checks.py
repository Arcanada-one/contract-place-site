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


# Expected public state labels for language renditions, independent of the site code that renders them (K8).
RENDITION_LABELS = {
    "reviewed": {"en": "Reviewed translation", "ru": "Рецензированный перевод", "zh-Hans": "已审校译文"},
    "partially-reviewed": {"en": "Partially reviewed translation", "ru": "Частично рецензированный перевод", "zh-Hans": "部分审校译文"},
    "unreviewed": {"en": "Unreviewed translation", "ru": "Перевод без рецензирования", "zh-Hans": "未审校译文"},
    "stale": {"en": "Translation out of date: the English source has changed.", "ru": "Перевод устарел: английский источник изменился.", "zh-Hans": "译文已过期：英文源文已更改。"},
    "missing": {"en": "No translation of this document is available.", "ru": "Перевода этого документа нет.", "zh-Hans": "本文档暂无译文。"},
}
RENDITION_FALLBACK = {"en": "The pinned English source text is shown instead.", "ru": "Вместо него показан закреплённый английский исходный текст.", "zh-Hans": "此处改为显示固定版本的英文源文。"}
RENDITION_RENDERED = ("reviewed", "partially-reviewed", "unreviewed")
RENDITION_LOCALES = ("ru", "zh-Hans")


def check_renditions(output: Path, records: list[dict], renditions_source: str | None = None, allow_fixture: bool = False) -> int:
    """Every localized reading page of a work with a rendition record must state its rendition state truthfully:
    the compiled state, the language of the text actually shown, an explicit English fallback label when the text is
    English, and complete prerendered text with a stable section mapping when it is a rendition. Returns the number of
    pages checked. Raises ValueError starting with a stable RENDITION_* code."""
    import json
    import re
    from html import escape
    from urllib.parse import unquote
    with_renditions = [r for r in records if r.get("renditions")]
    if renditions_source == "fixture" and not allow_fixture:
        raise ValueError("RENDITION_FIXTURE_ONLY: the output was built with a fixture sidecar (--renditions-file) and is not a publication")
    if renditions_source not in (None, "fixture", "knowledge-repository"):
        raise ValueError(f"RENDITION_FIXTURE_ONLY: unknown renditions source {renditions_source!r}")
    if not with_renditions:
        stray = [p.relative_to(output).as_posix() for p in output.rglob("*.html") if 'class="rendition-state"' in p.read_text(encoding="utf-8")]
        if stray or (output / "renditions.js").exists():
            raise ValueError(f"RENDITION_STATE_LABEL: rendition markup without compiled renditions: {stray[:3]}")
        return 0
    if renditions_source is None:
        raise ValueError("RENDITION_FIXTURE_ONLY: compiled renditions without a recorded sidecar source")
    errors, pages = [], 0
    state_pattern = re.compile(r'<aside class="rendition-state" data-state="([^"]*)" data-language="([^"]*)" data-body-language="([^"]*)" data-independent-source="([^"]*)" lang="([^"]*)"[^>]*>(.*?)</aside>', re.S)
    for record in with_renditions:
        bare = record["route"].replace("/en/", "", 1).strip("/")
        english = (output / "en" / bare / "index.html").read_text(encoding="utf-8")
        if 'class="rendition-state"' in english:
            errors.append(f"RENDITION_STATE_LABEL: the English source page of {record['id']} carries a rendition label")
        for locale in RENDITION_LOCALES:
            rd = record["renditions"][locale]
            rel = f"{locale}/{bare}/index.html"
            html = (output / rel).read_text(encoding="utf-8")
            pages += 1
            found = state_pattern.findall(html)
            if len(found) != 1:
                errors.append(f"RENDITION_SILENT_FALLBACK: {rel} has {len(found)} rendition state labels; a page of a work with renditions must state its state")
                continue
            state, language, body_language, independent, label_locale, inner = found[0]
            rendered = rd["state"] in RENDITION_RENDERED
            if state != rd["state"] or language != locale:
                errors.append(f"RENDITION_STATE_LABEL: {rel} labels the rendition {state!r}/{language!r}, compiled state is {rd['state']!r}/{locale!r}")
            if independent != "false":
                errors.append(f"RENDITION_STATE_LABEL: {rel} does not declare the rendition a non-independent source")
            expected = RENDITION_LABELS[rd["state"]][locale]
            if f"<strong>{escape(expected)}</strong>" not in inner:
                errors.append(f"RENDITION_STATE_LABEL: {rel} lacks the visible label {expected!r}")
            for other, label in RENDITION_LABELS.items():
                if other != rd["state"] and f"<strong>{escape(label[locale])}</strong>" in inner:
                    errors.append(f"RENDITION_STATE_LABEL: {rel} carries the label of state {other!r} but the rendition is {rd['state']!r}")
            body = re.search(r'<div class="source-body prose" lang="([^"]*)">', html)
            ld = re.search(r'"inLanguage":"([^"]*)"', html)
            if not body or not ld:
                errors.append(f"RENDITION_SILENT_FALLBACK: {rel} has no reading body or language metadata")
                continue
            if rendered:
                if body_language != language or body[1] != language or ld[1] != language:
                    errors.append(f"RENDITION_LANGUAGE: {rel} shows a {language} rendition with body lang={body[1]!r}, inLanguage={ld[1]!r}, label {body_language!r}")
                if rd["html"] not in html:
                    errors.append(f"RENDITION_SILENT_FALLBACK: {rel} lacks the complete prerendered rendition text")
                if record["html"] in html and rd["html"] != record["html"]:
                    errors.append(f"RENDITION_SILENT_FALLBACK: {rel} also carries the English body")
                if html.count("<math ") != rd["math_count"]:
                    errors.append(f"RENDITION_FORMULA_CHANGED: {rel} has {html.count('<math ')} formulas, expected {rd['math_count']}")
                for heading in rd["toc"]:
                    if f'id="{heading["id"]}"' not in rd["html"]:
                        errors.append(f"RENDITION_SECTION_UNRESOLVED: {rel} contents entry {heading['id']} has no heading")
                for pair in rd["sections"]:
                    if f'id="{pair["rendition"]}" data-source-section="{pair["source"]}"' not in html:
                        errors.append(f"RENDITION_SECTION_DRIFT: {rel} section {pair['source']} is not bound to {pair['rendition']}")
            else:
                if body_language != "en" or body[1] != "en" or ld[1] != "en":
                    errors.append(f"RENDITION_LANGUAGE: {rel} falls back to English text but declares body lang={body[1]!r}, inLanguage={ld[1]!r}")
                if record["html"] not in html:
                    errors.append(f"RENDITION_SILENT_FALLBACK: {rel} does not show the pinned English source")
                if f"{escape(RENDITION_FALLBACK[locale])}" not in inner:
                    errors.append(f"RENDITION_SILENT_FALLBACK: {rel} shows English text without the explicit fallback statement")
                if "html" in rd:
                    errors.append(f"RENDITION_SILENT_FALLBACK: {rel} compiled a rendition body for the {rd['state']} state")
    if errors:
        raise ValueError("\n".join(errors))
    return pages
