---
site: contract.place
section: journal
slug: rule-after-restart-2026-11-15
date: 2026-11-15
lang: en
title: "A rule after restart: from a repository snapshot to a local calculation"
excerpt: "A new offline consumer connects the repository session to Source Rule Checks. Before each new evaluation request it observes the committed inputs again; changed context requires an explicit resume. The candidate prepares a laboratory workflow without connecting the public lab or calling a language model."
---

A program can calculate a rule correctly and still use the wrong revision of it. After a pause, a source file may have changed while the agent remembers its earlier reading. The next engineering step in Knowledge Contract addresses that boundary: which exact source and interpretation packet may a local calculation use now?

The cited revision is the candidate in open PR 119; the observations below come from local execution.

## One calculation, one observed context

The candidate joins two existing components: the repository session, which records and adopts a bounded context, and Semantic Bridge, which evaluates explicitly supplied rules and alternative readings. Its complete file profile contains two committed inputs: the rule source and its interpretation packet. Both are required.

Starting a ready session adopts a context; it does not yet evaluate the rule. Each new "EVALUATE" request first makes a fresh repository observation. If the adopted context is no longer usable, the calculation is blocked. An explicit resume can adopt the newly observed context, after which a new evaluation checks it again. The bridge receives the exact bytes retained in that observation, rather than reopening the working-tree files after the check.

Source: the candidate implementation, [repository_rule_consumer.py](https://github.com/Arcanada-one/knowledge-contract/blob/872ba95da3703e3a11ee70a3bc1c38419ce3660a/tools/repository_rule_consumer.py), and the [source change](https://github.com/Arcanada-one/knowledge-contract/pull/119).

## What the local run actually checked

The completed local run matched the predeclared outcome at all 12 steps: 11 fresh consumer captures and one historical inspection. This was one authored sequence in a real local Git repository, not 12 independent trials. An unknown rule outcome remained undetermined; changing the interpretation packet blocked evaluation until an explicit resume; an unrelated commit preserved the accepted context. After an unsupported rule source was adopted, the bridge returned "UNSUPPORTED", with no truth result. Uncommitted decoy edits did not replace the captured committed inputs.

The first run stopped at step two because its authored example packet lacked required observation fields. The program refused that input. The example was corrected, and the failed run was retained alongside the completed run; it was not replaced by a success report.

A separate input review found that the capture-count limit was checked only after replaying the supplied history. The correction moves that guard before hashing and replay. Its synthetic boundary controls check early refusal of an oversized history; they are separate from the twelve-step lifecycle.

The retained result binds the input identities, repository observation, adopted context and calculation in one receipt. Inspecting a saved receipt recomputes the recorded result from its retained bytes, without making a new Git observation. It checks internal consistency and reports a historical result; it does not claim that the repository still has those contents.

Source: [the actual lifecycle receipt](https://github.com/Arcanada-one/knowledge-contract/blob/872ba95da3703e3a11ee70a3bc1c38419ce3660a/reviews/repository-rule-consumer-20261115/lab-run/RUN.json) and [the non-author review](https://github.com/Arcanada-one/knowledge-contract/blob/872ba95da3703e3a11ee70a3bc1c38419ce3660a/reviews/repository-rule-consumer-20261115/non-author/REVIEW.md).

## What this does not settle

The observation covers committed files at the recorded capture. It does not cover arbitrary uncommitted edits, the meaning of unrestricted prose, every dependency of a real task or changes after the capture. The receipt chain is not an authenticated signature or a guarantee of complete history. A successful calculation grants no permission to act.

The controlled rule grammar, manual interpretation packet and unknown observations keep their existing boundaries. No language-model call is needed for this local workflow. Review carried out by another task on the same controller, model family and host is internal non-author review, not external independence.

Source: [the consumer's declared scope](https://github.com/Arcanada-one/knowledge-contract/blob/872ba95da3703e3a11ee70a3bc1c38419ce3660a/tools/repository_rule_consumer.py) and the [Semantic Bridge specification](https://github.com/Arcanada-one/knowledge-contract/blob/872ba95da3703e3a11ee70a3bc1c38419ce3660a/engineering/specifications/semantic-bridge/SPECIFICATION.md).

## A preparation step for the laboratory

This is an offline engineering step. The public Knowledge Journey page still reports that it is unconnected, with upload and start controls disabled. Its existing observation and retained-file components are delivered as assets; that alone does not connect a producer, establish access to a private object or start a run.

The next laboratory integration can consume the same bounded receipts and distinguish an observed calculation from a historical one. A live browser connection still needs its own source binding, permitted read path, session lifecycle and actual browser acceptance. This journal entry records source work; it does not advance the published corpus pin or announce a production connection.

Source: [Knowledge Journey](https://contract.place/en/lab/knowledge-journey/) and its [existing reader boundary](https://github.com/Arcanada-one/contract-place-site/blob/050a4fef55f59f03a6e456e8e27c2bfd02d0a37d/docs/retained-object-reader.md).
