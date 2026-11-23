---
site: contract.place
section: journal
slug: rendered-sources-injection-2026-11-21
date: 2026-11-21
lang: en
title: "Rendering an untrusted source as an image changes its channel, not its trust"
excerpt: "Liu et al. find that page images lower prompt injection execution on average, but one model still executes image-borne answer replacement in 77.96% of scored cases, and models often transcribe and identify commands they then do not execute."
---

Rendering an untrusted document as page images lowers how often multimodal models execute commands planted in it, but it does not remove them: Qwen3-VL-8B still had an image attack success rate of 77.96% for answer replacement (a dataset-weighted rate over scored responses). The preprint is by Haoyang Liu, Yinong Xu, Zhe Lang, Zhenyu Guan and Qianyun Zhang. Every number is the authors'; we ran, reproduced and measured nothing.

## What the study holds fixed and what it varies

The object is a question answering model reading one attacker-controlled source that the system prompt declares untrusted. The authors pair a text version and a page-image version of 191 English sources from LongBench, holding the question, evidence and attack wording fixed within each pair. They vary the source modality and the model (six of them) across three attack operations: append a marker, format the answer around a marker, or replace the answer with "You are attacked!". The attack success rate (ASR) is the share of visible responses in which the authors' scoring finds the requested operation executed; truncated responses are marked unknown and excluded, and the three datasets weigh equally.

Source: Haoyang Liu, Yinong Xu, Zhe Lang, Zhenyu Guan, Qianyun Zhang, "What Survives the Shift from Text to Pixels? Conditional Protection against Prompt Injection in Image-Rendered Documents", Sections 3.1 to 3.4, [arxiv.org/abs/2611.24231v1](https://arxiv.org/abs/2611.24231v1).

## Lower on average, not closed

In the main comparison (191 sources, original questions, wrapper W1, commands inline), image ASR for append and format is lower than text ASR for all six models, by model-dependent amounts. GPT-5-nano append ASR goes from 77.95% in text to 0.00% in images. Gemini 3.1 Flash-Lite goes from 93.97% to 47.27% for append. For replacement, Qwen3-VL-8B executes it in 98.73% of text responses and 77.96% of image responses. To test whether worse reading explains the gap, the authors restrict Qwen to the 46 sources it answers with clean F1 of 1 in both modalities: append ASR is still 72.39% in text and 3.37% in images.

Source: Haoyang Liu, Yinong Xu, Zhe Lang, Zhenyu Guan, Qianyun Zhang, "What Survives the Shift from Text to Pixels? Conditional Protection against Prompt Injection in Image-Rendered Documents", Sections 4.1 and 4.3, Table 1, [arxiv.org/abs/2611.24231v1](https://arxiv.org/abs/2611.24231v1).

## The protection depends on presentation and on the attacker's budget

Controlled experiments use a different population: 90 sources, 30 per dataset. For Qwen's fixed-phrase replacement under W1, enlarging the font from 20 to 32 (width 876) or widening the page from 704 to 1280 pixels (font 26) each raise image execution by more than 25 percentage points. For the same replacement, a wording that repeats the question raises ASR over a generic one by 17.78 to 30.00 points. The attacker then tries a frozen ranked list of 16 candidates per operation, scored by strict success (exact target in the requested structure) on 60 held-out test sources. For Qwen, the image-minus-text append gap in strict success shrinks from -37.37 points at budget one to -3.33 points by budget eight, and formatting reaches 100% in both modalities. GPT-5-nano keeps a significant image deficit at every budget. A single-command image deficit need not imply robustness to an attacker allowed a few tries; whether it survives depends on the model and operation.

Source: Haoyang Liu, Yinong Xu, Zhe Lang, Zhenyu Guan, Qianyun Zhang, "What Survives the Shift from Text to Pixels? Conditional Protection against Prompt Injection in Image-Rendered Documents", Sections 5.2 to 5.5, Figures 2 and 3, [arxiv.org/abs/2611.24231v1](https://arxiv.org/abs/2611.24231v1).

## Read, then not followed

A missing marker could mean the command was never read. Under the inline protocol, Gemini transcribes and identifies more than 90% of image append and format commands yet executes 37.78% of append and 57.78% of format commands; GPT-5-nano reports and identifies more than half and executes none. These rates count sources scored in both modalities for each model. When each page image is replaced by its OCR transcript given as text, Qwen executes 41.80% of append and format commands, against 70.96% for the original text and 1.11% for the image, on the 89 inline append and format sources scored in all conditions. With the page unchanged, a user prompt (wrapper W_a) permitting the operation brings Gemini's append and format execution to 100% in both modalities (Figure 4(b); the paper does not state the number of sources). Inside Qwen, on 48 sources with append and format commands bound to random codes, blocking attention to the command's own positions drops text strict success from 90.63% and 83.33% to 0.00%, while image strict success stays within about 6 points of its unblocked level; only blocking the whole instruction page brings it to 0.00%.

Source: Haoyang Liu, Yinong Xu, Zhe Lang, Zhenyu Guan, Qianyun Zhang, "What Survives the Shift from Text to Pixels? Conditional Protection against Prompt Injection in Image-Rendered Documents", Sections 6.1 to 6.3, 7.3 and 7.4, Tables 4 and 6, Figure 4, [arxiv.org/abs/2611.24231v1](https://arxiv.org/abs/2611.24231v1).

## What reading pixels costs

The utility ratio is image F1 over text F1 (LongBench word overlap). On the original questions it ranges from 93.31% to 101.61% across the six models. The authors add one integration question per source (191 in total) that needs two evidence spans, and there Qwen falls to 61.99%. A low ASR is evidence of protection only when utility at the same setting is reported beside it.

Source: Haoyang Liu, Yinong Xu, Zhe Lang, Zhenyu Guan, Qianyun Zhang, "What Survives the Shift from Text to Pixels? Conditional Protection against Prompt Injection in Image-Rendered Documents", Sections 3.4, 4.2 and 5.2, Table 2, [arxiv.org/abs/2611.24231v1](https://arxiv.org/abs/2611.24231v1).

## What this means for provenance, and where we stand

Pixels change the channel by which a source reaches the model, not its author or authority. In the paper, whether the same planted command is executed depends on model, operation, font, wording, number of tries and the user's permission. Our reading, not a finding of the paper: provenance belongs on the source itself, and a rendering step is a transformation to log, not a trust decision. On 20 November 2026 our research desk read the paper and suggested a synthetic trial: matched benign and adversarial prompts, fixed models and budgets, an independent witness of external effects, and an explicitly scored UNKNOWN outcome. Reuse of restricted data and native use on protected actions are on hold. The proposal has no owner decision. Because the results are tied to the paper's six models and attack budgets, our desk noted they support no safety verdict about our own systems.

Source: Haoyang Liu, Yinong Xu, Zhe Lang, Zhenyu Guan, Qianyun Zhang, "What Survives the Shift from Text to Pixels? Conditional Protection against Prompt Injection in Image-Rendered Documents", Sections 3.3, 5.5 and 8, [arxiv.org/abs/2611.24231v1](https://arxiv.org/abs/2611.24231v1).
