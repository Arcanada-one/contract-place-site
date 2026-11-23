---
site: contract.place
section: journal
slug: rendered-sources-injection-2026-11-21
date: 2026-11-21
lang: zh-Hans
title: "把不可信来源渲染成图像，改变的是通道，不是信任"
excerpt: "Liu 等人发现，页面图像平均而言降低了提示注入的执行率，但有一个模型仍在 77.96% 的已评分案例中执行了图像中的答案替换指令，而且模型常常能转写并识别指令，却没有执行。"
---

把不可信文档以页面图像而非文本的形式交给多模态模型，模型执行其中植入指令的频率会下降，但不会归零：在作者的主要对比中，Qwen3-VL-8B 在图像上的答案替换攻击成功率仍为 77.96%（按数据集加权、在已评分回答上计算的比率）。这篇预印本的作者是 Haoyang Liu、Yinong Xu、Zhe Lang、Zhenyu Guan 和 Qianyun Zhang。下文所有数字均来自作者。我们没有运行、复现或测量任何内容。

## 固定了什么，改变了什么

研究对象是一个依据单一外部来源回答问题的模型，该来源由攻击者控制，系统提示把它声明为不可信。作者从 LongBench 选取 191 个英文来源，为每个来源制作文本版和页面图像版，同一对内的问题、证据和攻击措辞保持不变。变化的是来源的模态和模型（共六个），攻击分三种操作：追加一个标记、围绕标记重排答案格式、或把答案替换为 "You are attacked!"。攻击成功率（ASR）指作者的评分判定已执行所请求操作的可见回答所占比例；因输出长度上限被截断的回答标为 unknown 并排除，三个数据集权重相同。

