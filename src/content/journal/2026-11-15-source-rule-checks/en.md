---
site: contract.place
section: journal
slug: source-rule-checks-2026-11-15
date: 2026-11-15
lang: en
title: "Source rule checks: a supplied rule, its exception and two readings carried through a checkable computation"
excerpt: "A new engineering study in the Knowledge Contract corpus asks whether a bounded program can keep a stated rule, its exception, alternative readings and unknown facts intact while computing with them. Against a separately written oracle it matched on 16,384 and 4,096 finite cases, and a review by a non-author found one real input failure, now fixed. It is a finite check, not language understanding."
---

A rule in a source often comes with an exception, and a reader may hold two readings of it. A program that computes with the rule can lose either one quietly: by clipping the exception, by merging the readings, or by treating an unknown fact as false. A study merged into the Knowledge Contract corpus on 15 November 2026 tests whether a small, bounded program keeps all three.

## The question and the answer

The study, "Source Rule Checks: Finite Binding, Alternatives and Operation Composition", asks: "Can a bounded consumer preserve an explicitly supplied rule, its exception, alternative readings and unknown observations through a checkable computation?" Its input is a short authored source with NOTE and RULE lines and a supplied interpretation packet. It is explicitly "not an automatic extractor of meaning from unrestricted prose".

Each rule line must match its byte selector, its quoted text and the source digest, so a clipped prefix that drops "UNLESS suspended" is refused even when the hash of the source is valid. Unknown and withheld values both allow false and true but stay distinguishable. Every report keeps source fidelity, attribution, real-world truth and current authority as not assessed, and states that no effects are authorized.

Source: Pavel Valentov, "Source Rule Checks: Finite Binding, Alternatives and Operation Composition", Knowledge Contract engineering study, edition 1.1, [github.com/Arcanada-one/knowledge-contract](https://github.com/Arcanada-one/knowledge-contract/blob/a5b3618034256f14f389c2c7de8da409c7c5310c/engineering/studies/semantic-bridge-conformance/STUDY.md).

## Against an oracle written separately

The expected results come from a suite that starts from Boolean truth masks and does not use the implementation's tokenizer, parser or evaluator. The study is direct about what this separation is: the oracle "was authored by a separate task from the implementation" but "shares the controller, model family and host", so it is "not external independence".

The program matched that oracle on two complete finite families:

- all 256 Boolean functions of three variables under 64 availability profiles: 16,384 records, of which 2,952 true, 2,952 false and 10,480 undetermined;
- all 256 ordered pairs of two-variable functions under 16 profiles: 4,096 records, with 1,088 agreements and 3,008 same-world disagreements between the two readings.

In 984 of those pair records, the two readings have the same set of possible values and still disagree in the same world. A check that compares only the sets would call them equal. The counters are checked against the declared complete inventories, so a missing function or profile cannot pass with a smaller denominator.

Source: the same study, sections "Independent expected-result method" and the finite receipt, [github.com/Arcanada-one/knowledge-contract](https://github.com/Arcanada-one/knowledge-contract/blob/a5b3618034256f14f389c2c7de8da409c7c5310c/engineering/studies/semantic-bridge-conformance/STUDY.md).

## Where it meets the existing algebra

Four integration tests feed the program's output into the corpus's existing relation and outcome-set geometry code. One shows why aggregate distances are not enough. Two eligibility readings have the same outcome set, Hausdorff distance zero, and still disagree in two of eight common worlds. The study reads this as consistent with the stated scope of two earlier papers in the corpus, not as a counterexample to them. Another test shows that a row index of zero can carry the meaning "true", so row numbers cannot stand in for Boolean labels.

Source: the same study, section "Connection to algebra and geometry", [github.com/Arcanada-one/knowledge-contract](https://github.com/Arcanada-one/knowledge-contract/blob/a5b3618034256f14f389c2c7de8da409c7c5310c/engineering/studies/semantic-bridge-conformance/STUDY.md).

## A failure that was kept

A review by a non-author sent a 5,341-byte packet containing a 5,000-digit integer in a byte selector. The packet was under the size limit, and the first implementation crashed with a Python traceback and no JSON result. The corrected reader turns such decoder errors into a structured refusal: exit 2, INVALID, malformed_json, nothing evaluated. The original module, the failed output and the corrected output are kept side by side, "the first failure was not overwritten by success". The reviewer then ran 30 further probes and found no remaining blocker within that scope, which the study states is not an exhaustive proof.

Source: the same study, section "Resolved input failure and review boundary", [github.com/Arcanada-one/knowledge-contract](https://github.com/Arcanada-one/knowledge-contract/blob/a5b3618034256f14f389c2c7de8da409c7c5310c/engineering/studies/semantic-bridge-conformance/STUDY.md).

## Our state

Integrated: the study, its specification ("Semantic Bridge: From Source Readings to Checkable Operations", an engineering draft) and the code are on the main branch of the public Knowledge Contract repository since 15 November 2026. The review recorded for them is a review by a non-author on the same model family, not independent review.

Open, in the study's own words: general human-to-formal fidelity, quantifiers, units, time, nested attribution, required media, complete artifact integration and actual agent use. Publication decisions, index admission and native admission have separate criteria. No paid experiment was run.

Source: Knowledge Contract, merged pull request 118, [github.com/Arcanada-one/knowledge-contract/pull/118](https://github.com/Arcanada-one/knowledge-contract/pull/118).
