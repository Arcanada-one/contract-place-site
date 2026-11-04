# Knowledge Contract Arcana publication site

The source for [contract.place](https://contract.place). Publication edition **1.0** contains eight scientific papers, eleven engineering specifications, six engineering studies, a glossary, a bibliography and two appendices. Scientific arguments, normative requirements and observations have separate reading paths and explicit cross-references.

The interface retains the project's design, local fonts and illustrations in English, Russian and Chinese. **The 29 current manuscript texts are English.** Changing the interface language does not translate a manuscript. Earlier Russian texts remain traceable through the source-map appendix and pinned history. The Chinese interface has not received native editorial review.

## Reading structure

| Canonical source | English reading route |
| --- | --- |
| `papers/<slug>/PAPER.md` | `/en/science/<slug>/` |
| `engineering/specifications/<slug>/SPECIFICATION.md` | `/en/engineering/specifications/<slug>/` |
| `engineering/studies/<slug>/STUDY.md` | `/en/engineering/studies/<slug>/` |
| `reference/glossary/GLOSSARY.md` | `/en/reference/glossary/` |
| `reference/bibliography/BIBLIOGRAPHY.md` | `/en/reference/bibliography/` |
| `appendices/<slug>/APPENDIX.md` | `/en/appendices/<slug>/` |

The corresponding `/ru/` and `/zh-Hans/` pages provide localized navigation around the same English text. Previously published numbered addresses and unprefixed publication addresses are compatibility entries leading to the canonical documents.

Full manuscripts are present in built HTML. Pandoc preserves equations as MathML, tables, footnotes and document structure. Each reading page provides a table of contents, source attribution, a citation and links to its source revision.

## Source identity and generated data

`publication-manifest.json` pins the knowledge repository to an exact 40-character commit. Its `publication-catalog.json` is authoritative for the 29 canonical documents. The compiler generates their text, routes, metadata and source hashes in `src/content/catalog.json` and `src/site/content-provenance.json`; journal material and design remain in this repository.

`public/` is the complete deployment tree. Its `publication.json` records the source identity and document hashes. The catalogue also drives section indexes, sitemap and `llms.txt`. Do not edit generated HTML or replace manuscript paragraphs in generated data: change the canonical Markdown and rebuild.

An edition number identifies the documents. It does not certify scientific validity, change the stability of a historical protocol or authorize corpus admission.

## Build and preview

Use **Node.js 24**, Python 3.10 or newer, Git and **Pandoc 3.1.3**. The workflow uses Ubuntu 24.04 for the tested Pandoc version. Building makes no network requests.

Obtain a clean knowledge checkout at the exact commit in `publication-manifest.json`, then run:

```sh
python3 -B scripts/build_publication.py --source-dir /absolute/path/to/knowledge-contract
python3 -B scripts/check_publication.py
python3 -B scripts/check_hygiene.py .
python3 -B scripts/check_page.py public
python3 -B scripts/check_papers.py public
python3 -B scripts/check_links.py public
python3 -B scripts/test_build.py
node scripts/test_search.js
python3 -m http.server 8000 --directory public
```

Open `http://localhost:8000/en/`. Commit generated catalogue, provenance and `public/` with their source pin. `node build.mjs` reproduces the site from already compiled data for interface-only work; it does not reread Markdown. A source change requires the full Python compiler. Source commit and cleanliness are checked before and after compilation.

Edit the interface in `src/site/app.js`, CSS in `src/site/style.css` and assets in `src/site/assets/`. Preserve [design decisions](src/DESIGN.md) and asset notices. Rendering dependencies and visual assets are local; no browser rendering CDN is required.

## Search and API

Search uses the existing anonymous, read-only `https://api.contract.place/v1/search` route. Preserve result order, localized feedback, cancellation of earlier requests and pagination visibility. API text must remain text and must not become executable HTML.

The publication and API index are separate snapshots. A backend label of `current` does not establish equality with the site revision; compare the complete commit, repository and pinned source URL. Admission and uncertainty details remain available to readers.

The API restricts browser access to the production origin, so local preview is not an end-to-end API test. The frontend does not update the index. Requirements for task-specific contract delivery are in the [API appendix](https://contract.place/en/appendices/api-integration/); document search does not demonstrate implementation of those operations.

## CI and deployment

The reusable `check-publication` workflow checks out the exact source, compiles it, rebuilds the localized site, runs integrity, CSP, licensing markup, SEO, links, renderer and search checks, and verifies that generated catalogue, provenance and `public/` match committed files. It serves representative pages and assets locally and checks a missing page returns 404.

Regular CI preserves upstream REUSE, framework security and network-exposure jobs. Manual deployment requires publication validation before invoking the pinned shared workflow and publishes only `public/`.

The pinned knowledge commit must first exist in the public knowledge repository. After the authorized source contribution is merged, use its actual SHA, rebuild, commit and run CI. Local review snapshots do not substitute for the contributor's DCO attestation.

After deployment, read the served homepage, a paper, a specification, a study and `publication.json`; compare revisions and document hashes. Check desktop and mobile reading in a real browser. Admission and API indexing require their own controlled process and readback.

## Licensing and contributions

Text and original editorial illustrations use [CC BY 4.0](LICENSE); site code uses [Apache-2.0](LICENSE-CODE). Local fonts use SIL OFL 1.1 and retain their notices. Preserve [NOTICE](NOTICE), source credits and `REUSE.toml`. Credit Pavel Valentov, Knowledge Contract Arcana and https://contract.place. Names and logos are not licensed by the text/code licences; attribution does not imply endorsement.

Contributions require the Developer Certificate of Origin. The actual contributor signs off with `git commit -s` using their own identity. Content review, publication, index admission and deployment remain distinct decisions.

## Security

See [SECURITY.md](SECURITY.md) for private vulnerability reporting.
