---
site: contract.place
section: journal
slug: verdict-is-not-a-test-2026-11-13
date: 2026-11-13
lang: en
title: "A research agent's verdict is not a test of known size"
excerpt: "A study plants the truth in simulated data and scores what language-model research agents conclude. In simulated worlds with nothing to find, built without the repeated-value flaw of the earlier runs, three commercial research agents still claimed a finding in 34%, 16% and 44% of cases. A sentence about earlier research also changed verdicts on identical data."
---

When an agent analyses data and reports that it found something, who decided that the finding is real? Usually the agent itself. A new study measures how often that decision is wrong when the right answer is known in advance. We have not reproduced it. Below is what it shows and why it matters for any rule about reusing a result.

## The truth is planted, so every verdict can be scored

Chang Liu gives each agent a simulated world whose data-generating process the author controls. Most worlds are monthly return series in which one of eight candidate predictors carries a planted signal of chosen strength, or none at all; the other seven are distractors with no predictive power. The agent sees 700 months, writes and runs its own code within a budget of 40 calls, and submits a model with a verdict: the model beats a static benchmark, does not beat it, or the search is abandoned. A further 360 months never enter the agent's sandbox and are used only to evaluate what it submitted.

Because the truth is known by construction, the agent can be treated like any statistical test. Two quantities matter. Size is how often it claims a finding in a world without a signal. Power is how often it detects a signal that is there. The author scores the verdict against the conventional 5% level, although the brief names no level: which threshold the agent applies on its own is one of the things measured.

Source: Chang Liu, "Are LLM Research Agents Reliable Judges of Predictability? Evidence from Planted-Signal Worlds", [arXiv:2611.04070v1](https://arxiv.org/abs/2611.04070v1).

## A finding was reported where there was nothing to find

In the first two studies, three commercial models claimed predictability in 21%, 19% and 63% of the worlds without a signal. An external review then found a flaw in the worlds: resampled shock values repeated exactly, so a lookup of past returns could forecast even an empty world, and the model with the highest rate exploited it. A third study replaced those shocks with Gaussian ones. The rates became 34%, 16% and 44%, and each model still claimed more often than a conventional test run on the same worlds. An open-weight model that runs on one workstation claimed in 35% of the empty worlds, and its rate barely rose when a signal was planted.

The agent of the first study did detect weak signals more often than a conventional out-of-sample test. The author's explanation is that it accepts weaker evidence. Held to the same false-positive rate, a conventional in-sample test with a correction for multiple candidates detected weak signals about as often, and more often than the model with the highest false-claim rate.

The stated confidence added little. In all 3,990 runs of the three commercial models, the agent claimed a finding exactly when its stated probability was at least one half. In the author's words, the implicit rule is a 50% posterior, not a 5% test.

Source: Chang Liu, the same paper, sections 1, 4 to 5 and 7.1, [arXiv:2611.04070v1](https://arxiv.org/abs/2611.04070v1).

## One sentence about prior research moved the verdict

In the first study, 160 worlds were run three times with the same data and one sentence changed at the end of the brief: nothing, a remark that prior research found a signal, or a remark that it found none. The share of worlds in which the agent claimed a finding was 32% under the sceptical sentence, 46% under the neutral brief and 61% under the optimistic one. The verdict differed between framings in 50 of the 160 worlds. In the worlds without a signal, the optimistic sentence raised false claims from 15% to 32%. In the worlds with a signal, the sceptical sentence lowered detection from 56% to 40%.

Source: Chang Liu, the same paper, section 3.3, [arXiv:2611.04070v1](https://arxiv.org/abs/2611.04070v1).

## What the author recommends, and where the evidence stops

The protocol the paper proposes is short: give a neutral brief; let the agent build the model but not issue the verdict; fix the decision rule in advance, outside the agent; keep the holdout technically out of its reach. The author says plainly that the last item is enforced by his harness and was not tested as a factor.

A sealed holdout is not free. In an exploratory analysis of the models the agents submitted in the third study, a holdout test at the 5% level claimed in at most 5% of the empty worlds, but for the three commercial models it detected only 25% to 28% of the worlds whose planted signal explains 1% of the variance, against 54% for the in-sample test. The author therefore treats the holdout as confirmation and an efficient pre-specified test as the primary rule.

The limits are stated in the paper. One agent configuration, one tool set and one brief were studied. The worlds are stylised: one planted predictor among eight. The false-positive rate that anchors the matched comparisons rests on 40 worlds. Two of the models were served under names without dated snapshots. The pre-specifications were recorded in repository commits, not in a public registry, and several of the stronger comparisons were designed after the first results were known.

What this means for our work. Knowledge Contract asks when a result may be relied on by someone who did not produce it. This study gives a measured reason to keep two roles apart: the one who searches and the one who decides, with the deciding rule written down before the search starts. It also shows that a stated probability is not evidence of calibration. We have not run such an experiment ourselves. A comparison on synthetic cases with and without a planted effect, scored by a rule fixed beforehand, has been proposed inside our research intake and is on hold: no owner has accepted it and no work has started.

Source: Chang Liu, the same paper, sections 7.1 and 7.2, [arXiv:2611.04070v1](https://arxiv.org/abs/2611.04070v1).
