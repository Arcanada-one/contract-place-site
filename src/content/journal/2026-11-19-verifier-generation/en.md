---
site: contract.place
section: journal
slug: verifier-generation-2026-11-19
date: 2026-11-19
lang: en
title: "Agent-written verifiers in VerifierBench rejected invalid solutions more reliably than they accepted valid ones"
excerpt: "A new benchmark asks agents to write executable verifiers for 222 tasks and scores them on 4,993 hidden test cases. Across 19 models in one common harness, task-averaged acceptance of valid solutions ranged from 21.1% to 70.2%, while rejection of invalid ones ranged from 79.2% to 96.3%; in the records analysed for nine models, verifiers that rejected every case of their task produced 87.9% to 96.0% of false rejections."
---
In VerifierBench, executable verifiers written by agents were better at rejecting invalid solutions than at accepting valid ones. Scored against reference labels on hidden test cases, across 19 models run in one common harness, the task-averaged rate at which generated verifiers accepted valid solutions ranged from 21.1% to 70.2%, while the rate at which they rejected invalid solutions ranged from 79.2% to 96.3%. Every model accepted less reliably than it rejected. In the records analysed for nine models, verifiers that returned FAIL on every test case of their task produced 87.9% to 96.0% of each model's false rejections.

These findings are about generated verifiers' verdicts on hidden test cases. The numbers are the authors'; we have not run or reproduced anything.

## What the benchmark holds fixed and what it varies

The object under test is a generated verifier: a program an agent writes from the same instruction and environment a solver would receive, which must return PASS or FAIL for any candidate solution. A finding here is about that program's verdict on a candidate, not about whether the task itself was solved.

The authors hold the tasks, the hidden test cases and the reference labels fixed. They vary the model and the harness, the agent framework that runs it. The main comparison runs 19 models in one harness; 17 further configurations bring the total to 36.

VerifierBench has 222 tasks from six open-source agent benchmarks, covering tool-call, state and code tasks, with 4,993 hidden test cases. Of these, 1,566 are labelled PASS: 222 reference solutions and 1,344 valid variants that change presentation, implementation or execution path. The other 3,427 are labelled FAIL: 2,629 ordinary errors and 798 attacks on verification.

Source: Jianing Yin, Ziyi Chen, Hao Wang, Yiyou Sun, Zijian Jin, Dawn Song, Daoan Zhang, "VerifierBench: Benchmarking the Generation of Executable Verifiers for LLM Agents", arXiv:2610.28679v1, 19 October 2026, sections 2.1, 2.2 and 3.1 and Table 1, [arxiv.org/abs/2610.28679v1](https://arxiv.org/abs/2610.28679v1).

## Who decides what is correct

Each test case gets a construction label before any verifier runs. The authors then screen labels and the benchmarks' own source verifiers with a six-check audit they call Verifier4Verifier: replay, repeatability, provenance, input-label consistency, trivial baselines and mutation testing. Its trivial-baseline check requires the suite to expose verifiers that always accept, always reject or accept only the reference solution.

The audit started from 267 tasks and excluded 45 with confirmed source defects. On the 222 retained tasks, replay agreed on every test case, so each construction label equals the reference verifier's decision. Generated verifiers are scored against that reference label. The authors note that this agreement does not certify that every label is semantically correct.

Source: the same work, section 2.3, Appendix B and Limitations, [arxiv.org/abs/2610.28679v1](https://arxiv.org/abs/2610.28679v1).

## How acceptance and rejection are counted

The true positive rate is the share of positive cases that receive PASS, and the true negative rate the share of negative cases that receive FAIL, each computed per task and averaged across tasks. A timeout, crash, missing verifier or malformed output gives no valid decision and stays in the denominator without credit.

The primary score, normalized balanced accuracy, is true positive rate plus true negative rate minus 100, so a verifier that always says FAIL scores 0. Across the 19 models in the common harness it ranged from 10.6 to 62.1.

The gap is mostly active rejection, not silence. Counted over test cases rather than averaged by task, explicit FAIL accounted for 57.1% to 100% of each model's unaccepted positive cases. The authors state that rankings are point estimates without repeated generations or significance tests.

Source: the same work, sections 2.4 and 3.2, Table 2, Appendix G and Limitations, [arxiv.org/abs/2610.28679v1](https://arxiv.org/abs/2610.28679v1).

## Where the false rejections sit

The authors call a verifier all-reject if it returns a valid FAIL on every test case of its task.

The 87.9% to 96.0% figure is the share of each model's false rejections (FAIL on cases the reference label marks PASS) that came from all-reject verifiers. It is computed on an archived export of per-task records for nine of the 19 models, not on final per-task records for all of them. A separate batch for one model under four conditions shows the same pattern: 68 to 75 of the 222 verifiers were all-reject and produced 93.3% to 95.5% of false rejections.

A low rate of accepted attacks did not mean the verifier was good. On state tasks, one model in the common harness accepted 0.0% of attack cases but only 23.0% of positive cases.

Source: the same work, sections 3.2 and 3.4, Appendix F and Appendix H, [arxiv.org/abs/2610.28679v1](https://arxiv.org/abs/2610.28679v1).

## Why self-tests missed it in the inspected cases

Table 4 lists 16 verifiers from 12 tasks, all from one model's trace batch under four conditions, whose rejections the authors attribute after reading code and generation traces. They were selected to explain observed failures, so this shows mechanisms, not prevalence. The attributed checks are ones the task does not require, such as a tool allowlist that omits a permitted read-only query or a keyword list that omits one of the task's items.

For eight of these verifiers, the agent's self-tests used only solutions the faulty check already allowed. For the other eight, no positive self-test ever returned a complete PASS during generation; at evaluation those eight rejected all 72 of their positive judgments.

Source: the same work, sections 4.1 to 4.3 and Table 4, [arxiv.org/abs/2610.28679v1](https://arxiv.org/abs/2610.28679v1).

## What we are doing with it

On 18 November our research desk read this paper and proposed a bounded trial: 12 to 20 synthetic frozen agent traces with independent ground truth, legitimate alternative paths, invalid mutations, and deliberate deny-all and accept-all sentinels. It would compare an existing verifier against a gate balanced on positive and negative cases, at fixed budget and identical evidence, and report true and false positives, true and false negatives and abstentions separately. The proposed rejection rule: any forbidden action accepted, or valid-variant acceptance below a predeclared baseline.

The status is proposed. There is no owner decision, and nothing was run or reproduced. The lesson we take is that a verifier which rejects everything looks safe on negative-only tests, so positive cases and an explicit UNKNOWN are needed.

This continues yesterday's item on whether verifier judgments survive abstraction of agent evidence ([contract.place/en/journal/verification-transport-2026-11-18](https://contract.place/en/journal/verification-transport-2026-11-18/)); we are not opening a separate initiative.

Source: the same work, section 2.4, for the metric definitions the trial would reuse; the trial itself is our proposal, [arxiv.org/abs/2610.28679v1](https://arxiv.org/abs/2610.28679v1).
