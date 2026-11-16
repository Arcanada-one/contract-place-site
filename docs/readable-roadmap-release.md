<!-- SPDX-FileCopyrightText: 2026 Pavel Valentov and Knowledge Contract Arcana contributors -->
<!-- SPDX-License-Identifier: CC-BY-4.0 -->

# Readable Roadmap: Compatible source parsing and publication handoff

KC-Brain prepared this bounded repository correction under Pavel's 9 November 2026 instruction to publish a usable reader-facing edition. It does not dispatch a new worker, grant runtime authority or claim that a new site revision is deployed.

## Concrete mismatch

The accepted knowledge source contains readable `TASKS.md` headings such as **Claim Atlas: Recover the claim-level mathematical crosswalk**, named dependencies and Immediate/Next/Expansion priorities. At site base `b6d7532f48498d385171a41941cb864195a4fbc0`, `scripts/roadmap.py` recognizes only numbered headings and P0/P1/P2 priorities. Merely moving `roadmap-manifest.json` to the current source therefore cannot produce the new roadmap.

The baseline parser blob is `1131ea4e75200e2f6267f4dc09f43f9f58251767`. The inspected readable source `roadmap/TASKS.md` has blob `1ae826f2b98e5588e7143b8131aeaba2082c7d50` at both `0b284c6cd971566e7fe38d572c86b164c28b27c5` and `2b5bcff544fea5d1752ff009933e4ce0305dad8b`.

## Implemented change

`scripts/roadmap_names.py` strictly normalizes the new presentation syntax before the existing card parser. Explicit, unique `rm-` anchors establish identities; short names resolve dependencies. No identity is guessed from position. Dated artifact observations and original gaps remain visible as prose and are not converted into executable task state. Duplicate names, identifiers, aliases and dependencies, unknown names, missing anchors, mixed formats and unexpected fields fail closed.

The original graph, owner, source-pin, file-hash, cycle, private-data, HTML, link and planned-state checks remain. Only three exact inert editorial comment lines are removed before Markdown parsing; unknown raw HTML is still refused. The existing numbered source format passes through unchanged, retaining reproducibility of the currently pinned site.

## Actual local verification

`python3 -B scripts/test_roadmap_names.py -v` ran in the assistant's isolated container: 22 tests passed, with one additional real-checkout test skipped because the complete pinned checkout was not present there. These are parser/graph tests for this change, not the 22 scientific Knowledge Checks scenarios and not independent review. The tests retain both positive and adverse controls.

CI now executes the additional test against its actual `_knowledge-source` checkout. It parses all 25 accepted readable cards and compares identifiers, priorities, owners and named prerequisites with their original dependency graph. Existing renderer, link, security and committed-output reproducibility steps are unchanged. Hosted CI must be read before claiming this full check passed; a skipped local check is not a pass.

## Remaining release operations

This parser increment intentionally does not change either source manifest, the generated publication tree, manuscript bodies or their review records. The finite publication lane can proceed independently of unrelated live-runtime work.

The native site builder must consume the accepted source and this compatible parser, then complete the reader-facing renderer update: names rather than codes in contents, cards, dependency/advisory links and priority bands; old anchors retained as compatibility targets. It must rebuild and commit all generated files, run ordinary CI and review, deploy through the existing validated workflow and compare served `publication.json` and `roadmap.json` to the intended inputs. A code merge is not a claim that these operations occurred.

The knowledge-source naming canon and trilingual reading guides are already merged in source `2b5bcff544fea5d1752ff009933e4ce0305dad8b`. Current roadmap prose still contains historical pause/count observations; update the author-maintained present-tense release summary without rewriting historical evidence or inventing Muneral task states. The source-pinned translation drafts and their existing exact-subject review records remain separate from rendition admission. Never label all 50 authored drafts as reviewed or deployed merely to fill the catalogue.
