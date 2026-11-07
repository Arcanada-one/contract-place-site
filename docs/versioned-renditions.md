# Versioned language renditions: exact source and rendition pins (K8)

Status: engineering design and compiler implementation, no translation content. Muneral task `b2ffbd14-85c6-4ff7-a183-b7e411a6cdb2` (KC 1.1). Acceptance matrix: ML01–ML12 of `MULTILINGUAL-PUBLICATION-AND-SEMANTIC-PARITY.md` at `0a49f04719af3459f4691dffb9ab92101d3286e4`.

Ownership: KC-SWE owns source/variant storage and compiler integration (this document and its code). KC-Brain owns translations, terminology and semantic review. Nothing in this repository writes, machine-translates or reviews a manuscript.

## 1. Decision

**A linked, versioned sidecar, not a catalogue/provenance extension.**

| | Catalogue / provenance extension | Linked versioned sidecar (chosen) |
| --- | --- | --- |
| Closed schemas | `publication-catalog.json` gains per-document language arrays; every consumer of that catalogue sees a changed shape | `publication-catalog.json` gains one optional key naming a file; the document list is untouched |
| Review churn | Every new review fact changes the catalogue, which also drives indexing inventory | Review facts change only the sidecar |
| Default behaviour | A new array must be defaulted everywhere | Absent key means no renditions: the build is byte-identical to the build before this change |
| Fit with the spec | Spec §4: "propose an explicit versioned extension or linked sidecar"; §4 forbids ad hoc fields in book-package/2, KC2 and KCAO closed schemas | Separate, own closed schema, own version |
| Reuse of existing records | Would overload `language` (which today is validated to be `en`) | The `language: en` guard in `load_inputs` stays: a catalogued source document is English |

The English-only guard in `scripts/build_publication.py::load_inputs` is **kept**. A catalogued document is always the English source edition. A translation is not a catalogued document and has no route of its own as a work; it is a rendition of one.

## 2. Where the sidecar lives

In the **knowledge repository** (`Arcanada-one/knowledge-contract`), next to `publication-catalog.json`, because that repository is the source of truth for text. The rendition Markdown files live there too, so one publication commit pin covers the source, the sidecar and every rendition byte; the site stores no manuscript.

Proposed layout (a proposal for KC-Brain and the knowledge repository owners; this change writes nothing there):

```
publication-catalog.json            optional key: "renditions": "publication-renditions.json"
publication-renditions.json         the sidecar (schema below)
renditions/<language>/<work-slug>/<MAIN-FILENAME>.md      e.g. renditions/ru/revision-and-governance/PAPER.md
```

The site declares nothing about renditions in `publication-manifest.json`. The sidecar is found only through the pinned catalogue.

`--renditions-file PATH` exists on the compiler for **tests and fixtures only**. Its output is marked `renditions_source = fixture` (catalogue, provenance and `publication.json`), `scripts/check_publication.py` refuses such output (`RENDITION_FIXTURE_ONLY`), and the compiler refuses to combine it with a catalogue-declared sidecar. Production builds, CI and deploy validation read only the catalogue key.

## 3. Sidecar schema, version 1 (closed)

Unknown fields at any level are refused (`RENDITION_SIDECAR_SCHEMA`).

```json
{
  "schema_version": 1,
  "kind": "arcanada-publication-renditions",
  "edition": "1.1",
  "renditions": [
    {
      "work": "<catalogue slug>",
      "language": "ru | zh-Hans",
      "script": "Cyrl | Hans",
      "counts_as_independent_source": false,
      "source":    { "path": "<catalogue path>", "sha256": "<64 hex>", "revision": "<40 hex>", "language": "en" },
      "rendition": { "path": "renditions/<language>/<slug>/<FILE>.md", "sha256": "<64 hex>", "revision": "<40 hex>" },
      "review": {
        "status": "reviewed | unreviewed",
        "scope": "full | sections",
        "reviewed_sections": ["<source anchor>"],
        "method": "<text>", "limits": "<text>",
        "reviewers": [{ "kind": "agent | human", "ref": "<reference>" }],
        "evidence": ["<reference>"]
      },
      "sections": [{ "source": "<source anchor>", "rendition": "<rendition anchor>" }]
    }
  ]
}
```

