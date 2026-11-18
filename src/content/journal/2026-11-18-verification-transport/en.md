---
site: contract.place
section: journal
slug: verification-transport-2026-11-18
date: 2026-11-18
lang: en
title: "Correct verifier verdicts failed in 20.3% to 31.0% of cases once agent evidence was abstracted"
excerpt: "A new study holds agent traces fixed and changes only what an LLM verifier can see. Among judgments that were correct on the full trace, 31.0% failed under macro abstraction and 20.3% under history compaction; overall, restoring the execution provenance recovered 85.5% of failures across all three abstraction boundaries."
---
When an LLM verifier judges an agent trace correctly and the same trace is then shown to it through a compacted history, a delegation boundary or a macro action, in views the authors constructed from frozen traces, the correct judgment does not always survive. Sheshanarayana and Goli held the trace, the ground truth, the criterion and the verifier fixed and changed only the view. Among judgments that were correct on the native view, 31.0% failed under macro abstraction, 30.9% under delegation and 20.3% under history compaction. Putting the original provenance back recovered 85.5% of those failures.

## What was measured

The authors call the property Verification Transport: a verifier judgment that is correct on the native execution view should stay correct when the same execution is exposed through an abstraction. They built matched native, abstracted and restored views of frozen trajectories from four benchmarks: 250 trajectories from AgentProcessBench, 758 from ATBench, 441 pairwise comparisons from PlanRewardBench and 754 trajectories from AgentDojo. These counts are the instances that met each benchmark's eligibility rules for matched construction.

Three boundaries were tested. Macro abstraction hides low-level operations behind a higher-level action. Delegation hides a sub-execution behind an agent boundary and shows only the call and its result. Compaction replaces an earlier region of history with a marker. Seven verifier backbones ran under four protocols: direct judgment, evidence-grounded judgment, provenance-seeking agentic judgment, and a deliberative audit of the evidence-grounded verdict. All verifiers ran at temperature 0.

Source: Disha Sheshanarayana, Sai Linisha Reddy Goli, "Do Verifier Judgments Survive Abstraction? Measuring Verification Transport for LLM Agent Evaluation", arXiv:2611.18471v1, 13 November 2026, [arxiv.org/abs/2611.18471v1](https://arxiv.org/abs/2611.18471v1).

## How the failure rate is counted

The Verification Transport Failure Rate (VTFR) is conditional. Its population is only the instances the verifier judged correctly on the native view. Correctness is judged by comparing the verifier's verdict with the benchmark's ground-truth label; the verifier is the LLM under test. Within that population, VTFR counts every instance whose abstracted verdict is either wrong or not usable. Abstentions, unresolved outputs and protocol-invalid responses count as failures.

Pooled rates sum numerators and denominators across cells instead of averaging percentages. The 31.0%, 30.9% and 20.3% figures pool all four benchmarks, seven models and four protocols. The authors state that VTFR measures the stability of initially correct judgments, not overall verifier accuracy. Across benchmarks, aggregate VTFR ranged from 25.5% to 32.2% under macro abstraction, from 26.1% to 32.9% under delegation and from 16.2% to 24.7% under compaction.

Source: the same work, sections 4.2 and 5.1 and Appendix C (including C.1), [arxiv.org/abs/2611.18471v1](https://arxiv.org/abs/2611.18471v1).

## Two ways to fail

The paper splits VTFR into Wrong Verdict and No Verdict, both over the same native-correct denominator, and the two sum to VTFR. Under macro abstraction, the overall split was 13.4% wrong and 17.7% no verdict. Under delegation it was 13.2% and 17.7%; under compaction, 12.2% and 8.0%.

Protocols differed sharply. Direct judgment had the lowest pooled VTFR, 16.4% under macro abstraction, but its failures were almost all wrong verdicts: 15.8% wrong and 0.7% no verdict. The deliberative audit had the highest, 49.3%, made up of 9.4% wrong and 39.9% no verdict. The authors warn that a lower failure rate does not necessarily mean a more reliable verifier, and that, because VTFR is conditioned on native-correct judgments, which may be different instance subsets for different protocols, protocol comparisons are not paired on identical instances and should account for those differences.

Source: the same work, section 5.1, Appendix E.1, Table 4, and Appendix E.2, [arxiv.org/abs/2611.18471v1](https://arxiv.org/abs/2611.18471v1).

## What restoring provenance recovered

Each abstracted view has a restoration condition that reintroduces the original operations, the delegated trajectory or the original history from the same frozen trace. The Restoration Recovery Rate (RRR) counts, among native-correct instances that failed after abstraction, the share that became correct and usable again. The Restoration Degradation Rate (RDR) counts, among instances that stayed correct after abstraction, the share whose verdict became wrong or unusable after restoration.

Pooled over everything, restoration recovered 85.5% of failures and degraded 5.2% of preserved judgments. Recovery was 87.9% for macro abstraction, 86.9% for delegation and 79.8% for compaction. In an ablation on two benchmarks with two models, a plain re-query recovered 22.5% to 33.1%, a lossy restoration of action and tool identities 34.0% to 53.9%, and exact restoration 73.6% to 82.5%.

These are the authors' figures on constructed abstractions of frozen traces. Appendix G states that live abstractions may differ and that restoration assumes the original provenance is still available.

Source: the same work, section 5.1 RQ3, section 5.2 and Appendix G, [arxiv.org/abs/2611.18471v1](https://arxiv.org/abs/2611.18471v1).

## Why a Knowledge Contract reader should care

A verifier verdict is an assessment of an execution made from the evidence available to the verifier; it is not by itself established knowledge. When a verdict crosses a compaction or delegation boundary and the evidence stays behind, the receiver holds a claim whose support it cannot inspect. That is a provenance problem, not only an accuracy problem. The paper measures how often a verifier stops producing a correct, usable judgment for the same execution when supporting evidence is hidden, and how often restoring that evidence recovers the judgment. It also shows that a lossy restoration recovers less than the exact source.

For reuse, this suggests two rules worth testing. A verdict reached on abstracted evidence should not be accepted on that basis alone. An ambiguous case should refuse or ask for the exact source rather than guess.

The paper's abstract names a public code repository (github.com/Disha1001/Verification-Transport). When we requested that address on 18 November 2026 at 04:39 UTC, it returned HTTP 404.

Source: the same work, abstract, sections 3.2 and 6, [arxiv.org/abs/2611.18471v1](https://arxiv.org/abs/2611.18471v1).

## What we proposed, and what has not happened

Our research desk assessed the paper on 17 November 2026 and proposed a trial, not adoption: take 20 approved frozen traces, one pinned verifier and the same ground truth; show each trace in three abstracted views and with the exact original evidence restored by hash; record verdict flips, refusals, missing provenance and cost. Acceptance would require that nothing is accepted on abstracted evidence alone and that every ambiguous case refuses or asks for the exact source.

The status is proposed. No owner has decided, nothing has run, and the specific Knowledge Contract clause it maps to is not yet identified.

Source of the definitions this trial would use (the trial itself is our proposal): the same work, section 3.1, [arxiv.org/abs/2611.18471v1](https://arxiv.org/abs/2611.18471v1).
