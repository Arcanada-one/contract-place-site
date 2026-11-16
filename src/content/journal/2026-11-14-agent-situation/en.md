---
site: contract.place
section: journal
slug: agent-situation-2026-11-14
date: 2026-11-14
lang: en
title: "Agent Situation: keeping a bounded view current"
excerpt: "A new research draft examines how an agent establishes its situation, responds to change and selects context for a task. The programme separates finite controls, a planned language-model trial and eventual runtime use."
---

An agent returns to a conversation with a detailed account of yesterday's work. The active account, repository revision or outcome of a pending operation may already have changed. How should it establish what is current, what remains uncertain and what matters to its next step?

Agent Situation: Initialization, Change, and Bounded Context develops this question as a research draft within Knowledge Contract's existing Agent Application programme. This article is an editorial introduction; scientific acceptance and full-text translation review remain separate work.

## Begin with a partial situation

The draft proposes an initial inventory of the task, operating scope, relevant participants, available tools, ongoing operations, constraints, uncertainties and resources. Each operation selects the fields it needs. Repository maintenance may require a branch revision and build status; a physical agent may require a local reference frame and sensor observations.

Missing information stays explicit. A saved description does not establish today's account or permissions. Initialization has a bounded deadline and can support a limited response while leaving other operations unresolved. Source: [research draft and engineering design](https://github.com/Arcanada-one/knowledge-contract/pull/105).

## Follow relevant changes

The proposed lifecycle connects observations to the conclusions and plans that depend on them. A changed prerequisite invalidates the affected view. A later message can contain older information, and receiving an observation again does not make it newer.

Acquisition, state updates, context selection and model calls have separate schedules. Relevant events can trigger a focused update; expiry rules provide a backstop. Conflicting observations retain their sources and scope. An uncertain external outcome calls for reconciliation before a repeated action. Source: [change and refresh proposal](https://github.com/Arcanada-one/knowledge-contract/pull/105).

## Preserve the conditions needed for a decision

A model receives a selected view under a resource budget. The proposal retains declared mandatory dependencies, relevant uncertainty and an account of omissions. If required material cannot fit, the system exposes that limit and considers a smaller task or another representation.

This extends the existing Context Package vocabulary. Including a condition still leaves a further question: did the agent use it correctly? Source: [bounded-context argument](https://github.com/Arcanada-one/knowledge-contract/pull/105).

## Test the proposal in separate stages

The reading record now covers 21 selected primary sources across situation awareness, context-aware systems, robotics and agent memory. Two close architectural predecessors have been added: [CoALA](https://arxiv.org/html/2309.02427v3) describes persistent working memory and selected inputs for each model call; [CoDRA](https://doi.org/10.3389/frobt.2026.1847701) separates context observers from robot execution. The review remains targeted. Recent preprints retain their status; Scroll contributes an abstract-level comparison, and mutable ROS documentation has recorded access dates.

The companion Context Controls study reports 21 of 21 authored finite checks passing, with all three selected disabled-guard variants detected. The initial 18 checks missed a delayed-derivation defect; review exposed it, and the correction added three controls. These are local state-model checks, with no LLM calls or real authorization mechanism. The review used agents under the same controller; external independence is not established.

A continuation review found a separate defect in the test runner: omitting one registered check let it execute only 20 of the 21 expected cases and still report success. The repair passed nine separate checks of registration completeness and result accounting. These nine checks have their own scope and count, alongside the 21 model checks and three disabled-guard variants. The state model and literal expected outcomes are unchanged, and the historical evidence is preserved.

A separate, unexecuted LLM protocol proposes comparison with a strong deterministic state manager under matched resources, measuring valid task completion, stale-value use, unnecessary refusal and total cost. Conditions 4 and 5 share the same frozen projector, optional ranking, guards and budgets; only the optional acquisition and refresh schedule changes. This comparison is designed to isolate selective refresh, while a separate benefit from projection would need its own comparison. The allocation remains 450 proposed episode-runs; none of those LLM runs have been executed. No performance gain or cost saving is reported.

Further review and a bounded pilot remain planned. The results may support a simpler deterministic design. Source: [literature, finite-study scope and experiment plan](https://github.com/Arcanada-one/knowledge-contract/pull/105).
