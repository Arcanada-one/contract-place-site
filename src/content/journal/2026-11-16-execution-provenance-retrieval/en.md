---
site: contract.place
section: journal
slug: execution-provenance-retrieval-2026-11-16
date: 2026-11-16
lang: en
title: "Evidence cut along the execution record: in one study, source-aligned units delivered complete support more often than fixed token windows"
excerpt: "Seven researchers asked when the recorded structure of an agent's execution helps its memory retrieve evidence. On 2,000 queries, units aligned to tool arguments and outputs put the complete evidence inside a 2,048-token budget 19.07 points more often than 512-token windows, and a graph step added 4.55 points more, primarily where evidence spans several events. We keep the result as a reference and have changed nothing."
---

A claim that rests on several pieces of evidence is supported only when all of them are in front of the reader. A study submitted on 22 September 2026 applies that standard to agent memory: under a hard token budget, does retrieval deliver every required piece, and does the recorded structure of the execution help?

## The question and the measure

Yiqi Wang, Jinqian Ju, Jiaqi Zhang, Zequn Sun, Yiqun Duan, Mingkai Zheng and Taotao Cai treat retrieval from an agent's execution history as evidence completion. Each required item is an exact span in the original execution record, and every retrieved candidate maps back to the same source coordinates, so differently organised candidates can be scored against the same evidence.

Their main measure, Full Support, asks whether the retrieved candidates that fit the token budget cover every required span. The authors' reason: "partial evidence generally does not yield a correct answer."

The corpus, ISETrace, is synthetic: intents and interactions are generated, and the tool calls are executed in isolated operating-system environments. A language model wrote 2,000 queries over 1,207 held-out executions, each with one or more exact quotations from tool arguments or outputs; a quotation was accepted only if it located uniquely in its source event. The test set has 641 direct, 906 linked and 453 multi-fact queries.

Source: Yiqi Wang, Jinqian Ju, Jiaqi Zhang, Zequn Sun, Yiqun Duan, Mingkai Zheng, Taotao Cai, "When Does Execution Provenance Help Agent Memory Retrieval?", arXiv:2609.25913v1, 22 September 2026, [arxiv.org/abs/2609.25913v1](https://arxiv.org/abs/2609.25913v1).

## Units that follow the source beat fixed windows

The usual candidate is a fixed window of tokens. The authors build candidates from tool arguments and outputs instead, which they call provenance units. With the same fine-tuned dense scorer on both sides, provenance units raised Full Support at a 2,048-token budget by 19.07 points over 512-token windows. They stayed 11.96 points above an oracle that picks the best of four window sizes separately for each metric, a setting the authors call stronger than any single deployable one.

Shrinking the window does not rescue the flat view. Cutting it from 512 to 128 tokens raised Full Support at 2,048 tokens by 7.11 points, but the evidence was then scattered over more separately ranked candidates and early ranking fell.

The authors limit the claim themselves. The two views are not the same text cut differently: the flat view includes free-form messages and reasoning, while provenance units are restricted to tool arguments and outputs. They report the difference as an effect of the candidate view, "not a pure segmentation estimate".

Source: the same work, abstract and results on candidate views, [arxiv.org/abs/2609.25913v1](https://arxiv.org/abs/2609.25913v1).

## Graph gains concentrate where evidence spans several events

To isolate the graph, the authors hold the candidates and their dense scores fixed and add a learned correction over typed links between units. It adds 4.55 points of Full Support at 2,048 tokens, with a 95% interval of 2.98 to 6.18.

Split by query type, the gain is 0.19 points for direct queries, with an interval that includes zero, 4.00 for linked and 11.83 for multi-fact queries. Expanding flat chunks through an entity co-occurrence graph, by contrast, never differed from keyword retrieval by more than 1.1 points on any budgeted metric in their main table.

The hard case stays hard. On multi-fact queries the graph variant reaches 62.25 on Full Support at 2,048 tokens, so, in the authors' words, "more than one third of multi-fact queries still lack complete support".

Source: the same work, results on the graph-conditioned residual, [arxiv.org/abs/2609.25913v1](https://arxiv.org/abs/2609.25913v1).

## Does complete evidence give better answers

On a prespecified group of 315 linked and multi-fact queries, a judge that never saw the method scored strict answer accuracy at 71.75% with flat windows, 75.56% with provenance units and 77.78% with the graph variant. With the exact evidence supplied the figure is 86.35%; with no evidence, 1.27%.

The difference between the graph variant and flat windows is 6.03 points with a 95% interval of 0.00 to 12.10. The authors call this "borderline evidence" and describe the link between support and accuracy as "mechanistic consistency rather than causal identification".

Source: the same work, downstream answer study, [arxiv.org/abs/2609.25913v1](https://arxiv.org/abs/2609.25913v1).

## Limits the authors state

The queries were written by a language model from selected source packets. A human validator reviewed model judgments on 500 of them and did not re-annotate them blind; after correction, gold evidence is accurate for 96.0% and complete for 96.2%, and the human query type agrees with the authored one for 77.8%, so the three type labels are noisy. The graph is compiled from observable call and return structure, and the authors say a link in it "does not demonstrate semantic causality". They do not present the dataset as a community benchmark until a reviewed release is frozen, and they warn that exact-history retrieval can expose sensitive material without access control and redaction.

Source: the same work, limitations and ethical considerations, [arxiv.org/abs/2609.25913v1](https://arxiv.org/abs/2609.25913v1).

## What we take from it

We did not reproduce any of these numbers, and nothing in Knowledge Contract changed because of this study.

Two points are relevant to our work on reusing knowledge with its source kept. First, the measure: counting whether all required evidence arrived, not whether some relevant fragment did, matches how a bound claim has to be checked. Second, the order of effects: the shape of the evidence unit mattered several times more than the graph step, and in this evaluation the measured gains of the graph were concentrated on evidence spread over several events.

Our assessment keeps the paper as a reference and proposes one bounded trial: on 40 to 100 preselected synthetic traces, compare source-aligned evidence units with fixed windows under the same corpus, the same access and the same 2,048-token cap, and score exact-span completeness and independently checked answer accuracy. A graph runtime stays on hold until a cost-matched baseline supports it. The state is proposed; no owner has accepted it.

Source: Yiqi Wang, Jinqian Ju, Jiaqi Zhang, Zequn Sun, Yiqun Duan, Mingkai Zheng, Taotao Cai, "When Does Execution Provenance Help Agent Memory Retrieval?", arXiv:2609.25913v1, [arxiv.org/abs/2609.25913v1](https://arxiv.org/abs/2609.25913v1).
