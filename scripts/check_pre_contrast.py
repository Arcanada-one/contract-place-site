#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Static contrast check for every <pre> in the built body (light and dark themes).

CI does not install a browser, so this walks the committed CSS cascade for color and
background instead of Playwright computed styles. It fails when any body <pre> has
text/background contrast below 4.5:1 in either theme.

Usage: check_pre_contrast.py <public-dir>
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

MIN_RATIO = 4.5
THEME_ATTR = "data-theme"


def parse_color(value: str) -> tuple[float, float, float] | None:
    value = value.strip().lower()
    if value in ("transparent", "inherit", "currentcolor", "initial", "unset"):
        return None
    if value.startswith("var("):
        return None
    m = re.fullmatch(r"#([0-9a-f]{3}|[0-9a-f]{6})", value)
    if m:
        h = m.group(1)
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]
    m = re.fullmatch(r"rgba?\(\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)(?:\s*,\s*([0-9.]+))?\s*\)", value)
    if m:
        r, g, b = (float(m.group(i)) for i in range(1, 4))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        if a <= 0:
            return None
        if r > 1 or g > 1 or b > 1:
            r, g, b = r / 255, g / 255, b / 255
        return (r, g, b)
    return None


def relative_luminance(rgb: tuple[float, float, float]) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(fg: tuple[float, float, float], bg: tuple[float, float, float]) -> float:
    l1, l2 = relative_luminance(fg), relative_luminance(bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def specificity(selector: str) -> tuple[int, int, int]:
    s = selector
    a = len(re.findall(r"\[[^\]]+\]", s))
    s = re.sub(r"\[[^\]]+\]", "", s)
    a += len(re.findall(r"#[\w-]+", s))
    s = re.sub(r"#[\w-]+", "", s)
    b = len(re.findall(r"\.[\w-]+", s))
    s = re.sub(r"\.[\w-]+", "", s)
    b += len(re.findall(r":(?!:)[\w-]+(?:\([^)]*\))?", s))
    s = re.sub(r":(?!:)[\w-]+(?:\([^)]*\))?", "", s)
    s = s.replace("::", " ")
    c = len(re.findall(r"[\w-]+", s))
    return (a, b, c)


@dataclass(frozen=True)
class Rule:
    selector: str
    props: dict[str, str]
    order: int


def split_declarations(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in body.split(";"):
        if ":" not in part:
            continue
        name, value = part.split(":", 1)
        name, value = name.strip().lower(), value.strip()
        if name:
            out[name] = value
    return out


def load_rules(css_text: str) -> list[Rule]:
    rules: list[Rule] = []
    order = 0
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css_text):
        selectors, body = match.group(1), match.group(2)
        if selectors.strip().startswith("@"):
            continue
        props = split_declarations(body)
        interesting = {k: props[k] for k in ("color", "background", "background-color") if k in props}
        if not interesting:
            continue
        for raw in selectors.split(","):
            sel = re.sub(r"\s+", " ", raw.strip())
            if not sel:
                continue
            rules.append(Rule(sel, interesting, order))
            order += 1
    return rules


def resolve_vars(value: str, vars_map: dict[str, str]) -> str:
    previous = None
    current = value
    while previous != current:
        previous = current

        def repl(match: re.Match[str]) -> str:
            name = match.group(1).strip()
            return vars_map.get(name, match.group(0))

        current = re.sub(r"var\(\s*(--[\w-]+)\s*(?:,[^)]+)?\)", repl, current)
    return current


def theme_vars(css_text: str) -> dict[str, dict[str, str]]:
    root = {}
    dark = {}
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css_text):
        sel, body = match.group(1).strip(), match.group(2)
        props = split_declarations(body)
        custom = {k: v for k, v in props.items() if k.startswith("--")}
        if not custom:
            continue
        if sel == ":root":
            root.update(custom)
        if "html[data-theme=dark]" in sel.replace(" ", "") or sel.replace(" ", "") == "html[data-theme=dark]":
            dark.update(custom)
    return {"light": dict(root), "dark": {**root, **dark}}


