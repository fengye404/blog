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

> 本文由 AI 参与创作

## 前言

最近我在学 CS336「Language Modeling from Scratch」，斯坦福开的大语言模型构建课程。这门课在 X 上讨论度很高，但中文社区里完整分享学习过程的还不多，所以我想边学边写这个系列，把整个过程记录下来，也当作自己的学习笔记。

先叠个甲：我之前的背景是纯工程开发，25 年初开始转 Agent 方向，没有受过系统的机器学习训练。

这门课名字里的 from Scratch 是从零手搓的意思，课程本身不会从零教学。讲义默认你有神经网络和数学基础，对纯工程背景的人来说，学起来是要补不少课的。这也是我写这个系列的原因，尽量把工程同学会卡住的地方讲透。

这一篇是系列的第一篇，跟随 CS336 Assignment1 的思路，完整走一遍从零手搓 Transformer 的过程。不过我不会一上来就讲组件，而是先用自己写的一组小 lab 建立体感，再进 A1 的实现。先说明一点：最终目标不是复刻 2017 年那篇原始论文，CS336 要求实现的是现在真正在用的结构，pre-norm、RMSNorm、RoPE、SwiGLU 都会出现。这些变体为什么换、换完有什么收益，本身就是这门课最有价值的部分。文中代码都在本机跑过，测试方法一并写出来。

