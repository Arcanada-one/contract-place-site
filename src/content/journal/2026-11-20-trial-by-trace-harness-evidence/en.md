---
site: contract.place
section: journal
slug: trial-by-trace-harness-evidence-2026-11-20
date: 2026-11-20
lang: en
title: "Task success is not harness evidence: what Trial by Trace measures"
excerpt: "A benchmark of 3,420 agent runs scores the task outcome and the harness's own obligations separately. In 31.1% of runs the task passed while at least one harness criterion failed."
---
A new benchmark of AI agent harnesses reports that a passed task does not, by itself, show that the harness met its own obligations. Across 3,420 runs (4 harnesses, 9 models, 95 tasks), the authors find that 31.1% of runs met every task criterion while failing at least one harness criterion, and that ranking harnesses by task success gives a different order than ranking them by harness criteria. Every number below is the authors'. We ran, reproduced and measured nothing.

## What the study holds fixed and what it varies

The object under test is the native harness: the software that builds the model's context, exposes tools, carries calls and results, keeps state and enforces permissions. The model, task, environment and budgets are controlled inputs; the evaluator and capture machinery are treated as measurement apparatus, so apparatus failures are not counted as harness defects. The harnesses are Claude Code, Codex, DeepSeek Harness and OpenClaw. Each runs the same 95 tasks with each of 9 model groups, giving 855 matched model and task cells per harness. Tasks cover seven reliability components (context, execution, governance, lifecycle, observability, tools, verification). Each task carries two score sheets: an Agent layer (required actions, deliverables, checked against authoritative state) and a Harness layer (whether the native system delivered information and executed faithfully).

Source: Zhiyong Cao, Hengjie Zhu, Yongxin Wang, Xuchen Li, Jintao Li, Shuxia Liu, Dunqiang Liu, Bo Wang, Kairan Zhang, Cong Lin, JiangDi Yu, Siyuan Liu, Sijia Yao, Yi-Liang Wei, Lingxu Ma, Aijia Wang, Anxin Chen, Zixian Wei, Xiang Ruan, Ruizhi Xu, Ruqian Shi, Baihua Xiao and Sicheng Zhou (TraceLite AI; names in section 9), "Trial by Trace: Benchmarking AI Agent Harnesses for Reliability and Failure Attribution", arXiv:2610.32285v1, Abstract, sections 2.2, 3.1, 3.2.3, 4.1, 4.3, [arxiv.org/abs/2610.32285v1](https://arxiv.org/abs/2610.32285v1).

## Two layers, two rankings

A run counts as task success only if no Agent criterion scored zero. Over all 3,420 runs, 1,351 (39.5%) met that bar, and only 286 (8.4%) passed every criterion in both layers. The 31.1% figure (1,065 runs; abstract, sections 1, 5.5 and 8, Table 10) counts runs with task success and at least one failed Harness criterion, over the same 3,420 runs.

The rankings split. Claude Code had the highest Agent task success (44.0% of its 855 runs); OpenClaw had the highest Harness macro rate (72.0%, the mean of each run's share of passed Harness criteria). Harness macro rates spanned 12.2 points, from Codex at 59.8% to OpenClaw at 72.0%; task success spanned 8.2 points, from Codex at 35.8% to Claude Code at 44.0%.

Who decided: criteria with a task oracle were scored by deterministic verifiers; semantic criteria were scored by one fixed LLM Judge (deepseek-v4-flash), whose output limit was 4,096 tokens in 1,966 evaluations, 8,192 in 1,452 and 32,000 in two.

Source: the same work, Abstract, sections 1, 4.2, 4.3, 5.1, 5.2, 5.5, 8, Tables 6 and 10, [arxiv.org/abs/2610.32285v1](https://arxiv.org/abs/2610.32285v1).

## Which record speaks for what

Evidence authority is specific to the question. Environment or simulator state establishes what happened. Changed artifacts establish the persisted deliverable. The native model-facing record establishes what the model could see. An agent's final messages establish only what the agent asserted. Execution probes owned by the runner record process outcome, timeout and approvals "independent of prose reports".

A tool action can exist in several non-equivalent forms: the apparatus may know a process timed out while the model-facing result omits it, and keeping both is what makes a fidelity criterion possible. Tasks deliberately include nonzero exits paired with success-shaped artifacts. The runner's own result file supplies identity, but its score field is not the final-score authority. The paper does not, however, report a measured rate at which harness or agent claims of completion disagree with end state; only 1 of the 95 tasks sits in the Verification component, defined as consistency of completion claims with authoritative outcomes.

Source: the same work, sections 2.3, 3.1, 3.2.2, 3.3.1, 3.3.2, Table 3, Figure 4, section 4.2, [arxiv.org/abs/2610.32285v1](https://arxiv.org/abs/2610.32285v1).

## What a zero and a link do not prove

Attribution here is between the Harness layer and the Agent layer, not between harness and model. A Harness zero means the criterion was violated or the selected evidence did not establish it; an empty evidence selection also scores zero. A criterion marked "not exercised" is resolved from the Agent outcome, so the two layers are not statistically independent. Results use the raw zero sets, without the bypass adjustment the method defines.

A failure link is activated when a predeclared Harness criterion and Agent criterion both fail and the declared condition matches. The authors state this is a candidate, not causal propagation: validation requires manual review of event order, an observed intermediate distortion and competing explanations. The labels "harness_caused" and "agent_caused" are operational. The paper reports candidate links in 842 of 1,700 runs failing both layers (49.5%) and no count of validated links.

Source: the same work, sections 2.3, 3.4, 3.5, Tables 4 and 5, sections 4.3 and 5.5, Table 10, [arxiv.org/abs/2610.32285v1](https://arxiv.org/abs/2610.32285v1).

## Limits stated by the authors

Each cell holds one selected execution, including replacement runs from earlier recovery, so the authors do not estimate repeatability within a cell. They state that task revisions and recovery runs limit causal reading of differences between harnesses, and that they do not estimate selector recall, Judge agreement or candidate link precision. We checked the full arXiv PDF of v1, including tables and appendices. The authors add that coverage across mechanisms is uneven (section 6.1).

Source: the same work, sections 3.6, 4.1, 4.2, 4.4, 6.1, [arxiv.org/abs/2610.32285v1](https://arxiv.org/abs/2610.32285v1).

## What we proposed, and why we wait

Our research desk read the paper and proposed a trial: score the outcome a harness reports separately from the measured end state. This is inspired by the paper's split of evidence authority, not a copy of its two layers. Status: proposed, with no owner decision; nothing has been run. The arXiv listing gives CC BY-NC-SA 4.0 for the paper text. The paper links a code repository (github.com/TraceLite-AI/TraceTrial-Bench) but states no code licence, so reuse of the authors' code is on hold pending a licence check.

Source: the same work, arXiv listing, title page and section 4.4, [arxiv.org/abs/2610.32285v1](https://arxiv.org/abs/2610.32285v1).
