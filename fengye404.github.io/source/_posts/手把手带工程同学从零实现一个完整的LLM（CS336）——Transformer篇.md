---
title: 手把手带工程同学从零实现一个完整的LLM（CS336）——Transformer篇
typora-root-url: ./手把手带工程同学从零实现一个完整的LLM（CS336）——Transformer篇
date: 2026-09-20 01:45:00
tags:
  - AI
  - LLM
  - Transformer
  - CS336
  - PyTorch
---

# 手把手带工程同学从零实现一个完整的LLM（CS336）——Transformer篇

## 前言

最近我在学习 CS336「Language Modeling from Scratch」，是斯坦福大学的大语言模型构建课程。这门课程在各种社交媒体（X）中都很火爆，但是在内网似乎没有多少人分享过，所以我想写一系列文章来分享一下我的学习过程。

虽然课程名字中叫「from Scratch」，但是它的含义是从零手搓，而不是从零教学，因此对于没有过神经网络/机器学习基础的同学来说，学习起来还是比较困难的，需要有较为完善的体系知识。

> 先叠个甲，我之前的背景是纯工程开发，大概在 25 年初开始转向 Agent 开发，此前也没有过系统的机器学习、神经网络学习经验，因此我学习 CS336 的过程也是逐渐查漏补缺，即用即学，如果专业的算法同学发现文章有不当之处，欢迎指正

学习这门课程，最主要的就是完成它的 Assignment 作业，这一篇是这个系列中的第一篇文章，会跟随 CS336 Assignment1 的思路，完整介绍如何从零手搓一个 Transformer（注：非 Attention Is All You Need 原始论文版本，，其中会引入 RoPE、SwiGLU 等变体，这也是 CS336 这门课程的优秀之处）。

