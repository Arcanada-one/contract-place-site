# Working on the Knowledge Contract publication site

## Canonical sources

Read [README.md](README.md), [src/DESIGN.md](src/DESIGN.md), `publication-manifest.json` and the pinned knowledge repository's `AGENTS.md`. Scientific manuscripts, engineering specifications, studies and reference documents are authored in the knowledge repository. The site compiles those exact files; do not maintain a second manuscript in generated catalogue data.

Use meaningful hyphenated slugs and separate science, engineering, reference and appendix routes. Earlier numbered addresses are compatibility entries. Historical protocol labels remain in their compatibility context. Distinguish completed documents from their actual deployment status.

The roadmap (`/{en,ru,zh-Hans}/roadmap/`) is planned work with its own pin in `roadmap-manifest.json`, separate from the manuscript pin; never publish a task state other than planned without execution evidence, and never add roadmap items to the publication catalogue.

## Preserve the interface

Retain the current design, English/Russian/Chinese navigation, local fonts, illustrations and licences. Manuscript bodies remain English unless an actual reviewed translation is supplied. Translations enter only as versioned renditions declared by the knowledge repository's sidecar (see [docs/versioned-renditions.md](docs/versioned-renditions.md)), stored at `translations/<language>/<source path>` and nowhere else. Links inside a rendition are ordinary relative Markdown resolved from the rendition file's own directory (as GitHub renders them); each target is mapped to one logical canonical identity for parity and routing, and unresolved or unsafe links are refused with `RENDITION_LINK_*`. Require exact source and rendition pins, a closed review object bound to those blobs when claiming review, a visible state (reviewed, partially-reviewed, unreviewed, stale, missing) and an explicit, never silent, English fallback. A rendition is not an independent source. Never write or machine-translate manuscript text here, and never use `--renditions-file` outside tests. Preserve the notice that Chinese interface text lacks native editorial review.

Keep complete text in prerendered HTML, accessible navigation and keyboard focus, narrow-screen reading, native MathML, bounded table/formula scrolling, citations and working fragments. Do not introduce inline executable code or private Drive links into the public surface.

## Build and verification

Use Node 24, Python 3 and Pandoc 3.1.3. Build from a clean checkout at the exact source pin:

```sh
python3 -B scripts/build_publication.py --source-dir /absolute/path/to/knowledge-contract --roadmap-source-dir /absolute/path/to/knowledge-contract-roadmap
python3 -B scripts/check_publication.py
python3 -B scripts/check_hygiene.py .
python3 -B scripts/check_page.py public
python3 -B scripts/check_papers.py public
python3 -B scripts/check_links.py public
python3 -B scripts/check_roadmap.py public --source-dir /absolute/path/to/knowledge-contract-roadmap
python3 -B scripts/test_build.py
python3 -B scripts/test_journal.py
python3 -B scripts/test_renditions.py
ROADMAP_SOURCE_DIR=/absolute/path/to/knowledge-contract-roadmap python3 -B scripts/test_roadmap.py
node scripts/test_search.js
```

Commit generated `src/content/catalog.json`, `src/site/content-provenance.json` and `public/` with their pin. The full build must reproduce these files. `node build.mjs` uses compiled data and does not substitute for compiling a changed knowledge revision.

Run relevant existing CI and REUSE checks. Inspect changed reading/layout behavior in a real browser on desktop and mobile. Record whether API/browser tests use fixtures or the deployed service.

## Daily journal issue

Daily journal issues are authored in this repository, not in the knowledge pin. To publish a new morning issue:

1. Add `src/content/journal/<YYYY-MM-DD>-<slug>/{en,ru,zh-Hans}.md` with YAML front matter (`site`, `section`, `slug`, `date`, `lang`, `title`, `excerpt`) and the Markdown body. Do not edit, shorten, translate or augment the manuscript here beyond the supplied files.
2. Append an entry to `src/content/journal/manifest.json` with `slug`, `date`, `folder` and each language's `file` plus `sha256`.
3. Rebuild (`scripts/build_publication.py` … or at least `node build.mjs` after catalogue compile).

That is the full checklist: folder + manifest entry + build. Routes become `/{en,ru,zh-Hans}/journal/<slug>/`, the journal index lists issues newest first, and `building-a-place` remains a separate noindex legacy route. `scripts/check_page.py` derives every manifest issue × locale from `manifest.json` and requires each page to be present and indexable; do not hand-edit journal article URLs into the checker.

`scripts/test_journal.py` checks every manifest issue × locale (body, title, index membership, indexability), keeps the 2026-11-11 digests as a separate regression pin, and `--mutants` runs an honest harness (a)–(g) that requires a green baseline, proof of mutation, an exact refusal, restore, and INFRA_ERROR (never KILLED) when the environment is broken.

## Search and release boundaries

Preserve localized search feedback, request cancellation, pagination visibility, anonymous read-only requests and safe text insertion. Compare provenance to the full publication pin; a backend `current` label is insufficient. A retrieved passage does not establish runtime admission.

Keep deployment dependent on publication validation. Never manufacture a human DCO, alter historical receipts to cover new bytes, or report deployment/index promotion from local checks. Follow the knowledge repository's publication process and report actual merged, deployed and indexed revisions separately.
