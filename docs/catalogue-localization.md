# Source-bound reader metadata and retained article excerpts

The manuscript catalogue remains the English source inventory. Localized titles
and summaries do not add works or certify their translations. Complete manuscript
renditions retain the existing closed version-2 sidecar and its independent
review states. The eight historical body-review records are not extended to
new metadata or new rendition bytes.

## Audited inventory, 15 November 2026

The pinned site catalogue retains 31 works and all 322 baseline HTML routes.
Its 93 manuscript reader pages comprise 31 English originals and 62 Russian or
Simplified Chinese renditions. Eight historical reviewed rendition files remain
byte-identical; the other 54 bodies are visible with an unreviewed notice. Each
of the 31 works also has source-bound title/summary metadata in both target
languages. Metadata review state remains separate even when the corresponding
body has a historical review.

The two retained article excerpts provide six localized pages. Their four derived
Russian/Chinese translations show a notice that they translate a pinned English
excerpt and have not received semantic review. Original publication-status prose
is preserved as translated historical content. External source links continue
to identify their original publications; their entire destinations are outside
the excerpt translation scope.

The [dated localization audit](localization-audit-2026-11-15.md) covers the other
rendered surfaces, exact source boundaries, local controls and the separately
pending hosted/deployment readbacks. A later 36-work `main` catalogue is a
different source snapshot and does not enlarge this pinned publication.

## Knowledge-repository metadata

The compiler optionally reads the fixed file `publication-localization.json`
from the exact knowledge checkout. No manuscript is authored in site data.
The closed schema is:

| Level | Fields |
| --- | --- |
| Root | `schema_version: 1`, `kind: arcanada-publication-localization`, `source`, `entries` |
| Source | `catalog`, `revision`, `sha256` |
| Each entry | `work`, `language`, `source_path`, `source_sha256`, `title`, `summary`, `status` |

`source.catalog` equals the publication manifest's catalogue path. Its revision
must be an ancestor of the publication commit; both historical and current
catalogue bytes must match its SHA-256. Each source path/digest must identify the
current canonical work. There must be exactly one entry for every catalogued work
in each of `ru` and `zh-Hans`. Unknown fields, duplicate JSON keys, missing or
duplicate entries, wrong pins and stale bytes refuse compilation. Titles and
summaries are plain single-line strings in the declared script. Schema 1 permits
only `status: unreviewed`; it contains no mechanism for claiming review.

The generated record's `localization` maps each locale to `title`, `summary` and
`status`. The source file identity and complete binding inventory are retained in
`content-provenance.json.localizations`. Absent metadata preserves the previous
compiler behavior. Present but invalid metadata is an error, not an English
fallback. Metadata authoring and review remain separate from the body's review.

## Existing site-owned article excerpts

The two existing article records retain their English originals and external
source links. `src/content/article-localizations.json` contains complete derived
translations of their currently retained titles, descriptions, publication-status
paragraphs and abstracts. It does not replace or claim to translate the complete
external articles. In particular, its Russian v1 excerpt is translated from the
retained English record; it is not a recovered canonical frozen Russian source.

The closed root is `{schema_version: 1, kind: arcanada-article-localizations,
articles: [...]}`. Each entry has `id`, `source_sha256` and `translations`;
translations contains exactly `ru` and `zh-Hans`, each with the four nonempty
strings `title`, `description`, `status` and `abstract`. Here `status` translates
the original publication-status prose, not a review enum. Status and abstract
may contain paragraph breaks; executable markup and other control characters
are refused. The title, description and abstract must match the target script.

The source digest covers the complete original article record after removing
only a generated `translations` member. Its preimage is UTF-8 JSON with sorted
keys, unescaped Unicode and separators `(',', ':')`. This makes repeated builds
stable while refusing any changed English source record. Every original article
must appear exactly once. Generated `article.translations` carries the strings;
`content-provenance.json.articles_localizations` retains the source-file digest
and each original-record digest. With no source file, cached generated
translations are discarded rather than reused without a binding.

All four excerpt translations are unreviewed. Dates, numbers, limitations,
attribution and reported failures remain historical statements from the retained
source. Their translation is not a new empirical result, external review,
runtime admission or confirmation of present deployment.

## Verification

`python3 -B scripts/test_catalogue_localization.py` checks the complete positive
inventory, a harmless metadata change, repeated compilation and targeted refusals
for stale sources, unrelated pins with identical bytes, malformed inventories,
unsafe or wrong-language text, and fabricated metadata-review labels. The
synthetic tests validate compiler behavior, not semantic translation fidelity.
The ordinary full build still requires exact source commits, Pandoc 3.1.3 and the
existing publication, rendition, link and served-page checks.


## Natural-language prose inside formulas

The source repository owns `publication-formula-localizations.json`, a separate
closed schema for visible MathML prose. It binds each translated `mtext` to the
complete canonical file, an ancestor source revision, the exact Pandoc Math
position/type/TeX digest and the original mtext position and text. Both Russian
and Simplified Chinese entries are required. The descriptor itself must match
the pinned committed bytes; missing, duplicated, stale or unexpected bindings
are refused. A localized body with nonempty formula prose cannot silently
omit its descriptor.

`scripts/formula_localization.py` applies this layer after the ordinary exact
source/rendition Math comparison. Only the declared text-node contents may
change. TeX annotations, mathematical symbols, operators, indices, order, display
mode and all attributes remain canonical. Formula identifiers are not translated
by this mechanism. Formula localization provenance has its own unreviewed scope
and cannot promote the body or the canonical work to a reviewed state.

`scripts/test_formula_localization.py` exercises real temporary source histories,
valid bindings and targeted refusals. The final all-site check compares the
source-derived expected MathML, compiled body and actual public reader. The
publication pin and roadmap pin remain independent.


## Translated explanations of historical reviews

`publication-review-localizations.json` belongs to the pinned knowledge source.
Its closed schema names an ancestor revision and the exact rendition-sidecar
SHA-256, then binds each work/locale to the canonical JSON digest of its original
review and three complete translated fields: independence basis, method and
limitations. Every active reviewed or partially reviewed record is covered.
The historical review object is retained; presentation text has its own
`review_state: unreviewed` and cannot alter identity, scope, evidence or verdict.

The reader shows the localized explanations and their explicit scope notice.
Exact English originals remain available in a closed, labelled disclosure.
The source-to-page audit checks visible text, language, original bytes and the
embedded review/presentation facts. Legacy renderer compatibility does not
satisfy complete localization: missing presentation text on an otherwise
reviewed reader is refused by the all-site audit, including when a new outer
source pin was supplied after deleting the descriptor.

The Python `test_review_localization.py` uses real source histories and targeted
adverse inputs. `test_review_localization.js` checks actual compiled overlays
when present, and explicitly reports synthetic fixtures otherwise.
