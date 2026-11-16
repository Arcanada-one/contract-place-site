---
site: contract.place
section: journal
slug: rule-after-restart-2026-11-15
date: 2026-11-15
lang: zh-Hans
title: "暂停之后的规则：从仓库快照到本地计算"
excerpt: "一个新的离线使用程序把仓库会话与来源规则检查连接起来。每次新的求值请求之前，它都会重新观察已提交的输入；上下文变化后，需要明确恢复会话。这个候选实现为实验室流程做准备，不连接公开实验室，也不调用语言模型。"
---

程序可能正确计算一条规则，却使用了错误的规则版本。暂停之后，源文件可能已经改变，而智能体仍依赖先前的解读。Knowledge Contract 的下一个工程步骤关注的正是这条边界：本次本地计算究竟可以使用哪一份来源和解读数据包？

引用的版本是尚未合并的 PR119 候选版本；以下观察来自本地执行。

## 一次计算，一个观察到的上下文

候选实现连接两个已有组件：仓库会话记录并采用有界上下文，Semantic Bridge 则计算明确给定的规则和不同解读。完整的文件配置只有两个来自提交的输入：规则来源和它的解读数据包。两者都不可缺少。

会话成功开始后会采用一个上下文，但还不计算规则。每次新的 “EVALUATE” 请求之前都会重新观察仓库。如果已采用的上下文不再可用，计算就会被阻止。明确执行恢复操作后，可以采用新观察到的上下文；下一次求值仍会重新检查。桥接程序收到的是该次观察保留的确切字节，不是在检查结束后重新打开工作区文件所得的内容。

来源：候选实现 [repository_rule_consumer.py](https://github.com/Arcanada-one/knowledge-contract/blob/872ba95da3703e3a11ee70a3bc1c38419ce3660a/tools/repository_rule_consumer.py) 及[源代码变更](https://github.com/Arcanada-one/knowledge-contract/pull/119)。

## 本地运行实际检查了什么

完成的本地运行在全部12个步骤上符合预先声明的预期结果：11次新的使用程序快照，加上一次历史检查。这是在真实本地 Git 仓库中编写的一条流程，不是12次独立试验。未知的规则结果仍然保持未确定；解读数据包改变后，求值被阻止，直到明确恢复会话；与输入无关的提交则保留已采用的上下文。采用含有不受支持规则的来源后，桥接程序返回 “UNSUPPORTED”，不输出真值。工作区中未提交的干扰修改没有替换从提交中捕获的输入。

第一次运行在第二步停止，因为测试示例数据包缺少必需的观察字段，程序拒绝了该输入。示例随后得到修正；失败运行与完成运行一起保存，没有被成功报告覆盖。

另一项输入审查发现，快照数量限制原本在重放输入历史之后才检查。修正把这项检查移到哈希计算和重放之前。对应的合成边界检查验证过长历史是否被及早拒绝；这些检查与十二步生命周期分开计算。

保存的结果把输入标识、仓库观察、已采用的上下文和计算绑定在一份回执中。检查保存的回执会根据保留的字节重新计算记录的结果，不进行新的 Git 观察。它核对内部一致性并展示历史结果，不声称仓库内容仍然与当时相同。

来源：[实际生命周期回执](https://github.com/Arcanada-one/knowledge-contract/blob/872ba95da3703e3a11ee70a3bc1c38419ce3660a/reviews/repository-rule-consumer-20261115/lab-run/RUN.json)及[非作者审查](https://github.com/Arcanada-one/knowledge-contract/blob/872ba95da3703e3a11ee70a3bc1c38419ce3660a/reviews/repository-rule-consumer-20261115/non-author/REVIEW.md)。

## 仍在范围之外的事项

观察只覆盖记录快照时的已提交文件。它不覆盖任意未提交修改、自由文本的含义、真实任务的全部依赖，或快照之后发生的变化。回执链不是经过身份验证的签名，也不保证历史完整。计算成功不授予行动权限。

受控规则语法、明确编写的解读数据包以及未知观察都保留原有边界。这个本地流程不需要调用语言模型。在同一控制者、模型系列和主机上，由另一项任务完成的审查属于内部非作者审查，不是外部独立验证。

来源：[使用程序声明的范围](https://github.com/Arcanada-one/knowledge-contract/blob/872ba95da3703e3a11ee70a3bc1c38419ce3660a/tools/repository_rule_consumer.py)及 [Semantic Bridge 规范](https://github.com/Arcanada-one/knowledge-contract/blob/872ba95da3703e3a11ee70a3bc1c38419ce3660a/engineering/specifications/semantic-bridge/SPECIFICATION.md)。

## 实验室的准备步骤

这是一个离线工程步骤。公开的“知识旅程”页面仍显示未连接，文件上传和启动控件仍被禁用。已有的观察组件和保留文件读取组件已经作为网站资源交付；单凭这些资源，并不能连接数据生产方、取得私有对象的访问权或启动任务。

下一步实验室集成可以读取同样的有界回执，并区分观察到的计算与历史计算。真正的浏览器连接仍需要明确的来源绑定、获准的读取路径、会话生命周期以及实际浏览器验收。本篇记录源代码工作，不改变已发布语料库的版本，也不宣布生产环境已经接通。

来源：[“知识旅程”](https://contract.place/zh-Hans/lab/knowledge-journey/)、[现有读取边界](https://github.com/Arcanada-one/contract-place-site/blob/084509513ca71439d585adf5a90f26a60a8a5e7a/docs/retained-object-reader.md)以及[2026年11月15日的资源回读记录](https://github.com/Arcanada-one/contract-place-site/blob/084509513ca71439d585adf5a90f26a60a8a5e7a/docs/lab-asset-delivery-20261115.json)。
