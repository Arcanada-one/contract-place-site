# Reader-facing requirement identifiers

Date: 13 November 2026. Source-only proposal against site commit `98b3f6ab365b29571dc0ded0b8db0a8eeb9cac82`.

The canonical specification **must retain** stable requirement identifiers (e.g., `CTX-R013`) for machine use, references, citations, review, and exact source verification. But human readers should not see a line starting only with an opaque identifier.

This change adds a browser-side *presentation-only* layer. The stable prefix/numeric identifier is kept in `data-requirement-id`, hover title, and accessible name. The visible text becomes `Требование 13 — Сохранение защищённых единиц и неопределённости` in Russian, with English and Simplified Chinese equivalents. All 20 context-package requirements have short interpretive labels derived from the exact source at publication commit `161a01afb1b756adf059ea2e1cbdd0dca29d83a2`. Unmapped valid requirement codes receive a generic localized `Requirement / Требование / 要求 N` fallback.

The printed source paragraph is not changed in `r.html` or the generated HTML source. This intentionally preserves the project's source-bound publication check and keeps scientific claims unmodified. The browser-only enhancement executes after render if `requestAnimationFrame` exists, and on SPA rerenders. Without JavaScript the canonical identifier remains visible. The requirement number remains metadata, not a link or permission.

This **does not translate the English manuscript**. RU/ZH renderings are still English fallbacks unless a pinned, reviewed rendition is published. Translation drafts already exist in Knowledge Contract `main`, but those have `translation_status: author-draft` and must be reconciled with the pinned English source and independently reviewed before an edition is promoted. A separate canonical rendition proposal is necessary.

The unit harness tests 20 × 3 localized labels, invalid IDs, exact original-ID retention, preservation of unmodified text, reentrant idempotency, and browser-only invocation. Full browser/manual visual testing and release are separate gates.
