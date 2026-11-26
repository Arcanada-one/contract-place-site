---
site: contract.place
section: journal
slug: memory-substrates-held-out-evaluation-2026-11-26
date: 2026-11-26
lang: zh-Hans
title: "记忆路由器在一个基准上的增益，换到它没见过的对话上便不再显著"
excerpt: "一项对 11 种智能体记忆方法的受控比较，还测试了一个按问题挑选方法的路由器。在一个基准、一个骨干模型上，它相对最佳单一方法的增益在随机划分问题折时显著；当留出问题来自它从未见过的对话时，增益缩小并失去显著性。我们没有复现任何内容。"
---

一项关于语言模型智能体记忆的研究，在同一套共享框架（harness）下比较了 11 种记忆方法，结论是没有哪一种存储介质在所有场景下都胜出。作者在附录中还测试了一个按问题挑选方法的路由器。在一个基准、一个骨干模型上，当问题被随机划分成若干折时，路由器胜过最佳单一方法；但当每个留出问题都来自路由器从未见过的对话时，按对话分组的折上增益缩小，留一对话的划分下增益降至不显著的 0.001。论文为 arXiv 2608.15008v2，修订于 2026 年 11 月 4 日。我们没有运行、复现或测量任何内容。

## 论文固定了什么、改变了什么、结论针对什么

作者把记忆被表示和存储的介质称为记忆基底（memory substrate）。主比较固定了框架、骨干模型、提示和辅助模型，只改变基底。它涵盖七个家族的 11 种方法、三个骨干模型和四套基准：两套是基于长对话历史的问答，两套是智能体任务（具身规划和代码）。

在不同运行模式下，最佳基底随任务而变。按评审分数 P4，双层图在三个骨干模型上都在 LoCoMo 和 LME-S 问答中领先，而在其他对话能力上，领先者随能力和骨干模型而变；在 Qwen3-32B-AWQ 上，把轨迹提炼为策略的记忆在具身规划中领先。在检索深度扫描中（LoCoMo 用 Qwen3-8B，ALFWorld 用 Qwen3-32B-AWQ），检索更多条目有助于问答，却损害序列决策。

