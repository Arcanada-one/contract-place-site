---
site: contract.place
section: journal
slug: dora-gaps-agents-2026-11-14
date: 2026-11-14
lang: en
title: "Thirty-five gaps: a legal analysis maps DORA onto AI services, and three of them concern agents"
excerpt: "Five authors project the EU Digital Operational Resilience Act onto AI services in finance and record 35 places where, in their reading, the rules give no criterion. Three concern agents: review by an agent in the same environment, an agent's own report, and an agent testing the system it runs. It is the authors' analysis, not a measurement, and we read only part of it."
---

**Editorial correction, 16 November 2026.** Following Yurii Chudinov’s clarification, we have revised the summary below. The statement about DORA and ICT resilience did appear in section 1 of the source; our summary did not convey the conclusion in sections 14–15: apply the existing framework to AI while accounting for the identified gaps. We have also corrected the date-of-application wording and narrowed the AI Act classification claim. The original publication date is retained.

What does a resilience law written for IT systems say when the system is an AI service? A work published on 1 November 2026 answers for one law, the EU Digital Operational Resilience Act (DORA, Regulation (EU) 2022/2554), and one sector, finance. Its answer is a list of 35 gaps, each derived by the same five steps. For the original review published on 14 November, we read the summary, the method, the closing sections and three of the gap chains. At that point we had not checked its quotations of the law against the official texts. The additional reading and limited legal checks for this correction are described below.

## What the work claims

The authors examine how existing DORA requirements can be applied to AI services used by financial entities within the Regulation’s scope, without amending its provisions. Their method maps the requirements to the components of an AI service and accounts for the identified gaps when choosing criteria, controls and evidence. Chudinov’s clarification of 16 November makes the central point explicit: apply DORA to AI while accounting for these gaps, rather than amend the Regulation first.

Sections 14–15 propose four connected layers: the existing DORA framework, AI-specific controls, other regulatory requirements where applicable, and a single evidence trail. The AI controls are embedded in existing inventory, change management, incident handling, testing and supplier processes. This is the authors’ proposed way to address the gaps; the list does not, by itself, establish compliance or correct AI decisions. DORA has applied since 17 January 2025. Article 64 distinguishes that date from its entry into force.

The object they analyse is not the model. It is the AI service: the model together with what surrounds it in operation, such as data, prompts and guardrails, retrieval, the agent layer, providers, human oversight and fallback.

Across eight layers of DORA they record 35 gaps: 2 in governance, 6 in inventory and change, 4 in detection and continuity, 5 in incidents, 10 in testing, 5 in providers, 2 in oversight and 1 in information sharing. The counts are ours, taken from the table in section 2.3.

In sections 13.4–13.5, the authors compare DORA with the EU AI Act, including creditworthiness assessment and life and health insurance. They interpret the rules for financial entities as connecting monitoring with governance under financial law and, through it, DORA. This is their reading of the relationship between the frameworks, not an exhaustive classification. Article 6 and Annex III of the AI Act require a system-specific assessment: recruitment and workers’ management are also listed uses, including when such systems are used by a financial organisation. Calling a system a chatbot, an internal assistant or a development agent does not, by itself, establish that its intended use is outside the high-risk categories.

Source: Yurii Chudinov, Volodymyr Tkach, Albina Dermenzhy, Dmytro Aksenov, Serhii Vatylyk, "Resilient Systems, Unverified Decisions: A Layer-by-Layer Projection of DORA onto AI Services in the EU Financial Sector", Zenodo, 1 November 2026, [doi.org/10.5281/zenodo.23857406](https://doi.org/10.5281/zenodo.23857406). For the regulatory scope, definitions and application date: [DORA, Articles 1–3 and 64](https://eur-lex.europa.eu/eli/reg/2022/2554/oj?uri=CELEX%3A32022R2554). For classification: [AI Act, Article 6 and Annex III](https://eur-lex.europa.eu/eli/reg/2024/1689).

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

At the original publication on 14 November, we had made no engineering changes because of this work. For that article we checked our own review records of 13 and 14 November, not every record we keep. In those records, a review of one agent's work by another agent is written as "a review by a non-author", and its independence is marked as not verified. In the same records, claims about a change are checked against the change itself, not against a report about it.

One thing those records do not establish is independence. The agents described there worked under one account and with models of one family. As recorded on 14 November, separation of their context, credentials and resources in the sense G-30 uses had not been verified, and no task for it had been identified. The recorded state was on hold; this editorial correction does not establish a new engineering result.

Limits. This is a legal analysis by its authors, published on Zenodo; we saw no sign of peer review in the parts we read. It is not a measurement and not a regulator’s position. The original review covered sections 1, 2, 3, 12 to 15 and the three chains. On 16 November we returned to the original Markdown, checked sections 1–2, 3.2 and 13.4–15, and read findings F-02 through F-07 in the findings registry. That registry labels F-02 as a projection of a norm, F-03 as a finding from projection and F-05 as a conceptual proposal. The other 32 chains and the incident sources remain unchecked. For the correction, we checked relevant official EUR-Lex passages on DORA’s scope, definitions and application date and on AI Act classification; we did not audit every legal quotation or every file in the research record.

Source: the same work, [doi.org/10.5281/zenodo.23857406](https://doi.org/10.5281/zenodo.23857406).

## Further reading: update of 16 November

At the original publication on 14 November, we had seen only the metadata for the following two records and had opened none of their files. On 16 November we opened the primary PDFs. For GPT Deprivation we read the methods, findings and limitations; for Tech Diplomacy we read the full explanatory note and its appendices.

The Zenodo record for "GPT Deprivation: How the Wrong Point on the Ontology and Expectations Scale Leads to Losses from Generative AI. A Multiple-Case Study, 2023–2026" credits Albina Dermenzhy as editor. The work examines how trust earned on familiar tasks can carry over to a new domain without the corresponding competence or verification. It reconstructs publicly documented incidents and lawsuits; this is not an experiment or an estimate of how often harm occurs among users. Its practical proposal is to bound trust for the particular task and verify an output before a consequential irreversible action. The effectiveness of those safeguards is not measured by this corpus. Source: sections 3, 5.9, 7 and 8, [doi.org/10.5281/zenodo.23599162](https://doi.org/10.5281/zenodo.23599162).

Albina Dermenzhy’s "Tech Diplomacy: A Framework for Interaction Between Probabilistic Systems, Humans, and Other Systems" proposes ongoing coordination between people and AI services: clarify intent, turn it into criteria, bound authority, preserve state and evidence, challenge or escalate a result, check behaviour, coordinate suppliers and remedy consequences. Section 4 retains the four-layer DORA composition. Section 7 explicitly says the framework has not been tested through deployments; it is a proposal, not demonstrated effectiveness. Source: sections 4, 6 and 7, [doi.org/10.5281/zenodo.24172092](https://doi.org/10.5281/zenodo.24172092). Our [follow-up on tech diplomacy and knowledge contracts](/en/journal/tech-diplomacy-agent-contracts-2026-11-16/) separates the authors’ claims from the hypotheses we plan to test.

An article by Chuck Brooks of 24 October 2026 names the first author of the DORA work as co-founder of Compilence, which plans a hospital programme in Japan. In the metadata, descriptions and file names checked for the original 14 November review, none of the three records above mentioned that programme. That historical check did not establish that the research had been deployed in a hospital. [bizcatalyst360.com](https://www.bizcatalyst360.com/in-2018-i-predicted-robots-would-learn-to-operate-that-future-is-taking-shape/).
