# Knowledge Contract Arcana publication site

The source for [contract.place](https://contract.place). Publication edition **1.1** contains eight scientific papers, eleven engineering specifications, six engineering studies, a glossary, a bibliography and two appendices. Scientific arguments, normative requirements and observations have separate reading paths and explicit cross-references. This edition incorporates corrections to the published 1.0 corpus; its source review record distinguishes resolved findings from the remaining historical recovery gap.

The interface retains the project's design, local fonts and illustrations in English, Russian and Chinese. **The 30 current manuscript texts are English.** Changing the interface language does not translate a manuscript. Earlier Russian texts remain traceable through the source-map appendix and pinned history. The Chinese interface has not received native editorial review.

## Reading structure

| Canonical source | English reading route |
| --- | --- |
| `papers/<slug>/PAPER.md` | `/en/science/<slug>/` |
| `engineering/specifications/<slug>/SPECIFICATION.md` | `/en/engineering/specifications/<slug>/` |
| `engineering/studies/<slug>/STUDY.md` | `/en/engineering/studies/<slug>/` |
| `reference/glossary/GLOSSARY.md` | `/en/reference/glossary/` |
| `reference/bibliography/BIBLIOGRAPHY.md` | `/en/reference/bibliography/` |
| `appendices/<slug>/APPENDIX.md` | `/en/appendices/<slug>/` |

The corresponding `/ru/` and `/zh-Hans/` pages provide localized navigation around the same English text. Versioned language renditions (exact source and rendition pins, review state, explicit English fallback; none exist yet) are described in [docs/versioned-renditions.md](docs/versioned-renditions.md). Previously published numbered addresses and unprefixed publication addresses are compatibility entries leading to the canonical documents.

Full manuscripts are present in built HTML. Pandoc preserves equations as MathML, tables, footnotes and document structure. Each reading page provides a table of contents, source attribution, a citation and links to its source revision.

## Source identity and generated data

`publication-manifest.json` pins the knowledge repository to an exact 40-character commit. Its `publication-catalog.json` is authoritative for the 30 canonical documents. The compiler generates their text, routes, metadata and source hashes in `src/content/catalog.json` and `src/site/content-provenance.json`; journal material and design remain in this repository.

Daily journal issues live under `src/content/journal/`: three language Markdown files per issue plus `manifest.json` digests. After rebuild they appear at `/{en,ru,zh-Hans}/journal/<slug>/` and on the journal index (newest first). The legacy `/journal/building-a-place/` route stays noindex. See AGENTS.md “Daily journal issue”.

`public/` is the complete deployment tree. Its `publication.json` records the source identity and document hashes. The catalogue also drives section indexes, sitemap and `llms.txt`. Do not edit generated HTML or replace manuscript paragraphs in generated data: change the canonical Markdown and rebuild.

Runtime script and stylesheet URLs include their file-content hashes, so changed interface code does not reuse an earlier edition's browser cache entry. The compiled catalogue URL retains the full publication source pin.

An edition number identifies the documents. It does not certify scientific validity, change the stability of a historical protocol or authorize corpus admission.

## Build and preview

Use **Node.js 24**, Python 3.10 or newer, Git and **Pandoc 3.1.3**. The workflow uses Ubuntu 24.04 for the tested Pandoc version. Building makes no network requests.

Obtain a clean knowledge checkout at the exact commit in `publication-manifest.json` and a second clean checkout at the commit in `roadmap-manifest.json` (they may differ), then run:

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
node scripts/test_lab.js
python3 -m http.server 8000 --directory public
```

Open `http://localhost:8000/en/`. Commit generated catalogue, provenance and `public/` with their source pin. `node build.mjs` reproduces the site from already compiled data for interface-only work; it does not reread Markdown. A source change requires the full Python compiler. Source commit and cleanliness are checked before and after compilation.

Edit the interface in `src/site/app.js`, CSS in `src/site/style.css` and assets in `src/site/assets/`. Preserve [design decisions](src/DESIGN.md) and asset notices. Rendering dependencies and visual assets are local; no browser rendering CDN is required.

## Research roadmap

`/en/roadmap/`, `/ru/roadmap/` and `/zh-Hans/roadmap/` show the Knowledge Contract research roadmap as **planned work**: 25 task cards (`#rm-01` … `#rm-25`), priority bands, required and advisory dependencies as text tables, and links to the versioned sources. The task text is English on all three routes; the localized pages only translate navigation and labels. No task shows an execution state, date or progress, because none is synchronized: every task reads "planned".

The roadmap has its own pin, `roadmap-manifest.json`: repository, a full 40-character commit and the SHA-256 of each source file (`ROADMAP.md`, `roadmap/TASKS.md`, `roadmap/dependencies.json`, the linked `roadmap/EXPERIMENTS.md` and `roadmap/FOUNDATIONS_RELEASE_PLAN.md` (linked at the pin, not rendered), and `roadmap/SITE_DELIVERY.md`, from which only the public introduction is taken). It is independent of `publication-manifest.json`; the page shows both commits and states that they are separate. `scripts/roadmap.py` refuses a pin that is not a full commit, a checkout at another commit or with uncommitted changes, a hash mismatch, a missing or duplicate task, any disagreement between a card and `dependencies.json` (priority, owner, required outputs), a dangling or cyclic edge, any task state other than planned, and private identifiers. Compilation happens before any generated file is written. Known limit: the compiler checks structured state (task fields, `dependencies.json` keys, the one accepted `execution_bindings` value, dates), but it does not scan the free prose of card fields or of `ROADMAP.md` for status words such as "completed" or "active"; that text is published as written by the content owner, who reviews it. The TASKS.md preamble before the first card is rendered above the cards, and any unexpected text between a card header and its first field is refused. The roadmap is not part of the 29-document catalogue, and `public/roadmap.json` records its provenance.

## Search and API

Search uses the existing anonymous, read-only `https://api.contract.place/v1/search` route. Preserve result order, localized feedback, cancellation of earlier requests and pagination visibility. API text must remain text and must not become executable HTML.

The publication and API index are separate snapshots. A backend label of `current` does not establish equality with the site revision; compare the complete commit, repository and pinned source URL. Admission and uncertainty details remain available to readers.

The API restricts browser access to the production origin, so local preview is not an end-to-end API test. The frontend does not update the index. Requirements for task-specific contract delivery are in the [API appendix](https://contract.place/en/appendices/api-integration/); document search does not demonstrate implementation of those operations.

## CI and deployment

The reusable `check-publication` workflow checks out the exact source, compiles it, rebuilds the localized site, runs integrity, CSP, licensing markup, SEO, links, renderer and search checks, and verifies that generated catalogue, provenance and `public/` match committed files. It serves representative pages and assets locally and checks a missing page returns 404.

Regular CI preserves upstream REUSE, framework security and network-exposure jobs. Manual deployment requires publication validation before invoking the pinned shared workflow and publishes only `public/`.

The pinned knowledge commit must first exist in the public knowledge repository. After the authorized source contribution is merged, use its actual SHA, rebuild, commit and run CI. Local review snapshots do not substitute for the contributor's DCO attestation.

### Served-page readback

After the `publish` job, Deploy runs a `readback` job (`scripts/readback_served.py`). It fetches every `public/**/index.html` route from `https://contract.place` anonymously with a cache-busting query and compares the bytes with the committed build. Only the Cloudflare Web Analytics script tag is removed before comparing; any other difference counts. Mismatching routes are retried for up to 10 attempts, 30 s apart, to absorb edge propagation. HTTP errors and timeouts are failures. "Readback failed" means the publish step finished but the served bytes still differ from `public/`; the site is not yet serving this build, so do not report it as deployed. `scripts/test_readback.py` covers the script offline.

After deployment, read the served homepage, a paper, a specification, a study and `publication.json`; compare revisions and document hashes. Check desktop and mobile reading in a real browser. Admission and API indexing require their own controlled process and readback.

## Licensing and contributions

Text and original editorial illustrations use [CC BY 4.0](LICENSE); site code uses [Apache-2.0](LICENSE-CODE). Local fonts use SIL OFL 1.1 and retain their notices. Preserve [NOTICE](NOTICE), source credits and `REUSE.toml`. Credit Pavel Valentov, Knowledge Contract Arcana and https://contract.place. Names and logos are not licensed by the text/code licences; attribution does not imply endorsement.

Contributions require the Developer Certificate of Origin. The actual contributor signs off with `git commit -s` using their own identity. Content review, publication, index admission and deployment remain distinct decisions.

## Security

See [SECURITY.md](SECURITY.md) for private vulnerability reporting.
