<!--
SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors
SPDX-License-Identifier: CC-BY-4.0
-->

# Requirement labels: repair and build evidence, 13 November 2026

## Baseline and scope

Existing PR44 source head `731720eb54d42b5e07019d49b954a72e855ae912`, site production base `98b3f6ab365b29571dc0ded0b8db0a8eeb9cac82`. The source-only proposal passed its 77 label checks, but ordinary CI rejected the stale tracked `public/` tree. Knowledge source stays pinned to `161a01afb1b756adf059ea2e1cbdd0dca29d83a2`; no manuscript, rendition sidecar, catalogue or index admission changes.

An internal delegated reviewer examined the proposal and all 20 short labels against the pinned English clauses. This is an internal technical review; controller/model-family independence is NOT_VERIFIED. The reviewer also authored the accessibility repair, which KC-Brain then inspected separately. No external or human review is claimed.

## Repairs

- Original IDs are ordinary accessible text inside an existing visually-hidden span. The implicit strong role no longer receives a prohibited `aria-label`. Stable data/title attributes and no-JavaScript canonical IDs remain.
- The existing harness checks retained text, absence of forbidden naming attributes, repeated-decoration idempotence, and a new SPA body. It reports **81 checks** locally.
- Four Chinese short captions retain the source's subject revision, top-k/global distinction, delivered package plus requirements revision, and required acceptance cases.
- Source and generated assets are updated together.

The accessibility rationale is the [W3C strong role](https://www.w3.org/TR/wai-aria-1.2/#strong) and [ARIA in HTML](https://www.w3.org/TR/html-aria/#el-strong). A valid DOM structure is not a claim of tested assistive-technology behavior.

## Generation and reproducibility boundary

This environment has Pandoc 3.1.11.1, while the complete publisher requires 3.1.3. No renderer gate was changed or bypassed. The documented interface-only fixture path reused 34 exact committed inputs, including the previously compiled catalogue/journal data, then ran the repository renderer against the updated source.

All 346 resulting output files were compared with the pinned Git tree:
- 31 are byte-identical.
- 313 HTML files differ only in the two app/style cache hashes. Reversing only those hash substitutions reproduces every old Git blob.
- Two public assets equal their source bytes.
- Zero unexpected differences.

App source/public blob: `7a815924013132344757a4443af3705854f725af`; SHA-256 `0b8fc0225a29a7758623e0681dfcb8adeb6a1610368f791a62fbb27e1f0cc793`. Style source/public blob: `ab17913b5a660b81ee53a0e7d22bf2615ee068b5`. Label test blob: `08c3f55dee39c9ba3acc64e921fd73ac6d97e5c9`.

Existing local checks also passed: 31 exact canonical bodies / 93 locale reading pages; 540 original MathML expressions; 313 pages; 18,576 internal links; 111 full/index page checks and 62 exact repository source links; licensing, search, SEO, robots, sitemap and llms.txt checks. These are local source/output checks. The ordinary hosted full build with Pandoc 3.1.3 must independently reproduce the committed result before release.

## Actual browser observations and remaining check

A cloud browser inspected the existing public page through RU → EN → zh-Hans → RU at a 1363×936 viewport. Each showed 20 raw stable markers and zero enhanced markers. RU/ZH explicitly displayed English fallback, the same pinned source, and working section navigation; switching locale retained `#5-budget-and-projection`. The served app hash was the old `80322aedbd3c948ee4020e79ed39962b2e173ca1144cb7460e7759be7baf28ec`. This is baseline production evidence, not candidate acceptance.

Local Chromium could not launch (`socket() failed: Operation not permitted`). The local browser extension lacked an originating-browser context. The available cloud interface supports public navigation/read-only DOM inspection, but no candidate injection, local file serving, viewport resize or JavaScript disabling. No candidate/mobile/no-JavaScript/assistive-technology browser PASS is claimed.

The remaining operation is a narrow real-browser check of the exact successor: EN/RU/ZH, 320/390/1440 widths, light/dark, original-ID discoverability, keyboard/section navigation, SPA transitions and no-JavaScript source fallback. Then ordinary release and actual served asset/source readback. Rollback is a normal revert to the last accepted site version; no history rewrite.
