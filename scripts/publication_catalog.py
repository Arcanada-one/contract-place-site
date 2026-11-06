# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Compile complete Markdown publications into the localized site's catalog."""
from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
import posixpath
import re

from roadmap import provenance as roadmap_provenance


def legacy_aliases(source: Path, previous: dict, documents: list[dict]) -> dict[str, str]:
    """Resolve compatibility pages through actual source links, never guessed IDs."""
    by_path = {doc['path']: doc for doc in documents}
    aliases = dict(previous.get('aliases', {}))
    for record in previous['records']:
        if record.get('canonical'):
            continue
        prefix = 'papers' if record['kind'] == 'paper' else 'spec'
        old = source / prefix / record['filename']
        if not old.is_file():
            raise ValueError(f'Missing historical compatibility page: {old}')
        targets = re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', old.read_text())
        matches = []
        for target in targets:
            if '://' in target:
                continue
            path = posixpath.normpath(str(PurePosixPath(prefix) / target))
            if path in by_path:
                matches.append(by_path[path])
        if not matches:
            raise ValueError(f'Compatibility page has no canonical target: {old}')
        route = ('research/' if record['kind'] == 'paper' else 'docs/') + record['id']
        aliases[route] = matches[0]['route'].removeprefix('/en/').rstrip('/')
    aliases.update({
        'wiki/knowledge-contract': 'engineering/specifications/knowledge-contract-core',
        'wiki/provenance': 'science/semantic-objects-and-context',
        'wiki/versioned-knowledge': 'science/revision-and-governance',
        'docs/model': 'engineering/specifications/knowledge-contract-core',
    })
    return aliases


def write_catalog(source: Path, site: Path, manifest: dict, documents: list[dict], renderer, roadmap: dict) -> None:
    path = site / 'src/content/catalog.json'
    previous = json.loads(path.read_text())
    aliases = legacy_aliases(source, previous, documents)
    records = []
    images = ('knowledge-prism.webp', 'knowledge-landscape.webp', 'knowledge-dialogue.webp')
    categories = {
        'semantic-objects-and-context': 'foundations',
        'constrained-transformations': 'foundations',
        'retrieval-and-context-composition': 'systems',
        'interaction-and-memory': 'systems',
        'revision-and-governance': 'systems',
        'controlled-knowledge-reuse': 'evaluation',
        'evidence-and-falsification': 'evaluation',
        'knowledge-utility': 'evaluation',
    }
    for number, doc in enumerate(documents):
        fragment = renderer.document(doc)
        kind = 'spec' if doc['type'] == 'specification' else doc['type']
        records.append({
            'canonical': True, 'id': doc['slug'], 'kind': kind,
            'type': doc['type'], 'path': doc['path'], 'route': doc['route'],
            'title': doc['title'], 'titleRu': doc['title'],
            'summary': doc.get('summary', ''), 'language': 'en',
            'html': fragment['html'], 'toc': fragment['toc'],
            'title_id': fragment['title_id'], 'math_count': fragment['math_count'],
            'source': renderer.source_url(doc['path']),
            'history': renderer.source_url(doc['path'], True),
            'source_sha256': doc['sha256'], 'revision': manifest['commit'],
            'image': images[number % len(images)],
            'category': categories.get(doc['slug'], 'engineering'),
        })
    payload = {
        'publication': manifest,
        'records': records, 'articles': previous['articles'], 'aliases': aliases,
        'roadmap': roadmap,
        'source': 'https://contract.place/', 'license': 'CC-BY-4.0',
        'author': 'Pavel Valentov', 'retrieved': '2026-11-04',
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
    old_provenance = json.loads((site / 'src/site/content-provenance.json').read_text())
    provenance = {
        'publication': manifest,
        'records': [{k: r[k] for k in ('id', 'type', 'path', 'source', 'source_sha256', 'revision')} for r in records],
        'articles': old_provenance['articles'],
        'roadmap': roadmap_provenance(roadmap),
        'site_integration_base': '91da6a35b4234d409de4c0a0777ff9c469bc8400',
        'license': 'CC-BY-4.0', 'author': 'Pavel Valentov',
    }
    (site / 'src/site/content-provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n')
