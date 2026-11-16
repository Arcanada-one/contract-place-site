# Chudinov correction, tech diplomacy and current Journal integration

Source preparation on 16 November 2026 for Pavel's direct publication request.
The initial source-only state is historical. Native build evidence is recorded below;
this record does not assert independent review, deployment or Live Lab completion.

## Exact inputs

- Current site main, including Books: `2f93245563f100188f58359e8cff869771615376`.
- Existing RSS/Atom PR #57: `ce1075a2dca9263fe68c6ae72930079acfac568d`.
- Existing Journal PR #52: `631ece58ce82b0da2c209cfad6b96deaee770cfd`.
- Common base: `d3d17929f209612669f38db6a735d46bc9ec309c`.

The source merge preserves all current Books blocks. The two conflicts were
adjacent Books/Journal functions in `app.js` and appended Books/subscription
styles in `style.css`. Both sets are retained. The three rule-after-restart
Markdown sources and its manifest entry remain byte-identical to PR #52.
Its dated native-build receipt describes that earlier seven-issue snapshot,
not this combined candidate.

## Editorial changes

The three 14 November DORA articles retain their original URLs, titles and
publication dates and gain a dated correction. The genuine §1 statement is
reconciled with §§14–15: apply the existing framework to in-scope AI services
while accounting for gaps. The application date is distinguished from entry
into force; the AI Act scope statement is narrowed against Article 6/Annex III.

Three new Tech Diplomacy articles distinguish original findings, untested
proposals and our prospective T1 / checked R1 / distinct T2 experiment. The
GPT Deprivation sensitivity table retains all unknown-case denominators and
does not infer a population rate or causal protection effect. No TDGI
affiliation, programme admission or Forbes publication is asserted.

The final authored manifest has **eight issues and 24 localized Journal
articles**: six current issues, PR #52's seventh issue and this follow-up.
The separate unapproved daily briefing for 16 November is not included.
Content digests bind the corrected DORA files and new articles. Publication
and roadmap pins, existing attribution scope and source review states remain
unchanged. The multi-source article is not inserted into the single-study
attribution allowlist.

## Build, review and release boundary

No generated HTML, catalogue or provenance file was hand-edited. This source
candidate requires the normal native full build on the exact combined head.
Use the pinned clean manuscript and roadmap checkouts, Pandoc 3.1.3 and the
repository's supported Node version, then commit the actual generated output.
The source-only integration commit intentionally retains main's generated
baseline until that build; it is not a releasable reproducible publication.

The initial native-build handoff was superseded by agreement with KC-SWE:
Agent-Brain owns this combined branch and retains ordinary CI's actual generated
bytes; KC-SWE remains the normal release owner. No competing worker is created.
Confirm Books preservation, eight entries per locale in RSS and Atom, corrected
DORA bodies and the seventh issue's presence.

KC-Brain and DEUS-Arcana should provide scoped non-author content/language
review. Internal cross-review by the authoring context is not independent
acceptance. Existing exact-head CI, normal merge/deploy, ordinary and
cache-busting served readback and desktop/mobile inspection remain required.
An earlier green PR #52 or #57 does not establish this combined result.

The original private ARC material remains unavailable. This research does
not grant source admission, execution permission or a TDGI relationship.

## Native compile finding and bounded source repair

CI 43859078002 at `6ac2dd357803062ed8cd30d4e76d138878d32030` failed
before reproducibility: the feed projector refused Pandoc's table presentation
`style` attributes. The pinned Pandoc 3.1.3 writer emits integer percent widths
on table/col and left/right/center alignment on th/td. The successor parser
recognizes only those exact forms and discards them; arbitrary CSS, extra
declarations, duplicate style attributes, event handlers and unsafe URLs remain
refused. Semantic table structure, headers, spans, text and links are retained.
Four regression methods cover all three languages and both feed formats,
width/alignment boundaries, 24 unsupported-style cases and seven combined
unsafe/duplicate-attribute cases. Native test/build outcomes are still required.