What it pins, per work and language:

- **Source revision and hash**: `source.revision`, `source.sha256` (raw bytes, before any normalization).
- **Rendition revision and hash**: `rendition.revision`, `rendition.sha256` (raw bytes).
- **Translator/reviewer evidence reference**: `review.reviewers[]` (kind `agent` or `human`, never inferred), `review.evidence[]`, `review.method`, `review.limits` (for example "agent-only, non-blind").
- **Review scope and status**: `review.status`, `review.scope`, `review.reviewed_sections`.
- **Section mapping**: `sections[]`, an explicit source-anchor to rendition-anchor list. Anchors are never guessed from translated heading text.
- **Independence**: `counts_as_independent_source` must be `false`.

`reviewed_sections` is present exactly when `scope` is `sections`. Status `reviewed` requires non-empty `method`, `limits`, `reviewers` and `evidence`; status `unreviewed` must carry none of them (`RENDITION_REVIEW_UNEVIDENCED`). Reviewer kinds are recorded as given; the compiler cannot verify a human review and does not claim to.

### Pin model

The sidecar lives in the publication commit, so it cannot contain that commit's hash. A pin therefore names the commit that authored exact bytes and is verified, not trusted:

- `source.revision` and `rendition.revision` must be ancestors of (or equal to) the publication commit, and the blob of the pinned path at that revision must hash to the pinned `sha256` (`RENDITION_SOURCE_PIN`, `RENDITION_REVISION_PIN`).
- The rendition's revision must not predate the source revision it claims to render (`RENDITION_REVISION_PIN`, "mixed source/rendition pins").
- The rendition bytes in the publication commit must equal the pinned bytes (`RENDITION_DIGEST`).
- The source's current bytes at the publication commit are compared with the pinned source hash. A difference is **not** a build failure; it is the computed state `stale` (§4).

This is stricter than comparing a commit string for equality: a pin to an unrelated history with identical bytes is refused.

## 4. States and what the reader sees

The state is computed by the compiler, never declared in the sidecar.

| State | Condition | Shown on `/ru/…` and `/zh-Hans/…` |
| --- | --- | --- |
| `reviewed` | pins match, `review.status = reviewed`, `scope = full` | complete prerendered rendition, label "Reviewed translation" |
| `partially-reviewed` | `reviewed`, `scope = sections` | complete prerendered rendition, label "Partially reviewed translation", reviewed sections listed |
| `unreviewed` | pins match, `review.status = unreviewed` | complete prerendered rendition, label "Unreviewed translation" |
| `stale` | pinned source hash ≠ current source hash | pinned **English source**, label "Translation out of date: the English source has changed." plus the explicit fallback sentence |
| `missing` | no rendition record for the work and language | pinned **English source**, label "No translation of this document is available." plus the explicit fallback sentence |

Every localized reading page of a work, once any sidecar exists, carries exactly one `<aside class="rendition-state">` with `data-state`, `data-language`, `data-body-language`, `data-independent-source="false"`, the source and rendition pins (path, short hashes, short revisions), the review method, reviewers, evidence and limits, and a link to the English source route. The English page carries none.

**Fallback to English is explicit, never silent.** A page that shows English text under a `/ru/` or `/zh-Hans/` URL states that in the interface language, links the pinned source, declares `lang="en"` on the body and `"inLanguage":"en"` in its JSON-LD, and is never counted as a completed translation. An unreviewed or stale rendition is never displayed with the "reviewed" label (`RENDITION_STATE_LABEL`). A stale rendition's text is not displayed at all.

Labels (interface text, drafts):

| State | en | ru | zh-Hans |
| --- | --- | --- | --- |
| reviewed | Reviewed translation | Рецензированный перевод | 已审校译文 |
| partially reviewed | Partially reviewed translation | Частично рецензированный перевод | 部分审校译文 |
| unreviewed | Unreviewed translation | Перевод без рецензирования | 未审校译文 |
| stale | Translation out of date: the English source has changed. | Перевод устарел: английский источник изменился. | 译文已过期：英文源文已更改。 |
| missing | No translation of this document is available. | Перевода этого документа нет. | 本文档暂无译文。 |
| fallback | The pinned English source text is shown instead. | Вместо него показан закреплённый английский исходный текст. | 此处改为显示固定版本的英文源文。 |

