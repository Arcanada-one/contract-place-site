---
site: contract.place
section: journal
slug: control-for-topic-2026-11-12
date: 2026-11-12
lang: en
title: "Before crediting the context, control for the topic"
excerpt: "A paper shows that a standard test of personalised memory mostly measures topic match. What that means for any claim that selected knowledge helped, and one audit of our own that moved from proposal to the main branch."
---

Knowledge Contract is about what an agent may rely on. A neighbouring question is how anyone shows that the knowledge an agent was given actually helped. One paper this week takes apart a common way of showing it. We also report a change of state in our own work.

## The wrong-user test measures the topic

Karina Romanova, Igor Kiselev, Vladimir Platonov, Viliana Devbunova, Gregory Leleytner, Adeliya Leleytner, Lina Veltman and Aleksandr Nikolich examine a test that is widely used for personalised models. Give the model a user's own history, then replace it with another user's history, and measure how far accuracy drops. The drop is read as proof that the model uses what it knows about this person.

The authors point out that the swap changes two things. The other user wrote about other subjects, so the history stops matching the topic of the question as well as the person. They separate the two on a news categorisation task (LaMP-2) with a frozen language model, using histories of similar users and synthetic histories assembled from other users' articles. The measure throughout is accuracy of the predicted category.

The user's own history improves accuracy by 2.3 percentage points over a model trained without any history. If history is removed only at evaluation, from a model trained with it, the same gain appears as 4.8 points. Category labels alone reproduce 86% of the accuracy gap between the user's own history and a random user's history. When the synthetic history is matched on labels and on text similarity, the gap falls to 0.9 points. Across two user splits and three training seeds, the advantage of the own history over a similar user's history is 3.2 points for users seen in training and 0.65 points for unseen users, and the authors call the evidence for the latter inconclusive.

The limits are theirs: one main task, a small model, and a second experiment on movie tags with a single training seed. Whether the result holds for larger models and other tasks is not shown.

What this means for Knowledge Contract. Replace "the user's history" with "the context selected for this task" and the same trap is open. If an agent does better with selected knowledge than with a random document, part of the gain is that the selected text is about the right subject. That says little about whether the admitted, scoped, evidenced knowledge was the cause. A claim of benefit needs two comparisons the paper names: a control of similar content that is not the selected knowledge, and a baseline that was set up to work without the context, not one that had it taken away at test time.

Our state: on hold. The control design is recorded in our research roadmap as a requirement for any future benefit claim. We have not measured a benefit of context selection, with or without this control, and we have not reproduced the paper. The return condition is a concrete, measurable claim that selection helped.

Source: Karina Romanova, Igor Kiselev, Vladimir Platonov, Viliana Devbunova, Gregory Leleytner, Adeliya Leleytner, Lina Veltman, Aleksandr Nikolich. Not Your Diary, Just Your Topic: Grading the Wrong-User Control. [arXiv:2611.09609v1](https://arxiv.org/abs/2611.09609v1), 6 November 2026.

## The audit of the first premise is now on the main branch

Yesterday we described an audit of one of our propositions as an open proposal. It concerns a chain of transformations: if a property holds at the start and each step preserves it under stated conditions at the joins, it holds at the end. The audit asked what is lost if the starting premise is dropped.

That proposal was merged on 11 November. It is worth being exact about what the merge contains. It adds an audit note, ten finite test cases and a workflow that runs them in continuous integration. One case is a small witness showing that without the starting premise the conclusion can fail. Four two-step cases separate the two conditions at the joins from each other. The merge does not amend the proposition and does not prove it by enumeration; the text of the paper is unchanged. A later increment in the same change tightened the accounting of the tests themselves, so that the workflow checks which cases were actually selected and executed and does not rely on a count of definitions.

We did not re-run the cases for this article; the description follows the merged change itself.

Source: Knowledge Contract, "C03 scientific audit: preserve initial-state premise in chain observation theorem", [knowledge-contract #98](https://github.com/Arcanada-one/knowledge-contract/pull/98), merged 11 November 2026.

## What comes next

The two items meet in one rule. A statement that something holds, or helps, has to name what it was compared with and what was assumed at the start. For the proposition, the starting premise is now guarded by tests. For context selection, the comparison does not exist yet, and until it does we make no claim of benefit.
