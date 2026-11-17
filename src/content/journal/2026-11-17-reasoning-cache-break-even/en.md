---
site: contract.place
section: journal
slug: reasoning-cache-break-even-2026-11-17
date: 2026-11-17
lang: en
title: "Reasoning kept as code: API-based cost estimates and the break-even of reuse"
excerpt: "Five researchers turned a large model's reasoning traces into small programs that execute as ordinary code on a CPU and call a small target model only for language operations. On eight benchmark sets the programs answered about as accurately as the source model and, on problems they already answered correctly, passed at least 90.8% of validated rewordings and re-parameterizations. Using March 2026 retail API rates, the authors estimate construction at the cost of 12 to 84 source calls and break-even at about 13 to 90 invocations of an applicable entry for similar questions; these figures do not measure the cost of a live request stream. We keep the work as a reference and have changed nothing."
---

Reusing a result is cheaper than producing it again only if the result is reused often enough and stays correct when the question changes a little. A study submitted on 6 November 2026 puts numbers on both conditions for one form of reuse: a language model's reasoning, rewritten as a program.

## The method: a trace becomes a program

Peter Belcak, Greg Heinrich, Saurav Muralidharan, Shizhe Diao and Pavlo Molchanov start from the observation that language models solve every problem from scratch, although many solutions apply to a whole class of problems that differ in wording or in some parameters. Their method takes the transcript of a large source model solving one problem and has a builder model rewrite it in five phases: isolate input and expected output, decompose the reasoning into function-sized steps, recognise which parts of the input are parameters, plan the program, and implement it.

The result is a set of Python functions in which a small target model performs only the language operations. Each candidate function is tested against the corresponding fragment of the transcript. The finished entry is tested end to end against both the transcript and the benchmark's reference answer, and then with parameters extracted from the raw question by the small model. At serving time a new question is matched to an entry by embedding similarity; if nothing is similar enough, the question goes to the source model.

Source: Peter Belcak, Greg Heinrich, Saurav Muralidharan, Shizhe Diao, Pavlo Molchanov, "CPU-ARC: Agentic Reasoning Caching for on-CPU Reasoning Reuse", arXiv:2611.09891v1, 6 November 2026, [arxiv.org/abs/2611.09891v1](https://arxiv.org/abs/2611.09891v1).

## Accuracy against the reference and against the source

The evaluation covers six benchmarks in eight sets: competition and school mathematics, graduate science questions and a multidisciplinary set. Source and builder are the same large model; the target was first a small commercial model (Claude Haiku 4.5) and then a 1B-parameter model (Llama 3.2 1B) that the authors fine-tuned. The paper does not say which of the two produced each accuracy figure; the invocation cost is valued at rates for the 1B model.

Two quantities are reported per set. Cache accuracy is the share of benchmark problems for which the program gives the reference answer. Fidelity is the share for which judges find the program's answer equivalent to the source model's answer. Cache accuracy matched or exceeded source accuracy on seven of the eight sets, for example 93.3% against 83.3% on one mathematics set, and trailed on one, 98.0% against 98.5%. The authors attribute the gains to cases where the source reasons correctly and slips in the last steps, while the program executes the same reasoning as deterministic code. Fidelity exceeded 98% on six of eight sets.

One detail matters for reading these figures: construction checks each entry against the reference answer of the very problem it is later scored on.

Source: the same work, sections 2.2.1, 2.2.4 and 3.4 to 3.6, Table 2, [arxiv.org/abs/2611.09891v1](https://arxiv.org/abs/2611.09891v1).

## Does the program survive a changed question

Three tests vary the wording, the parameter values, or both. The pass rates are counted over rewritten problems that a committee of two judges accepted unanimously as faithful, and only for problems the program already answered correctly. Generator and judges are instances of the same model as the source. For changed parameters the expected answer is the generator's own worked solution, since the benchmark's reference no longer applies.

Under these conditions the programs handled at least 90% of rewritten problems in every set and mode; the lowest rate is 90.8%, for combined changes on one mathematics set. Combined changes gave the lowest rate in six of eight sets.

Source: the same work, sections 3.2, 3.4 and 3.6, [arxiv.org/abs/2611.09891v1](https://arxiv.org/abs/2611.09891v1).

## The price of reuse

The cost table reports API-based estimates per problem using March 2026 rates, in three figures: one source call, building the entry, one invocation of the program. An invocation costs $0.0004 to $0.0019, which is 16 to 291 times less than a source call. Building costs 12 to 84 source calls: lowest where the source reasons at length and the computation is simple, highest where the source answers briefly and the entry still needs full construction.

The authors give the break-even themselves: the build cost divided by the saving per call. An entry for the hardest mathematics problems pays for itself after approximately 13 invocations in its neighbourhood of similar questions, an entry for grade-school word problems after approximately 90. The cost of fine-tuning the small target model is not among the three figures. For that model the authors took 20% of the usage examples from the benchmark evaluations, had the source model produce a synthetic set about ten times larger, and fine-tuned on the resulting data; the cost of producing that set is also outside the three figures.

Source: the same work, sections 2.2.4, 3.1, 3.5 and 3.6, [arxiv.org/abs/2611.09891v1](https://arxiv.org/abs/2611.09891v1).

## What the study does not show

The benchmarks are mathematics and science questions with known answers. The authors say they chose them as a proxy for difficulty, not as the intended use, which is software where the same instructions meet varying payloads. The paper reports no rate of matches and fallbacks on a live stream of requests, and merging similar functions into a more general one is, in the authors' words, not addressed.

Source: the same work, sections 3.3 and 4, [arxiv.org/abs/2611.09891v1](https://arxiv.org/abs/2611.09891v1).

## What we take from it

We did not reproduce any of these numbers, and nothing in Knowledge Contract changed because of this study.

Knowledge Contract is about reusing knowledge within a stated scope and with evidence. This paper is useful to us as a worked example of the accounting. It separates three things that are easy to blur: fidelity to the source, agreement with a reference, and survival under a changed question. It also states the price of reuse as a break-even count, not as a ratio per call.

Our assessment keeps the paper as a reference and proposes one rule for our own reuse decisions: compute the break-even with the full fixed cost, including validation and training, and with the share of real requests that the reused artefact completes without falling back. A cheap call to an entry that already exists is not a cheap stream of tasks. The state is proposed; no owner has accepted it, and we are not building such a cache.

Source: Peter Belcak, Greg Heinrich, Saurav Muralidharan, Shizhe Diao, Pavlo Molchanov, "CPU-ARC: Agentic Reasoning Caching for on-CPU Reasoning Reuse", arXiv:2611.09891v1, [arxiv.org/abs/2611.09891v1](https://arxiv.org/abs/2611.09891v1).
