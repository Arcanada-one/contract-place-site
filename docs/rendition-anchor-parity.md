<!-- SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Rendition Anchors: Preserve a reviewed heading without inventing missing prose

KC-Brain authored this bounded compiler correction under Pavel's instruction to publish the accepted corpus. It addresses the four reported preamble refusals without rewriting reviewed manuscript bytes. The current programme release remains independent and is already merged at `b1a2cb006077eea52fd09ad0b7a6fdbe5f538c65`.

## One narrow representation rule

The source prefix immediately before its first H1 must consist only of an optional exact `markdownlint-disable-next-line MD033` HTML comment and one empty HTML anchor with a simple stable id. The rendition must begin with a real Pandoc H1 carrying that exact id. That id must occur exactly once in each AST, including raw HTML and Pandoc attributes. Only then is the source prefix omitted from a temporary structural-comparison view. Neither source bytes, rendition bytes nor either input AST is changed.

A code example is not an H1. An arbitrary comment, substantive text, an extra HTML attribute, another anchor, a missing/wrong id, or a duplicate id does not qualify. Prose after the H1 is still required. All ordinary section, formula, code, reference, source-pin, review-evidence and rights checks remain in effect. This rule is not a general permission to delete preambles or HTML.

The integration in `scripts/renditions.py` adds two lines before ordinary parity evaluation. The stored file also normalizes its final-newline representation; no other checker behavior is changed. The helper is `scripts/rendition_preamble.py`. The exact earlier checker is Git blob `764227c70a6f1c02fd20ed083c54e1cbaa8e9fe1` at site commit `b1a2cb00`.

## Actually executed locally

Python 3.13.5 and Pandoc 3.1.11.1: all 22 tests in `scripts/test_rendition_preamble.py` passed. On the same positive synthetic input, the exact earlier checker refused with `RENDITION_SECTION_MISSING`; the changed checker passed. Negative controls cover lost prose, unsupported markup, wrong/missing/duplicate anchors, fake headings in code, changed formulas and dropped references. Ordinary unchanged and retained-preamble cases remain positive controls. These are author-run finite tests, not external review or production evidence.

## Exact-file regression in ordinary CI

The workflow also invokes `scripts/check_reviewed_preamble.py` against read-only pinned checkouts. It compares the actual earlier compiler with the new compiler on the four exact reviewed files below, checks the source/target Git blobs, whole-document structural/formula/code/reference parity, refusal of inserted-prose and missing-anchor mutations, and unique ids in raw Pandoc-rendered fragments. Missing test inputs fail rather than silently skipping. Hosted CI uses its normal Pandoc 3.1.3; its results must be read from the actual run, not inferred from the local synthetic tests.

English source checkout: `46af0f06218e590e047a585ac74820f3c6336604`.
Reviewed rendition checkout (Phase-A bytes-import commit with corrected Reuse ru): `cad15f92f1821cf5ffe9c3d257bdbac8beba23ba`.
Code-span refusal fixture checkout: `64aa36781f92b1b1a376613f847c82e098720b1d` (Reuse ru `7376c330` must still raise `RENDITION_CODE_CHANGED`).
Prior refusal-fixture checkout: `151dc8927547d27a88d0d5082b8abd1f98bd7b33` (old zh-Hans Uncertainty and both Reuse blobs must still raise `RENDITION_FORMULA_CHANGED`).
An in-memory mutant that re-adds one inline code span to Reuse ru `f7d53ee8` must also raise `RENDITION_CODE_CHANGED`.

| Study | English source Git blob | Russian Git blob | Simplified Chinese Git blob | Exact-file outcome |
| --- | --- | --- | --- | --- |
| Uncertainty Preservation | `8ca885fc3f144d89e95e4813868fd953450f1f71` | `8aaa8dae18a2014be6495c479e85a3e114538420` | `9a94c63085287f59f42df75014844801f1ffca1e` | expected parity-pass |
| Reuse Economics | `aff97b3cda92bbb8067b1db47ce7c16ddd98c5ac` | `f7d53ee85bea6966c7068a0835b19ba4593a8e19` | `f07227366731e2fb946285ec696c7199ae48565f` | expected parity-pass; prior `7376c330` remains a predeclared `RENDITION_CODE_CHANGED` negative |

The existing composite fidelity evidence is in knowledge-contract at `791d23c3c2e44c17c0f6d123f0d9d9e0af4aceec`, path `reviews/renditions/k8-composite-exact-blob-evidence-20261109.md`, blob `eb689d2b5eaf40cd124fdec27d4fe312867d2d73`. This note does not replace those Agent-Brain findings or claim new human/native-speaker review.

## Separate publication decisions

The additional checkouts are test inputs only. They do not change publication or roadmap manifests, the catalogue, the sidecar, review states, generated pages or index admission. The ordinary source build and its prior regression suites still run. A separate exact-code review is requested from Agent-Brain. Real sidecar integration, full site rendering of all admitted renditions and served/browser checks remain separate evidence. No new task, worker, permissions or runtime authority is created by this correction.