Primary code reference: Pandoc `3.1.3`,
`src/Text/Pandoc/Writers/HTML.hs`, blob
`17fe2c945e6c4aaec3bf10922abf2e6da4d2880d` (`tableToHtml`,
`colSpecListToHtml`, `tableCellToHtml`), plus `Writers/Shared.hs` for alignment.

## Journal CSP and source-text oracle repair

CI 43860274916 on `26b795e442d4ece8f5891f4eaabc8d44e3d53b5a`
completed the native 328-page compile, then hygiene correctly rejected inline
styles in the three new Journal pages. Journal now uses the existing
`build_publication.csp_table_classes` transformation, retaining the same CSP
and ordinary hygiene gate. Unsupported styles are not silently accepted.

The integrity oracle reads the manuscript with pinned Pandoc 3.1.3's JSON
reader, independently of the HTML writer and table-class transformation.
It retains emphasis/link labels, headers, list paragraphs and individual table
cells. Cell and HTTPS-link multiplicities are checked so a repeated number
elsewhere cannot mask a changed or deleted cell. Existing digest, locale,
index, noindex and rendered-link negative controls remain in force.

All six authored manuscripts use absolute HTTPS canonical internal links,
which the existing Journal decorator permits; no link policy was broadened.
The referenced core-contract and API-integration routes were checked for
EN/RU/zh-Hans against the current committed route tree. The six manuscript
digests were updated for those link-only changes. Native combined tests,
generated-output reconciliation and non-author release review remain open.

## Journal-only client cache identity

The previous `/content.js?v=<knowledge pin>` URL could remain unchanged when
Journal bytes changed. `app.js` reads `window.CP_CONTENT` and replaces the
prerendered main body, so an old cached catalogue could overwrite a corrected
article. Source inspection establishes that key collision; production warm-cache
behaviour is not claimed as measured.

The build now hashes the exact emitted content.js bytes and uses that SHA256
in every HTML reference, while keeping the scientific source pin in the data.
The ordinary publication checker covers every generated HTML page. A native
Journal regression changes only Journal input with a byte-identical publication
manifest, requires a different key, refuses the old source-pin-only key and
requires deterministic bytes/key when rebuilding identical inputs.

## Non-author correspondence findings and retained native output

KC-Brain review [6916080839](https://github.com/Arcanada-one/contract-place-site/pull/57#issuecomment-6916080839)
identified two meaning changes in four RU/zh-Hans spans: controller identity
became environment, and a concrete assignment became general tool purpose.
Commit `fc1e2324d52622cff876a50dfbc74503cf3d8946` applies exactly the
four proposed replacements and updates only the two manuscript digests.
The other four editorial bodies remain unchanged. Re-reading the corrected
spans by the non-author reviewer is a separate gate; structural/numeric/link
parity alone did not detect these distinctions.

`docs/editorial-native-build-20261116.json` records the actual successor
native source, synthetic checkout, workflow, artifact SHA256 and all 377 output
identities. Run 43867888073 / job 133301057854 produced 328 HTML pages,
eight issues in each of six feeds and actual content.js cache key
`4d92b5be88f90474178258964d811b477e7bc27cdd3e6767ae85fcc67766acb0` on every page.
All four corrected wording spans were read in the artifact. DORA retains its
14 November publication date and declares its 16 November correction date.

The native run passed eight Journal tests, 19 feed tests, all 126 rendition
tests and the remaining renderer/search and pinned regression groups. It then
failed only at the unchanged committed-output reproducibility gate because this
bundle had not yet been committed. Served readback was skipped. This is not a
green release workflow.

The previous capture's rendition-comparison failure has been resolved: the
test validates each page's cache key against its own content bytes before
normalizing that one verified URL. Existing other-byte, wrong-language and
extra-byte controls remain, and the old source-pin URL is rejected. The native
successor above actually executed that repair.

The output commit removes the temporary collector and retains exact native
bytes. A new normal exact-head workflow must reproduce the committed bundle
and pass all remaining checks, including served readback. This record is not
a production or independent editorial acceptance receipt.
