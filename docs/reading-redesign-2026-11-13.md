# Reading interface revision — 13 November 2026

Scope: source-only UI changes for contract.place. Prepared by KC-Brain from operator feedback. Status: **candidate; not built, merged or deployed**.

## Baseline

Repository: Arcanada-one/contract-place-site, main `41032b80209dd315b3dff95ec7c69a7b4ed80bf6`.
Local CodexPro clone: `~/research/contract-place-site`.
Source files: `src/site/style.css` and `src/site/app.js`. No manuscript or rendition files changed.
The committed `public/` tree is GENERATED and must be rebuilt on the exact source pins; do not hand-edit it.

## Source changes

- Links in journal, science, specifications, references, documentation and citations are always visibly underlined and coloured in light and dark modes. Visited, hover and focus are distinct.
- Main reading text uses 17 px at the default 16 px browser root (16.5 px on narrow devices), with a 1.65 line height; H1 is bounded to 28–38 px and H2/H3 are reduced. Native browser zoom and text preferences stay available.
- On narrow screens, breadcrumb links do not break the word «Главная» in the middle.
- The search trigger becomes a pill; its existing modal, local search and public read-API search are retained, not replaced by a fake engine.
- English, Russian and Simplified Chinese are available as three directly visible links with round flags plus text codes. Native-language tooltips work on hover and focus; Escape dismisses. A real href provides a non-JS fallback. The existing locale change handler remains responsible for SPA navigation and stored preference.
- On smaller viewports the theme button remains available. At widths below 360 px the controls use a second row rather than squeeze the reading area.

## Verification performed by KC-Brain

Eight narrow static checks PASS, including 24 candidate link/visited/hover colour-vs-background combinations, all at least 4.5:1; minimum measured contrast 5.43:1. These are CSS-token checks only, not a full browser or WCAG certification. The current CodexPro safe mode refused `node --check src/site/app.js`; don't mark script execution as passed.

## Required DEVS build and review

1. Reconcile existing KC-SWE / Muneral work; do not duplicate a build task. Confirm main/PR head before applying.
2. Use existing Node 24, Python 3 and **Pandoc 3.1.3** on DEVS. Compile/rebuild using `AGENTS.md` / `README.md`; commit updated `public/` and cache-busted asset hashes to the same PR.
3. Run project CI: `scripts/check_publication.py`, `check_links.py`, `check_page.py`, `test_build.py`, `test_journal.py`, `test_renditions.py`, `node scripts/test_search.js`, plus the current required integrity and licensing checks. Inspect exact test commands and logs.
4. Manual browser matrix: this article, /ru/engineering/specifications/context-package/, one scientific work with MathML, journal index, search and 404. Light/dark × EN/RU/zh-Hans × widths 320/390/768/1440. Verify keyboard navigation, screen reader labels, no horizontal document scroll, fragments, fonts, hover/focus tooltips, Ctrl/⌘K, search cancellations and language fallback notices.
5. Verify the source/rendition status separately. **This PR does not deliver full scientific RU/ZH translations**; current fallback is not to be represented as translated content. Do not render `CTX-R013` as a meaningless lone reader-facing heading in the next content/editorial pass: retain stable requirement IDs in sources, registers and anchors, but pair them with readable descriptive labels on all locales, subject to exact source review.
6. Obtain an exact-head review, merge only after build and evidence. Deploy via the existing release pipeline. Independently read back served pages **and CSS/JS assets**; verify CDN propagation, mobile breadcrumb and actual search.

## Release boundaries

Do not change scientific claims, catalogue status, provenance, API permissions, language verification states, analytics consent, licensing notices or historical receipts as a side effect of UI work.

This candidate is deliberately narrower than the full redesign: complete translations and explanatory requirement headings require coordinated canonical source/rendition changes, separate reviews and a publication pin. No acceptance, merge, deployment or real-device verification is claimed here.
