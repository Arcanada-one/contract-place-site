# Daily Journal RSS and Atom

The public daily Journal has separate RSS 2.0 and Atom 1.0 feeds for English,
Russian and Simplified Chinese:

| Language | RSS | Atom |
| --- | --- | --- |
| English | https://contract.place/en/journal/rss.xml | https://contract.place/en/journal/atom.xml |
| Русский | https://contract.place/ru/journal/rss.xml | https://contract.place/ru/journal/atom.xml |
| 简体中文 | https://contract.place/zh-Hans/journal/rss.xml | https://contract.place/zh-Hans/journal/atom.xml |

A reader can paste one address into a feed reader. Ordinary links on the
Journal index, daily issue pages and site footer expose both formats.
Prerendered home, Journal index and manifest-backed daily issue pages include
locale-specific RSS/Atom autodiscovery links. Noindex pages, aliases, 404s,
research readers and other sections do not receive feed alternate metadata.
Visible footer links remain ordinary navigation on those pages.
The existing client-side locale handling also updates discovery when a saved
language is selected on the root page. No account, JavaScript-only action,
third-party subscribe service or tracker is required for the feeds.

## Scope and source

The sole membership source is the existing published daily-issue manifest,
`src/content/journal/manifest.json`. The existing journal compiler verifies
the source files against each declared SHA-256 and their front matter before
the feed generator receives the compiled records.

The first implementation includes the 50 most recent declared daily issues,
ordered by authored date descending, then slug ascending. Each language uses
that same membership window. Empty feeds remain valid.

The two historical Arcanada source-review pages in `catalog.articles` are not
daily issues and do not have publication dates in the site source. They are
not silently given invented dates. The noindex `building-a-place` legacy note,
scientific manuscript catalogue, research drafts, roadmap, books, private
storage and Lab data are outside these daily-Journal feeds. A future feed for
another section needs that section's own actual publication membership and
date metadata.

Only the published article's existing localized title, excerpt and rendered
body are reused. The generator does not author or translate an article.
RSS has a summary in `description` and full article HTML in `content:encoded`;
Atom has a text summary and HTML content. The canonical article URL remains
available in both. Rendered HTML is parsed to make links and image URLs
absolute, retain text and MathML, and refuse active HTML or unsafe URL schemes.
This is feed serialization of the existing rendering, not another Markdown
compiler or a new publication authority.

## Identity, dates and corrections

Each entry's ID/GUID is its absolute, locale-specific canonical article URL.
Changing a title or correcting the article does not create a new ID. Feed IDs
and self links use the permanent locale/format address.

Issue metadata has an authored publication calendar `date`. RSS `pubDate` and
Atom `published` normalize it to 00:00:00 UTC; this is a documented day-precision
convention, not evidence of a midnight deployment. An optional manifest
`updated` records the editor-declared calendar date of a known correction.
It must be a real ISO `YYYY-MM-DD` date on or after `date`; null, malformed and
backward values are refused. The compiler propagates it only when provided.
Atom entry `updated` uses that explicit date at 00:00:00 UTC, otherwise the
publication-date fallback for historical records whose edit date is unknown.
Neither value is an independently measured edit timestamp. RSS `lastBuildDate`
and Atom feed `updated` use the greatest included entry update date, never the
current build clock. Sorting and the membership window remain based on the
original publication date.

For an empty feed, the committed creation timestamp
`2026-11-16T08:30:59Z` supplies Atom's required feed `updated` and RSS
`lastBuildDate`. Rebuilding identical inputs produces identical feed bytes.

Corrections keep their canonical identity and become visible in the rendered
content at the next deployment. Known dated corrections must declare `updated`;
unknown historical dates are not invented. The 16 November 2026 DORA correction
therefore retains publication date `2026-11-14` and declares update date
`2026-11-16`. Whether a reader marks a corrected issue unread still depends on
that reader. Updating the source's existing hash pins and rebuilding remains
mandatory.

## Build and checks

`node build.mjs` calls `src/journal_feeds.py` with the exact compiled
`journal_issues` records already used by the site, writes six XML files under
`public/<locale>/journal/`, and prerenders discovery links and visible links.
The full canonical compiler remains required when the knowledge source pin
changes. Feed generation requires only the Python standard library.

Run the existing full build and checks; the new focused check is:

```sh
python3 -B scripts/test_feeds.py
```

It is part of the normal publication CI's renderer lane. It parses XML and
checks locale identity, full text and summaries, absolute references, date
validation, stable IDs, XML escaping, malformed or active HTML refusal,
duplicate/missing records, deterministic order and truncation, empty output,
manifest membership and links in generated HTML.

The existing exact-generated-output gate is unchanged. During initial
connector-based implementation, a temporary read-only CI artifact supplied
the native build output. That collection step was removed after retrieval;
it is not an ongoing publication or storage dependency. Generated files must
be committed and the normal reproducibility checks must pass before release.

## Release verification

Follow the existing review and manual Deploy workflow. After deployment,
check all six ordinary feed URLs, not only query variants: HTTP 200 without an
HTML fallback or redirect, XML media type (application/rss+xml,
application/atom+xml or a generic XML type supported by the static host),
well-formed XML, expected canonical entry URLs and language, and equality
with committed feed bytes. Check RSS/Atom links on all three Journal indexes
and a daily issue, keyboard access, and narrow-screen wrapping in a browser.
The present served-page checker covers HTML only; its success alone does not
establish feed delivery or feed-reader interoperability.

