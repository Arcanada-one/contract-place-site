---
site: contract.place
section: journal
slug: logic-consistency-agentware-2026-11-25
date: 2026-11-25
lang: en
title: "Passing tests, contradicting rules: a two-scenario pilot on logic consistency"
excerpt: "A vision paper argues that, with no specification to check code against, a development workflow can still be checked for contradicting itself. Its pilot is two scenarios, each run once and analysed by hand by the authors. We reproduced nothing."
---

A vision paper argues that when no specification exists to check generated code against, one can still ask whether a development workflow contradicts itself. Its evidence is two scenarios, each generated once with one model and analysed by hand by the authors. In both, every generated test passed, while the authors found a contradiction in one scenario and an unverified assumption in the other. The paper is by Xue Qin and Maurício Gruppi (arXiv 2611.27829v1). This is preliminary simulation by the authors. We ran, reproduced and measured nothing.

## What the paper holds fixed, what it varies, what it is about

Held fixed: one model, GPT-5.2, started from a clear history and memory and wrote all the code (in the wallet scenario the agent kept the turn 1 code and prompts for turn 2). Each scenario was executed once per workflow configuration. The tests came from the same model in a separate chat session, given the task prompt and the generated code. The analysis was done by hand.

Varied: the workflow. In the parallel one, two independent instances implement related features from prompts that are not synchronised, in a hospital door-control system. In the sequential one, a single agent extends a wallet class over two turns. The paper pairs each workflow with a different application domain (Section 2.2), so the two scenarios cannot tell the effect of one from the other. This is our inference; the paper does not discuss it.

The claim is about a workflow's internal consistency: whether prompts, code and tests agree with each other. It is not about whether the code is true or correct, and the authors say they set that question aside because no ground truth exists. The paper states that its aim is feasibility, not the frequency of inconsistencies, and that evaluating a model normally needs several runs.

Source: Xue Qin, Maurício Gruppi, "From Correctness to Consistency: Redefining Reliability for the Agentware Era", Sections 1, 2.2 and 3.1, [arxiv.org/abs/2611.27829v1](https://arxiv.org/abs/2611.27829v1).

## Two agents, each right alone

One agent was told that on "Code Red" the door state must fail open. The other was told that on "Biohazard" the door state must be locked. Each did so, and each treated its own condition as overriding the door state. The authors' table shows that when both alerts are active, the shared door state is forced open by one agent and forced locked by the other. They call this a contradiction that local correctness masks.

Each agent's suite had 7 tests, all passing. Coverage was 94.4% for the first agent and 95.8% for the second. The paper says coverage is structural (for example statement or branch) and does not name the exact kind. One test asserts that the door is open under Code Red, the other that it is locked under Biohazard, so each suite confirms the rule its own code assumed.

Source: Xue Qin, Maurício Gruppi, "From Correctness to Consistency: Redefining Reliability for the Agentware Era", Sections 2.2.1, 3.2 and 3.4, Tables 1 and 3, [arxiv.org/abs/2611.27829v1](https://arxiv.org/abs/2611.27829v1).

## One agent, two turns

In turn 1 the agent was asked for a wallet in which users withdraw instantly while the balance is positive. In turn 2 it was asked to add password changes, where a change locks the account for 24 hours, and a status check.

The turn 2 withdrawal check stayed logically identical to turn 1 (the balance test is unchanged), while the method's docstring and a note in the password-change method call the resulting behaviour, withdrawals allowed while locked, a "platform rule" that the prompt never stated. The authors classify this as an unverified assumption about how two requirements interact, not as a coding error. They add that the opposite choice, blocking withdrawals while locked, would need the same verification.

The turn 1 suite had 5 tests and the turn 2 suite 12, all passing. Coverage was 100% and 98.2%. One turn 2 test asserts that a withdrawal of 5 still succeeds in a locked account, so it checks the assumed rule, not a requirement.

Source: Xue Qin, Maurício Gruppi, "From Correctness to Consistency: Redefining Reliability for the Agentware Era", Sections 2.2.2, 3.3 and 3.4, Tables 2 and 3, [arxiv.org/abs/2611.27829v1](https://arxiv.org/abs/2611.27829v1).

## What is shown and what is only argued

Shown, in these two single runs: generated tests passed in full while there was a contradiction in the door scenario and an unverified interaction assumption in the wallet scenario, both found by the authors' manual reading. They label the relation between statements as entailment, contradiction or neutral.

Argued only: that logic consistency is a measurable proxy for reliability, and that the method can be automated. The paper describes three steps (extract premises, form pairs of artifacts, classify each pair) and proposes automating all three in future work. It built none of this. It reports no comparison with another checking method, no error rate and no repeated runs.

Source: Xue Qin, Maurício Gruppi, "From Correctness to Consistency: Redefining Reliability for the Agentware Era", Sections 2.3, 3.1, 4 and 6, [arxiv.org/abs/2611.27829v1](https://arxiv.org/abs/2611.27829v1).

## Where we stand

Our knowledge contracts are written rules with a local check of each contract on its own; whether any check of ours detects a contradiction between two contracts is not measured, and neither is runtime enforcement. We propose a consistency check across declared rules as a candidate, judged by whether it catches a contradiction we plant on purpose. The proposal is not adopted, nothing has been reproduced, and the work is on hold until an owner and a work item exist. The description of our contracts and the proposal are ours.

Source: the idea of a cross-artifact consistency check is from Xue Qin, Maurício Gruppi, "From Correctness to Consistency: Redefining Reliability for the Agentware Era", Sections 2.3 and 4, [arxiv.org/abs/2611.27829v1](https://arxiv.org/abs/2611.27829v1).