> Assignment1 的原始资料：[stanford-cs336/assignment1-basics](https://github.com/stanford-cs336/assignment1-basics/tree/main)

如果你也想学习 LLM 的底层原理，强烈建议跟着本篇文章，独立认真完成 Assignment 1（注：CS336 的 Assigment 中都会附带一份 AGENTS.md，以防你的 coding agent 直接帮你一键完成作业）

为了先建立对于神经网络体感，文章开头不会带你直接进入 Assignment1，而是会先从最基础的 MLP、FFN 等概念引入。

## 为什么要学习这个

在正式开始之前，我想先解释一下为什么我认为所有工程同学都需要学习 CS336。

我从 25 年初转向 Agent 开发，这一年多里 LLM 对我来说基本就是一个 HTTP 接口：prompt 进去，文本出来，中间发生什么一概不管。这个状态能干活，但天花板很明显。模型行为不符合预期的时候，黑盒外面的人只能猜：是 prompt 写得不好，还是上下文塞得太长，还是任务本身超了模型能力？猜来猜去都是玄学。

其实很多问题的答案写在模型内部。比如长上下文该硬塞还是做检索，取决于模型训练时的上下文长度和位置编码怎么设计——RoPE 外推到训练时没见过的长度，注意力分数会明显劣化，prompt 写得再好也救不回来。推理成本和并发吞吐也有确定的账：attention 的计算量随序列平方增长，KV cache 随序列线性增长，这两个数直接决定部署时的显存预算。还有 tokenizer，工具调用参数里那些 JSON 括号、空格和转义符，切出来的 token 长什么样，直接影响成本和模型对格式的敏感程度。

这些都不是调 API、改 prompt 能解决的。CS336 的做法是让你把每个零件亲手写一遍：tokenizer 自己训练，attention 自己算，位置编码自己旋转。写完之后回头看 vLLM 的 PagedAttention、看各种长上下文外推方案，都能看懂背后的设计取舍了。

## 1. 两个仓库

学习材料分两层。[cs336-study](https://github.com/fengye404/cs336-study) 是我搭的小 lab，每个只解决一个小问题，代码短，跑完马上能看到 shape 和数字；[cs336-assignment](https://github.com/fengye404/cs336-assignment) 放官方作业的正式实现。

不直接开 assignment 的原因很简单：A1 的脚手架很少，拿到手就是一个 PDF 加一堆测试，容易懵。先在 lab 里把每个组件的简化版过一遍，再回去写正式实现，精力才能放在设计取舍上，不至于卡在某个 shape 里。

后面的顺序：MLP 热身，TinyGPT 搭骨架，然后对照 A1 把零件一个个换掉。

## 2. MLP：先把训练回路跑通

第一个 lab 不碰语言模型。任务是拟合 `y = sin(x) + 0.3 * cos(3x)`，输入落在 `[-2π, 2π]`，加了噪声。模型是三层 MLP，`1 → 64 → 64 → 1`，Tanh 激活。

训练循环就这几行：

```python
pred = model(x_train[idx])          # 前向
loss = loss_fn(pred, y_train[idx])  # 算误差
optimizer.zero_grad()               # 清上一步的梯度
loss.backward()                     # 反向
optimizer.step()                    # 更新
```

权重一开始是随机的。前向算出预测，loss 衡量预测和答案差多少，`backward()` 给每个参数算梯度，`step()` 用梯度更新参数。后面换成语言模型，回路还是这几行。

800 步跑完的真实日志：

```text
step 0001 | train_loss=0.57724 | val_loss=0.35146
step 0100 | train_loss=0.08547 | val_loss=0.25838
step 0300 | train_loss=0.06590 | val_loss=0.64648
step 0800 | train_loss=0.00640 | val_loss=0.24745
```

train loss 降到 0.0064，val loss 上下波动。这两个数要分开看：train loss 降说明模型在拟合训练数据，val loss 飘说明数据里的噪声学不进去，这很正常。后来看语言模型的训练日志，最早的直觉就来自这种小实验。

`zero_grad()` 那行漏掉的话，PyTorch 会把梯度一直累积下去，loss 曲线直接就是平的。我养成习惯：每次写训练循环，先把这五行骨架搭好，于是再填别的。

## 3. TinyGPT：能跑的最小语言模型

第二个 lab 把整套结构搭起来。语料是一段重复 40 遍的小文本，字符级 tokenizer，词表 23。任务只有一个：预测下一个字符。

输入 ID 是 `[10, 20, 30]`，目标就是往后错一位的 `[20, 30, 40]`。每个位置输出一组词表分数，叫 logits，拿右移一位的 ID 算交叉熵 loss，再走刚才那条回路。

整体数据流：

![Transformer 整体数据流](arch.svg)

先不展开 attention 和 MLP 的公式。盯住一条链路：输入 `(B, S)` 的字符 ID，输出 `(B, S, 23)` 的 logits，拿右移一位的 ID 算 loss，反向传播，更新权重。

TinyGPT 的 block 把 attention 和 MLP 的输出加回原向量，输入输出始终是 `(B, S, D)`。位置信息来自一张可学习的位置向量表。

300 步的真实日志：

```text
step 0001 | loss=3.3545
step 0050 | loss=0.9013
step 0100 | loss=0.1608
step 0300 | loss=0.1020
```

生成结果已经像模像样：

```text
anguage models predich tokens from previous tokens. attention lets each token read useful
earlier tokens. agents plan actions observe results and update context. language models pre
```

注意 `predich`——predict 都拼错了。0.10 的 loss 有水分，语料重复了 40 遍，模型基本是背下来的。能跑就行。

这个骨架用的是 `nn.Linear`（带 bias）、`nn.LayerNorm`、可学习位置编码和 GELU，属于 GPT-2 的默认搭配。A1 要全部手写，并且换上 RMSNorm、RoPE 和 SwiGLU。接下来先解决输入问题——文本怎么变成 token。

## 4. 文本编码与 Tokenizer

### 字符、Unicode 与 UTF-8

计算机只存数字，要显示字符得先定义编号。ASCII 给 127 个字符编号；Unicode 给全球 15 万+ 字符分配码点。比如 `A` 的码点是 65，「中」的码点是 20013。

码点只是编号，UTF-8 负责把码点变长编码成字节。ASCII 一个字节，汉字一般三个字节：

```python
>>> list("中".encode("utf-8"))
[228, 184, 173]
```

Python 的 `str` 是字符序列，`encode` 之后才是字节序列。字符、字节、token 是三种不同的东西。说上下文长度 128，数的是 token，不是 128 个字或者 128 个 byte。做 Agent 上下文预算的时候，这个换算天天要用。

### BPE：预分词与合并规则

为什么不能直接喂字节？词表确实只要 256 个值，但序列会变得非常长。`Transformer` 一个单词 11 个字节，attention 的计算量随序列长度平方增长。Tokenizer 的作用是在词表大小和序列长度之间找平衡，本质是对文本的压缩。

BPE 从 256 个单字节 token 起步，统计语料里哪些字节组合最值得合并。它的训练是频次统计，产物是一张合并规则表，和梯度训练是两码事。

合并之前先做预分词。A1 给了一条 GPT-2 风格的正则，把文本切成带前导空格的单词、数字、标点等片段，BPE 只在片段内部合并：

```python
PATTERN = r"""'(?:[sdmt]|ll|ve|re)| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
```

没有预分词，"您好 人没了" 里可能切出 "好 人" 这种横跨两个词的 token。

训练时先数每种 pre-token 出现多少次，再转成 UTF-8 字节序列。统计 pair 的时候，我一开始只数了每个片段里 pair 出现的次数，忘了乘上片段本身的频率。比如 `abab` 出现 5 次，pair `(a,b)` 在里面出现 2 次，实际应该贡献 10 次，不是 2 次。频率丢了，merge 顺序就变了。

每轮找计数最高的相邻 pair，拼成新 token，记录进 `vocab` 和 `merges`。`merges` 的顺序必须留住：编码新文本时要按学习时的顺序重放。同频次的时候 A1 规定了字典序的 tie-breaking，这种细节值得拿小样例走一遍。

特殊 token 也容易踩坑。以 `<|endoftext|>` 为例，它表示文档边界，训练前先按它把文本切开，内部不参与 pair 统计，两侧也不允许合并。边界不能跨。

我在示例语料上跑了一遍：vocab 500，学到 243 条 merge，前几条依次是 `(" ","t")`、`(" ","a")`、`("h","e")`，第 5 条已经把 `" t"` 和 `"he"` 合成 `" the"`。高频组合先被学走。

写 BPE `encode_iterable` 的时候，我突然有点怀念写 Java 的日子，至少字符串处理不用先转成 bytes 再担心半个汉字的问题。

### Tokenizer 的封装：编码与解码

`train_bpe` 的产出是 `vocab`（ID → bytes）和有序的 `merges`。给定新文本，encode 先识别特殊 token，再做预分词，普通片段拆成单字节 token，按 `merges` 顺序重放合并，最后查词表得到整数 ID。decode 反过来：ID 找回 bytes，全部拼起来之后统一做 UTF-8 解码。

decode 别逐 token 解码。一个 token 的 bytes 可能只是某个汉字 UTF-8 编码的一部分，单独解码直接报错。先拼全部 bytes，遇到非法序列用替代字符处理。大文件还要用 `encode_iterable` 流式产出 ID。

到这里，原始文本变成了模型能接收的整数序列。

## 5. Transformer 模块串讲：先看整条数据流

进组件之前，先把 decoder-only 语言模型的整条前向通路摆出来：

```text
输入 token IDs        (B, S)
→ Embedding           (B, S, D)
→ Transformer Block×L (B, S, D)
→ RMSNorm             (B, S, D)
→ LM head             (B, S, V)
```

`B` 是 batch，`S` 是序列长度，`D` 是模型宽度，`V` 是词表大小。token ID 先查表变成向量；中间 `L` 个 block 反复加工，形状始终是 `(B, S, D)`；最后归一化，LM head 把每个位置映射成词表分数。

block 里只有两类东西：attention 负责 token 之间交换信息，FFN 负责对每个位置单独加工，归一化和残差连接把它们包起来。

和 TinyGPT 对照，A1 要换的零件就这几处：

| 组件 | TinyGPT（lab） | Assignment1（要手写） | 换的原因 |
|------|---------------|----------------------|---------|
| Linear | `nn.Linear`，带 bias | 手写无 bias 版本 | 把权重形状和初始化摆到台面上 |
| Embedding | `nn.Embedding` | 手写查找表 | 看清 ID 如何变成向量 |
| 归一化 | LayerNorm | RMSNorm | 沿最后一维控制数值尺度 |
| 位置编码 | 可学习的绝对位置 | RoPE，作用在 q/k 上 | 把位置放进 attention 分数的计算 |
| FFN | GELU，两层 Linear | SwiGLU，三层 Linear | 加一条门控分支 |
| 残差结构 | pre-LN | pre-norm | block 的输入输出形状保持一致 |

残差和 pre-norm 的布局不用动，骨架是好的。作业要求自己写 Linear、Embedding、softmax——初始化、bias、dtype 这些平时被框架藏起来的细节，自己写一次才知道哪里会出问题。`cs336-assignment` 里的 `model.py` 注释比代码多，RoPE 那段我先把旋转矩阵推了一遍，再拆成两两配对，最后才落成逐元素公式。

## 6. Embedding 和 Linear

Embedding 就是一张查找表。词表大小 `V`，每个 token 的向量维度 `D`，表本身就是 `(V, D)`。输入 `(B, S)` 的 token ID，查完表变成 `(B, S, D)`。这张表初始时不含任何「语义」，里面的向量全靠训练更新。

Linear 负责向量维度的投影，Q/K/V、FFN、LM head 里全是它。这份作业里它只有矩阵乘法和受控初始化，没有 bias。作业给的初始化公式是 `sqrt(2/(d_in+d_out))`，截断在 ±3σ。

权重形状我一开始按直觉写成了 `(in, out)`，前向直接 `x @ W`，结果和参考对不上。后来才发现 PyTorch 里向量按行存，权重是 `(out, in)`，前向要转置：`y = x @ W.T`。输入前面带多少 batch 维都行，矩阵乘法只作用在最后一维。

## 7. Attention 与因果多头自注意力

softmax 实现时先减最大值再算指数。不减的话，分数稍大 `exp` 就溢出。

Attention 就是加权投票：每个 token 决定从前面哪些 token 各取多少信息。公式是 `softmax(QKᵀ / √d_k) V`。`√d_k` 不能省：Q 和 K 的分量近似独立时，点积的方差随 `d_k` 线性增长，不缩放的话 softmax 被推到饱和区，梯度接近 0。

语言模型不能偷看未来。因果 mask 是下三角，第 t 个位置只能看到 1 到 t。被掩掉的位置填 `-inf`，softmax 之后权重就是 0。前提是每行至少有一个可见位置——因果 mask 的对角线保证了这一点。

多头把这套并行跑 `H` 份，每个 head 分到 `d_k = D / H` 的宽度：

![Attention 的形状流转](attention-shapes.svg)

TinyGPT 把 qkv 放在一次投影里算，A1 拆成三个 Linear，对照公式更直观。形状流转：

```text
x:       (B, S, D)
q/k/v:   (B, S, D)
拆多头:   (B, H, S, d_k)
scores:  (B, H, S, S)
拼回来:   (B, S, D)
```

拆多头时先把最后一维分成 `(H, d_k)`，再把 `H` 转到序列维前面；算完 attention 再转回来，过输出 Linear。把这几个 shape 标在代码旁边，比背公式更能防错。

## 8. RoPE：把位置旋进 q 和 k

TinyGPT 的位置信息是查表查来的。RoPE 换了个思路：把 q 和 k 的每两个分量当成二维平面上的一个点，按 token 的位置旋转一个角度。

![RoPE 的旋转示意](rope.svg)

位置 m 旋转 `m·θ`，位置 n 旋转 `n·θ`，两个向量做点积时角度相减，结果只剩 `(m - n)·θ`——q 和 k 的内积只跟相对距离有关。「前一个词」这种关系，不应该因为句子变长就改变。

先把每个位置的 cos/sin 预计算成表。`theta` 控制不同分量对的旋转速度：前面的转得快，管近距离；后面的转得慢，管远距离。

应用时把最后一维两两分组，每组当二维向量转。`repeat_interleave(2)` 把每对分量共用的 cos/sin 复制两份；`unflatten + unbind` 取出偶数、奇数分量；`stack((-odd, even))` 就是二维旋转里的 `(-y, x)`。数学上等价于一个分块对角的旋转矩阵，但逐元素算更省。

这里用的是相邻两个分量配对。配对顺序必须和参考权重一致——顺序混用的话，张量形状全对，数值全错。

相对位置这个性质不用等训练，直接就能测：

```python
rope = RotaryPositionalEmbedding(d_k=16, theta=10000.0, max_seq_len=64)
base_q = torch.randn(1, 1, 1, 16).expand(1, 1, 8, 16)
base_k = torch.randn(1, 1, 1, 16).expand(1, 1, 8, 16)
positions = torch.arange(8).expand(1, 8).unsqueeze(1)
qr, kr = rope(base_q, positions), rope(base_k, positions)

# 位置 (2, 1) 和 (5, 4) 的相对距离都是 1，点积应该相等
a = (qr[0, 0, 2] * kr[0, 0, 1]).sum()
b = (qr[0, 0, 5] * kr[0, 0, 4]).sum()
torch.testing.assert_close(a, b)   # 验证通过
```

最后说一个形状上的坑。RoPE 只作用在 q 和 k 上，v 不旋转。接回多头 attention 时，位置下标是 `(B, S)`，q/k 是 `(B, H, S, d_k)`。直接拿 `(B, S)` 查 cos/sin 表得到 `(B, S, d_k)`，和 `(B, H, S, d_k)` 逐元素乘，B 和 H 两个轴会对撞。正确做法是查表前给位置下标补一个 head 轴，变成 `(B, 1, S)`。坑在这里。batch 等于 1 的时候广播恰好能过，这个错误的暴露很容易被推迟到真正训练之前。

## 9. SwiGLU：每个位置自己的前馈网络

Attention 负责 token 之间的信息交换，block 里还需要一条对每个位置分别工作的前馈网络。原始 Transformer 用两层 Linear 加 ReLU；A1 用 SwiGLU，多一条门控分支：

```text
SwiGLU(x) = W₂(SiLU(W₁x) ⊙ W₃x)
```

`W₁` 和 `W₃` 都把 `D` 升到 `d_ff`，两路结果逐元素相乘，`W₂` 再降回 `D`。

为什么 `d_ff` 常取约 `8D/3`？传统两层 FFN 隐藏宽度取 `4D` 时，两个矩阵约 `8D²` 个参数；SwiGLU 有三个矩阵，`d_ff` 取 `8D/3` 时也约是 `8D²`。参数量对齐了，不同 FFN 之间才好公平比较。

## 10. RMSNorm

归一化做两件事：把激活值的尺度拉回来，再乘一个可学习的缩放。LayerNorm 减均值、除标准差；RMSNorm 省掉减均值，也没有 bias，只按最后一维算均方根。

输入输出都是 `(B, S, D)`，形状不变。平方、均值、缩放先在 fp32 里算，再转回输入 dtype——低精度训练时，这一步能减少归一化环节的数值误差。作业 PDF 明确要求这个 upcast，照做就是。

## 11. 组装：Transformer Block 与完整语言模型

一个 pre-norm block 有两次残差相加：

```python
def forward(self, x, token_positions):
    x = x + self.attention(self.norm1(x), token_positions)
    x = x + self.ffn(self.norm2(x))
    return x
```

RMSNorm 不改形状，attention 和 SwiGLU 的输出也都是 `(B, S, D)`，两次相加都成立。残差保留原输入，让子层在原向量基础上做增量更新。

![pre-norm 残差结构](block.svg)

完整 Transformer LM：前面接 token embedding，中间叠 `L` 个 block，最后接 RMSNorm 和 LM head，回到第 5 节那条通路。A1 的模型没有另加位置 embedding，位置全由各层 attention 内部的 RoPE 处理。

这也是我觉得前面两个 lab 有必要的原因：看到 logits 时，我们已经知道它可以和右移一位的目标算 loss；生成时取最后一个位置的 logits 采样出下一个 token，再接回输入。这一篇先把前向接稳。

### 参数量和计算量也要对得上

不带 bias、输入 Embedding 和输出 LM head 不共享权重时，参数量是：

```text
2VD + L × (4D² + 3D·d_ff + 2D) + D
```

拿 `V=256、D=256、L=4、d_ff=704` 代入，算出来 `3,344,640`，和 `sum(p.numel() for p in model.parameters())` 跑出来的完全一致。数字对上了。以后对不上，就回去查漏层或者重复建层。

参数量还解释不了长序列的成本。四个 attention 投影的计算随 `B·S·D²` 增长，QKᵀ 和对 V 加权随 `B·S²·D` 增长，SwiGLU 随 `B·S·D·d_ff` 增长。上下文长度 `S` 拉大时，attention 的平方项不能忽略。

### 怎么确认它真接通了

写完每个组件，我用三类检查确认它们真接通了。一是形状：完整模型的输出必须是 `(B, S, V)`，每个组件的输入输出也要和第 5 节的通路对得上。二是因果性：改动输入序列的后半段，前半段的 logits 应该不变——mask 写反了，这个检查立刻能抓出来。三是数值：RoPE 用两组相同相对距离的位置验证点积，参数量用上面的公式核对。

模型主路径跑通，和所有输入形状都处理正确，是两件事，得分别验证。

## 后记

到这里，文本能经过 BPE 变成 token ID，再经过自己写的 Transformer 变成下一 token 的 logits。回头看开头的 TinyGPT，训练循环那几行代码消费的东西终于有了具体的形状。

上次有这种把书上的系统搬到终端里的感觉，还是做 MIT 6.824 的 lab。那时主要盯日志和网络分区，现在盯的是 token 边界、张量形状和数值。挺有意思的。

---

参考资料：

- [CS336: Language Modeling from Scratch](https://cs336.stanford.edu/)
- [Assignment 1: Basics](https://github.com/stanford-cs336/assignment1-basics/tree/main)
- [cs336-study（lab 仓库）](https://github.com/fengye404/cs336-study)
- [cs336-assignment（A1 实现）](https://github.com/fengye404/cs336-assignment)
- [RoFormer: Enhanced Transformer with Rotary Position Embedding](https://arxiv.org/abs/2104.09864)
- [Root Mean Square Layer Normalization](https://arxiv.org/abs/1910.07467)
- [GLU Variants Improve Transformer](https://arxiv.org/abs/2002.05202)
