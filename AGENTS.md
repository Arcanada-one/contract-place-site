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
python3 -B scripts/test_renditions.py
ROADMAP_SOURCE_DIR=/absolute/path/to/knowledge-contract-roadmap python3 -B scripts/test_roadmap.py
node scripts/test_search.js
```

Commit generated `src/content/catalog.json`, `src/site/content-provenance.json` and `public/` with their pin. The full build must reproduce these files. `node build.mjs` uses compiled data and does not substitute for compiling a changed knowledge revision.

Run relevant existing CI and REUSE checks. Inspect changed reading/layout behavior in a real browser on desktop and mobile. Record whether API/browser tests use fixtures or the deployed service.

## Search and release boundaries

Preserve localized search feedback, request cancellation, pagination visibility, anonymous read-only requests and safe text insertion. Compare provenance to the full publication pin; a backend `current` label is insufficient. A retrieved passage does not establish runtime admission.

Keep deployment dependent on publication validation. Never manufacture a human DCO, alter historical receipts to cover new bytes, or report deployment/index promotion from local checks. Follow the knowledge repository's publication process and report actual merged, deployed and indexed revisions separately.
