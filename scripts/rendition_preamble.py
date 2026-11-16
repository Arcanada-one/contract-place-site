# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""One representation-only bridge: a legacy empty anchor moved onto the first H1.

Only an optional exact markdownlint directive and one empty HTML anchor before
an H1 are eligible. The target must begin with a real H1 carrying that exact id,
which occurs exactly once in each AST. No scientific text or stored bytes are
changed; callers still perform all ordinary section, formula and link checks.
"""
from __future__ import annotations

from collections import Counter
from html.parser import HTMLParser
import re

_ANCHOR_ONLY = re.compile(
    r'\s*(?:<!-- markdownlint-disable-next-line MD033 -->\s*)?'
    r'<a id="(?P<id>[A-Za-z][A-Za-z0-9_.:-]*)">\s*</a>\s*'
)


def _raw_prefix(blocks: list[dict]) -> str | None:
    """Accept only literal HTML and whitespace, never prose or a code sample."""
    pieces: list[str] = []
    for block in blocks:
        if block.get("t") == "RawBlock" and block["c"][0] == "html":
            pieces.append(block["c"][1])
        elif block.get("t") in {"Para", "Plain"}:
            inline: list[str] = []
            for node in block["c"]:
                if node.get("t") == "RawInline" and node["c"][0] == "html":
                    inline.append(node["c"][1])
                elif node.get("t") in {"Space", "SoftBreak", "LineBreak"}:
                    inline.append(" ")
                else:
                    return None
            pieces.append("".join(inline))
        else:
            return None
    return "\n".join(pieces)


class _RawIds(HTMLParser):
    def __init__(self, found: Counter):
        super().__init__(convert_charrefs=True)
        self.found = found

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key == "id" and value:
                self.found[value] += 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)


def _identifiers(blocks: list[dict]) -> Counter:
    """Count Pandoc Attr identities, including table cells, plus raw HTML ids.

    Attr is [identifier, classes, key/value pairs]. A code block's literal text
    is not HTML. Unknown/malformed HTML is never used as the qualifying H1.
    """
    found: Counter = Counter()

    def visit(value):
        if isinstance(value, list):
            if (len(value) == 3 and isinstance(value[0], str)
                    and isinstance(value[1], list)
                    and all(isinstance(c, str) for c in value[1])
                    and isinstance(value[2], list)
                    and all(isinstance(p, list) and len(p) == 2
                            and all(isinstance(c, str) for c in p) for p in value[2])):
                if value[0]:
                    found[value[0]] += 1
                # An Attr is terminal: do not count it twice through its fields.
                return
            for item in value:
                visit(item)
        elif isinstance(value, dict):
            if value.get("t") in {"RawBlock", "RawInline"}:
                content = value.get("c", [])
                if len(content) == 2 and content[0] == "html":
                    parser = _RawIds(found)
                    parser.feed(content[1])
                    parser.close()
            for item in value.values():
                visit(item)

    visit(blocks)
    return found


def source_for_anchor_parity(source_ast: dict, rendition_ast: dict) -> dict:
    """Return the original AST unless the exact, unique first-H1 bridge holds.

    This does not mark a rendition reviewed, admit a source, transform a heading,
    normalize prose or render anything. On success only the recognized source
    prefix is omitted from the *structural comparison*; the input AST is intact.
    """
    source = source_ast["blocks"]
    target = rendition_ast["blocks"]
    title_index = next((i for i, block in enumerate(source)
                        if block.get("t") == "Header" and block["c"][0] == 1), None)
    if title_index is None or title_index == 0 or not target:
        return source_ast
    raw = _raw_prefix(source[:title_index])
    match = _ANCHOR_ONLY.fullmatch(raw) if raw is not None else None
    if match is None:
        return source_ast
    anchor = match["id"]
    title = target[0]
    if (title.get("t") != "Header" or title["c"][0] != 1
            or title["c"][1][0] != anchor):
        return source_ast
    if _identifiers(source)[anchor] != 1 or _identifiers(target)[anchor] != 1:
        return source_ast
    return {**source_ast, "blocks": source[title_index:]}
