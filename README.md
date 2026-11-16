# Knowledge Contract Arcana publication site

The source for [contract.place](https://contract.place). The pinned edition **1.1** reading catalogue contains **31 works**: ten scientific papers (eight baseline papers and two foundations research drafts), eleven engineering specifications, six engineering studies, a glossary, a bibliography and two appendices. Scientific arguments, normative requirements and observations have separate reading paths and explicit cross-references. This edition incorporates corrections to the published 1.0 corpus; its source review record distinguishes resolved findings from the remaining historical recovery gap. The later 36-work inventory on the knowledge repository's `main` is a separate snapshot; this release retains the pinned 31-work catalogue.

The interface retains the project's design, local fonts and illustrations in English, Russian and Simplified Chinese. English remains the canonical source language. Every pinned work has a Russian and Simplified Chinese body rendition: **62 renditions across 93 reader pages**, with eight historical reviewed renditions preserved byte for byte and 54 visible unreviewed renditions carrying an explicit notice. Source-bound localized titles and summaries have their own unreviewed status. Earlier Russian texts remain traceable through the source-map appendix and pinned history. Automated coverage and author-side checks do not establish native-speaker or external editorial review. The [15 November localization audit](docs/localization-audit-2026-11-15.md) records coverage, controls and the separate release/readback status.

## Reading structure

| Canonical source | English reading route |
| --- | --- |
| `papers/<slug>/PAPER.md` | `/en/science/<slug>/` |
| `engineering/specifications/<slug>/SPECIFICATION.md` | `/en/engineering/specifications/<slug>/` |
| `engineering/studies/<slug>/STUDY.md` | `/en/engineering/studies/<slug>/` |
| `reference/glossary/GLOSSARY.md` | `/en/reference/glossary/` |
| `reference/bibliography/BIBLIOGRAPHY.md` | `/en/reference/bibliography/` |
| `appendices/<slug>/APPENDIX.md` | `/en/appendices/<slug>/` |

The corresponding `/ru/` and `/zh-Hans/` pages provide localized navigation, metadata and complete body renditions with visible fidelity state. [Versioned language renditions](docs/versioned-renditions.md) retain exact source/rendition pins, historical review scope and explicit missing/stale states. The current coverage gate requires a visible body for every work and target language. Previously published numbered addresses and unprefixed publication addresses remain compatibility entries leading to the canonical documents; all 322 baseline HTML routes are retained.

Full manuscripts are present in built HTML. Pandoc preserves equations as MathML, tables, footnotes and document structure. Each reading page provides a table of contents, source attribution, a citation and links to its source revision.

## Source identity and generated data

`publication-manifest.json` pins the knowledge repository to an exact 40-character commit. Its `publication-catalog.json` is authoritative for the 31 catalogued works. The source repository's `publication-localization.json` binds localized titles and summaries separately from the body records in `publication-renditions.json`; see [catalogue localization](docs/catalogue-localization.md). Source-owned `publication-formula-localizations.json` separately binds visible prose inside formulas; the renderer retains canonical TeX and mathematical structure and records an unreviewed presentation scope. `publication-review-localizations.json` separately translates historical review explanations while preserving the original records and their scope. The compiler generates text, routes, metadata and source hashes in `src/content/catalog.json` and `src/site/content-provenance.json`; journal material and design remain in this repository.

Daily journal issues live under `src/content/journal/`: three language Markdown files per issue plus `manifest.json` digests. The eight dated issues provide 24 localized journal pages at `/{en,ru,zh-Hans}/journal/<slug>/` and appear on the journal index newest first. Local search includes these issues. The legacy `/journal/building-a-place/` route stays noindex; its retained project note is localized. See AGENTS.md “Daily journal issue”.

The daily Journal also provides full-article RSS 2.0 and Atom 1.0 feeds at `/{en,ru,zh-Hans}/journal/rss.xml` and `/{en,ru,zh-Hans}/journal/atom.xml`. The index and footer expose subscription links, and HTML includes autodiscovery. Feed membership follows the published daily-issue manifest; undated source-review pages, legacy noindex notes, research works and private Lab data are excluded. See [Daily Journal feeds](docs/journal-feeds.md) for scope, day-precision dates, stable IDs and release checks.

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
python3 -B scripts/check_localization.py public --source-dir /absolute/path/to/knowledge-contract --roadmap-source-dir /absolute/path/to/knowledge-contract-roadmap
python3 -B scripts/test_build.py
python3 -B scripts/test_journal.py
python3 -B scripts/test_renditions.py
python3 -B scripts/test_catalogue_localization.py
python3 -B scripts/test_formula_localization.py
python3 -B scripts/test_review_localization.py
node scripts/test_review_localization.js
python3 -B scripts/test_localization.py
ROADMAP_SOURCE_DIR=/absolute/path/to/knowledge-contract-roadmap python3 -B scripts/test_roadmap.py
python3 -B scripts/test_roadmap_localization.py
node scripts/test_search.js
node scripts/test_ui_localization.js
node scripts/test_lab.js
python3 -m http.server 8000 --directory public
```

Open `http://localhost:8000/en/`. Commit generated catalogue, provenance and `public/` with their source pin. `node build.mjs` reproduces the site from already compiled data for interface-only work; it does not reread Markdown. A source change requires the full Python compiler. Source commit and cleanliness are checked before and after compilation.

Edit the interface in `src/site/app.js`, CSS in `src/site/style.css` and assets in `src/site/assets/`. Preserve [design decisions](src/DESIGN.md) and asset notices. Rendering dependencies and visual assets are local; no browser rendering CDN is required.

## Research roadmap

`/en/roadmap/`, `/ru/roadmap/` and `/zh-Hans/roadmap/` show the Knowledge Contract research roadmap as **planned work**: 25 task cards (`#rm-01` … `#rm-25`) per language, priority bands, required and advisory dependencies as text tables, and links to the versioned sources. The overview, introduction, names and task fields are localized: 75 rendered cards and 453 rendered fields across the three pages. Russian and Chinese translations visibly remain unreviewed. Every task retains its planned status and the source's dated observations; the page does not claim synchronized execution state or live progress.

The roadmap has its own pin, `roadmap-manifest.json`: repository, a full 40-character commit and the SHA-256 of each source file (`ROADMAP.md`, `roadmap/TASKS.md`, `roadmap/dependencies.json`, the linked `roadmap/EXPERIMENTS.md` and `roadmap/FOUNDATIONS_RELEASE_PLAN.md` (linked at the pin, not rendered), and `roadmap/SITE_DELIVERY.md`, from which only the public introduction is taken). Localization additionally pins `roadmap/localizations.json`, both `roadmap/ROADMAP.full.<locale>.md` overviews and both `roadmap/TASKS.<locale>.json` payloads. It is independent of `publication-manifest.json`; the page shows both commits and states that they are separate. `scripts/roadmap.py` refuses a pin that is not a full commit, a checkout at another commit or with uncommitted changes, a hash mismatch, a missing or duplicate task, any disagreement between a card and `dependencies.json` (priority, owner, required outputs), a dangling or cyclic edge, any task state other than planned, and private identifiers. `scripts/roadmap_localization.py` separately binds translations to unchanged historical and current source bytes, preserves dates, numbers, links, code and mathematics, and rejects translated state/authority injection. Compilation happens before any generated file is written. Known limit: the compiler checks structured state (task fields, `dependencies.json` keys, the one accepted `execution_bindings` value, dates), but it does not scan the free prose of card fields or of `ROADMAP.md` for status words such as "completed" or "active"; that text is published as written by the content owner, who reviews it. The TASKS.md preamble before the first card is rendered above the cards, and any unexpected text between a card header and its first field is refused. The roadmap is separate from the 31-work reading catalogue, and `public/roadmap.json` records its provenance.

## Search and API

Search uses the existing anonymous, read-only `https://api.contract.place/v1/search` route. Preserve result order, localized feedback, cancellation of earlier requests and pagination visibility. API text must remain text and must not become executable HTML.

The publication and API index are separate snapshots. A backend label of `current` does not establish equality with the site revision; compare the complete commit, repository and pinned source URL. Admission and uncertainty details remain available to readers.

The API restricts browser access to the production origin, so local preview is not an end-to-end API test. The frontend does not update the index. Requirements for task-specific contract delivery are in the [API appendix](https://contract.place/en/appendices/api-integration/); document search does not demonstrate implementation of those operations.

## CI and deployment

The reusable `check-publication` workflow checks out the exact source, compiles it, rebuilds the localized site, runs integrity, CSP, licensing markup, SEO, links, renderer and search checks, and verifies that generated catalogue, provenance and `public/` match committed files. It serves representative pages and assets locally and checks a missing page returns 404.

Regular CI preserves upstream REUSE, framework security and network-exposure jobs. Manual deployment requires publication validation before invoking the pinned shared workflow and publishes only `public/`.

The pinned knowledge commit must first exist in the public knowledge repository. After the authorized source contribution is merged, use its actual SHA, rebuild, commit and run CI. Local review snapshots do not substitute for the contributor's DCO attestation.

### Served-page readback

After the `publish` job, Deploy runs a `readback` job (`scripts/readback_served.py`). It fetches every committed `public/**/index.html` route from `https://contract.place` anonymously, with `Accept: text/html`, in two forms: the ordinary URL without a query (`bare`) and the URL with `?readback=<run-id>` (`readback_query`). Both responses must be HTTP 200 and match the committed build in the same attempt. Redirects are not followed: any 3xx is reported as `ERROR <route> … HTTP <code> Location=<value>`. Before comparing, at most one Cloudflare Web Analytics tag is removed, and only if it has exactly this shape: `<script type="module" src="https://static.cloudflareinsights.com/beacon.min.js/v<hex>" integrity="sha512-<base64>" data-cf-beacon='{"version":…,"token":<32 hex>,"r":…,"spa":…}' crossorigin="anonymous"></script>` with an empty body, the attributes in that order and no others. Cloudflare inserts the tag followed by one newline (`\n`) directly before `</body>`; exactly that tag plus that newline, immediately followed by `</body>`, is removed, and the same tag elsewhere, or without the newline, is a mismatch. The edge does this only for requests that send `Accept: text/html`, and not from every network location, so a probe may see no injection at all. Any other script, a changed attribute, a second tag or any other difference counts as a mismatch. Mismatching routes are retried for up to 10 attempts, 30 s apart; both variants are fetched again on each retry. HTTP errors and timeouts are failures.

Every readback prints a `witness:` header before the route lines: `build_revision`, `origin`, `request_method`, `request_accept`, `request_user_agent`, `request_variants: bare,readback_query`, `redirects: refused`, `cache_token` (used by the query variant), `probe` (runner name, OS and environment, or `local`; never hostnames or IPs), `probe_region` (`UNKNOWN` unless given by `--probe-region`), `started_utc`, `finished_utc` and `normaliser` (a name plus the SHA-256 of the compiled pattern). Each route has two result lines retaining the `IDENTICAL`, `DIFF` or `ERROR` prefix and `status`, `raw_sha256`, `norm_sha256` and `stripped` fields, with an added `variant=bare` or `variant=readback_query`. The final `readback: X/N IDENTICAL` summary still counts routes: a route counts only when both variants match. `witness: injected_pages=<n>` counts unique routes where the analytics tag was removed from either response. A verdict holds only for the printed request shapes and probe, not for other browsers, user agents or regions.

Earlier readback logs without `request_variants` checked only the query form. Their recorded outcomes remain evidence for that request; they do not establish success for ordinary URLs. A difference between variants does not by itself establish a cache-related cause. The complete HTML inventory is derived from the generated deployment tree, including the separate `404.html`. The default served-page readback selects every generated `index.html` route and makes two request variants per route on its first attempt; each run records its actual inventory and request count. Adding a Journal issue changes those counts, so previous release totals are not a fixed gate. The existing timeout and bounded retry policy are unchanged.

A failed readback means `publish` already ran and the bytes served for the current build are mismatched or unverified; it does not undo the upload and does not by itself say why. Limits: it checks only committed `index.html` routes, from one probe location; it does not check non-HTML assets, every CDN region, access control or publication admission. `scripts/test_readback.py` covers the script offline.

After deployment, read the served homepage, a paper, a specification, a study and `publication.json`; compare revisions and document hashes. Check desktop and mobile reading in a real browser. Admission and API indexing require their own controlled process and readback.

## Licensing and contributions

Text and original editorial illustrations use [CC BY 4.0](LICENSE); site code uses [Apache-2.0](LICENSE-CODE). Local fonts use SIL OFL 1.1 and retain their notices. Preserve [NOTICE](NOTICE), source credits and `REUSE.toml`. Credit Pavel Valentov, Knowledge Contract Arcana and https://contract.place. Names and logos are not licensed by the text/code licences; attribution does not imply endorsement.

Contributions require the Developer Certificate of Origin. The actual contributor signs off with `git commit -s` using their own identity. Content review, publication, index admission and deployment remain distinct decisions.

## Security

See [SECURITY.md](SECURITY.md) for private vulnerability reporting.

