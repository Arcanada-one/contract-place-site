# Coordinated Work programme publication

This addition opens a Journal issue and a three-language programme reader at
`/{en,ru,zh-Hans}/roadmap/coordinated-work/`. It is a research proposal and is
separate from the manuscript catalogue, source admission and actual task state.

## Sources and routes

- Journal source: `src/content/journal/2026-11-18-coordinated-work/`, with exact
  language hashes in the existing Journal manifest.
- Programme prose: the knowledge repository's
  `roadmap/coordinated-work/plan/PROGRAMME.md`, `PROGRAMME.ru.md` and
  `PROGRAMME.zh-Hans.md`.
- Counts: the same revision's `execution-graph.json`, not hardcoded completion
  counters or a second task registry.
- `coordinated-work-manifest.json` binds the three texts and graph to the exact
  roadmap source commit. The manuscript publication pin remains independent.
- Generated public provenance: `/coordinated-work.json`. It contains source
  identity and proposal counts, without native task identities or assignments.

The reader reuses the site's source reading layout and contents navigation.
Language links preserve the programme route; matching heading structure allows
section links to follow the same position in another language. The roadmap,
repository, local search, Journal and newest-article homepage provide entry
points. The existing six feeds retain their manifest-driven membership.

The canonical programme's Mermaid source is kept in an expandable source block.
Its adjacent numbered delivery sequence remains ordinary readable text. No
remote diagram renderer is loaded, and diagram syntax is not treated as a
scientific or execution verdict.

## Build and bounded verification

Use the existing full build with Pandoc 3.1.3, a clean manuscript checkout and a
clean roadmap checkout at their respective exact pins. `compile_coordinated_work`
runs before generated files are written and again before the build completes.
It refuses a mismatched revision/hash, missing locale, dirty source, unknown
prerequisite, duplicate task identity, unsafe link or unsupported raw HTML. Its
proposal checks are not a replacement for the source repository's graph,
scientific or per-paper release validators.

```sh
python3 -B scripts/test_coordinated_work.py
python3 -B scripts/build_publication.py --source-dir /absolute/manuscript --roadmap-source-dir /absolute/roadmap
python3 -B scripts/test_journal.py
python3 -B scripts/test_feeds.py
python3 -B scripts/check_page.py public
python3 -B scripts/check_links.py public
```

The tests are local finite controls. They do not establish hosted CI, source
acceptance, independent translation review, publication, browser visibility or
Muneral registration. Release still uses the existing reviewed source, manual
Deploy workflow, served-page readback and actual desktop/mobile inspection.

## Rollback

Revert the scoped publication change and rebuild from its previous source pins.
The existing publication and Journal histories remain intact. A source revert
does not undo native task operations; this site change performs none.
