---
site: contract.place
section: journal
slug: memory-substrates-held-out-evaluation-2026-11-26
date: 2026-11-26
lang: en
title: "A memory router's gain on one benchmark is not significant on conversations it never saw"
excerpt: "A controlled comparison of 11 agent memory methods also tests a router that picks one method per question. On one benchmark with one backbone, its gain over the best single method is significant under random question folds, and it shrinks and loses significance when the held-out questions come from conversations it never saw. We reproduced nothing."
---

A study of agent memory compares 11 memory methods under one shared harness and finds that no single storage medium wins in every setting. In an appendix it also tests a router that picks one method per question. On one benchmark and one backbone, the router beats the best single method when questions are split into folds at random, but when every held-out question comes from a conversation the router has never seen, the gain shrinks under grouped folds and falls to a non-significant 0.001 under leave-one-conversation-out. The paper is arXiv 2608.15008v2 (revised 4 November 2026). We ran, reproduced and measured nothing.

## What the paper holds fixed, what it varies, what it is about

The authors call the medium in which memory is represented and stored a memory substrate. The main comparison holds the harness, the backbone, the prompting and the auxiliary model fixed, and varies only the substrate. It covers 11 methods in seven families, three backbones and four benchmark suites: two of question answering over long dialogue histories, and two of agent tasks (embodied planning and code).

Across operating regimes, the best substrate changes with the task. By the judge score P4, a dual-level graph leads question answering on LoCoMo and LME-S on all three backbones, while on the other dialogue capabilities the leader changes with the capability and the backbone; on Qwen3-32B-AWQ a memory that distils trajectories into strategies leads embodied planning. In a retrieval-depth sweep, run on LoCoMo with Qwen3-8B and on ALFWorld with Qwen3-32B-AWQ, retrieving more entries helps question answering and hurts sequential decisions.

Source: Wei-Chieh Huang, Weizhi Zhang, Yuchen Wu, Yankai Chen, Eric Hanchen Jiang, Wooseong Yang, Yiwei Yang, Henry Peng Zou, Hanrong Zhang, Ying Nian Wu, Haolun Wu, Kai-Wei Chang, Philip S. Yu, Xue Liu, Aylin Caliskan, "Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents", Abstract, Sections 1 to 4 and 5.2, Tables 1 and 2, [arxiv.org/abs/2608.15008v2](https://arxiv.org/abs/2608.15008v2).

## Random question folds against new conversations

The split result concerns a different object: a router, a selection policy placed in front of a pool of substrates, not a new memory mechanism. It is scored by the accuracy of the routed system against the single best fixed substrate on the same held-out questions. Everything runs on one benchmark, LoCoMo, with one backbone, Qwen3-8B. LoCoMo has ten multi-session conversations and 1,986 questions.

Accuracy here is the paper's LLM-judge score: the fraction of answers that GPT-4o-mini labelled CORRECT, given the question, the gold answer and the model's answer. The comparison uses an exact McNemar test on paired per-question outcomes.

Under the reported protocol, a random partition of the 1,986 questions into five folds, the paper tests four routers, and only the per-substrate one (one classifier per substrate, predicting its correctness) clears the fixed baseline by a margin: 0.671 against 0.648 for the best fixed substrate. It is right where the fixed choice is wrong 223 times, against 179 the other way (p=0.032), and it wins all five folds. These folds are not grouped by conversation, so questions from one conversation can sit in both training and held-out folds. The authors repeat the comparison with the same router design, refitted on the new training folds, against the same fixed baseline and judge labels, changing only how the folds are built:

- conversation-grouped, five folds: 0.661 against 0.648, p=0.22, three of five folds won;
- leave-one-conversation-out, ten folds: 0.649 against 0.648, p=0.96, five of ten folds won.

In the authors' words, the gain shrinks under grouped folds and disappears under leave-one-conversation-out, and neither difference is significant. They limit the claim to a deployment that has accumulated outcomes over its own traffic and routes new questions from the same conversations, and they do not claim transfer to unseen conversations. The finding is about this router on this benchmark and backbone, with ten conversations; the paper does not test it elsewhere.

Source: Wei-Chieh Huang, Weizhi Zhang, Yuchen Wu, Yankai Chen, Eric Hanchen Jiang, Wooseong Yang, Yiwei Yang, Henry Peng Zou, Hanrong Zhang, Ying Nian Wu, Haolun Wu, Kai-Wei Chang, Philip S. Yu, Xue Liu, Aylin Caliskan, "Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents", Section 3, Appendix D and Appendix E.3, Tables 12 and 13, [arxiv.org/abs/2608.15008v2](https://arxiv.org/abs/2608.15008v2).

## What else the paper marks as in-sample, and who judged

Picking one substrate per operating regime beats any single fixed substrate on its benchmarks, but the choice is read off the same results, so the authors call it an in-sample comparison rather than a held-out test. For query-level routing on LoCoMo with Qwen3-8B, a per-question oracle that picks a correct substrate whenever one exists, a reference that cannot be observed at inference, would score 0.93 against 0.648 for the best fixed substrate, and the paper says that query-level routing, whose best router reaches 0.671 under random folds, leaves most of this headroom open.

All the dialogue scores above come from one judge model, which is also the auxiliary model that writes memory. The authors re-scored 595 predictions, balanced across the CORRECT and WRONG labels, with four judges. On these items a fresh run of the production judge agreed with its own labels on 95.8%, and the four judges reached a Fleiss kappa of 0.73. All four judges come from one provider, and the authors state that a human or cross-provider check is outside the study.

Source: Wei-Chieh Huang, Weizhi Zhang, Yuchen Wu, Yankai Chen, Eric Hanchen Jiang, Wooseong Yang, Yiwei Yang, Henry Peng Zou, Hanrong Zhang, Ying Nian Wu, Haolun Wu, Kai-Wei Chang, Philip S. Yu, Xue Liu, Aylin Caliskan, "Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents", Abstract, Section 7, Appendices E.2 and E.3, Tables 11 and 12, [arxiv.org/abs/2608.15008v2](https://arxiv.org/abs/2608.15008v2).

## Where we stand

We read the paper. It is a reference for a proposed, design-only evaluation of how our knowledge contracts are reused across projects: evaluate on held-out conversations or projects, grouped so that the same source never appears in both training and evaluation, and not on random question splits. Extending the paper's conversation result to projects is our step; the paper does not discuss projects. How our own memory and search index map onto the paper's memory substrates is not mapped yet. Nothing was run, reproduced or measured by us.

Source: the grouped split protocol is from Wei-Chieh Huang, Weizhi Zhang, Yuchen Wu, Yankai Chen, Eric Hanchen Jiang, Wooseong Yang, Yiwei Yang, Henry Peng Zou, Hanrong Zhang, Ying Nian Wu, Haolun Wu, Kai-Wei Chang, Philip S. Yu, Xue Liu, Aylin Caliskan, "Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents", Appendix E.3, Table 13, [arxiv.org/abs/2608.15008v2](https://arxiv.org/abs/2608.15008v2).
