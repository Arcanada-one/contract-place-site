# Localization audit — 15 November 2026

## Scope and release identity

This audit covers the complete rendered contract.place site in English, Russian
and Simplified Chinese, including manuscript readers, catalogue metadata,
navigation, search feedback, journal, programme, retained article excerpts,
roadmap and public Lab/unavailable states. English remains the canonical source
language. Scientific notation, literal code, technical identifiers, attribution,
rights and primary-reference identities retain their source meaning.

The publication scope is the pinned **31-work reading catalogue**. A later
36-work inventory on the knowledge repository's `main` is a separate snapshot;
those additional entries are not silently included in this release.

| Boundary | Exact reference or current state |
| --- | --- |
| Audited site baseline | `69a15f5446029bac7b2f11f04b11d34aaf97b215` |
| Canonical English content used for the translations | `161a01afb1b756adf059ea2e1cbdd0dca29d83a2` in knowledge-contract |
| Existing source contribution | [knowledge-contract PR #122](https://github.com/Arcanada-one/knowledge-contract/pull/122), integration head `902924e35198061fcf5ccc3744e690649bb7cf72` |
| Pre-format source integration snapshot | `86c5654c3e3811891793655da345f5084b4eaf7f`; superseded for final publication by the formatting follow-up |
| Formatting body commit | `101431f2cf0b141d317445fabd6b6122f9fe1dba` |
| Final source pin after formatting and rendition repinning | [`55e279c43dc9bcf8732467a32661c2ac4b7cf920`](https://github.com/Arcanada-one/knowledge-contract/tree/55e279c43dc9bcf8732467a32661c2ac4b7cf920) |
| Final site build revision | **PENDING** |
| Complete hosted CI on that final revision | **PENDING** |
| Public deployment and exact served-byte readback | **PENDING** |
| Authorized/private runtime and Lab readback | **PENDING**; this localization work establishes no private execution |

The final source revision is recorded by [publication-manifest.json](../publication-manifest.json)
and the separately pinned [roadmap-manifest.json](../roadmap-manifest.json).
The final source build retains 31 works, 62 renditions and 322 HTML routes.
The release owner must replace the remaining pending entries with actual
immutable revisions and run/readback links. Local compilation and source
acceptance are separate from deployment, corpus admission and operational use.

## Coverage

All **322 baseline HTML routes are preserved**, and the checked local build
contains the same 322 routes. Route identity is compared with the baseline;
an equal total with a missing route and an unrelated replacement is refused.

| Surface | Checked coverage | Interpretation |
| --- | ---: | --- |
| Manuscript readers | 93 pages | 31 works in each of three languages |
| Body renditions | 62 target-language bodies | Eight historical reviewed files unchanged; 54 visible unreviewed bodies |
| Journal | 18 pages | Six dated issues in three languages |
| Programme | 3 pages | One complete page per language |
| Retained article excerpts | 6 pages | Two existing English records with Russian and Chinese derivatives |
| Roadmap | 3 pages, 75 cards, 453 fields | Complete per-language cards and fields; source graph and planned status preserved |

The card/field counts describe content within the roadmap pages. The complete
route inventory also includes section indexes, search/availability/about pages,
Lab routes and compatibility entries.

Shared UI coverage includes navigation, menus, cards, metadata, filters, reader
controls and notices, source/citation labels, search feedback, footer and legal
labels, accessible names, language links and public Lab state text. Local search
includes the six dated journal issues and localized catalogue metadata.

## Baseline findings and repairs

### Complete text and honest review state

The earlier site had English catalogue titles/summaries and incomplete visible
body coverage in the target languages. The previous README also described 30
English-only manuscripts and English task prose on all roadmap routes.

All 31 pinned works now have source-bound localized titles, summaries and body
renditions. The body compiler preserves the existing version-2 rendition
contract; [catalogue localization](catalogue-localization.md) is a separate
closed source binding. Its metadata cannot claim independent review.

The eight historical reviewed body files and their review scope are preserved.
The other 54 renditions are explicitly visible as unreviewed. A draft heading
suffix is allowed only for the declared draft state; it is not permission to
append arbitrary status claims. A page count, a file's existence or an English
fallback cannot substitute for a visible translated body.

The two existing site-owned article records retain their original English
content and links. Their translated titles, descriptions, status paragraphs and
abstracts are complete derivatives of the pinned retained excerpts. The reader
notice states that semantic review has not yet been performed. In particular,
the Russian v1 excerpt is a translation of the retained English text, not a
recovered frozen Russian original.

### Navigation, anchors and document metadata

Language changes previously retained fragments that did not identify headings
in the destination journal/programme language. Percent-encoded Russian/Chinese
fragments also needed decoding. Single-page route changes could leave canonical,
alternate-language and structured head metadata from the previous document.

Route-changing links now load the destination document; query/filter changes
within a route remain local. Journal/programme language links use heading
correspondence only after verifying their heading structure. Rendition readers
use their explicit source/rendition section mapping and title aliases. Malformed
fragments and incompatible structures do not invent a correspondence. Lab
language links retain the Lab route and its allowed public run/node parameters.

### Journal, programme, roadmap and ordinary UI

Navigation, cards, reader controls, search feedback, accessible labels, about and
footer text, public Lab/unavailable text and the retained short project note
are localized. The journal's Russian terminology was corrected from authorship
to attribution where the source discusses attribution, and from a generic
admission phrase to native admission; its corresponding digest was updated.
Published issue facts, dates, counts and limitations remain historical.

The roadmap uses complete Russian and Chinese overviews plus structured task
translations. Titles, descriptions, priority labels and source-file role labels
are localized. The dependency graph, IDs, owners, planned status and execution
boundaries come from the source structure. A visible notice identifies the
translation as an unreviewed, pinned snapshot. Dated source observations do not
become current Muneral execution evidence.

Date comparison recognizes equivalent English, Russian and Chinese calendar
expressions while retaining their day, month, optional year and multiplicity.
It keeps non-date numbers exact and rejects invalid dates and partial month-name
matches. Natural Chinese month notation is preserved.

### Formatting repair without content change

Source PR #122's pre-format snapshot produced 52 Markdown lint findings in 48
unreviewed translation files: 48 MD022 findings and four MD012 findings. Pinned
`markdownlint-cli2@0.24.0` corrected only blank lines in those 48 bodies. It then
reported zero issues across all 54 unreviewed rendition files.

For every changed body, the complete Pandoc 3.1.3 AST before and after was equal,
including metadata, title, mathematical content, code and links. All nonblank
source lines and raw fenced/indented code blocks remained byte-identical. The
eight historical reviewed bodies, six other unreviewed bodies and sidecar files
were unchanged by that formatting pass. The release owner then committed the
corrected bodies at `101431f2cf0b141d317445fabd6b6122f9fe1dba` and repinned the
48 changed rendition objects in the source integration. The other 14 rendition
objects remained unchanged. The final source pin is recorded above.

## Controls and observed local results

The scope of a check is recorded separately from a translated document's
semantic fidelity. These are local author/controller-side observations, not
independent collective or external acceptance. The local controls below were
observed during integration; the complete exact-final-pin workflow and its
immutable run receipt remain pending.

| Check | Observed local result | Scope |
| --- | --- | --- |
| `node scripts/test_ui_localization.js` | Complete 31-work catalogue: 487 cases PASS; earlier baseline: 325 cases PASS | Compiled UI, language navigation, anchors, labels and state handling; the count grows with the reader inventory |
| `python3 -B scripts/test_catalogue_localization.py` | 13 methods PASS | Metadata and retained-excerpt bindings, complete inventories, harmless changes and targeted refusals |
| `python3 -B scripts/test_localization.py` | 20 methods PASS | Source → compiled record → actual HTML coverage, language/state, route identity and field-omission controls |
| `python3 -B scripts/test_roadmap_localization.py` | 16 methods PASS | Real temporary Git histories, historical/current bindings, before/after graph preservation, targeted refusals and calendar controls |
| `scripts/check_localization.py` on the final source build | PASS: 322 routes, 93 readers, 18 journal, three programme, six excerpt pages, 75 roadmap cards and 453 fields | Actual local source/compiled/HTML comparison; the pre-format build had the same coverage |
| Formatting-only rendition comparison | 48/48 complete AST comparisons PASS; 54-file lint PASS | Empty-line repair with exact content/code preservation |

The final local run retained logs for the 20-method all-site suite and the
487-case UI suite. The final source build also passed the local publication,
page, paper, link, hygiene, localization, roadmap and programme checks. The
hosted workflow will provide its own immutable execution receipt. The complete
publication workflow remains pending on the final pinned revision; selected
local results do not establish a successful complete CI run.

Targeted adverse controls cover stale or unrelated source revisions, missing or
duplicate metadata/tasks, wrong body language, missing paragraphs, removed fields,
hidden translations, forged review/status claims, wrong locale head metadata,
route replacement, changed source links/code/mathematics, and altered dates or
non-date numbers. Positive controls retain harmless metadata/prose changes,
correctly equivalent dates and unchanged source graph/status. Invalid inputs
are committed and their outer pin is refreshed where appropriate, so a dirty
checkout or stale outer digest cannot impersonate the intended semantic guard.

The reusable [publication workflow](../.github/workflows/check-publication.yml)
runs these controls alongside the existing build, rendition, programme, journal,
link, search, Lab, readback and security checks. Reproduction uses the exact
source checkouts and Pandoc 3.1.3 documented in the [README](../README.md).

## Limits and follow-up evidence

This is an audit of the rendered site and its pinned content. External GitHub
source links, historical originals and primary citations continue to identify
their original-language records; their destinations are not blindly translated
or rewritten. Literal technical identifiers and scientific notation retain their
meaning and provenance.

Structural parity, correct pins, finite negative controls and script detection
do not prove full semantic fidelity or natural-language quality. The 54 body
renditions, new catalogue metadata, roadmap translations and retained excerpt
translations have no new independent semantic acceptance. Human native-speaker
and external scientific review are not established by this work.

Final hosted CI, deployment, exact public served-byte readback and authorized
private/runtime readback remain **PENDING** in the release table above. Local
HTML checks do not establish behavior in every browser, viewport or CDN region.
The existing served-page check uses its explicit bare/query request shapes;
asset/browser checks, API-index identity, access control and native execution
have their own evidence boundaries. No source review, translated page or local
Lab fixture authorizes private data access, corpus admission or a native task.
