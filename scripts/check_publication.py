#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
# SPDX-License-Identifier: Apache-2.0
"""Verify complete article text, source pins, translated UI and compatibility."""
from collections import Counter
import json
from pathlib import Path
import re
from publication_checks import check_site

ROOT = Path(__file__).resolve().parents[1]
public = ROOT / 'public'
manifest = json.loads((ROOT / 'publication-manifest.json').read_text())
published = json.loads((public / 'publication.json').read_text())
catalog = json.loads((ROOT / 'src/content/catalog.json').read_text())
assert not published.get('preview')
for key in ('schema_version', 'commit', 'edition', 'repository', 'catalog'):
    assert published[key] == manifest[key] == catalog['publication'][key], key
assert Counter(d['type'] for d in published['documents']) == {
    'paper': 8, 'specification': 11, 'study': 6, 'glossary': 1,
    'bibliography': 1, 'appendix': 2,
}, 'Publication inventory is incomplete'
records = {r['route']: r for r in catalog['records']}
assert len(records) == 29
equations = 0
for doc in published['documents']:
    record = records[doc['route']]
    assert doc['sha256'] == record['source_sha256']
    assert re.fullmatch('[0-9a-f]{64}', doc['sha256'])
    assert record['revision'] == manifest['commit']
    assert record['language'] == 'en'
    for locale in ('en', 'ru', 'zh-Hans'):
        route = doc['route'].replace('/en/', '/' + locale + '/', 1)
        html = (public / route.lstrip('/') / 'index.html').read_text()
        assert record['html'] in html, 'Source body altered or abbreviated: ' + route
        assert 'class="source-body prose" lang="en"' in html, route
        assert record['source'] in html and record['history'] in html, route
        assert '<h1 id="' + record['title_id'] + '" lang="en">' in html, route
        assert html.count('<math ') == doc['math_count'], route
        assert 'type="application/ld+json"' in html and '"inLanguage":"en"' in html, route
    equations += doc['math_count']
    for heading in record['toc']:
        assert 'id="' + heading['id'] + '"' in record['html'], doc['route']
for locale in ('en', 'ru', 'zh-Hans'):
    home = (public / locale / 'index.html').read_text()
    for marker in ('3.0.0-draft.1', 'not in this release', 'sandbox:/'):
        assert marker not in home, (locale, marker)
    assert '/publication.json' in home
    search = (public / locale / 'search/index.html').read_text()
    assert 'data-publication-commit="' + manifest['commit'] + '"' in search
    for alias, target in catalog['aliases'].items():
        html = (public / locale / alias / 'index.html').read_text()
        assert 'name="robots" content="noindex,follow"' in html
        assert 'href="/' + locale + '/' + target + '/"' in html
        assert 'class="source-body prose"' not in html, 'Alias must not duplicate the corpus'
for page in public.rglob('*.html'):
    html = page.read_text()
    assert 'src="/content.js?v=' + manifest['commit'] + '"' in html, 'Unversioned publication catalog: ' + str(page)
count = check_site(public)
print(f'Publication checks OK: 29 full documents / 87 localized reading pages, {equations} original MathML expressions, {count} pages; exact body and source bindings.')
