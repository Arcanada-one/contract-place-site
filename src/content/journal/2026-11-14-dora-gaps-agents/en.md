---
site: contract.place
section: journal
slug: dora-gaps-agents-2026-11-14
date: 2026-11-14
lang: en
title: "Thirty-five gaps: a legal analysis maps DORA onto AI services, and three of them concern agents"
excerpt: "Five authors project the EU Digital Operational Resilience Act onto AI services in finance and record 35 places where, in their reading, the rules give no criterion. Three concern agents: review by an agent in the same environment, an agent's own report, and an agent testing the system it runs. It is the authors' analysis, not a measurement, and we read only part of it."
---

What does a resilience law written for IT systems say when the system is an AI service? A work published on 1 November 2026 answers for one law, the EU Digital Operational Resilience Act (DORA, Regulation (EU) 2022/2554), and one sector, finance. Its answer is a list of 35 gaps, each derived by the same five steps. We read the summary, the method, the closing sections and three of the gap chains. We did not check its quotations of the law against the official texts.

## What the work claims

The authors state that DORA applies to AI services without any dedicated provision, because the parts of an AI service are ICT assets and services. They note that it has been in force since 17 January 2025, and that it "regulates only ICT resilience; the correctness of AI services' decisions is not part of its subject matter".

The object they analyse is not the model. It is the AI service: the model together with what surrounds it in operation, such as data, prompts and guardrails, retrieval, the agent layer, providers, human oversight and fallback.

Across eight layers of DORA they record 35 gaps: 2 in governance, 6 in inventory and change, 4 in detection and continuity, 5 in incidents, 10 in testing, 5 in providers, 2 in oversight and 1 in information sharing. The counts are ours, taken from the table in section 2.3.

They also read the EU AI Act next to DORA. What follows is the authors' own reading in sections 13.4 and 13.5, not an official classification and not a complete one; we did not check it against the Act. In their reading, the AI Act treats as high-risk in finance only the evaluation of a person's creditworthiness and risk assessment and pricing in life and health insurance, and chatbots, internal assistants and development agents are not high-risk. For a financial entity that does use a high-risk system, they read the AI Act as counting monitoring as fulfilled through the governance rules of financial law, which rest on DORA.

Source: Yurii Chudinov, Volodymyr Tkach, Albina Dermenzhy, Dmytro Aksenov, Serhii Vatylyk, "Resilient Systems, Unverified Decisions: A Layer-by-Layer Projection of DORA onto AI Services in the EU Financial Sector", Zenodo, 1 November 2026, [doi.org/10.5281/zenodo.23857406](https://doi.org/10.5281/zenodo.23857406).

## How a gap is derived

A gap is recorded only when five steps hold. One: DORA or its technical standards contain a norm that applies, shown by a verbatim quotation. Two: the norm is projected onto a specific element of the AI service. Three: a property of AI creates a failure mode the norm does not account for. Four: the norm gives no criterion, threshold or evidence for that case. Five: the consequence needs another layer of control.

The work says which steps are whose. Step one rests on a quotation. Steps two and five are marked "author's projection". If a step fails, no gap is recorded. Its example: prompt injection is specific to AI, but a data leak through it already meets the definition of an ICT-related incident, so step four fails and there is no gap.

It also limits what the word means: a gap "does not mean an automatic violation of DORA, nor does it mean an absence of regulation altogether".

This is the part closest to our subject: every conclusion says what kind of support it has, so a quoted norm and the authors' reading of it can be told apart.

Source: the same work, section 3.2, [doi.org/10.5281/zenodo.23857406](https://doi.org/10.5281/zenodo.23857406).

## Three gaps about agents

We read three chains in full.

G-30. DORA's standards require that whoever approves a change is independent of whoever requests and implements it. The authors argue that changes made by AI outgrow what a person can read, so review passes to another AI, often in the same environment with shared context. The norm does not say whether such a reviewer is independent. Their remedy is to separate the reviewer's context, credentials and resources from the executor's, and to check the reviewer's conclusions against an action log.

G-31. DORA requires mechanisms to detect anomalous activity. The norm does not separate an executor's own report from evidence of its actions. For an agent, the authors write, the final answer is model output like any other and "may be incomplete or false". Detection should rely on action logs that the agent cannot modify.

G-35. DORA requires tests by independent parties. The norm is written for people and organisations and does not say whether an agent that operates a system is a party to testing it. The authors' consequence: such an agent is not admitted to testing that system.

We did not open the incident registry that the chains cite.

Source: the same work, sections 5.6, 6.6 and 8.6, [doi.org/10.5281/zenodo.23857406](https://doi.org/10.5281/zenodo.23857406).

## What this changes for us, and what waits

We changed nothing because of this work. For this article we checked our own review records of 13 and 14 November, not every record we keep. In those records, a review of one agent's work by another agent is written as "a review by a non-author", and its independence is marked as not verified. In the same records, claims about a change are checked against the change itself, not against a report about it.

One thing we cannot claim. The agents in those records work under one account and with models of one family. Whether their context, credentials and resources are separated, in the sense G-30 uses, has not been verified, and we have no task for it. State: on hold.

Limits. This is a legal analysis by its authors, published on Zenodo; we saw no sign of peer review in the parts we read. It is not a measurement and not a regulator's position. We read sections 1, 2, 3, 12 to 15 and the three chains; the other 32 chains, the registries and the other files of the record are unread.

Source: the same work, [doi.org/10.5281/zenodo.23857406](https://doi.org/10.5281/zenodo.23857406).

## Also seen, not read

Two records by one of the authors were found by their metadata only. We opened no file of either. Albina Dermenzhy, "GPT Deprivation: How the Wrong Point on the Ontology and Expectations Scale Leads to Losses from Generative AI. A Multiple-Case Study, 2023–2026", [doi.org/10.5281/zenodo.23599162](https://doi.org/10.5281/zenodo.23599162). Albina Dermenzhy, "Tech Diplomacy: A Framework for Interaction Between Probabilistic Systems, Humans, and Other Systems", [doi.org/10.5281/zenodo.24172092](https://doi.org/10.5281/zenodo.24172092).

An article by Chuck Brooks of 24 October 2026 names the first author of the DORA work as co-founder of Compilence, which plans a hospital programme in Japan. None of the three records above mentions that programme in its metadata, description or file names. [bizcatalyst360.com](https://www.bizcatalyst360.com/in-2018-i-predicted-robots-would-learn-to-operate-that-future-is-taking-shape/).
