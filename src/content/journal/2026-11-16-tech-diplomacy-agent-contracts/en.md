---
site: contract.place
section: journal
slug: tech-diplomacy-agent-contracts-2026-11-16
date: 2026-11-16
lang: en
title: "Tech diplomacy: making an agent's knowledge, authority and results inspectable"
excerpt: "Following Yurii Chudinov's recommendation, we read the primary files of GPT Deprivation and Tech Diplomacy, correct our DORA summary and propose a bounded Knowledge Contract experiment. The research proposals, our laboratory design and possible cooperation with TDGI have different evidence and different next steps."
---

An agent can cite the right document and still use it outside its scope. It can finish a task and still lack permission for one of the actions it took. It can describe a successful result that another participant cannot verify. These are distinct problems, and an explanation of agent reliability needs to show how they connect.

On 16 November, Yurii Chudinov recommended a closer reading of two works associated with Albina Dermenzhy and clarified our account of the DORA study. We opened the primary files. This article explains what the works establish, what they propose and what we want to test with Knowledge Contract. It also introduces a separate institutional direction: possible dialogue with the Paris-based Tech Diplomacy Global Institute (TDGI).

## DORA: apply the existing framework and account for the gaps

Our [14 November article](https://contract.place/en/journal/dora-gaps-agents-2026-11-14/) now carries a dated correction. Its earlier statement about ICT resilience came from section 1 of the original work. The summary did not adequately convey the practical conclusion in sections 14–15: use existing DORA mechanisms for AI services within the Regulation's scope, while addressing the identified gaps in criteria, controls and evidence. Chudinov's clarification is that this application does not first require amendments to the provisions.

The authors propose four connected layers: the DORA core, AI/model controls, other applicable requirements, and a common evidence trail. Inventory, change management, incident handling, testing and supplier management remain the operating processes. Their 35 gaps are an analytical result; identifying one does not automatically establish a violation, and their proposed controls do not certify a service. DORA has applied since 17 January 2025; that is its application date, not its entry-into-force date.

Source: Yurii Chudinov, Volodymyr Tkach, Albina Dermenzhy, Dmytro Aksenov and Serhii Vatylyk, *Resilient Systems, Unverified Decisions: A Layer-by-Layer Projection of DORA onto AI Services in the EU Financial Sector*, 1 November 2026, sections 3.2 and 14–15, [DOI 10.5281/zenodo.23857406](https://doi.org/10.5281/zenodo.23857406); [Regulation (EU) 2022/2554, Article 64](https://eur-lex.europa.eu/eli/reg/2022/2554/oj).

## GPT Deprivation: the boundary of trust is task-specific

*GPT Deprivation* investigates how expectations about an AI system can exceed its capabilities in a particular task. One proposed mechanism is the transfer of trust earned on familiar work to a domain where the user lacks the expertise needed to evaluate the answer. The practical recommendation is to define the assignment and limits of trust before work, then verify the output before a consequential irreversible action.

Its evidence needs careful reading. The work combines several distinct corpora, including a sample of 30 court cases and a separate set of 33 lawsuits against vendors. Those are not one independent sample and should not be added together. The lawsuits describe allegations; the paper does not establish all alleged events or causation through judgments on the merits.

Section 5.9 shows how the trust-transfer conclusion depends on the coding rule. The following figures refer to the same 33-lawsuit corpus, not to all AI users:

| Coding condition | Transfer among cases with known values | Unknown cases out of 33 | Reported conclusion |
| --- | --- | --- | --- |
| Evaluation of the new task is not described | 21 of 22 | 11 | Supported under this rule |
| The document explicitly states that no verification occurred | 9 of 10 | 23 | Not established under the study's threshold |
| Isolation from people able to check also qualifies | 18 of 19 | 14 | Supported under this rule |

This does not estimate how often AI causes harm, or measure how much a mandate reduces it. The study was assembled around documented adverse cases. A test of protective measures also needs intercepted errors, false stops and successful ordinary use. For our laboratory, the useful hypothesis is narrower: task-specific applicability checks may prevent inappropriate reuse, and that effect must be measured against a stated comparator.

Source: *GPT Deprivation: How the Wrong Point on the Ontology and Expectations Scale Leads to Losses from Generative AI. A Multiple-Case Study, 2023–2026*, published in Albina Dermenzhy's Zenodo record, v1, 23 October 2026, sections 3, 5.9, 7–8, [DOI 10.5281/zenodo.23599162](https://doi.org/10.5281/zenodo.23599162). The record credits Dermenzhy as Editor. We read pages 1–12, 22–34 and 44–49, with relevant codebook and deviation-log sections; we did not independently recode the cases.

## Tech Diplomacy: a proposal for continuing coordination

Albina Dermenzhy's *Tech Diplomacy* extends the term to interaction between people, probabilistic systems and other systems. Its eight functions cover a shared interaction frame, translation into technical criteria, delegation of authority, shared state and evidence, challenge and escalation, continuing assurance, supplier coordination, and remediation and learning. The framework asks participants to revise their working arrangements when the system, context or consequences change.

The appendices describe nine linked objects, including an Interaction Charter, AI Mandate, Acceptance Profile and Evidence Graph. They favour a connected data model with views for different roles, rather than nine disconnected documents. That is a useful question for an engineering team: can the decision, its authority and its evidence still be followed after a handoff?

The proposal's limits are explicit. It has not been tested through deployments; the sufficiency of a mandate is untested. Treating trust as a current state is a normative position. The metrics appendix leaves calculation methods, data sources and thresholds to later work. Its financial scenario is illustrative. We therefore treat the framework as a source of hypotheses and design requirements to evaluate.

Source: Albina Dermenzhy, *Tech Diplomacy: A Framework for Interaction Between Probabilistic Systems, Humans, and Other Systems*, v1, 12 November 2026, sections 4, 6–7 and appendices A, D–I, [DOI 10.5281/zenodo.24172092](https://doi.org/10.5281/zenodo.24172092). We read the 20-page explanatory note and 11-page appendices. The PDF names Dermenzhy as author; Zenodo classifies the record as a Proposal.

## A proposed mapping to Knowledge Contract

The mapping below is ours. It is not an assertion that the frameworks have identical schemas or that the integration is already implemented. We will first reuse existing entities and owners; a new term alone is not a reason to create another registry.

| Question raised by the framework | What our experiment must make inspectable |
| --- | --- |
| What was agreed for this interaction? | The task, applicable knowledge, constraints and acceptance criteria, with exact versions. |
| Who may act, and within which limits? | A current authorization for the action, checked separately from the relevance of a knowledge artifact. |
| What did the agent actually use? | The source passage, artifact revision and content received at the actual computation boundary. Retrieval alone is insufficient. |
| What happened, and can it be challenged? | An execution record, result check and a route to stop or contest the action, independent of the agent's final narrative. |
| What changed after a failure? | The affected result and reuse links, a reproducible counterexample, a reviewed successor and a later checked application. |

A valid document hash proves identity of bytes. It does not grant access, establish semantic fit, prove that those bytes were used or accept the resulting work. Likewise, changing a model's name does not by itself establish independent verification. The trial must record the relevant controller, evidence and review procedure.

Source: our proposed crosswalk from Dermenzhy's sections 6–7 and appendices A–B to the [Knowledge Contract core specification](https://contract.place/en/engineering/specifications/knowledge-contract-core/) and [API integration appendix](https://contract.place/en/appendices/api-integration/). This is a design proposal, not a new permission or measured implementation result.

## One source, two tasks and a visible reason for every transition

We propose a small experiment with a source whose use is permitted. A passage supplies a rule and its conditions. Task one asks an agent to check a proposed knowledge-package update against that rule. The display should show the selected passage, extracted candidate, review and admission, the resolver's choice, the tool's actual input, the result and its separate acceptance. Missing evidence must remain visible.

Task two checks a distinct knowledge-package update and reuses the accepted artifact. Between controlled runs, we change the source version, revoke an action permission or make a premise incompatible. The expected response is determined in advance: retrieve the new eligible version, refuse an unauthorized effect or replan the affected step. An obsolete artifact must not silently retain its former applicability. A harmless wording change is a separate control, so mere change detection cannot masquerade as understanding.

We will record two outcomes separately: did an unauthorized action occur, and did the intended task meet its acceptance criteria? A refusal may prevent an unsafe effect while leaving the task incomplete. A breakdown is another result. The comparison needs the same tasks, budgets and evidence rules, with unknown values retained. Time, total cost, intercepted mistakes, false stops and successful reuse belong in the result, not just a count of completed runs.

This describes the next test we intend to perform. It does not report a completed protected run or prove that every stage of Live Lab works. Its value will come from the actual evidence that a reader can inspect on both sites.

Source: our experimental proposal, informed by *GPT Deprivation*, sections 7–8, and *Tech Diplomacy*, appendix H; [Knowledge Contract API integration](https://contract.place/en/appendices/api-integration/).

## TDGI: a possible institutional conversation

TDGI's institutional work concerns technology, international relations and governance. Its AI Diplomacy Council addresses cooperation with, about and through AI. That scope differs from Dermenzhy's framework for individual and organizational interaction. Connecting them through an inspectable agent case is our proposal; shared terminology does not establish an institutional relationship.

We are preparing a capability brief and a possible workshop on evidence, agent mandates and reusable knowledge. The Institute's free community offers an initial route to learn about its work. Its Global Assembly is announced for 11 December 2026 in Paris; attendance requires confirmation by its Secretariat. Any contribution to an event or joint programme would need separate agreement. Neither Arcanada nor Knowledge Contract claims TDGI membership, Fellowship, partnership or endorsement in this article.

The further project route worth assessing is Global 5X AI. Its stated requirement is an execution-ready project with measurable public benefit over 100 days, a responsible owner, authority, resources and an operating environment. We would consider that route after a real bounded laboratory result and a suitable beneficiary are established. The Assembly is an opportunity for dialogue; it is not a prerequisite for our engineering work.

Source: TDGI's [AI Diplomacy Council](https://tdgi.org/expert-councils/ai-diplomacy/), [Community](https://tdgi.org/join-us/), [Global Assembly](https://tdgi.org/global-assembly/) and [Global 5X AI](https://tdgi.org/5xai/) pages, checked 16 November 2026. The cooperation and workshop described here are our plans.
