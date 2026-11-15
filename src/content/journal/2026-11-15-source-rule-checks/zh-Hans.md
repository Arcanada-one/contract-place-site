---
site: contract.place
section: journal
slug: source-rule-checks-2026-11-15
date: 2026-11-15
lang: zh-Hans
title: "来源规则检查：给定的规则、它的例外和两种解读经过可检查的计算"
excerpt: "Knowledge Contract 语料库中的一项新工程研究提出：一个有界程序在计算时，能否完整保留给定的规则、它的例外、不同解读和未知事实。与单独编写的预期结果对照，它在16,384个和4,096个有限情形上全部一致；一次非作者审查发现了一个真实的输入故障，现已修复。这是有限检查，不是语言理解。"
---

来源中的规则常常带有例外，读者也可能持有两种解读。按这条规则计算的程序可能悄悄丢掉其中任何一样：截掉例外，合并解读，或把未知事实当作假。2026年11月15日并入 Knowledge Contract 语料库的一项研究，检验一个小型有界程序能否三者都保留。

## 问题与答案

这项研究名为《Source Rule Checks: Finite Binding, Alternatives and Operation Composition》，它的问题是：有界的使用方能否在整个可检查的计算中，保留明确给定的规则、它的例外、不同解读和未知观察。输入是一段带有 NOTE 和 RULE 行的简短人工来源，以及给定的解读数据包。研究明确说明，它不是从任意文本中自动提取含义的工具。

每一条规则行都必须与其字节选择器、引用文本和来源摘要一致，因此即使来源哈希有效，丢掉“UNLESS suspended”的截断片段也会被拒绝。未知值和被隐去的值都允许真和假，但二者仍可区分。每份报告都把来源忠实度、归属、现实中的真伪和当前权限标为未评估，并声明不授权任何操作。

来源：Pavel Valentov，《Source Rule Checks: Finite Binding, Alternatives and Operation Composition》，Knowledge Contract 工程研究，第1.1版，[github.com/Arcanada-one/knowledge-contract](https://github.com/Arcanada-one/knowledge-contract/blob/a5b3618034256f14f389c2c7de8da409c7c5310c/engineering/studies/semantic-bridge-conformance/STUDY.md)。

## 与单独编写的预期结果对照

预期结果来自一套测试，它从布尔真值掩码出发，不使用程序自身的分词器、解析器或求值器。研究直接说明了这种分离的性质：预期结果由另一个任务编写，但与实现共用同一个控制者、同一模型系列和同一台主机，因此不是外部独立性。

程序在两个完整的有限族上与预期结果一致：

- 三变量的全部256个布尔函数，在64种可用性配置下：16,384条记录，其中2,952条为真，2,952条为假，10,480条未确定；
- 二变量函数的全部256个有序对，在16种配置下：4,096条记录，两种解读一致1,088条，在同一世界中不一致3,008条。

在这些成对记录中，有984条的两种解读拥有相同的可能取值集合，却在同一世界中给出不同结果。只比较集合的检查会认为它们相同。计数会与声明的完整清单核对，所以缺少一个函数或配置不可能以较小的分母通过。

来源：同一项研究，“Independent expected-result method”一节及有限检查回执，[github.com/Arcanada-one/knowledge-contract](https://github.com/Arcanada-one/knowledge-contract/blob/a5b3618034256f14f389c2c7de8da409c7c5310c/engineering/studies/semantic-bridge-conformance/STUDY.md)。

## 与已有代数的衔接

四个集成测试把程序的输出交给语料库中已有的关系与结果集合几何代码。其中一个说明了为什么只看聚合距离不够：两种资格解读拥有相同的结果集合，豪斯多夫距离为零，但在八个共同世界中有两个不一致。研究认为这与语料库中两篇早先论文所声明的范围相符，而不是它们的反例。另一个测试表明，序号为零的行可以表示“真”，所以不能把行号等同于布尔标签。

来源：同一项研究，“Connection to algebra and geometry”一节，[github.com/Arcanada-one/knowledge-contract](https://github.com/Arcanada-one/knowledge-contract/blob/a5b3618034256f14f389c2c7de8da409c7c5310c/engineering/studies/semantic-bridge-conformance/STUDY.md)。

## 被保留下来的故障

一次非作者审查提交了一个5,341字节的数据包，其字节选择器中含有一个5,000位的整数。数据包没有超过大小限制，而最初的实现直接崩溃，输出 Python 回溯，没有 JSON 结果。修正后的读取器把这类解码错误转为结构化拒绝：退出码2，INVALID，malformed_json，不进行任何求值。原始模块、失败输出和修正后的输出并排保存，第一次失败没有被成功覆盖。审查者随后又做了30项检查，在该范围内没有发现剩余的阻断问题；研究说明这不是穷尽的证明。

来源：同一项研究，“Resolved input failure and review boundary”一节，[github.com/Arcanada-one/knowledge-contract](https://github.com/Arcanada-one/knowledge-contract/blob/a5b3618034256f14f389c2c7de8da409c7c5310c/engineering/studies/semantic-bridge-conformance/STUDY.md)。

## 我们的状态

已集成：这项研究、它的规范（《Semantic Bridge: From Source Readings to Checkable Operations》，工程草案）和代码自2026年11月15日起位于公开的 Knowledge Contract 仓库主分支。为它们记录的审查由非作者完成，但使用同一模型系列，不是独立审查。

按研究本身的说法，仍未解决的有：从人类语言到形式表达的一般忠实度、量词、单位、时间、嵌套归属、必需的媒体、完整的制品集成以及智能体的实际使用。发布决定、索引收录和原生收录各有单独的标准。没有进行任何付费实验。

来源：Knowledge Contract，已合并的拉取请求118，[github.com/Arcanada-one/knowledge-contract/pull/118](https://github.com/Arcanada-one/knowledge-contract/pull/118)。
