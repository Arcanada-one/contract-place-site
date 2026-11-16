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

Current issue metadata has an authored calendar date, not a publication time
or source-modification timestamp. RSS `pubDate` and Atom `published` normalize
that date to 00:00:00 UTC; this is a documented day-precision convention, not
evidence of a midnight deployment. Atom `updated` currently uses the same
authored-date fallback because the source has no distinct modification field.
It must not be interpreted as independently measured edit time. RSS
`lastBuildDate` and Atom feed `updated` use the greatest included entry date,
never the current build clock.

For an empty feed, the committed creation timestamp
`2026-11-16T08:30:59Z` supplies Atom's required feed `updated` and RSS
`lastBuildDate`. Rebuilding identical inputs produces identical feed bytes.

Corrections keep their canonical identity and become visible in the rendered
content at the next deployment. This first version does not promise that a
reader will mark an old corrected issue unread: that behavior requires a
source-owned update timestamp and reader support. Updating the source's
existing hash pins and rebuilding remains mandatory.

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

The existing exact-generated-output gate is unchanged. A read-only CI artifact
stores only `public/`, `src/content/catalog.json` and
`src/site/content-provenance.json`, named by the immutable build SHA and run
attempt, for one day. It helps commit the native build's exact output when the
contributor is using the GitHub connector. An artifact upload is not approval,
successful validation or deployment; a source-only candidate still fails the
normal gate until generated files are committed and the same checks pass.

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