def selector_matches(selector: str, classes: set[str], tag: str, theme: str, parent_classes: set[str]) -> bool:
    sel = selector.strip()
    if sel.startswith("@"):
        return False
    # Theme-qualified html selectors are handled via variable maps, not element matching.
    if sel.startswith("html[") or sel == ":root" or sel == "html":
        return False

    # Support simple descendant forms used in this stylesheet: ".a .b", ".a pre", "pre", ".endpoint-code"
    parts = sel.split()
    if len(parts) == 1:
        return simple_match(parts[0], classes, tag)
    if len(parts) == 2:
        parent_sel, child_sel = parts
        if not simple_match(child_sel, classes, tag):
            return False
        # Parent may be any ancestor class set we pass as parent_classes for the element.
        return ancestor_match(parent_sel, parent_classes)
    if len(parts) == 3:
        # e.g. .roadmap-body .source-body pre
        a, b, c = parts
        if not simple_match(c, classes, tag):
            return False
        return ancestor_match(a, parent_classes) and ancestor_match(b, parent_classes)
    return False


def simple_match(token: str, classes: set[str], tag: str) -> bool:
    token = token.strip()
    if not token:
        return False
    if token.startswith("."):
        name = token[1:]
        if ":" in name:
            name = name.split(":", 1)[0]
        return name in classes
    if token.startswith("#"):
        return False
    if re.fullmatch(r"[\w-]+", token):
        return token == tag
    # compound tag.class
    m = re.fullmatch(r"([\w-]+)\.([\w-]+)", token)
    if m:
        return m.group(1) == tag and m.group(2) in classes
    m = re.fullmatch(r"\.([\w-]+)\.([\w-]+)", token)
    if m:
        return m.group(1) in classes and m.group(2) in classes
    return False


def ancestor_match(token: str, ancestor_classes: set[str]) -> bool:
    token = token.strip()
    if token.startswith("."):
        return token[1:] in ancestor_classes
    return False


def apply_cascade(
    rules: list[Rule],
    classes: set[str],
    tag: str,
    theme: str,
    ancestor_classes: set[str],
    vars_map: dict[str, str],
    inherited_color: str | None,
) -> dict[str, str]:
    scored: list[tuple[tuple[int, int, int], int, Rule]] = []
    for rule in rules:
        if selector_matches(rule.selector, classes, tag, theme, ancestor_classes):
            scored.append((specificity(rule.selector), rule.order, rule))
    scored.sort(key=lambda item: (item[0], item[1]))
    computed: dict[str, str] = {}
    if inherited_color:
        computed["color"] = inherited_color
    for _, _, rule in scored:
        for key, raw in rule.props.items():
            prop = "background-color" if key == "background" else key
            # Ignore image/shorthand layers that are not plain colors.
            resolved = resolve_vars(raw, vars_map)
            if prop == "background-color":
                # background shorthand may include other layers; take a leading color token if present.
                color_token = resolved.split()[0] if resolved else resolved
                if parse_color(color_token) is None and not color_token.startswith("#") and not color_token.startswith("rgb"):
                    # e.g. background:var(--subtle) already resolved, or leave as-is
                    if parse_color(resolved) is None and not resolved.startswith("#") and "gradient" in resolved:
                        continue
                    computed[prop] = resolved if parse_color(resolved) or resolved.startswith("#") or resolved.startswith("rgb") or resolved.startswith("var(") else color_token
                else:
                    computed[prop] = color_token
            else:
                computed[prop] = resolved
    return computed


class BodyPreCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, set[str]]] = []
        self.in_body = False
        self.pres: list[dict] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {k: (v or "") for k, v in attrs}
        classes = set(attr.get("class", "").split())
        if tag == "body":
            self.in_body = True
        self.stack.append((tag, classes))
        if self.in_body and tag == "pre":
            ancestors: set[str] = set()
            for _, cls in self.stack[:-1]:
                ancestors |= cls
            self.pres.append(
                {
                    "classes": classes,
                    "ancestors": ancestors,
                    "index": len(self.pres),
                }
            )

    def handle_endtag(self, tag: str) -> None:
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
        if tag == "body":
            self.in_body = False


