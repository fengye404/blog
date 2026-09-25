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

最近在做 Stanford CS336 的 Assignment 1。拿到作业时，仓库里基本只有一份 PDF、一组测试和等着自己填的代码。课程叫 *Language Modeling from Scratch*，这里的 from scratch 是从字节级 BPE、Linear 一路写到 Transformer LM；它默认你已经熟悉神经网络训练。

我之前主要写工程代码，后来开始做 Agent，也一直想弄清楚：一段文本进了模型以后到底经过了什么？光看 Transformer 结构图，箭头和方框都认识，连起来却没什么体感。于是我先在 [cs336-study](https://github.com/fengye404/cs336-study) 做了一组小 lab，再回到 [cs336-assignment](https://github.com/fengye404/cs336-assignment) 写正式作业。这篇文章也按这个顺序走。

范围先说清楚：**从原始文本出发，实现 tokenizer 和能够输出下一 token 分数的 Transformer LM**。开头的 MLP、TinyGPT 会跑几步训练，帮我们看懂这些模块为什么要存在；正式的优化器、训练脚本和消融实验留在后面的文章。

```text
文本 --BPE tokenizer--> token IDs --Embedding--> 向量
  --多个 Transformer Block--> 每个位置的 logits --> 下一个 token
```

做 Agent 时，tokenizer 会影响一段工具调用在模型眼里如何分段，位置编码和 attention 则影响上下文怎样被读取。以前我常把这些藏在 API 后面；这次想把这条路径沿着代码走一遍。

原始作业资料在 [stanford-cs336/assignment1-basics](https://github.com/stanford-cs336/assignment1-basics/tree/main)。如果你也在跟课，建议先自己做题，再把这里当作实现思路的复盘。

## 先用 MLP 把训练回路跑通

第一个 lab（`week-01-pytorch-basics`）不碰语言模型。任务是拟合 `y = sin(x) + 0.3 * cos(3x)`，输入均匀落在 `[-2π, 2π]`，加了一点噪声。模型是三层 MLP，`1 → 64 → 64 → 1`，Tanh 激活：

```python
class TinyMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(1, 64),
            nn.Tanh(),
            nn.Linear(64, 64),
            nn.Tanh(),
            nn.Linear(64, 1),
        )

    def forward(self, x):
        return self.net(x)
```

训练循环大致是下面几行：

```python
pred = model(x_train[idx])          # 前向
loss = loss_fn(pred, y_train[idx])  # 算误差
optimizer.zero_grad()               # 清上一步的梯度
loss.backward()                     # 反向
optimizer.step()                    # 更新
```

权重一开始是随机的；前向计算得到预测，loss 衡量预测和答案差了多少，`backward()` 给权重算梯度，`step()` 用梯度更新权重。后面换成语言模型，基本回路仍然是这几步。

800 步跑完，真实输出：

```text
step 0001 | train_loss=0.57724 | val_loss=0.35146
step 0100 | train_loss=0.08547 | val_loss=0.25838
step 0300 | train_loss=0.06590 | val_loss=0.64648
step 0800 | train_loss=0.00640 | val_loss=0.24745
```

train loss 一路降到 0.0064，val loss 则明显上下波动。训练语言模型时日志里两个 loss 要分开看，最早的直觉就来自这种小实验。先有体感。`zero_grad` 那一行漏掉，梯度会一直累积，后面的 loss 曲线基本就是玄学。

## TinyGPT：能跑的最小骨架

第二个 lab（`week-05-tiny-gpt`）把整套结构搭起来。语料是一段重复 40 次的小文本，字符级 tokenizer，词表 23。模型要做的是预测下一个字符：如果输入 ID 是 `[10, 20, 30]`，目标就是原序列往后错一位的 `[20, 30, 40]`。每个位置都会输出一组词表分数，叫 logits；它和目标 ID 一起计算 loss，再走刚才见过的反向传播回路。

整体数据流：

![Transformer 整体数据流](arch.svg)

这里先把 attention 和 MLP 当成图里的两个模块，不急着展开公式。输入是 `(B, S)` 的字符 ID，模型输出 `(B, S, 23)` 的 logits；拿右移一位的 ID 算 loss，再反向传播、更新权重。看训练脚本时，先盯住这一条链路就够了。

TinyGPT 的 block 把 attention 和 MLP 的输出加回原向量，输入输出始终是 `(B, S, D)`。它还给每个 token 加了一张可学习的位置向量表。后面会把这些做法逐个拆开，再对照 A1 改成自己写的版本。

跑 300 步，loss 从 3.35 到 0.10，生成结果已经像模像样：

```text
anguage models predich tokens from previous tokens. attention lets each token read useful
earlier tokens. agents plan actions observe results and update context. language models pre
```

这个 0.10 有水分：语料本身重复了 40 次，模型基本是背下来的。这个 lab 的意义在于验证 shape 和梯度路径是通的。至少现在我们知道后面那些模块在服务什么：它们把 token ID 逐步加工成下一 token 的 logits。

能跑归能跑，这个骨架用的是 `nn.Linear`、`nn.LayerNorm`、可学习位置编码和 GELU，属于 GPT-2 那一代的默认搭配。A1 要自己实现基础模块，并换上 RMSNorm、RoPE 和 SwiGLU。

## 文本怎么变成 token：从 UTF-8 到 BPE

TinyGPT 用字符级 tokenizer 热身，一个字符对应一个 ID，写起来方便。正式模型要处理英文、中文、标点、空格，还有从没出现过的新词。直接给每个 Unicode 字符分配 ID，词表会很大；按完整单词切，又会碰到词表外的词。CS336 A1 用的是 byte-level BPE：从 256 种单字节值起步，再从语料里学习常见的字节组合。

### 字符和字节先分清

ASCII 的 `A` 在 UTF-8 里只占一个字节；汉字「中」编码后是 `E4 B8 AD`，占三个字节。Python 里的 `str` 是字符序列，`bytes` 才是编码后的字节序列：

```python
>>> list("中".encode("utf-8"))
[228, 184, 173]
```

BPE 的初始词表包含 `0..255` 这 256 个单字节 token。UTF-8 文本总能先拆成这些 token，后面学到的 token 可以对应多个字节，也可以横跨几个字符。**token、字符、字节是三种不同的单位。** 以后说上下文长度是 128，数的是 token，不能直接理解成 128 个字或 128 个 byte。

### 先预分词，再学合并规则

A1 给了一条 GPT-2 风格的正则做预分词，把文本切成带前导空格的单词、数字、标点等片段。BPE 只在各个片段内部合并。代码里的核心正则是：

```python
PATTERN = r"""'(?:[sdmt]|ll|ve|re)| ?\p{L}+| ?\p{N}+| ?[^\s\p{L}\p{N}]+|\s+(?!\S)|\s+"""
```

训练时先数每种 pre-token 出现多少次，再把它们转成 UTF-8 字节序列。假设片段 `abab` 出现 5 次，序列是 `(b"a", b"b", b"a", b"b")`，那么 pair `(b"a", b"b")` 在这个片段里出现两次，给全局计数贡献的是 **10 次**。只数一次会把语料频率丢掉，合并顺序也会变。

每轮找出现次数最多的相邻 pair，把两段 bytes 拼成新 token，记录到 `vocab` 和 `merges`，再更新所有片段中的 token 序列。`merges` 的顺序必须留住：编码新文本时还要按学习时的顺序应用。遇到相同频次，A1 还有确定的字典序规则，这种细节最适合拿一个很小的样例验证。

特殊 token 更容易踩坑。以 `<|endoftext|>` 为例，它表示文档边界，应该作为一个整体进入词表。训练 BPE 前先按它切开文本，标记内部不参与 pair 统计，标记两侧也不能被合并。边界不能跨。只在词表里多加一项，还没处理完这个 token 对训练过程的影响。

当前 [BPE 实现](https://github.com/fengye404/cs336-assignment/blob/main/assignment1/cs336_basics/bpe.py) 是便于核对规则的直接写法：每轮重新统计 pair。它通过了小样例和速度测试，但会把语料读进内存；处理完整语料时还得考虑并行预分词、增量更新 pair 计数和内存占用。先把规则写对，再优化热点。

### 训练完词表，还要能编码和解码

`train_bpe` 的结果是 `vocab: ID → bytes` 和有序的 `merges`。给定新文本，tokenizer 要先识别特殊 token，再做同样的预分词；普通片段拆成 UTF-8 单字节 token，按 `merges` 顺序合并，最后查词表得到整数 ID。decode 则拿 ID 找回 bytes，拼起来之后统一做 UTF-8 解码。

这里别逐 token 解码。一个 token 的 bytes 可能只是某个汉字 UTF-8 编码的一部分，单独解码会失败。先拼接全部 bytes，遇到非法序列再按作业要求用替代字符处理。大文件还需要 `encode_iterable` 逐步产出 ID，避免一次加载全文。

我主要用普通英文、中文、包含 `<|endoftext|>` 的文本检查往返编码，也跑了 A1 的对应测试。当前仓库的 BPE 和 tokenizer 测试有 26 项通过，另两项内存测试在 macOS 上按测试配置跳过。到这里，原始文本已经变成模型能接收的整数序列，接下来才轮到 Transformer。

## 对照 A1：给 TinyGPT 换零件

把 TinyGPT 和 A1 的要求列出来，差异就几处：

| 组件 | TinyGPT（lab） | Assignment1（要手写） | 换的原因 |
|------|---------------|----------------------|---------|
| Linear | `nn.Linear`，带 bias | 手写无 bias 版本 | 把权重形状和初始化摆到台面上 |
| Embedding | `nn.Embedding` | 手写查找表 | 看清 ID 如何变成向量 |
| 归一化 | LayerNorm | RMSNorm | 沿最后一维控制数值尺度 |
| 位置编码 | 可学习的绝对位置 | RoPE，作用在 q/k 上 | 把位置放进 attention 分数的计算 |
| FFN | GELU，两层 Linear | SwiGLU，三层 Linear | 加一条门控分支 |
| 残差结构 | pre-LN | pre-norm | block 的输入输出形状保持一致 |

残差和 pre-LN 不用动，骨架是好的。

作业要求自己写 Linear、Embedding、softmax 等基础操作。初始化、bias、dtype 这些细节平时被框架藏起来，自己写一次才知道哪里可能出问题。

`cs336-assignment` 里的 `model.py` 注释比代码多。RoPE 那段，旋转矩阵推一遍、两两配对拆一遍，最后才落成逐元素公式。

## Linear 和 Embedding

Linear 在这份作业里只有矩阵乘法和受控初始化，没有 bias：

```python
class Linear(nn.Module):
    def __init__(self, in_features, out_features, device=None, dtype=None):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        std = math.sqrt(2.0 / (in_features + out_features))
        self.W = nn.Parameter(
            torch.empty(out_features, in_features, device=device, dtype=dtype)
        )
        nn.init.trunc_normal_(self.W, mean=0.0, std=std, a=-3 * std, b=3 * std)

    def forward(self, x):
        return x @ self.W.T
```

初始化标准差按作业要求取 `sqrt(2 / (d_in + d_out))`，并截断在 ±3σ。权重形状是 `(out_features, in_features)`，前向要转置；输入前面带多少个 batch 维，矩阵乘法都会作用在最后一维。

Embedding 是一张查找表：

```python
class Embedding(nn.Module):
    def __init__(self, vocab_size, d_model, device=None, dtype=None):
        super().__init__()
        self.embedding = nn.Parameter(
            torch.empty(vocab_size, d_model, device=device, dtype=dtype)
        )
        nn.init.trunc_normal_(self.embedding, mean=0.0, std=1.0, a=-3.0, b=3.0)

    def forward(self, token_ids):
        return self.embedding[token_ids]
```

输入 token IDs 的形状是 `(B, S)`，查完表就是 `(B, S, D)`。这张表初始时并没有人替它填好「语义」，里面的向量会在训练中更新。

## RMSNorm

归一化做两件事：把激活值的尺度拉回来，再乘一个可学习的缩放。LayerNorm 减均值、除标准差；RMSNorm 省掉了减均值，也没有 bias。

RMSNorm 只按最后一维计算均方根，所以输入输出都是 `(B, S, D)`。它省掉了减均值的计算；这里先关心公式和数值精度，具体速度还得看实现和设备。

```python
class RMSNorm(nn.Module):
    def __init__(self, d_model, eps=1e-5, device=None, dtype=None):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d_model, device=device, dtype=dtype))

    def forward(self, x):
        in_dtype = x.dtype
        x = x.to(torch.float32)
        rms = torch.sqrt(x.pow(2).mean(dim=-1, keepdim=True) + self.eps)
        return ((x / rms) * self.weight).to(in_dtype)
```

平方和、均值与缩放先用 fp32 计算，再转回输入 dtype。低精度训练时，这样处理能减少归一化步骤的数值误差。

## Attention

Softmax 先减最大值再算，不然容易溢出：

```python
def softmax(x, dim=-1):
    x = x - x.max(dim=dim, keepdim=True).values
    exp = torch.exp(x)
    return exp / exp.sum(dim=dim, keepdim=True)
```

softmax 对输入整体加常数不变，减最大值不改变结果，纯粹为了数值稳定。

Attention 可以理解成一次带权重的投票：每个 token 决定从哪些历史 token 里各取多少信息。公式是 `softmax(QKᵀ / sqrt(d_k)) V`。这个 `sqrt(d_k)` 不能省：Q 和 K 的每个分量独立时，点积的方差随 `d_k` 线性增长，不缩放 softmax 会被推到饱和区，梯度接近 0。开方之后方差回到 1 附近。

因果 mask 是下三角，第 t 个位置只能看 1 到 t：

```python
def scaled_dot_product_attention(Q, K, V, mask=None):
    d_k = K.shape[-1]
    scores = Q @ K.mT / math.sqrt(d_k)
    if mask is not None:
        scores = scores.masked_fill(~mask, float("-inf"))
    return softmax(scores, dim=-1) @ V
```

被掩掉的位置填 `-inf`，softmax 之后就是 0。前提是每行至少有一个位置可见，因果 mask 的对角线保证了这个前提。上 padding mask 的时候要小心，整行全 `-inf` 会算出 nan。

多头就是把上面这套并行跑 H 份：

![Attention 的形状流转](attention-shapes.svg)

TinyGPT 把 qkv 放在一次投影里算，A1 拆成三个 Linear，对照公式更直观。设 `D` 是模型宽度，`H` 是 head 数量，`d_k=D/H`，形状会这样变化：

```text
x:       (B, S, D)
q/k/v:   (B, S, D)
拆多头:   (B, H, S, d_k)
scores:  (B, H, S, S)
拼回来:   (B, S, D)
```

拆多头时先把最后一维分成 `(H, d_k)`，再把 `H` 转到序列维前面。Attention 算完还要转回来，并经过输出 Linear。把这几个 shape 标在代码旁边，比背一遍公式更能防止写错。

## RoPE

TinyGPT 的位置信息是查表来的。RoPE（Rotary Position Embedding，来自 RoFormer）换了个思路：把 q 和 k 的每两个分量当成复平面上的一个点，按 token 的位置旋转一个角度。

![RoPE 的旋转示意](rope.svg)

位置 m 的旋转角是 `m * θ`，位置 n 的旋转角是 `n * θ`，两个向量做点积时角度相减，只剩 `(m - n) * θ`。结果只跟相对距离有关。语料里"前一个词"这种关系，不应该因为句子变长就改变。

先把每个位置的 cos/sin 预计算出来：

```python
class RotaryPositionalEmbedding(nn.Module):
    def __init__(self, theta, d_k, max_seq_len, device=None):
        super().__init__()
        self.d_k = d_k
        inv_freq = 1.0 / (theta ** (torch.arange(0, d_k, 2, device=device).float() / d_k))
        positions = torch.arange(max_seq_len, device=device).float()
        angles = torch.outer(positions, inv_freq)   # (S, d_k / 2)
        self.register_buffer("cos_table", angles.cos())
        self.register_buffer("sin_table", angles.sin())
```

`theta` 控制不同分量对的旋转速度：前面的转得快，管近距离；后面的转得慢，管远距离。

应用旋转时把最后一维两两分组，每组当二维向量转：

```python
    def forward(self, x, token_positions):
        # x: (..., seq_len, d_k)，q/k 比位置多一个 head 维
        cos = self.cos_table[token_positions].repeat_interleave(2, dim=-1)
        sin = self.sin_table[token_positions].repeat_interleave(2, dim=-1)
        even, odd = x.unflatten(-1, (-1, 2)).unbind(-1)
        x_rotated = torch.stack((-odd, even), dim=-1).flatten(-2)
        return x * cos + x_rotated * sin
```

`repeat_interleave(2)` 是把每对分量共用的 cos/sin 复制两份，`unflatten + unbind` 取出偶数、奇数分量，`stack((-odd, even))` 就是二维旋转里的 `(-y, x)`。

这里使用相邻两个分量配对。具体代码和参考权重必须采用同一种配对顺序，顺序混用时即使张量形状全对，数值也会错。

相对位置这个性质可以直接测出来，不用等训练：

```python
rope = RotaryPositionalEmbedding(d_k=16, theta=10000.0, max_seq_len=64)
base_q = torch.randn(1, 1, 1, 16).expand(1, 1, 8, 16)
base_k = torch.randn(1, 1, 1, 16).expand(1, 1, 8, 16)
positions = torch.arange(8).expand(1, 8).unsqueeze(1)
qr = rope(base_q, positions)
kr = rope(base_k, positions)

# 位置 (2, 1) 和 (5, 4) 的相对距离都是 1，点积应该相等
a = (qr[0, 0, 2] * kr[0, 0, 1]).sum()
b = (qr[0, 0, 5] * kr[0, 0, 4]).sum()
torch.testing.assert_close(a, b)   # 验证通过
```

接回多头 Attention 时，RoPE 只作用在 q 和 k 上，v 不旋转。位置下标原本是 `(B, S)`，q/k 是 `(B, H, S, d_k)`；查 cos/sin 表前给位置下标补一个 head 轴，变成 `(B, 1, S)`，结果才能广播到所有 head。坑在这里。我重新用 `B=2` 跑本地模型，当前实现仍在这一步报错；之前 `B=1` 能跑，掩盖了这个问题。

## SwiGLU：每个位置自己的前馈网络

Attention 让 token 从前文读取信息，block 里还需要一条对每个位置分别工作的前馈网络。原始 Transformer 使用两层 Linear 和 ReLU；A1 使用 SwiGLU，多出一条门控分支：

```text
SwiGLU(x) = W₂(SiLU(W₁x) ⊙ W₃x)
SiLU(x)   = x · sigmoid(x)
```

`W₁` 和 `W₃` 都把 `D` 升到 `d_ff`，两路结果逐元素相乘，`W₂` 再把宽度降回 `D`。代码里最值得看的是最后一行：

```python
def forward(self, x):
    return self.w2(silu(self.w1(x)) * self.w3(x))
```

为什么 `d_ff` 常取约 `8D/3`？传统两层 FFN 如果隐藏宽度是 `4D`，两个矩阵约有 `8D²` 个参数。SwiGLU 有三个矩阵，取 `d_ff≈8D/3` 时也约是 `8D²`。这样比较不同 FFN 时，参数量不会差太多。实际实现还会把宽度取整到 64 的倍数。

## 把 block 和完整模型装起来

一个 pre-norm block 有两次残差相加：

```python
def forward(self, x, token_positions):
    x = x + self.attention(self.norm1(x), token_positions)
    x = x + self.ffn(self.norm2(x))
    return x
```

RMSNorm 不改变形状，Attention 和 SwiGLU 也都把输出带回 `(B, S, D)`，所以两次相加都能成立。残差保留原输入，让子层在原向量的基础上更新表示。这里的 `pre-norm` 指先归一化，再进入 attention 或 FFN。

![pre-norm 残差结构](block.svg)

完整 Transformer LM 在前面接 token embedding，中间叠 `L` 个 block，后面再接 RMSNorm 和 LM head：

```text
输入 token IDs        (B, S)
→ Embedding           (B, S, D)
→ Transformer Block×L (B, S, D)
→ RMSNorm             (B, S, D)
→ LM head             (B, S, V)
```

其中 `V` 是词表大小。输出的 `(B, S, V)` 就是 TinyGPT 那一节见过的 logits，每个位置都有一组预测下一 token 的分数。A1 的模型没有另加可学习的位置 embedding，位置由各层 attention 内部的 RoPE 处理。

这也是我觉得前面两个 lab 有必要的原因：看到 logits 时，我们已经知道它可以和右移一位的目标算 loss；生成时则取最后一个位置的 logits，选出下一个 token，再接回输入。后面做正式训练会展开这些步骤，这一篇先把模型前向接稳。

### 参数量和计算量也要对得上

不带 bias、输入 Embedding 与输出 LM head 不共享权重时，参数量是：

```text
2VD + L × (4D² + 3D·d_ff + 2D) + D
```

`2VD` 是输入 embedding 与 LM head，`4D²` 是每层 attention 的 q、k、v、输出四个投影，`3D·d_ff` 是 SwiGLU，`2D` 是两层 RMSNorm，最后一个 `D` 是模型末尾的 RMSNorm。拿 `V=256、D=256、L=4、d_ff=704` 代入，得到 `3,344,640` 个参数，和本地 `sum(p.numel() for p in model.parameters())` 对得上。数字对上了。以后对不上，就回去查漏层或重复建层。

参数量还解释不了长序列的成本。四个 attention 投影的计算随 `B·S·D²` 增长，QKᵀ 和对 V 加权随 `B·S²·D` 增长；SwiGLU 的矩阵乘法随 `B·S·D·d_ff` 增长。上下文长度 `S` 增大时，attention 的平方项不能随手忽略。

### 最后怎么确认它真接通了

我先跑组件测试，再检查完整模型输出是 `(B, S, V)`。改动输入序列的后半段，前半段 logits 应当不变；这个因果性检查能直接抓到 mask 写反的问题。RoPE 还可以用两组相同相对距离的位置验证点积，参数量则用上面的公式核对。

当前仓库的 `test_transformer_lm` 和截断输入测试能够通过，但我另外加的 `B=2` 前向检查揭出了上面的广播问题；单独的 SwiGLU、SiLU 测试适配器也还需要补齐。模型主路径跑通和所有输入形状都处理正确，还得分别验证。

## 后记

到这里，文本能经过 BPE 变成 token ID，再经过自己写的 Transformer 变成下一 token 的 logits。回头看开头的小 TinyGPT，训练时那几行代码消费的东西终于有了具体形状。

上次有这种把书上的系统搬到终端里的感觉，还是做 MIT 6.824 的 lab。那时主要盯日志和网络分区，现在盯的是 token 边界、张量形状和数值。下一篇再接着写正式训练：交叉熵、AdamW、数据加载、checkpoint，还有模型跑起来之后该怎么判断结果。

---

参考资料：

- [CS336: Language Modeling from Scratch](https://cs336.stanford.edu/)
- [Assignment 1: Basics](https://github.com/stanford-cs336/assignment1-basics/tree/main)
- [cs336-study（lab 仓库）](https://github.com/fengye404/cs336-study)
- [cs336-assignment（A1 实现）](https://github.com/fengye404/cs336-assignment)
- [RoFormer: Enhanced Transformer with Rotary Position Embedding](https://arxiv.org/abs/2104.09864)
- [Root Mean Square Layer Normalization](https://arxiv.org/abs/1910.07467)
- [GLU Variants Improve Transformer](https://arxiv.org/abs/2002.05202)