来源：Wei-Chieh Huang, Weizhi Zhang, Yuchen Wu, Yankai Chen, Eric Hanchen Jiang, Wooseong Yang, Yiwei Yang, Henry Peng Zou, Hanrong Zhang, Ying Nian Wu, Haolun Wu, Kai-Wei Chang, Philip S. Yu, Xue Liu, Aylin Caliskan, "Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents"，摘要、第 1 至 4 节和第 5.2 节，表 1 和表 2，[arxiv.org/abs/2608.15008v2](https://arxiv.org/abs/2608.15008v2)。

## 按问题随机分折，对比全新的对话

关于数据划分的结果针对的是另一个对象：路由器。论文把它定义为放在一组基底前面的选择策略，而不是新的记忆机制。评价指标是路由后整个系统的准确率，对照对象是在相同留出问题上表现最好的固定基底。全部实验只在一个基准 LoCoMo 上、用一个骨干模型 Qwen3-8B 完成。LoCoMo 含十段多轮会话对话和 1,986 个问题。

这里的准确率是论文的 LLM 评审分：GPT-4o-mini 在看到问题、标准答案和模型回答后标为 CORRECT 的回答所占比例。比较采用对逐题配对结果的精确 McNemar 检验。

在论文报告的方案中，1,986 个问题被随机分成五折。论文测试了四个路由器，只有按基底预测结果的那一个（每个基底一个分类器，预测该基底能否答对）明显超过固定基线：得分 0.671，最佳固定基底为 0.648。路由器答对而固定选择答错的有 223 次，反过来是 179 次（p=0.032），并且五折全胜。这些折没有按对话分组，同一对话的问题可能同时出现在训练折和留出折中。作者用同样设计的路由器在新的训练折上重新拟合，对照同一个固定基线和同样的评审标签，只改变折的构建方式，重复了比较：

- 按对话分组的五折：0.661 对 0.648，p=0.22，五折中胜三折；
- 留一对话，十折：0.649 对 0.648，p=0.96，十折中胜五折。

按作者的说法，增益在分组折下缩小，在留一对话下消失，两个差值都不显著。他们把结论限定为：一个已在自身流量上积累了结果、并为同一批对话中的新问题做路由的部署；他们不声称能迁移到未见过的对话。这一发现针对的是这个路由器、这个基准和这个模型，共十段对话；论文没有在其他条件下检验它。

来源：Wei-Chieh Huang, Weizhi Zhang, Yuchen Wu, Yankai Chen, Eric Hanchen Jiang, Wooseong Yang, Yiwei Yang, Henry Peng Zou, Hanrong Zhang, Ying Nian Wu, Haolun Wu, Kai-Wei Chang, Philip S. Yu, Xue Liu, Aylin Caliskan, "Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents"，第 3 节、附录 D 和 E.3，表 12 和表 13，[arxiv.org/abs/2608.15008v2](https://arxiv.org/abs/2608.15008v2)。

## 论文还把哪些比较标为样本内，以及由谁评判

按运行模式各选一个基底，在它的基准上胜过任何单一固定基底，但这个选择是从同一批结果中读出的，因此作者称之为样本内比较，而不是留出检验。对于 LoCoMo 上 Qwen3-8B 的逐题路由，一个只要存在答对的基底就选中它的逐题神谕（推理时无法观测的参照）可得 0.93，而最佳固定基底为 0.648；论文表示，逐题路由（其最佳路由器在随机折下为 0.671）仍未弥合这段空间的大部分。

上面所有对话类分数都来自同一个评审模型，它同时也是写入记忆的辅助模型。作者用四个评审模型重新评分了 595 条预测，按 CORRECT 和 WRONG 两种标签进行平衡抽样。在这些样本上，生产评审的重新运行与其原有标签一致的比例为 95.8%，四个评审的 Fleiss kappa 为 0.73。四个评审都来自同一家提供商，作者说明，人工或跨提供商的核验不在本研究范围内。

来源：Wei-Chieh Huang, Weizhi Zhang, Yuchen Wu, Yankai Chen, Eric Hanchen Jiang, Wooseong Yang, Yiwei Yang, Henry Peng Zou, Hanrong Zhang, Ying Nian Wu, Haolun Wu, Kai-Wei Chang, Philip S. Yu, Xue Liu, Aylin Caliskan, "Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents"，摘要、第 7 节、附录 E.2 和 E.3，表 11 和表 12，[arxiv.org/abs/2608.15008v2](https://arxiv.org/abs/2608.15008v2)。

## 我们的现状

我们读了这篇论文。它是一项已提出、仅停留在设计阶段的评估的参考：评估我们的知识契约如何在项目之间复用，做法是在留出的对话或项目上评估，并按来源分组，使同一来源绝不同时出现在训练和评估中，而不是用随机的问题划分。把论文关于对话的结论推广到项目，是我们自己的一步；论文没有讨论项目。我们自己的记忆和搜索索引如何对应论文中的记忆基底，尚未梳理。我们没有运行、复现或测量任何内容。

来源：分组划分方案出自 Wei-Chieh Huang, Weizhi Zhang, Yuchen Wu, Yankai Chen, Eric Hanchen Jiang, Wooseong Yang, Yiwei Yang, Henry Peng Zou, Hanrong Zhang, Ying Nian Wu, Haolun Wu, Kai-Wei Chang, Philip S. Yu, Xue Liu, Aylin Caliskan, "Harness the Memory: A Holistic Evaluation of Memory Substrates in Memory Agents"，附录 E.3，表 13，[arxiv.org/abs/2608.15008v2](https://arxiv.org/abs/2608.15008v2)。