Assignment1 的原始资料在[这里](https://github.com/stanford-cs336/assignment1-basics/tree/main)。课程 honor code 要求独立完成实现，在跟课的同学先自己写，这篇当作复盘参考。

## 为什么要学习这个

动手之前先回答一个问题：都 2026 年了，模型 API 一个比一个强，为什么还要花时间学底层？

CS336 的课程导论里给过答案：把语言模型当成黑盒，能做的事情就止步于调 API 和改 prompt；理解内部结构，才能判断什么问题该交给模型，什么问题该在模型外面解决。

这个判断放到 Agent 开发上更具体。我今年做的一直是 Agent 相关的工作，见过很多问题表面看是 prompt 没写好，往深了挖是模型的行为边界没搞清楚。举几个例子：长上下文方案该硬塞还是做检索，取决于模型训练时的序列长度和位置编码是怎么设计的；推理成本和并发吞吐，取决于 KV cache 随序列怎么增长。再往下还有 tokenizer 的切分方式，它直接决定工具调用参数里那些空格和转义长什么样。

这些问题的答案都在模型内部。我之前也把 LLM 当魔法黑盒 API，模型不听话的时候就靠试。理解了底层，至少知道该往哪个方向试。说白了，Agent 和 harness 工程的上限，取决于你对模型行为的预判能力。

下面进入正题。

## 1. 学习路线：先把 lab 跑通，再啃 assignment

我给自己搭了两个仓库。

一个是 [cs336-study](https://github.com/fengye404/cs336-study)，里面是我自己写的小 lab。每个 lab 只解决一个小问题，代码短，有引导，跑完能立刻看到 shape 和数字。

另一个是 [cs336-assignment](https://github.com/fengye404/cs336-assignment)，放官方作业的实现。A1 的脚手架很少，拿到手就是一堆测试和一个 PDF，直接开写很容易懵。

所以我的学习顺序是固定的三层：

- 先扫一遍 lecture，知道这个概念解决什么问题
- 再去 lab 里把它变成能跑的代码，把 shape 对上
- 等几个相关 lab 都熟了，才回 assignment 里写正式实现

官方 A1 的测试很严格，直接上的话，光是搞清楚 `Linear` 为什么要自己实现初始化就要卡半天。先跑 lab 的好处是，每个组件你都先见过一个能跑的简化版本，后面再看正式实现，注意力会放在设计取舍上。

这篇只讲 Transformer 这部分，路线也是一样的：先用 lab 里的 MLP 和 TinyGPT 建立训练和结构的体感，再对照 A1 的要求把玩具版本换成现代组件。

## 2. 热身：一个 MLP 把训练回路跑通

第一个 lab（`week-01-pytorch-basics`）连语言模型都不碰，就练训练循环。

任务是一个回归问题：拟合 `y = sin(x) + 0.3 * cos(3x)`，输入均匀分布在 `[-2π, 2π]`，加一点噪声。模型是最普通的三层 MLP，`1 → 64 → 64 → 1`，激活用 Tanh：

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

训练循环是全篇最重要的东西，后面所有 LLM 训练代码都是这四步的重复：

```python
pred = model(x_train[idx])          # 前向：拿预测
loss = loss_fn(pred, y_train[idx])  # 算误差
optimizer.zero_grad()               # 清掉上一步的梯度
loss.backward()                     # 反向：算梯度
optimizer.step()                    # 更新参数
```

跑 800 步，真实输出是这样：

```text
step 0001 | train_loss=0.57724 | val_loss=0.35146
step 0100 | train_loss=0.08547 | val_loss=0.25838
step 0300 | train_loss=0.06590 | val_loss=0.64648
step 0800 | train_loss=0.00640 | val_loss=0.24745
```

train loss 一路降到 0.0064，val loss 在 100 步之后开始上下弹。这个分叉值得盯一眼：模型已经开始记噪声了，训练集上的漂亮数字不再代表泛化能力。

这个现象后面还会出现。语言模型的训练日志里，train loss 和 val loss 要分开看，就是从这里来的直觉。

## 3. Tiny GPT：先有一个能跑的完整骨架

热完身，第二个 lab（`week-05-tiny-gpt`）把整套结构搭起来。语料是一段重复 40 次的小文本，字符级 tokenizer，词表 23。

模型结构和 GPT-2 是一个路子：

```text
token ids (B, S)
  → token embedding + position embedding   (B, S, D)
  → 2 × Block
       LayerNorm → CausalSelfAttention → 残差
       LayerNorm → MLP(GELU)            → 残差
  → LayerNorm
  → lm_head                                (B, S, V)
logits
```

三个关键点，代码都在 lab 里：

attention 用一次投影算出 qkv，拆成多头，下三角 mask 挡住未来，softmax 之后加权求和：

```python
q, k, v = self.qkv(x).chunk(3, dim=-1)
q = q.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
k = k.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
v = v.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)

scores = q @ k.transpose(-2, -1) / math.sqrt(self.head_dim)
scores = scores.masked_fill(self.mask[:seq_len, :seq_len] == 0, float("-inf"))
weights = F.softmax(scores, dim=-1)
out = weights @ v
```

block 是 pre-LN 结构，`x + 子层(LN(x))`，残差保证输入输出都是 `(B, S, D)`：

```python
def forward(self, x):
    x = x + self.attn(self.ln1(x))
    x = x + self.mlp(self.ln2(x))
    return x
```

位置信息用可学习的绝对位置 embedding，和 token embedding 直接相加：

```python
x = self.token_embedding(idx) + self.position_embedding(positions)
```

跑起来，300 步，loss 从 3.35 降到 0.10，生成结果已经像模像样：

```text
anguage models predich tokens from previous tokens. attention lets each token read useful
earlier tokens. agents plan actions observe results and update context. language models pre
```

这里得诚实一点：语料本身是重复的，loss 能压到 0.10 基本是背下来了，不代表模型学会了什么。这个 lab 的目标是验证结构能跑、shape 没写错，不是看泛化。

到现在为止，训练回路和 Transformer 骨架都有了。但这个小 GPT 用的是 `nn.Linear`、`nn.LayerNorm`、可学习位置编码和 GELU FFN，属于 GPT-2 那一代的默认搭配。A1 要求的是现在主流大模型的结构。

## 4. 从玩具到 Assignment1：换掉哪几个零件

把 TinyGPT 和 A1 的要求放在一起，差异只有少数几处：

| 组件 | TinyGPT（lab） | Assignment1（要手写） | 换的原因 |
|------|---------------|----------------------|---------|
| Linear | `nn.Linear`，带 bias | 手写，无 bias，截断正态初始化 | 控制初始化，默认初始化对 Transformer 偏大 |
| Embedding | `nn.Embedding` | 手写查找表 | 作业要求自己实现底层 |
| 归一化 | LayerNorm | RMSNorm | 少一次 reduce，效果几乎不变 |
| 位置编码 | 可学习绝对位置 | RoPE，作用在 q/k 上 | 相对位置，长度外推更好 |
| FFN | GELU，隐藏层 4 倍 | SwiGLU，隐藏层 8/3 倍 | 门控带来收益，参数量对齐 |
| 精度 | 默认 | RMSNorm 内部 upcast fp32 | 混合精度下更稳定 |
| 残差结构 | pre-LN | pre-LN | 一致，不用换 |

残差和 pre-LN 不用动，说明 TinyGPT 的骨架是对的，换的是零件。

为什么作业不让你用 `nn.Linear`？因为一旦用了现成的，初始化、bias、dtype 这些全被藏起来了。手写一遍，你才会认真对待 `std = sqrt(2 / (d_in + d_out))` 这种细节，后面调模型的时候才知道该看哪里。

下面按 A1 的顺序，一个一个实现。

## 5. Linear 与 Embedding

Linear 就是不带 bias 的仿射变换，加上一个受控的初始化：

```python
class Linear(nn.Module):
    def __init__(self, in_features, out_features, device=None, dtype=None):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        std = math.sqrt(2.0 / (in_features + out_features))
        self.weight = nn.Parameter(
            torch.empty(out_features, in_features, device=device, dtype=dtype)
        )
        nn.init.trunc_normal_(self.weight, mean=0.0, std=std, a=-3 * std, b=3 * std)

    def forward(self, x):
        return x @ self.weight.T
```

PyTorch 默认的初始化对 Transformer 来说偏大，深层网络叠加之后激活值容易爆掉。这里按 Xavier 的思路，从标准差为 `sqrt(2 / (d_in + d_out))` 的正态分布里采样，并截断在 ±3σ，防止个别 outlier 权重把训练带偏。

权重形状是 `(out_features, in_features)`，前向时转置一下，和 `nn.Linear` 保持一致。

Embedding 是一张查找表，初始化用标准正态截断：

```python
class Embedding(nn.Module):
    def __init__(self, vocab_size, d_model, device=None, dtype=None):
        super().__init__()
        self.weight = nn.Parameter(
            torch.empty(vocab_size, d_model, device=device, dtype=dtype)
        )
        nn.init.trunc_normal_(self.weight, mean=0.0, std=1.0, a=-3.0, b=3.0)

    def forward(self, token_ids):
        return self.weight[token_ids]
```

这种自己定义权重、手动控制初始化的写法，让我想起刚学 Java 那会第一次调线程池参数。`corePoolSize` 和 `maxPoolSize` 也是两个数各管一段，配错了表面上也能跑，压力上来才出问题。初始化同样是这个性质，训练前期看不出差别，步数多了才分得出高下。

## 6. RMSNorm

归一化层做两件事：把激活值的尺度拉回稳定范围，再乘一个可学习的缩放。LayerNorm 是减均值、除标准差；RMSNorm 省掉了减均值，只除以均方根（root mean square），也没有 bias。

这个改动其实挺激进：减均值在 LayerNorm 里被当成必要步骤。但实验下来，去掉它对最终效果影响很小，换来的是少一次 reduce，kernel 更快。LLaMA 之后的模型基本都换成了它。

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
        return (x / rms).to(in_dtype) * self.weight
```

中间转到 fp32 是踩过坑的：模型跑 bf16 时，平方和累加的精度不够，几百步之后 loss 会开始抖。转成 fp32 算完再转回来，这点开销换稳定性很值。

## 7. RoPE

TinyGPT 用的是可学习的绝对位置 embedding，把位置当成"第几个 token"查表。RoPE（Rotary Position Embedding，来自 RoFormer）换了个思路：把 q 和 k 的每两个分量看成复平面上的一个点，按 token 的位置旋转一个角度。

位置是 m 时，第 i 对分量的旋转角是 `m * θ_i`。查询向量旋转 `m * θ`，键向量旋转 `n * θ`，两者做点积时角度相减，只剩 `(m - n) * θ`。点积结果只依赖两个 token 的相对距离，跟绝对位置无关。这个性质对语言很合理："前一个词"这个关系不应该因为句子变长而改变。

先把每个位置的 `cos` 和 `sin` 预计算出来：

```python
class RotaryPositionalEmbedding(nn.Module):
    def __init__(self, d_k, theta, max_seq_len, device=None):
        super().__init__()
        self.d_k = d_k
        inv_freq = 1.0 / (theta ** (torch.arange(0, d_k, 2, device=device).float() / d_k))
        positions = torch.arange(max_seq_len, device=device).float()
        angles = torch.outer(positions, inv_freq)   # (S, d_k / 2)
        self.register_buffer("cos_table", angles.cos())
        self.register_buffer("sin_table", angles.sin())
```

`theta` 控制不同分量对旋转的快慢：前面的分量转得快，负责近距离区分；后面的分量转得慢，负责远距离。

应用旋转的时候，把最后一维按两两一组切开，每组当成二维向量旋转：

```python
    def forward(self, x, token_positions):
        # x: (..., seq_len, d_k)，q/k 比位置多一个 head 维
        cos = self.cos_table[token_positions].repeat_interleave(2, dim=-1)
        sin = self.sin_table[token_positions].repeat_interleave(2, dim=-1)
        even, odd = x.unflatten(-1, (-1, 2)).unbind(-1)
        x_rotated = torch.stack((-odd, even), dim=-1).flatten(-2)
        return x * cos + x_rotated * sin
```

`repeat_interleave(2)` 是把每对分量共用的 cos/sin 复制成两份，好让它们和 `x` 逐元素相乘。`unflatten + unbind` 拿到偶数和奇数位置，`stack((-odd, even))` 实现二维旋转里的 `(-y, x)`。

这里用的是相邻配对的约定，也是 A1 handout 和 GPT-NeoX 的写法。HuggingFace 的 LLaMA 实现用的是"前后对半"配对，两者等价，只是排列不同，别混用就行。

相对位置这个性质值得写个测试确认，不然后面 RoPE 写错了很难发现：

```python
base_q = torch.randn(1, 1, 1, d_k).expand(1, 1, 8, d_k)
base_k = torch.randn(1, 1, 1, d_k).expand(1, 1, 8, d_k)
positions = torch.arange(8).expand(1, 8).unsqueeze(1)
qr = rope(base_q, positions)
kr = rope(base_k, positions)

# 位置 (2, 1) 和 (5, 4) 的相对距离都是 1，点积应该相等
a = (qr[0, 0, 2] * kr[0, 0, 1]).sum()
b = (qr[0, 0, 5] * kr[0, 0, 4]).sum()
torch.testing.assert_close(a, b)   # 验证通过
```

## 8. Attention

Softmax 是第一个要小心的实现。直接指数容易溢出，标准做法是每行减去最大值再算：

```python
def softmax(x, dim=-1):
    x = x - x.max(dim=dim, keepdim=True).values
    exp = torch.exp(x)
    return exp / exp.sum(dim=dim, keepdim=True)
```

因为 softmax 对输入整体加常数不变，减最大值不改变结果，纯粹是为了数值稳定。

Scaled dot-product attention 的公式是 `softmax(QKᵀ / sqrt(d_k)) V`。除以 `sqrt(d_k)` 是必要的：Q 和 K 的每个分量独立时，点积的方差随 `d_k` 线性增长，不缩放的话值会很大，softmax 被推到饱和区，梯度接近 0。开方之后方差回到 1 附近。

因果 mask 是一个下三角矩阵，第 t 个位置只能看 1 到 t：

```python
def scaled_dot_product_attention(Q, K, V, mask=None):
    d_k = K.shape[-1]
    scores = Q @ K.mT / math.sqrt(d_k)
    if mask is not None:
        scores = scores.masked_fill(~mask, float("-inf"))
    return softmax(scores, dim=-1) @ V
```

被掩掉的位置填 `-inf`，softmax 之后就是 0。这里有个前提：每一行至少有一个位置可见。因果 mask 的对角线保住了这个前提，如果是 padding mask，得保证每行至少剩一个有效 token，否则整行 `-inf` 会算出 nan。

多头注意力把这套东西并行跑 H 份。TinyGPT 里 qkv 是一次投影出来的，A1 的实现拆成了三个 Linear，更容易对照公式：

```python
class MultiheadSelfAttention(nn.Module):
    def __init__(self, d_model, num_heads, theta=None, max_seq_len=None, device=None, dtype=None):
        super().__init__()
        assert d_model % num_heads == 0
        self.d_model = d_model
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        self.W_Q = Linear(d_model, d_model, device=device, dtype=dtype)
        self.W_K = Linear(d_model, d_model, device=device, dtype=dtype)
        self.W_V = Linear(d_model, d_model, device=device, dtype=dtype)
        self.out_proj = Linear(d_model, d_model, device=device, dtype=dtype)
        if theta is not None and max_seq_len is not None:
            self.rope = RotaryPositionalEmbedding(self.head_dim, theta, max_seq_len, device=device)
        else:
            self.rope = None

    def forward(self, x, token_positions=None):
        batch_size, seq_len, _ = x.shape
        if token_positions is None:
            token_positions = torch.arange(seq_len, device=x.device).expand(batch_size, seq_len)
        q = self.W_Q(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.W_K(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.W_V(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        if self.rope is not None:
            # token_positions: (B, S) -> (B, 1, S)，给 head 维留出广播位置
            positions = token_positions.unsqueeze(1)
            q = self.rope(q, positions)
            k = self.rope(k, positions)
        mask = torch.tril(torch.ones(seq_len, seq_len, dtype=torch.bool, device=x.device))
        out = scaled_dot_product_attention(q, k, v, mask)
        out = out.transpose(1, 2).contiguous().view(batch_size, seq_len, self.d_model)
        return self.out_proj(out)
```

两个细节。RoPE 只加在 q 和 k 上，v 不加，因为位置信息只需要影响"谁该关注谁"这个匹配过程，不需要改变传递的内容。多头拆分的顺序是 `(B, S, H, head_dim)` 再 transpose 到 `(B, H, S, head_dim)`，顺序别写反。

## 9. SwiGLU

原始 Transformer 的 FFN 是两层线性加 ReLU：`W2(ReLU(W1(x)))`。SwiGLU 加了一个门控，用第三个矩阵控制信息流：

```python
def silu(x):
    return x * torch.sigmoid(x)


class SwiGLU(nn.Module):
    def __init__(self, d_model, d_ff, device=None, dtype=None):
        super().__init__()
        self.w1 = Linear(d_model, d_ff, device=device, dtype=dtype)
        self.w2 = Linear(d_ff, d_model, device=device, dtype=dtype)
        self.w3 = Linear(d_model, d_ff, device=device, dtype=dtype)

    def forward(self, x):
        return self.w2(silu(self.w1(x)) * self.w3(x))
```

`d_ff` 为什么是 `8/3 * d_model`？SwiGLU 有三个矩阵，比 ReLU FFN 多一个。为了让两者的参数量接近，把隐藏层宽度从 `4d` 缩到 `8/3 d`，`3 * d * (8/3 d) = 8d²` 正好对上 `2 * d * 4d = 8d²`。再向上取到 64 的倍数，让 kernel 少处理一些尾块：

```python
def default_d_ff(d_model):
    return 64 * math.ceil((8 / 3 * d_model) / 64)
```

消融实验里要对比的 GELU FFN 就是去掉门控的两矩阵版本，隐藏层宽度取 `4d` 才能和 SwiGLU 参数对齐：

```python
class GELUFFN(nn.Module):
    def __init__(self, d_model, d_ff, device=None, dtype=None):
        super().__init__()
        self.w1 = Linear(d_model, d_ff, device=device, dtype=dtype)
        self.w2 = Linear(d_ff, d_model, device=device, dtype=dtype)

    def forward(self, x):
        return self.w2(F.gelu(self.w1(x)))
```

## 10. 组装 TransformerLM

block 是 Attention 和 FFN 各带一层残差。主流的做法是 pre-norm：先归一化再进子层，残差路径上不经过任何 norm。为了后面做 ablation，我留了几个开关：

```python
class TransformerBlock(nn.Module):
    def __init__(self, d_model, num_heads, d_ff, theta=None, max_seq_len=None,
                 use_norm=True, pre_norm=True, use_swiglu=True, device=None, dtype=None):
        super().__init__()
        norm = (lambda: RMSNorm(d_model, device=device, dtype=dtype)) if use_norm else (lambda: nn.Identity())
        self.norm1 = norm()
        self.norm2 = norm()
        self.attention = MultiheadSelfAttention(
            d_model, num_heads, theta=theta, max_seq_len=max_seq_len, device=device, dtype=dtype
        )
        self.ffn = SwiGLU(d_model, d_ff, device=device, dtype=dtype) if use_swiglu else GELUFFN(d_model, d_ff, device=device, dtype=dtype)
        self.pre_norm = pre_norm

    def forward(self, x, token_positions=None):
        if self.pre_norm:
            x = x + self.attention(self.norm1(x), token_positions)
            x = x + self.ffn(self.norm2(x))
        else:
            x = self.norm1(x + self.attention(x, token_positions))
            x = self.norm2(x + self.ffn(x))
        return x
```

两种 norm 位置的区别直接体现在梯度上。Post-norm 是 `norm(x + f(x))`，梯度回传时要穿过每一层的 norm，底层拿到的梯度被反复缩放，层数一多就要靠 warmup 和小心调参才能训起来。Pre-norm 的残差路径是一条从输出到输入的直连通道，梯度原样回到浅层，训练稳得多。代价是最后要补一个 norm。

完整的模型和 A1 的结构一一对应：

```python
class TransformerLM(nn.Module):
    def __init__(self, vocab_size, num_layers, d_model, num_heads, d_ff, theta=None, max_seq_len=None,
                 use_norm=True, pre_norm=True, use_swiglu=True, device=None, dtype=None):
        super().__init__()
        self.token_embedding = Embedding(vocab_size, d_model, device=device, dtype=dtype)
        self.layers = nn.ModuleList([
            TransformerBlock(d_model, num_heads, d_ff, theta=theta, max_seq_len=max_seq_len,
                             use_norm=use_norm, pre_norm=pre_norm, use_swiglu=use_swiglu,
                             device=device, dtype=dtype)
            for _ in range(num_layers)
        ])
        self.norm = RMSNorm(d_model, device=device, dtype=dtype) if use_norm else nn.Identity()
        self.lm_head = Linear(d_model, vocab_size, device=device, dtype=dtype)

    def forward(self, token_ids):
        batch_size, seq_len = token_ids.shape
        x = self.token_embedding(token_ids)
        token_positions = torch.arange(seq_len, device=token_ids.device).unsqueeze(0).expand(batch_size, seq_len)
        for layer in self.layers:
            x = layer(x, token_positions)
        x = self.norm(x)
        return self.lm_head(x)
```

注意这里没有可学习的位置 embedding 了，位置信息全部由 RoPE 在 attention 内部处理。

## 11. 算一笔账

工程同学对资源开销应该都有直觉，模型这边也有几个粗略公式。

参数量（无 bias）：`2VD + L * (4D² + 3D*d_ff + 2D) + D`。第一项是输入 embedding 和 `lm_head`，括号里依次是 attention 的四个投影、SwiGLU 的三个矩阵、两个 RMSNorm，最后是最终 norm。

拿本文的配置（V=256，D=256，L=4，d_ff=704）算，一共 3,344,640 个参数，约 3.34M，和 `sum(p.numel() for p in model.parameters())` 分毫不差，可以用这个公式检查实现有没有漏层。

显存预算按"每个参数 16 字节"估：fp32 参数 4 字节、梯度 4 字节、Adam 的 m 和 v 各 4 字节。3.34M 参数就是 53MB，CPU 上都能跑。这个公式放大到 7B 模型：`7e9 * 16 = 112GB`，还没算激活值。这就是为什么大模型训练必须上 ZeRO、FSDP 这类切分方案，单卡 80G 的 H100 连状态都放不下。

计算量：前向每个 token 约 `2N` FLOPs，N 是参数量；反向约 `4N`，加起来训练一个 token 约 `6N`。这是不含 attention 二次项的低估，序列长的时候 attention 开销会顶上来。用这个公式估训练时间和买卡预算，八九不离十。

## 12. 训练与验证

### 12.1 数据

tokenizer 留到下一篇，这里先用最简单的 byte 级编码顶上：把文本文件按字节读进来，每个字节就是一个 token，词表大小 256。字节编码序列长、效率低，但零依赖，验证模型结构足够了。

```python
with open("TinyStoriesV2-GPT4-valid.txt", "rb") as f:
    raw = f.read(8 * 1024 * 1024)
data = torch.frombuffer(bytearray(raw), dtype=torch.uint8).long()
```

取 batch 就是从序列里随机截固定长度的片段，输入是 `[s, s+S)`，标签是右移一位的 `[s+1, s+1+S)`：

```python
def get_batch(data, batch_size, context_length):
    starts = torch.randint(0, len(data) - context_length - 1, (batch_size,))
    x = torch.stack([data[s:s + context_length] for s in starts])
    y = torch.stack([data[s + 1:s + 1 + context_length] for s in starts])
    return x, y
```

### 12.2 先过一遍 sanity check

正式训练之前，先做两件便宜的事。

第一，固定一个 batch 反复训，模型应该能把它背下来，loss 从 `ln(V)` 掉到接近 0。我拿 batch 8、序列 128 试了 200 步，loss 从 6.06 掉到 0.0000。这个检查能过滤掉一大半的低级错误：如果 loss 卡在 5.5 附近不动，多半是标签没右移、mask 写反或者梯度没清零；如果 loss 变 nan，去看初始化和 mask。

第二，验证因果性：改掉序列后面的 token，前面的 logits 不能变。

```python
x2 = x.clone()
x2[0, 40:] = torch.randint(0, 256, (88,))
assert (model(x)[0, :40] - model(x2)[0, :40]).abs().max() < 1e-6
```

### 12.3 正式训练

超参和循环：

```python
model = TransformerLM(vocab_size=256, num_layers=4, d_model=256, num_heads=8,
                      d_ff=default_d_ff(256), theta=10000.0, max_seq_len=128)
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, betas=(0.9, 0.95), weight_decay=0.1)

for step in range(total_steps):
    x, y = get_batch(data, batch_size=16, context_length=128)
    lr = lr_at(step, max_lr=1e-3, min_lr=1e-4, warmup_steps=100, total_steps=600)
    for g in optimizer.param_groups:
        g["lr"] = lr
    loss = cross_entropy(model(x), y)
    optimizer.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    optimizer.step()
```

`betas=(0.9, 0.95)` 是第二矩的衰减调低了，Transformer 的梯度分布比较尖，默认的 0.999 反应太慢。`weight_decay=0.1` 是 AdamW 的解耦权重衰减。梯度裁剪设 1.0，防止个别 batch 把参数带飞。学习率线性 warmup 100 步再余弦退火，原因在 loss 曲线上看得很清楚：训练早期参数离最优点很远，一上来用大学习率容易把权重推到坏区域。

后来我在 CPU 上跑了 600 步，loss 从 5.98 降到 1.06：

```text
step     0 | loss 5.9772 | lr 1.00e-05
step   100 | loss 1.7271 | lr 1.00e-03
step   300 | loss 1.2439 | lr 6.89e-04
step   599 | loss 1.0607 | lr 1.00e-04
```

对照一下：随机猜的 loss 是 `ln(256) ≈ 5.55`，模型已经明显在学东西了。这个数字比 TinyGPT 的 0.10 高不少，因为一个是背固定语料，一个是在 8MB 真实文本上学 next-token prediction，任务难得多。

A1 要求的正式训练是在 BPE 之后的 TinyStories 上跑完整模型，那部分的细节（BPE、数据管线、正式验证）放到下一篇。

## 13. Ablation：A1 的四组对照

A1 要求在训好的基础上做四组消融，验证每个设计的必要性。配置开关已经留好了，改一个参数跑一遍就行。我用同一份数据、同一个种子，每组跑 600 步，结果如下：

| 实验 | 改动 | 600 步后 loss | 观察 |
|------|------|--------------|------|
| 基线 | RoPE + RMSNorm + pre-norm + SwiGLU | 1.061 | 对照组 |
| NoPE | `theta=None` | 1.505 | 差距最明显，位置信息确实关键 |
| 去掉 RMSNorm | `use_norm=False` | 1.062 | 起步 loss 是 42.7，50 步内追平 |
| post-norm | `pre_norm=False` | 1.031 | 4 层太浅，差异落在噪声里 |
| GELU FFN（参数对齐） | `use_swiglu=False`，d_ff=1024 | 1.022 | 差异也在噪声里 |
| GELU FFN（d_ff 没对齐） | `use_swiglu=False`，d_ff=704 | 1.191 | 参数少了两成，不能直接比 |

两个结果值得单独说。

去掉 RMSNorm 之后，第 0 步的 loss 是 42.7，基线是 5.98。没有归一化，初始 logits 就是一团乱麻，损失自然大得离谱。但它很快追了上来，600 步后和基线持平。这说明在这个规模下 RMSNorm 的作用主要体现在训练早期的稳定性，而不是最终的 loss 数字。层数更深、学习率更大的时候，它能避免的就可能是直接发散了。

另一个是 post-norm。讲义里说它训练更难、更需要 warmup，但 4 层的短跑里没有体现出来，反而略好一点。这属于噪声，不用过度解读。

短程对比有个坑。

几百步的差异里噪声占比不小，同一个配置两个种子跑出来的差别可能比配置之间的差别还大。判断某个设计有没有用，要么固定种子多跑几次，要么把训练步数拉长。只看单次结果就下结论，容易翻车。

## 14. 踩坑清单

**RoPE 的广播**。这个坑我印象最深：`token_positions` 传的是 `(B, S)`，q 是 `(B, H, S, d)`，cos/sin 算出来是 `(B, S, d)`，直接相乘只有 batch=1 能跑（长度为 1 的轴可以自动广播）。batch 一大于 1 就报错。修法是给位置补一个 head 维：`token_positions.unsqueeze(1)`，让 cos/sin 变成 `(B, 1, S, d)`。

**RMSNorm 的 fp32**。bf16 下平方和累加的精度不够，几百步之后 loss 会开始抖。归一化内部 upcast 到 fp32 再转回来，能解决大部分精度问题。

**mask 整行被遮**。因果 mask 有对角线兜底，属于特例。一旦上 padding mask，要保证每行至少剩一个有效 token，否则整行 `-inf` 算出来就是 nan。

**`optimizer.zero_grad()` 漏了**。梯度一直累积，loss 不降或者乱跳，排查时容易在模型结构里绕圈。

**参数量和公式对不上**。八成是 RMSNorm 的权重没算进去，它们不显眼，但每层有两个。数一遍：`L * 2 * D + D`。

## 后记

写完这套代码，Transformer 对我最大的变化是从"论文里的图"变成了"一堆可以拆开的零件"。每个零件都在回答一个具体问题：初始化为的是训练起步不发散，RMSNorm 为的是尺度稳定，RoPE 为的是相对位置，mask 为的是不能偷看未来。

没有哪个是魔法。

我已经很久没有这样系统学习一门课程了。上一次类似的体验，还是跟着 MIT 6.824 做 lab：看文档、写代码、跑测试，把分布式系统从纸上搬进终端。这次做 CS336 的感觉很像，只是验证标准从测试用例变成了 loss 曲线，调试对象从网络分区变成了张量形状。

如果你也在学 CS336，或者想从工程方向往 Agent 深入一点，希望这篇能帮你省点时间。下一篇写 tokenizer，BPE 的合并逻辑比 attention 更绕，值得单独讲。

---

参考资料：

- [CS336: Language Modeling from Scratch](https://cs336.stanford.edu/)
- [Assignment 1: Basics](https://github.com/stanford-cs336/assignment1-basics/tree/main)
- [我的 lab 仓库 cs336-study](https://github.com/fengye404/cs336-study)
- [我的 A1 实现 cs336-assignment](https://github.com/fengye404/cs336-assignment)
- [RoFormer: Enhanced Transformer with Rotary Position Embedding](https://arxiv.org/abs/2104.09864)
- [Root Mean Square Layer Normalization](https://arxiv.org/abs/1910.07467)
- [GLU Variants Improve Transformer](https://arxiv.org/abs/2002.05202)