def effective_colors(
    rules: list[Rule],
    pre: dict,
    theme: str,
    vars_map: dict[str, str],
) -> tuple[tuple[float, float, float], tuple[float, float, float], str, str]:
    body_color = resolve_vars("var(--ink)", vars_map)
    body_bg = resolve_vars("var(--bg)", vars_map)
    inherited = resolve_vars(body_color, vars_map)
    computed = apply_cascade(rules, pre["classes"], "pre", theme, pre["ancestors"], vars_map, inherited)
    color_raw = computed.get("color", inherited)
    bg_raw = computed.get("background-color")
    # If pre background is missing/transparent, fall back to body background.
    # Nested .source-body code paints a chip background behind glyphs; treat that as the
    # text backdrop when the pre itself has no opaque background.
    if not bg_raw or parse_color(resolve_vars(bg_raw, vars_map)) is None:
        code_computed = apply_cascade(
            rules,
            set(),  # tag-less code uses class selectors only when present
            "code",
            theme,
            pre["ancestors"] | pre["classes"] | {"source-body"} if "source-body" in pre["ancestors"] else pre["ancestors"] | pre["classes"],
            vars_map,
            color_raw,
        )
        # Prefer explicit .source-body code background when pre sits in a source body.
        if "source-body" in pre["ancestors"]:
            code_bg = apply_cascade(
                rules,
                set(),
                "code",
                theme,
                pre["ancestors"],
                vars_map,
                color_raw,
            )
            # Matching .source-body code requires ancestor source-body and tag code.
            scored_bg = None
            for rule in rules:
                if rule.selector == ".source-body code" or rule.selector.endswith(" code") and "source-body" in rule.selector:
                    if "background" in rule.props or "background-color" in rule.props:
                        raw = rule.props.get("background-color", rule.props.get("background", ""))
                        scored_bg = resolve_vars(raw, vars_map)
            if scored_bg and parse_color(scored_bg.split()[0] if scored_bg else "") is not None:
                bg_raw = scored_bg.split()[0]
            elif scored_bg:
                bg_raw = scored_bg
            else:
                bg_raw = body_bg
            _ = code_computed
        else:
            bg_raw = body_bg
    color_val = resolve_vars(color_raw, vars_map)
    bg_val = resolve_vars(bg_raw, vars_map)
    fg = parse_color(color_val)
    bg = parse_color(bg_val.split()[0] if bg_val else "")
    if fg is None or bg is None:
        raise ValueError(f"unresolved colors theme={theme} color={color_val!r} bg={bg_val!r}")
    return fg, bg, color_val, bg_val


def check_public(public_dir: Path) -> list[str]:
    css_path = public_dir / "style.css"
    if not css_path.is_file():
        return [f"missing stylesheet: {css_path}"]
    css_text = css_path.read_text(encoding="utf-8")
    rules = load_rules(css_text)
    themes = theme_vars(css_text)
    errors: list[str] = []
    pages = sorted(public_dir.rglob("index.html"))
    checked = 0
    for page in pages:
        html = page.read_text(encoding="utf-8")
        if "<pre" not in html:
            continue
        collector = BodyPreCollector()
        collector.feed(html)
        rel = page.relative_to(public_dir).as_posix()
        for pre in collector.pres:
            checked += 1
            for theme_name, vars_map in themes.items():
                fg, bg, color_val, bg_val = effective_colors(rules, pre, theme_name, vars_map)
                ratio = contrast_ratio(fg, bg)
                if ratio < MIN_RATIO:
                    errors.append(
                        f"{rel} pre#{pre['index']} theme={theme_name} contrast={ratio:.2f} "
                        f"(min {MIN_RATIO}) color={color_val} background={bg_val}"
                    )
    if checked == 0:
        errors.append("no <pre> elements found under body in public/")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: check_pre_contrast.py <public-dir>", file=sys.stderr)
        return 2
    public_dir = Path(sys.argv[1])
    if not public_dir.is_dir():
        print(f"not a directory: {public_dir}", file=sys.stderr)
        return 2
    errors = check_public(public_dir)
    if errors:
        print(f"FAIL: {len(errors)} pre contrast violation(s)")
        for err in errors:
            print(err)
        return 1
    print("PASS: all body <pre> elements meet 4.5:1 contrast in light and dark themes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
