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

Layout (the layout that the knowledge repository's translation drafts already use; this change writes nothing there):

```
publication-catalog.json            optional key: "renditions": "publication-renditions.json"
publication-renditions.json         the sidecar (schema below), next to the catalogue
translations/<language>/<source-relative path>
                                    e.g. translations/ru/papers/revision-and-governance/PAPER.md
                                         translations/ru/engineering/specifications/book-package/SPECIFICATION.md
```

**The rendition path must equal `translations/<language>/` followed by the source path, exactly.** Any other path (the earlier `renditions/<language>/<slug>/<FILE>`, another language directory, a renamed file, an extra directory) is refused with `RENDITION_LAYOUT` when the sidecar is validated, before any file is read. A source document cannot itself live under `translations/`. The sidecar keeps its name and location: the K8 source decision (`K8-RENDITION-SOURCE-DECISION.md`) leaves "the particular path and versioned wire schema" to KC-SWE's reviewed choice and forbids only ad hoc fields in book-package/2, KC2 and KCAO, which this sidecar does not touch.

The site declares nothing about renditions in `publication-manifest.json`. The sidecar is found only through the pinned catalogue.

`--renditions-file PATH` exists on the compiler for **tests and fixtures only**. Its output is marked `renditions_source = fixture` (catalogue, provenance and `publication.json`), `scripts/check_publication.py` refuses such output (`RENDITION_FIXTURE_ONLY`), and the compiler refuses to combine it with a catalogue-declared sidecar. Production builds, CI and deploy validation read only the catalogue key.

## 3. Sidecar schema, version 2 (closed)

Unknown fields at any level are refused (`RENDITION_SIDECAR_SCHEMA`). Schema version 1 is refused. Relation of each entry to its English work is the provenance relation **`rendition_of`** (KC-Brain): one translated Markdown revision in a target locale → one canonical English source revision of one logical work. It is not `same_as`, semantic equivalence, or an independent source.

Closed field names (for Agent-Brain agreement):

| Level | Fields |
| --- | --- |
| top | `schema_version`, `kind`, `edition`, `renditions` |
| entry | `work`, `language`, `script`, `counts_as_independent_source`, `source`, `rendition`, `sections`, optional `author`, optional `review` |
| `author` | `identity` |
| `source` | `path`, `sha256`, `revision`, `language` (always `en`) |
| `rendition` | `path`, `sha256`, `revision` |
| `review` (closed; absent ⇒ author-draft unreviewed) | `reviewer`, `method`, `reviewed`, `scope`, `corrections`, `reviewed_at`, `limitations`, `evidence` |
| `review.reviewer` | `identity`, `kind` (`agent` only until a human label exists), `independent_of_author`, `independence_basis` |
| `review.reviewed` | `source_blob`, `rendition_blob` (full 40-hex git blob ids) |
| `review.scope` | `coverage` (`full` \| `partial`), `sections`, `claims`, `proofs` |
| `review.corrections[]` | `section`, `description` |
| `review.evidence` | `path` (repo path), `blob` (40-hex); free text such as `"x"` is refused |
| `sections[]` | `source`, `rendition` |
| digest label | `sha256` on pins; blob ids on reviewed/evidence |

```json
{
  "schema_version": 2,
  "kind": "arcanada-publication-renditions",
  "edition": "1.1",
  "renditions": [
    {
      "work": "<catalogue slug>",
      "language": "ru | zh-Hans",
      "script": "Cyrl | Hans",
      "counts_as_independent_source": false,
      "author": { "identity": "<translator identity>" },
      "source":    { "path": "<catalogue path>", "sha256": "<64 hex>", "revision": "<40 hex>", "language": "en" },
      "rendition": { "path": "translations/<language>/<source path>", "sha256": "<64 hex>", "revision": "<40 hex>" },
      "review": {
        "reviewer": { "identity": "<id>", "kind": "agent", "independent_of_author": true, "independence_basis": "<text>" },
        "method": "<text>",
        "reviewed": { "source_blob": "<40 hex>", "rendition_blob": "<40 hex>" },
        "scope": { "coverage": "full | partial", "sections": ["<source anchor>"], "claims": [], "proofs": [] },
        "corrections": [],
        "reviewed_at": "2026-01-31T12:00:00Z",
        "limitations": "<text>",
        "evidence": { "path": "reviews/<file>.md", "blob": "<40 hex>" }
      },
      "sections": [{ "source": "<source anchor>", "rendition": "<rendition anchor>" }]
    }
  ]
}
```

A review object is required for any reviewed or partially-reviewed state. Binding (C1–C3): the compiler compares reviewed blobs to the pinned source and rendition blobs and checks the evidence path+blob in the publication commit. A mismatch yields `RENDITION_REVIEW_UNBOUND` and the page renders **unreviewed** (build continues). `independent_of_author=false` or author identity equal to reviewer yields `RENDITION_REVIEW_NOT_INDEPENDENT` and the same unreviewed rendering. A stale source never reports reviewed on the page or in `publication.json` (C1). Partial scope (for example two sections of a longer paper) never yields a whole-paper `reviewed` label.

### Pin model

The sidecar lives in the publication commit, so it cannot contain that commit's hash. A pin therefore names the commit that authored exact bytes and is verified, not trusted:

- `source.revision` and `rendition.revision` must be ancestors of (or equal to) the publication commit, and the blob of the pinned path at that revision must hash to the pinned `sha256` (`RENDITION_SOURCE_PIN`, `RENDITION_REVISION_PIN`).
- The rendition's revision must not predate the source revision it claims to render (`RENDITION_REVISION_PIN`, "mixed source/rendition pins").
- The rendition bytes in the publication commit must equal the pinned bytes (`RENDITION_DIGEST`).
- The source's current bytes at the publication commit are compared with the pinned source hash. A difference is **not** a build failure; it is the computed state `stale` (§4).

This is stricter than comparing a commit string for equality: a pin to an unrelated history with identical bytes is refused. Tests cover both pins: a `source.revision` and a `rendition.revision` that hold exactly the pinned bytes on a commit that is not an ancestor of the publication commit are refused (`RENDITION_SOURCE_PIN`, `RENDITION_REVISION_PIN`, "not an ancestor").

**Why the in-repo sidecar cannot name its own commit.** A Git commit hash is a hash of the tree, and the tree contains the sidecar. A sidecar that carried the hash of the commit that contains it would have to contain a value that depends on its own bytes: there is no such fixed point to compute, and any later edit of the sidecar changes the commit. The sidecar therefore names only commits that already exist when it is written (the commit that authored the source bytes and the commit that authored the rendition bytes). The commit that contains the sidecar is named from outside, by `publication-manifest.json` in this repository, and that is the "manifest commit" against which every pin is checked for ancestry. A pin that is not an ancestor of the manifest commit, or whose blob at the pinned path differs from the pinned SHA-256, is refused.

### Links inside a rendition (fail closed; R-K8-LINK-BASE1)

Two coordinate systems stay explicit (Agent-Brain 6717017943):

1. **Literal Markdown / GitHub navigation.** Relative hrefs are resolved from the **rendition file's own directory** (`translations/<lang>/…`), so drafts navigate correctly on GitHub (for example PR76 RU/zh-Hans `../../../../../schemas/book-package.schema.json` from `translations/<lang>/engineering/specifications/book-package/`).
2. **Publication canonical identity.** After a safe resolve (no traversal, including encoded traversal), the target maps to **one** logical identity: a canonical-tree path (invariant artifact or catalogue document), or a **registered same-language** peer `translations/<lang>/<path>` mapped to the English work `<path>`.

The **same** mapping is used in `classify_link`, in `check_parity` / `facts` / `normalize_target` (the rendition side uses the rendition path as base, never the source base), and in `link_hooks` rendering. Parity compares the multiset of `(Link|Image kind, canonical target, mapped section/fragment)` against the English source. Only then does rendering choose the same-locale route if a rendition exists, otherwise a clearly labelled English fallback.

| Class | What it is | Result |
| --- | --- | --- |
| invariant | any non-catalogue file or directory that exists at the pinned commit | pinned GitHub blob URL or copied asset; identical to the English page's target |
| document | a catalogue document at its canonical English path | same-language route; state on the link; explicit English fallback when the target is stale/missing |
| peer | a pinned same-language `translations/<lang>/<source path>` of a catalogue document | canonical identity = that source path; then same route rule as `document` |
| fragment | `#anchor` in the same document | mapped section or shared identifier only |
| external | `http(s):` or `mailto:` outside the repository | unchanged |

Refusals (existing `RENDITION_LINK_*` codes, never weakened): cross-locale peers and other unregistered `translations/` targets (`RENDITION_LINK_TRANSLATION`); unpinned same-language peers (`RENDITION_LINK_UNPINNED`); nonexistent targets (`RENDITION_LINK_DANGLING`); traversal including encoded traversal (`RENDITION_LINK_ESCAPES`); unsafe schemes (`RENDITION_LINK_SCHEME`); changed citation/fragment identity (`RENDITION_REFERENCE_*` / `RENDITION_LINK_FRAGMENT`). Links are checked after section/structure checks and before reference comparison.

**Decision for document links: same-language route, not the English route.** Linking to the same-language route keeps the reader in the chosen interface language; the target page already states its rendition state or its explicit fallback (§4).

## 4. States and what the reader sees

The state is computed by the compiler, never declared in the sidecar.

| State | Condition | Shown on `/ru/…` and `/zh-Hans/…` |
| --- | --- | --- |
| `reviewed` | current source pin; closed review bound to both blobs; `scope.coverage = full`; independent reviewer | complete prerendered rendition; internal-agent-review label |
| `partially-reviewed` | same binding; `scope.coverage = partial` | complete prerendered rendition; partial internal-agent-review label; scope listed |
| `unreviewed` | no review, or review unbound / not independent | complete prerendered rendition; unreviewed label (and typed issue when a claim failed to bind) |
| `stale` | pinned source hash ≠ current source hash | pinned **English source**; stale label + fallback sentence (never "reviewed") |
| `missing` | no rendition record for the work and language | pinned **English source** with a resolvable source URL (C6); missing label + fallback sentence |

Every localized reading page of a work, once any sidecar exists, carries exactly one `<aside class="rendition-state">` with `data-state`, `data-language`, `data-body-language`, `data-independent-source="false"`, `data-relation="rendition_of"`, full `data-*-sha256` digests, a `<script type="application/json" class="rendition-facts">` block with full pins/review (C4), and a link to the English source route. The English page carries none.

**Fallback to English is explicit, never silent.** A page that shows English text under a `/ru/` or `/zh-Hans/` URL states that in the interface language, links the pinned source, declares `lang="en"` on the body and `"inLanguage":"en"` in its JSON-LD, and is never counted as a completed translation. A stale rendition's text is not displayed at all.

Labels (interface text; **KC-Brain-proposed** wording):

| State | en | ru | zh-Hans |
| --- | --- | --- | --- |
| reviewed | Translation reviewed within the stated scope (internal agent review) | Перевод проверен в указанном объёме (внутренняя агентная рецензия) | 译文已按所述范围完成内部代理审查 |
| partially-reviewed | Translation partly reviewed within the stated scope (internal agent review) | Перевод проверен частично, в указанном объёме (внутренняя агентная рецензия) | 译文已按所述范围完成部分内部代理审查 |
| unreviewed | Translation without semantic review | Перевод без смысловой рецензии | 尚未经语义审校的译文 |
| stale | Translation out of date: the English source has changed. | Перевод устарел: английский источник изменился. | 译文已过期：英文源文已更改。 |
| missing | No translation of this document is available. | Перевода этого документа нет. | 本文档暂无译文。 |
| fallback | The pinned English source text is shown instead. | Вместо него показан закреплённый английский исходный текст. | 此处改为显示固定版本的英文源文。 |

These are interface labels, not manuscript text. The zh-Hans text carries the same caveat as the rest of the zh-Hans interface (no native editorial review).

## 5. Language and metadata rules

- Interface locale (`<html lang>`, navigation) and document language are separate. `<html lang>` stays the interface locale; the reading body carries `lang` of the text actually shown.
- Sidecar `language` must be exactly `ru` or `zh-Hans`. `script` must match (`Cyrl`, `Hans`).
- The rendition file's own front matter `language` must equal the sidecar language, and its text must be predominantly in the declared script.
- JSON-LD (C9): a shown rendition uses the **localized** URL as `url`, `inLanguage` of its language, and `translationOfWork` pointing at the English route only. A fallback page keeps `url` and `inLanguage: "en"` on the English work.
- **Fallback indexing (C5):** once any sidecar exists, a locale counts as translated indexed content only for `reviewed` / `partially-reviewed`. An English body under `/ru` or `/zh-Hans`, and an unreviewed rendition, get `robots noindex`, no hreflang alternate, no canonical claiming a translation, and no translation entry in the sitemap. The no-sidecar build stays byte-identical (`APPLY_FALLBACK_INDEXING_WITHOUT_RENDITIONS=false`).
- Publication output reports state from the compiler (never a stale "reviewed" claim): `publication.json` carries state, pins, `review_status` / `review_scope` / `review_issue`, and `counts_as_independent_source: false`.

## 6. Structural preservation checked by the compiler

For every non-stale rendition, before anything is written (the checks are structural; semantics belong to KC-Brain):

- **Sections**: every source `h2`/`h3` anchor appears exactly once in the mapping (`RENDITION_SECTION_MISSING`); the mapping names no vanished source section and repeats no anchor (`RENDITION_SECTION_DRIFT`); every mapped rendition anchor exists (`RENDITION_SECTION_UNRESOLVED`); the rendition has no unmapped extra sections, keeps source order and heading levels (`RENDITION_SECTION_DRIFT`); a section with text in the source has text in the rendition (`RENDITION_SECTION_MISSING`).
- **Structure**: per section, the same number of tables, lists, quotations, code blocks and rules (`RENDITION_STRUCTURE_MISMATCH`).
- **Formulas**: the exact LaTeX of every formula and its inline/display mode, in order (`RENDITION_FORMULA_CHANGED`).
- **Code and identifiers**: exact text of every code block and inline code span, in order (`RENDITION_CODE_CHANGED`).
- **References**: the multiset of link, image and citation targets after the logical-identity mapping of §3 (source side from the source path; rendition side from the rendition path) and the footnote count (`RENDITION_REFERENCE_DROPPED`, `RENDITION_REFERENCE_CHANGED`). A same-document link to a guessed fragment is refused (`RENDITION_LINK_FRAGMENT`).
- **Rendering**: the rendition is rendered by the same Pandoc/MathML pipeline as the source with the same raw-HTML and link checks, and the formula count of the HTML is verified.
- **Anchors**: each mapped rendition heading is emitted with `data-source-section="<source anchor>"`; when the ids differ, an alias anchor with the source id is emitted before it, so a source fragment still resolves on the rendition page.

None of this proves that a translation preserves meaning. Semantic fidelity, terminology and the necessity/sufficiency distinction are KC-Brain review (ML03, ML05).

**C7 / C8 (Agent-SWE consumer review): NOT_MEASURED.** Identifier tokens in running prose (outside code spans) and non-heading / title-id stability beyond mapped `h2`/`h3` are not enforced by this compiler round; they remain open hardening items.

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
| ML08 | Partly implemented | Provenance, section mapping and deterministic link resolution (invariant, sibling, fragment; typed refusals) in the compiled records and the page; cross-language retrieval is design only (§8): NOT_MEASURED |
| ML09 | Not applicable here | No access control exists on this public static site; NOT_MEASURED for the API and cache layers owned by Agent-SWE |
| ML10 | Out of compiler scope | Original quotations and labelled translations are authored content; the compiler preserves quotation text only through the exact link, code and structure checks. KC-Brain-owned |
| ML11 | Implemented | Reproducible compile; exact pins; silent fallback, mixed pins and wrong language metadata refused; complete text in prerendered HTML |
| ML12 | NOT_MEASURED | Needs a deployed build and retained desktop/mobile browser evidence per locale. CI is not that evidence |

## 11. Read-only audit of a checkout

`scripts/renditions_dry_run.py --source-dir CHECKOUT --source-revision COMMIT` runs the layout, pin, digest, language, link and parity stages over a clean checkout's `translations/` directory with every file treated as an unreviewed draft (a positional section mapping is derived for the audit only; a real sidecar declares it). It prints counts per language: files found, path matches, link classes, links whose literal reading from the rendition's directory would not exist, unresolved links and parity failures. It writes nothing and its output is not a publication; it never marks anything reviewed, deployed or indexed.

## 12. Limits

- Synthetic tests use placeholder text. Real PR76 draft bytes are an additional read-only integration input for link-identity red-before/green controls and a local pilot dry run; they are never committed from this repository and do not authorize publication.
- The client script `renditions.js` re-applies the state on client-side navigation through a `MutationObserver`; it was exercised through the build-time prerender (same script, a string-based DOM stub). Desktop/mobile browser evidence for a deployed build remains ML12 NOT_MEASURED except where a local pilot records screenshots.
- The browser-side replacement matches the page markup by regular expression and fails loudly (`RENDITION_SILENT_FALLBACK`) if the reading-page structure changes, rather than leaving an unlabelled English body.
- Fragments of cross-document links are not checked against the target's anchors; only the target file is checked to exist at the pinned commit.
- The state of a link target is the state of the compiled sidecar. A target that is shown but only `unreviewed` is linked as `unreviewed`; the link does not make it reviewed.
- C7 (prose identifier multisets) and C8 (title / non-heading id binding) remain NOT_MEASURED.
- Sidecar additions to the knowledge repository and the catalogue key that activates them are a later step reviewed by KC-Brain. Author drafts under `translations/` do not render anything until a sidecar names them, and a draft is never `reviewed` without a bound closed review. Until then the site builds with no renditions.
