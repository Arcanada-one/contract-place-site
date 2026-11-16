# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Strict compatibility adapter for the accepted, readable roadmap source format.

Only presentation syntax is normalized. Task ids, graph checks, scope, all prose
and the old planned-only state gate remain the responsibility of roadmap.py.
"""
from __future__ import annotations

import re

_MARKER = '<!-- markdownlint-disable-next-line MD033 -->'
_CARD = re.compile(r'(?m)^<a id="(rm-[0-9]{2})"></a>[ \t]*$')
_ALIAS = re.compile(r'^<a id="([a-z][a-z0-9-]*)"></a>$')
_HEADER = re.compile(
    r'(?m)^\*\*Priority:\*\* (Immediate|Next|Expansion) · '
    r'\*\*Owner:\*\* ([^·\n]+?) · \*\*Required outputs:\*\* (.+?)\.[ \t]*$'
)
_PRIORITY = {'Immediate': 'P0', 'Next': 'P1', 'Expansion': 'P2'}
# Exactly one Artifact observation before the priority header; optionally one
# Current source observation after it. Same date/text character classes; any
# other header prose still raises the existing unexpected-prose error.
_OBSERVATION = re.compile(
    r'\A\s*\*\*Artifact observation \(([^\n()*]+)\)\.\*\* ([^\n]+)'
    r'(?:\s*\*\*Current source observation \(([^\n()*]+)\)\.\*\* ([^\n]+))?'
    r'\s*\Z'
)
_GAP = re.compile(r'\A\s*\*\*Original gap \(([^\n()*]+)\)\.\*\* ')


def strip_editorial_markers(text: str) -> str:
    """Remove only known, inert whole-line source maintenance comments.

    Other raw HTML, including unknown comments, is retained for the existing
    Pandoc/HTML refusal. This does not create an HTML allowlist or accept anchors
    in arbitrary prose.
    """
    allowed = {_MARKER, '<!-- WORKSTREAM_TABLE -->', '<!-- /WORKSTREAM_TABLE -->'}
    return ''.join(line for line in text.splitlines(keepends=True)
                   if line.rstrip('\r\n') not in allowed)


def normalize_tasks(text: str) -> str:
    """Return the old card syntax for strictly recognized readable source.

    Legacy source is returned byte-for-byte. For readable cards, unique explicit
    compatibility anchors establish identity; unique short names resolve named
    dependencies. There is no positional assignment of an RM identifier.
    """
    if not isinstance(text, str):
        raise ValueError('TASKS.md must be text')
    starts = list(_CARD.finditer(text))
    if not starts:
        return text
    if re.search(r'(?m)^## RM-', text):
        raise ValueError('Mixed legacy and readable roadmap card syntax')
    # An H2 card without an explicit compatibility id must not disappear.
    if len(re.findall(r'(?m)^## ', text)) != len(starts):
        raise ValueError('Every readable card needs exactly one explicit compatibility anchor')
    cards = []
    names: dict[str, str] = {}
    seen_ids: set[str] = set()
    seen_anchors: set[str] = set()
    preamble = strip_editorial_markers(text[:starts[0].start()]).rstrip()
    for index, start in enumerate(starts):
        ident = start[1].upper()
        if ident in seen_ids or not 1 <= int(ident[3:]) <= 25:
            raise ValueError('Duplicate or unsupported roadmap identity: ' + ident)
        seen_ids.add(ident)
        end = starts[index+1].start() if index+1 < len(starts) else len(text)
        chunk = strip_editorial_markers(text[start.start():end]).strip()
        lines = chunk.splitlines()
        cursor = 0
        while cursor < len(lines) and (not lines[cursor].strip() or _ALIAS.fullmatch(lines[cursor])):
            alias = _ALIAS.fullmatch(lines[cursor])
            if alias:
                if alias[1] in seen_anchors:
                    raise ValueError('Duplicate roadmap anchor: ' + alias[1])
                seen_anchors.add(alias[1])
            cursor += 1
        if cursor >= len(lines) or not lines[cursor].startswith('## '):
            raise ValueError(ident + ': readable heading missing or unsafe markup before heading')
        title = lines[cursor][3:]
        short, separator, subtitle = title.partition(': ')
        if (not separator or not subtitle.strip() or not 1 <= len(short.split()) <= 3
                or re.search(r'[<>\[\]{}]|\b(?:RM|F|G|S|N|P)-?\d+\b', title)):
            raise ValueError(ident + ': expected a readable short name and explanatory subtitle')
        if short in names:
            raise ValueError('Ambiguous roadmap short name: ' + short)
        names[short] = ident
        body = '\n'.join(lines[cursor+1:]) + '\n'
        headers = list(_HEADER.finditer(body))
        if len(headers) != 1:
            raise ValueError(ident + ': exactly one readable priority/owner/dependency header required')
        header = headers[0]
        observation = _OBSERVATION.fullmatch(body[:header.start()])
        if not observation:
            raise ValueError(ident + ': dated artifact observation missing or unexpected header prose')
        rest = body[header.end():]
        gap = _GAP.match(rest)
        if not gap:
            raise ValueError(ident + ': dated original gap missing')
        # Preserve dated observations as verbatim history within the old Gap field.
        gap_parts = [
            '\n\n**Gap.** *Artifact observation (' + observation[1] + ').* '
            + observation[2]
        ]
        if observation[3] is not None:
            gap_parts.append(
                '\n\n*Current source observation (' + observation[3] + ').* '
                + observation[4]
            )
        gap_parts.append(
            '\n\n*Original gap (' + gap[1] + ').* ' + rest[gap.end():]
        )
        rest = ''.join(gap_parts)
        if rest.count('**Preparation boundary.**') != 1:
            raise ValueError(ident + ': exactly one preparation boundary required')
        rest = rest.replace('**Preparation boundary.**', '**Start boundary.**')
        cards.append((ident, title, header[1], header[2].strip(), header[3], rest))
    output = [preamble + '\n\n']
    for ident, title, priority, owner, required_text, rest in cards:
        required = [] if required_text == 'none' else [name.strip() for name in required_text.split(',')]
        if len(required) != len(set(required)) or any(name not in names for name in required):
            raise ValueError(ident + ': unknown or duplicate named dependency')
        identifiers = ', '.join(names[name] for name in required) or 'none'
        output.append(f'## {ident}\n\n### {title}\n\n**Priority:** {_PRIORITY[priority]} · '
                      f'**Owner:** {owner} · **Required outputs:** {identifiers}.' + rest.rstrip() + '\n\n')
    return ''.join(output)


DISPLAY_NAME_KEYS = frozenset({'display_name', 'display_name_ru'})
_NAME = re.compile(r"[^\W\d_]+(?:[-’'][^\W\d_]+)*(?: [^\W\d_]+(?:[-’'][^\W\d_]+)*){0,2}\Z")


def validate_display_names(nodes: list[dict]) -> None:
    """Validate the two optional presentation fields without changing the graph.

    Legacy nodes have neither field. A readable graph has both fields on every node,
    with unique, plain-text, one-to-three-word labels in each language. Unknown
    fields and execution-state assertions remain subject to the original validator.
    """
    modes = set()
    seen = {key: set() for key in DISPLAY_NAME_KEYS}
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError('Malformed dependency node')
        present = set(node) & DISPLAY_NAME_KEYS
        if present and present != DISPLAY_NAME_KEYS:
            raise ValueError('Both roadmap display names are required together')
        modes.add(bool(present))
        for key in present:
            value = node[key]
            if not isinstance(value, str) or len(value) > 120 or not _NAME.fullmatch(value):
                raise ValueError('Invalid plain-text roadmap display name: ' + key)
            normalized = value.casefold()
            if normalized in seen[key]:
                raise ValueError('Duplicate roadmap display name: ' + value)
            seen[key].add(normalized)
    if len(modes) > 1:
        raise ValueError('Mixed legacy and readable dependency node names')


def check_card_display_name(card: dict, node: dict) -> None:
    """The named graph and parsed English card must name the same stable id."""
    if 'display_name' not in node:
        return
    short, separator, subtitle = card.get('title', '').partition(': ')
    if not separator or not subtitle.strip() or short != node['display_name']:
        raise ValueError(str(node.get('id')) + ': card title differs from dependency display_name')


# Closed set of exact historical (display_revision, execution_pause) pairs from
# accepted source snapshots, not current execution. Validated but never emitted
# as a live task state. Changed values require another explicit compatibility
# review.
# (a) 2026-11-08 accepted snapshot
# (b) 2026-11-11 from KC-A1 (knowledge-contract 161a01af)
_EDITORIAL_KEYS = ("display_revision", "execution_pause")
_EDITORIAL_PAIRS = (
    {
        "display_revision": "2026-11-08",
        "execution_pause": (
            "Engineering paused by operator; analytical authorship continues; "
            "not a Muneral state update"
        ),
    },
    {
        "display_revision": "2026-11-11",
        "execution_pause": (
            "rescinded_by_operator_2026-11-11; see roadmap/EXECUTION_STATUS.md; "
            "not a Muneral state update"
        ),
    },
)


class _EditorialMetadata:
    """Closed set of historical pairs; iterates as field names for TOP_LEVEL_KEYS."""

    __slots__ = ("_pairs",)

    def __init__(self, pairs: tuple[dict[str, str], ...]) -> None:
        normalized = []
        for pair in pairs:
            if tuple(pair) != _EDITORIAL_KEYS or set(pair) != set(_EDITORIAL_KEYS):
                raise ValueError("internal: editorial pair keys must be exact")
            normalized.append(frozenset(pair.items()))
        self._pairs = frozenset(normalized)

    def __iter__(self):
        return iter(_EDITORIAL_KEYS)

    def __len__(self) -> int:
        return len(_EDITORIAL_KEYS)

    def recognizes(self, deps: dict) -> bool:
        try:
            observed = frozenset((key, deps[key]) for key in _EDITORIAL_KEYS)
        except TypeError:
            return False
        return observed in self._pairs


EDITORIAL_METADATA = _EditorialMetadata(_EDITORIAL_PAIRS)
# Named copies of the two accepted snapshots for tests and byte checks.
EDITORIAL_METADATA_PAIR_A = dict(_EDITORIAL_PAIRS[0])
EDITORIAL_METADATA_PAIR_B = dict(_EDITORIAL_PAIRS[1])


def validate_editorial_metadata(deps: dict) -> None:
    """Recognize only accepted historical notes, without applying their policy.

    Neither field authorizes stopping or restarting anything. The actual source
    bytes remain pinned, and every emitted task still has the planned-only state.
    Unknown, partial, altered or mixed legacy/current declarations are refused.
    """
    present = set(deps) & set(EDITORIAL_METADATA)
    if not present:
        return
    if present != set(EDITORIAL_METADATA) or not EDITORIAL_METADATA.recognizes(deps):
        raise ValueError('Unrecognized historical roadmap display metadata')
    if not deps.get('nodes') or any('display_name' not in node for node in deps['nodes']):
        raise ValueError('Historical display metadata requires the readable node schema')