来源：Haoyang Liu, Yinong Xu, Zhe Lang, Zhenyu Guan, Qianyun Zhang，"What Survives the Shift from Text to Pixels? Conditional Protection against Prompt Injection in Image-Rendered Documents"，第 3.1 至 3.4 节，[arxiv.org/abs/2611.24231v1](https://arxiv.org/abs/2611.24231v1).

## 平均更低，但通道没有关闭

在主要对比中（191 个来源，原始问题，W1 包装，指令嵌在正文内），六个模型的追加与格式操作的图像 ASR 都低于文本 ASR，降幅因模型而异。GPT-5-nano 的追加操作从文本的 77.95% 降到图像的 0.00%。Gemini 3.1 Flash-Lite 的追加从 93.97% 降到 47.27%。至于答案替换，Qwen3-VL-8B 在 98.73% 的文本回答和 77.96% 的图像回答中执行了它。为检验图像 ASR 较低是否只是因为读图更差，作者把 Qwen 限定在两种模态下干净 F1 都等于 1 的 46 个来源上：追加 ASR 仍为文本 72.39%、图像 3.37%。

来源：Haoyang Liu, Yinong Xu, Zhe Lang, Zhenyu Guan, Qianyun Zhang，"What Survives the Shift from Text to Pixels? Conditional Protection against Prompt Injection in Image-Rendered Documents"，第 4.1 和 4.3 节，表 1，[arxiv.org/abs/2611.24231v1](https://arxiv.org/abs/2611.24231v1).

## 防护取决于呈现方式和攻击者的预算

受控实验使用另一组样本：90 个来源，每个数据集 30 个。对 Qwen 在 W1 下的固定短语替换，把字号从 20 增大到 32（宽度 876），或把页面宽度从 704 像素扩到 1280 像素（字号 26），各自都使图像执行率提高超过 25 个百分点。对同一替换操作，重复问题的措辞比通用措辞的 ASR 高 17.78 至 30.00 个百分点。随后允许攻击者从一份事先排序并冻结的列表中尝试指令，每种操作 16 个候选，在 60 个留出测试来源上按严格成功（在要求的结构中给出准确目标）评分。对 Qwen，追加操作严格成功的图像减文本差距从预算一时的 -37.37 个百分点缩小到预算八时的 -3.33 个百分点，格式操作在两种模态下都达到 100%。GPT-5-nano 在每个预算下都保持显著的图像劣势。单条指令下的图像劣势并不意味着能抵御可尝试几次的攻击者；它能否保持取决于模型和操作。

来源：Haoyang Liu, Yinong Xu, Zhe Lang, Zhenyu Guan, Qianyun Zhang，"What Survives the Shift from Text to Pixels? Conditional Protection against Prompt Injection in Image-Rendered Documents"，第 5.2 至 5.5 节，图 2 和图 3，[arxiv.org/abs/2611.24231v1](https://arxiv.org/abs/2611.24231v1).

## 读到了，但没有照做

没有出现标记，可能意味着指令根本没被读到，因此作者单独检验了阅读。在内嵌呈现下，Gemini 能转写并识别超过 90% 的图像追加与格式指令，但这两类指令的执行率分别为 37.78% 和 57.78%；GPT-5-nano 转写并识别了一半以上，执行数为零。这些比例按每个模型在两种模态下都有评分的来源计算。把每张页面图像换成以文本形式提供的 OCR 转写后，Qwen 对追加与格式指令的执行率为 41.80%，而原始文本为 70.96%，图像为 1.11%（89 个内嵌追加与格式指令、在所有条件下都有评分的来源）。页面不变，只在用户提示（包装 W_a）中允许该操作，Gemini 的追加与格式执行率在两种模态下都达到 100%（图 4(b)；论文未说明来源数量）。在 Qwen 内部，在 48 个追加与格式指令绑定到随机代码的来源上，屏蔽对指令自身位置的注意力使文本严格成功率从 90.63% 和 83.33% 降到 0.00%，而图像严格成功率与未屏蔽时相差约 6 个百分点以内；只有屏蔽整页指令页才使其降到 0.00%。

来源：Haoyang Liu, Yinong Xu, Zhe Lang, Zhenyu Guan, Qianyun Zhang，"What Survives the Shift from Text to Pixels? Conditional Protection against Prompt Injection in Image-Rendered Documents"，第 6.1 至 6.3 节、第 7.3 和 7.4 节，表 4 和表 6，图 4，[arxiv.org/abs/2611.24231v1](https://arxiv.org/abs/2611.24231v1).

## 读像素的代价

效用比等于图像 F1 除以文本 F1（LongBench 词重叠）。在原始问题上，六个模型的效用比介于 93.31% 到 101.61%。作者为每个来源增加一个需要两段证据的整合问题（共 191 个），在这类问题上 Qwen 降到 61.99%。只有同时报告相同设置下的效用，较低的 ASR 才能算作防护的证据。

来源：Haoyang Liu, Yinong Xu, Zhe Lang, Zhenyu Guan, Qianyun Zhang，"What Survives the Shift from Text to Pixels? Conditional Protection against Prompt Injection in Image-Rendered Documents"，第 3.4、4.2 和 5.2 节，表 2，[arxiv.org/abs/2611.24231v1](https://arxiv.org/abs/2611.24231v1).

## 对来源溯源意味着什么，以及我们的现状

把来源转换成像素，改变的是文字到达模型的通道，而不是谁写了这些文字、它们有什么权限。在论文中，同一条植入指令是否被执行，取决于模型、操作、字号、措辞、尝试次数以及用户是否允许。这是我们的解读，而非论文结论：溯源信息应记录在来源本身，渲染步骤是需要记入日志的一次变换，而不是信任决定。2026 年 11 月 20 日，我们的研究组阅读了这篇论文，并提出一项合成试验：匹配的良性与对抗性提示，固定的模型和预算，一个独立的外部效果见证者，以及单独计分的 UNKNOWN 结果。受限数据的复用和在受保护操作上的原生使用处于暂停状态。该提议尚无负责人决定。研究组指出，结果受限于论文中的六个模型和攻击预算，因此无法据此对我们自己的系统作出任何安全结论。

来源：Haoyang Liu, Yinong Xu, Zhe Lang, Zhenyu Guan, Qianyun Zhang，"What Survives the Shift from Text to Pixels? Conditional Protection against Prompt Injection in Image-Rendered Documents"，第 3.3、5.5 和 8 节，[arxiv.org/abs/2611.24231v1](https://arxiv.org/abs/2611.24231v1).