These RU and zh-Hans strings are **interface labels drafted by KC-SWE, not reviewed by KC-Brain**. The zh-Hans text carries the same caveat as the rest of the zh-Hans interface (no native editorial review). They are a labelled open point for KC-Brain wording review; they are not manuscript text. The published pages keep the existing notice about unreviewed Chinese interface text.

## 5. Language and metadata rules

- Interface locale (`<html lang>`, navigation) and document language are separate. `<html lang>` stays the interface locale; the reading body carries `lang` of the text actually shown.
- Sidecar `language` must be exactly `ru` or `zh-Hans` (the current locales). `zh`, `zh-Hant`, `ru-RU`, `en` and anything else are refused (`RENDITION_LANGUAGE`); another script is a separate scope decision. `script` must match (`Cyrl`, `Hans`).
- The rendition file's own front matter `language` must equal the sidecar language, and its text must be predominantly in the declared script, so an English or wrongly tagged body cannot be published under a Russian or Chinese label.
- JSON-LD: a displayed rendition gets `inLanguage` of its language, its own `name`, and `translationOfWork` pointing to the English work; `isBasedOn` remains the pinned English source. A fallback page keeps `inLanguage: "en"`.
- `hreflang`/canonical: unchanged by this implementation. The three locale URLs of a work continue to be alternates of one another with `x-default` English. A fallback page still lists them, which over-claims a language for English content; whether to `noindex` or drop alternates for fallback pages is an SEO decision that changes already indexed pages, so it is **not** taken here and is recorded as an open point.
- Publication output reports the facts: `publication.json` documents carry `renditions[language]` with state, source hash, current source hash, rendition path, hash and revision, review status and scope, and `counts_as_independent_source: false`; `src/site/content-provenance.json` carries `renditions` entries with the sidecar hash and `renditions_source`.

## 6. Structural preservation checked by the compiler

For every non-stale rendition, before anything is written (the checks are structural; semantics belong to KC-Brain):

