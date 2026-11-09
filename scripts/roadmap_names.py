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
_OBSERVATION = re.compile(r'\A\s*\*\*Artifact observation \(([^\n()*]+)\)\.\*\* ([^\n]+)\s*\Z')
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
        # Preserve both dated observations as prose within the old Gap field.
        rest = ('\n\n**Gap.** *Artifact observation (' + observation[1] + ').* '
                + observation[2] + '\n\n*Original gap (' + gap[1] + ').* '
                + rest[gap.end():])
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
