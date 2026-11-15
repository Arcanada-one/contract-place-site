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