- **Sections**: every source `h2`/`h3` anchor appears exactly once in the mapping (`RENDITION_SECTION_MISSING`); the mapping names no vanished source section and repeats no anchor (`RENDITION_SECTION_DRIFT`); every mapped rendition anchor exists (`RENDITION_SECTION_UNRESOLVED`); the rendition has no unmapped extra sections, keeps source order and heading levels (`RENDITION_SECTION_DRIFT`); a section with text in the source has text in the rendition (`RENDITION_SECTION_MISSING`).
- **Structure**: per section, the same number of tables, lists, quotations, code blocks and rules (`RENDITION_STRUCTURE_MISMATCH`).
- **Formulas**: the exact LaTeX of every formula and its inline/display mode, in order (`RENDITION_FORMULA_CHANGED`).
- **Code and identifiers**: exact text of every code block and inline code span, in order (`RENDITION_CODE_CHANGED`).
- **References**: the multiset of link, image and citation targets (relative links resolved against each file's own directory; same-document fragments mapped through the section mapping) and the footnote count (`RENDITION_REFERENCE_DROPPED`, `RENDITION_REFERENCE_CHANGED`). A same-document link to a guessed fragment is refused.
- **Rendering**: the rendition is rendered by the same Pandoc/MathML pipeline as the source with the same raw-HTML and link checks, and the formula count of the HTML is verified.
- **Anchors**: each mapped rendition heading is emitted with `data-source-section="<source anchor>"`; when the ids differ, an alias anchor with the source id is emitted before it, so a source fragment still resolves on the rendition page.

None of this proves that a translation preserves meaning. `MayExecute implies CurrentPermission` rewritten as an equivalence passes every structural check above. Semantic fidelity, terminology and the necessity/sufficiency distinction are KC-Brain review (ML03, ML05).

## 7. Output checks

`scripts/publication_checks.py::check_renditions`, run by `scripts/check_publication.py`, checks the built pages against the compiled records: one correct state label per localized page, the compiled state, body and JSON-LD language, complete prerendered text and formula count for displayed renditions, the explicit fallback sentence and English source for fallbacks, section bindings, no rendition markup on English pages or when no renditions exist, and refusal of fixture-built output. `check_papers.py` and `check_publication.py` accept a displayed rendition body only where the compiled state allows it.

## 8. Search across languages (design, not implemented)

The search API and its index are a separate snapshot and are not changed here. Rules for the follow-up with Agent-SWE:

- A record is identified by `(work, language, rendition revision, source revision)`, never by language alone.
- A result in `ru` or `zh-Hans` cites both the rendition (path, hash, revision, state) and the English source it renders; the compiled `renditions` record already carries both.
- Translations are not independent sources: counting `ru`, `zh-Hans` and `en` hits of one work as three supports of a claim is wrong (`counts_as_independent_source` is always `false`).
- `stale`, `missing` and `unreviewed` renditions must not be indexed as current reviewed text.
- Locale selection changes presentation only. It never changes the subject, authorization view, filters or cache key beyond the language/revision components above.
- Cyrillic and Chinese tokenization, truncation, byte limits and font coverage need their own tests: NOT_MEASURED here.

## 9. Translations are not independent evidence

A rendition is a rendering of one exact source edition. The sidecar field `counts_as_independent_source` is required and must be `false`; the compiler, `build.mjs` and the published manifest all refuse otherwise. Source and rendition keep separate hashes; no claim of byte identity across languages is made.

## 10. ML01–ML12

| Case | Status | Evidence in this change |
| --- | --- | --- |
| ML01 | Engineering part implemented; semantic part KC-Brain-owned | Complete prerendered synthetic rendition (compile + page tests). Missing section, summary-only and empty-section controls. A real approved source with a real rendition: NOT_MEASURED |
| ML02 | Implemented | Separate source and rendition hashes and revisions; a changed source makes the state `stale` and removes the reviewed label |
| ML03 | KC-Brain-owned (semantic) | Not detectable by structure; the limit is stated in §6. Nothing is claimed |
| ML04 | Implemented for formulas, code, identifiers, reference targets | Controls change a formula (sign, relation, display mode), drop a formula, change a code identifier, retarget and drop references. Units, signs in prose and numerals outside formulas are not checked |
| ML05 | Implemented for review-state promotion; semantic part KC-Brain-owned | An unreviewed rendition cannot carry reviewed status or label; translating NOT_MEASURED as passed is a semantic review matter |
| ML06 | Not applicable to this change | No execution, tool, scope or digest handling is touched. NOT_MEASURED |
| ML07 | Implemented | Stale detection, visible stale label, historical text withheld; a later source edit cannot keep an older translation current |
| ML08 | Partly implemented | Provenance and section mapping in the compiled records and the page; cross-language retrieval is design only (§8): NOT_MEASURED |
| ML09 | Not applicable here | No access control exists on this public static site; NOT_MEASURED for the API and cache layers owned by Agent-SWE |
| ML10 | Out of compiler scope | Original quotations and labelled translations are authored content; the compiler preserves quotation text only through the exact link, code and structure checks. KC-Brain-owned |
| ML11 | Implemented | Reproducible compile; exact pins; silent fallback, mixed pins and wrong language metadata refused; complete text in prerendered HTML |
| ML12 | NOT_MEASURED | Needs a deployed build and retained desktop/mobile browser evidence per locale. CI is not that evidence |

## 11. Limits

- No real translation exists; every rendition in the tests is synthetic placeholder data. Nothing was deployed, indexed or admitted.
- The client script `renditions.js` re-applies the state on client-side navigation through a `MutationObserver`; it was exercised through the build-time prerender (same script, a string-based DOM stub), not in a real browser. Desktop and mobile browser inspection is NOT_MEASURED.
- The browser-side replacement matches the page markup by regular expression and fails loudly (`RENDITION_SILENT_FALLBACK`) if the reading-page structure changes, rather than leaving an unlabelled English body.
- Cross-document links inside a rendition resolve to the English route of the target work, even when that work has its own rendition.
- Sidecar and rendition-file additions to the knowledge repository, and the catalogue key that activates them, are a later step reviewed by KC-Brain. Until then the site builds with no renditions.
