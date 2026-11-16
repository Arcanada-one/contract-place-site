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
| Accepted main localization | Source PR #122 merged at `45730e337eaaaaac76e824118b2f34b1c6fa6008`; site PR #55 merged at `7e6b21ff48d3a31e0c68020c2cb7e7138c0d226b` |
| Presentation completeness follow-up | [knowledge-contract PR #123](https://github.com/Arcanada-one/knowledge-contract/pull/123); final revision recorded in the manifest |
| Pre-format source integration snapshot | `86c5654c3e3811891793655da345f5084b4eaf7f`; superseded for final publication by the formatting follow-up |
| Formatting body commit | `101431f2cf0b141d317445fabd6b6122f9fe1dba` |
| Publication source pin including formula and review prose | [`39e4054830d9cb05bc0432d25f7320cb8a97f054`](https://github.com/Arcanada-one/knowledge-contract/tree/39e4054830d9cb05bc0432d25f7320cb8a97f054) |
| Independent unchanged roadmap pin | `55e279c43dc9bcf8732467a32661c2ac4b7cf920` |
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
| `node scripts/test_ui_localization.js` | Complete 31-work catalogue: 491 cases PASS; earlier baseline: 325 cases PASS | Compiled UI, language navigation, anchors, labels and state handling; the count grows with the reader inventory |
| `python3 -B scripts/test_catalogue_localization.py` | 13 methods PASS | Metadata and retained-excerpt bindings, complete inventories, harmless changes and targeted refusals |
| `python3 -B scripts/test_localization.py` | 20 methods PASS | Source → compiled record → actual HTML coverage, language/state, route identity and field-omission controls |
| `python3 -B scripts/test_roadmap_localization.py` | 16 methods PASS | Real temporary Git histories, historical/current bindings, before/after graph preservation, targeted refusals and calendar controls |
| `scripts/check_localization.py` on the final source build | PASS: 322 routes, 93 readers, 18 journal, three programme, six excerpt pages, 75 roadmap cards and 453 fields | Actual local source/compiled/HTML comparison; the pre-format build had the same coverage |
| Formatting-only rendition comparison | 48/48 complete AST comparisons PASS; 54-file lint PASS | Empty-line repair with exact content/code preservation |

The final local run retained logs for the 20-method all-site suite and the
491-case UI suite. The final source build also passed the local publication,
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


## Final service-page repair and preserved hosted failure

The first site CI run, [43742952907](https://github.com/Arcanada-one/contract-place-site/actions/runs/43742952907), failed the attribution preflight after compilation and renderer/localization controls passed. The changed Russian journal issue still had its old blob in `attribution-scope.json`. Review against the exact English issue confirmed only the three terminology repairs: attribution, nested attribution and native admission. The scope now explicitly names `d22e3e5de51e7300701c859da7d1da618ae9f264`; checker and study pins, authorship, numbers and refusal logic remain unchanged. The corrected preflight and all six wrapper tests pass locally. The old failure is not a successful run.

A final audit of the other page types checked all 262 interface keys and actual RU/zh home, wiki/docs, about, books, references, repository, search and public Lab pages. It found two additional defects: the search's missing-title fallback was English in every locale, and the shared static 404 offered only English before JavaScript. The search now uses the selected language for its own fallback while preserving source titles, quotations and technical paths. The single shared 404 now contains three visible, language-labelled error sections and home links, one h1 and the same noindex policy; JavaScript still selects the requested locale for an unknown path.

The rebuilt search passes 24 tests. The renderer/prerender suite passes 491 controls, including the shared error document and unknown routes in all three languages. Exact prior search and prerender modules each fail the new corresponding regression control in disposable copies. Thirty synthetic API error/empty/timeout cases also had localized feedback; this is not a live API-service claim. Official external titles, identifiers and 24 explicitly English historical review-provenance blocks remain source quotations.

The initial 487-control result and site head `2ede2317909e82d6d6f88657c638d2ae83e44827` remain historical preparation evidence. [Site PR #55](https://github.com/Arcanada-one/contract-place-site/pull/55) records the replacement head, its CI and any subsequent delivery. These local results do not establish deployment or served/browser verification.


## Formula prose and real-browser follow-up

The corrected earlier site head `fcc79d06c0cceffaa1f9574a5fc402cb22ca7133`
passed all four hosted jobs in [CI 43745173854](https://github.com/Arcanada-one/contract-place-site/actions/runs/43745173854).
Agent-Brain closed the stale Russian attribution-pin hold on that exact head;
that bounded check did not accept the full source corpus or release. A later
rendered-page audit found a gap the green suite had not covered: eight ordinary
English MathML `mtext` labels in each target language, across four unreviewed
papers. The earlier successful run does not verify the subsequent repair.

The source-owned `publication-formula-localizations.json` registers these eight
locations with complete manuscript digests, one-based Pandoc Math positions,
display mode, exact TeX hashes, mtext positions and source wording, including
boundary spaces. It supplies 16 Russian/Chinese translations. The source and
rendition Math AST comparison still runs first. The presentation layer permits
only the registered visible prose replacements; every other MathML node,
attribute, symbol, order, display mode and canonical TeX annotation is retained.
All eight historical reviewed rendition files remain byte-identical, and the
new presentation translations remain explicitly unreviewed.

The longest label retains the negation of “both answer sets are the same
singleton”. It does not claim that both sets must be non-singletons. Positive
cases include two different singletons and equal sets with multiple elements;
removing the negation or requiring two non-singletons gives different results.
These finite controls establish the bounded predicate distinction, not general
semantic translation quality.

A local real-browser comparison uses the unchanged generated pages in three
390 × 844 CSS iframe viewports. With the observed scrollbar, each document's
content viewport is 375 pixels wide; the EN/RU/zh reader pages have no root
horizontal overflow. This is a browser layout check, not mobile-device hardware
emulation or a public served-byte observation. It also exposed an obsolete
reader notice claiming language selection changed only the interface. The
notice now describes available full-body renditions and their review states.
The release table remains pending until the corrected exact revision is tested,
reviewed and delivered.


## Preserved review records and localized presentation

An additional visible-text pass found 24 ordinary English prose fields in the
eight historical reviewed rendition records: reviewer independence basis,
method and limitations. Localized field labels and an HTML `lang="en"`
attribute did not provide a translated explanation. This is a separate coverage
gap from the manuscripts themselves. The follow-up supplies complete localized
presentation text, keeps the exact original review prose in clearly labelled
English disclosure blocks, and labels the translation of the historical record
as unreviewed. It does not change the original verdict, controller identity,
reviewed blobs, date, evidence path, scope or manuscript-review state.

Agent-Brain independently accepted the earlier source/site integration in
[comment 6899417294](https://github.com/Arcanada-one/knowledge-contract/pull/122#issuecomment-6899417294)
and [comment 6899417529](https://github.com/Arcanada-one/contract-place-site/pull/55#issuecomment-6899417529).
Those accepted revisions merged on 15 November at 18:46:55 and 18:47:10 UTC.
The follow-up requires its own head, execution and review evidence.

The same review identified a stale AGENTS summary saying all bodies remained
English unless reviewed. Its linked, already implemented rendition contract
has long allowed visibly unreviewed reading while excluding it from translation
indexing. The summary now faithfully describes those existing states. No new
admission, indexing or release permission is introduced by that clarification.


### Complete follow-up source and local execution

The final source presentation snapshot is `39e4054830d9cb05bc0432d25f7320cb8a97f054`,
retained by source PR #123 integration head `16fba6ed774fe06af342379c194dce36f5bd171f`.
Its exact hosted CI runs 43749870207 and 43749870000 passed. Formula descriptor
blob `5f0dc741b7ba80d88c560e24d338564b6a68b5c8` and review-prose descriptor blob
`e05becc7fffd42ebafec692e24492eb75e25bc54` were read back in both Git trees.
The source additions do not change the eight historical review objects or any
canonical manuscript/body rendition.

The complete local build retains 322 HTML files, 93 reader pages, 62 renditions
and the separate roadmap pin. Fifteen local publication, hygiene, page, paper,
link, roadmap, localization, renderer and regression commands passed. The new
formula suite has 18 methods; the review-binding suite has 14. The complete-page
audit additionally refuses removing the review descriptor in a new committed
source with an updated outer pin: a compatible legacy renderer may still read
such an old-style record, but it cannot pass the complete-localization check.
The original review JSON and the separate unreviewed presentation in embedded
machine-readable facts must also match their bound source.

The review renderer suite checks 23 cases, including all eight records and 24
visible translated fields, verbatim originals, a closed labelled disclosure,
unchanged status/scope and ten malformed presentations. A prior renderer fails
the new disclosure regression. The full-width and narrow browser previews use
actual generated HTML. The long formula has bounded horizontal scrolling while
the document itself retains its viewport width; this is local browser evidence.
The final site hosted run, non-author verdict and public served revision are
recorded separately in the follow-up PR; they are not inferred from these tests.
