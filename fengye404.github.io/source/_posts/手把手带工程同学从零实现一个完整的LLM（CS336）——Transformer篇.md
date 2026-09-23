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

最近我在学习 CS336「Language Modeling from Scratch」，是斯坦福大学的大语言模型构建课程。这门课程在各种社交媒体（X）中都很火爆，但是在内网似乎没有多少人分享过学习过程，所以我想写一系列文章来分享一下我的学习过程。

虽然课程名字中叫「from Scratch」，但是它的含义是从零手搓，而不是从零教学，因此对于没有过神经网络/机器学习基础的同学来说，学习起来还是比较困难的，需要有较为完善的体系知识。

> 先叠个甲，我之前的背景是纯工程开发，大概在 25 年初开始转向 Agent 开发。

这一篇是这个系列中的第一篇文章，会跟随 CS336 Assignment1 的思路，完整介绍如何从零手搓一个 Transformer（注：并非原始论文版本，其中会引入 RoPE、SwiGLU 等变体，这也是 CS336 这门课程的优秀之处）。

Assignment1 的原始资料：[stanford-cs336/assignment1-basics](https://github.com/stanford-cs336/assignment1-basics/tree/main)。

为了先建立体感，文章开头会先用一组小 lab 热身，再进 A1 的实现。文中代码都在本机跑过，测试方法一并写出来。在跟课的同学先自己写：课程 honor code 要求独立完成实现，这篇当作复盘参考。

## 为什么要学习这个

CS336 的课程导论里解释了为什么现在还需要学习 LLM 底层：语言模型是当前 NLP 应用的地基，从数据、模型结构、训练到评估部署，每个环节的设计取舍都会直接影响最终效果。把模型当成黑盒，能做的事情就止步于调 API 和改 prompt；理解了内部结构，遇到问题时才知道该往哪里查。

目前很多 Agent 开发者（包括之前的我），只把 LLM 当做一个神奇的魔法黑盒 API，而不去了解它的底层，这样的话是做不好 Agent 和 harness 工程的。

举几个例子：长上下文方案该硬塞还是做检索，取决于模型训练时的序列长度和位置编码是怎么设计的；推理成本和并发吞吐，取决于 KV cache 随序列怎么增长。再往下还有 tokenizer 的切分方式，它直接决定工具调用参数里那些空格和转义长什么样。这些问题都指向模型内部。

## 1. 两个仓库

学习材料分两层。[cs336-study](https://github.com/fengye404/cs336-study) 是配套的小 lab，每个只解决一个小问题，代码短，跑完马上能看到 shape 和数字；[cs336-assignment](https://github.com/fengye404/cs336-assignment) 放官方作业的正式实现。

不直接开 assignment 的原因很简单：A1 的脚手架很少，拿到手就是一堆测试加一个 PDF，容易懵。先在 lab 里用简化版本把每个组件过一遍，再回去写正式实现，精力才能放在设计取舍上，不至于卡在某个 shape 里。

后面的顺序：MLP 热身，TinyGPT 搭骨架，对照 A1 换零件。

## 2. 先用 MLP 把训练回路跑通

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

训练循环就四步：

```python
pred = model(x_train[idx])          # 前向
loss = loss_fn(pred, y_train[idx])  # 算误差
optimizer.zero_grad()               # 清上一步的梯度
loss.backward()                     # 反向
optimizer.step()                    # 更新
```

后面所有 LLM 训练代码都是这四步的重复，换的只是数据和模型。

800 步跑完，真实输出：

```text
step 0001 | train_loss=0.57724 | val_loss=0.35146
step 0100 | train_loss=0.08547 | val_loss=0.25838
step 0300 | train_loss=0.06590 | val_loss=0.64648
step 0800 | train_loss=0.00640 | val_loss=0.24745
```

train loss 一路降到 0.0064，val loss 在 100 步左右探到最低点，之后开始上下弹。模型把噪声也一起拟合了。训练语言模型时日志里两个 loss 要分开看，最早的直觉就来自这种小实验。`zero_grad` 那一行漏掉，梯度会一直累积，后面的 loss 曲线基本就是玄学。

## 3. TinyGPT：能跑的最小骨架

第二个 lab（`week-05-tiny-gpt`）把整套结构搭起来。语料是一段重复 40 次的小文本，字符级 tokenizer，词表 23。整体数据流：

![Transformer 整体数据流](arch.svg)

attention 一次投影算出 qkv，拆多头，下三角 mask 挡住未来：

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

block 是 pre-LN，残差保证输入输出都是 `(B, S, D)`：

```python
def forward(self, x):
    x = x + self.attn(self.ln1(x))
    x = x + self.mlp(self.ln2(x))
    return x
```

位置信息用可学习的位置 embedding，直接和 token embedding 相加：

```python
x = self.token_embedding(idx) + self.position_embedding(positions)
```

跑 300 步，loss 从 3.35 到 0.10，生成结果已经像模像样：

```text
anguage models predich tokens from previous tokens. attention lets each token read useful
earlier tokens. agents plan actions observe results and update context. language models pre
```

这个 0.10 有水分：语料本身重复了 40 次，模型基本是背下来的，不代表学会了。这个 lab 的意义在于验证 shape 和梯度路径是通的。

能跑归能跑，这个骨架用的是 `nn.Linear`、`nn.LayerNorm`、可学习位置编码和 GELU，属于 GPT-2 那一代的默认搭配。A1 要的是现在主流的结构。

## 4. 对照 A1：换零件

把 TinyGPT 和 A1 的要求列出来，差异就几处：

| 组件 | TinyGPT（lab） | Assignment1（要手写） | 换的原因 |
|------|---------------|----------------------|---------|
| Linear | `nn.Linear`，带 bias | 手写，无 bias，截断正态初始化 | 控制初始化，默认初始化对 Transformer 偏大 |
| Embedding | `nn.Embedding` | 手写查找表 | 作业要求自己实现底层 |
| 归一化 | LayerNorm | RMSNorm | 少一次 reduce，效果几乎不变 |
| 位置编码 | 可学习绝对位置 | RoPE，作用在 q/k 上 | 相对位置，长度外推更好 |
| FFN | GELU，隐藏层 4 倍 | SwiGLU，隐藏层 8/3 倍 | 门控带来收益，参数量对齐 |
| 精度 | 默认 | RMSNorm 内部 upcast fp32 | 混合精度下更稳定 |
| 残差结构 | pre-LN | pre-LN | 一致，不用换 |

残差和 pre-LN 不用动，骨架是好的。

作业不让用 `nn.Linear` 这些现成的，就是要亲手把初始化、bias、dtype 过一遍。这些细节平时被藏起来，调模型的时候又恰恰是最容易出问题的地方。

`cs336-assignment` 里的 `model.py` 注释比代码多。RoPE 那段，旋转矩阵推一遍、两两配对拆一遍，最后才落成逐元素公式。

## 5. Linear 和 Embedding

Linear 就是不带 bias 的仿射变换，加一个受控初始化：

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

PyTorch 默认初始化对 Transformer 偏大，深层叠加之后激活容易爆。这里按 Xavier 的公式取标准差 `sqrt(2 / (d_in + d_out))`，截断在 ±3σ，避免个别 outlier 权重把训练带偏。权重形状是 `(out_features, in_features)`，前向要转置，和 `nn.Linear` 的约定一致。

Embedding 是一张查找表：

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

初始化是慢变量：前几百步看不出差别，步数多了才分高下。

## 6. RMSNorm

归一化做两件事：把激活值的尺度拉回来，再乘一个可学习的缩放。LayerNorm 减均值、除标准差；RMSNorm 省掉了减均值，也没有 bias。

这个改动其实挺激进，减均值在 LayerNorm 里被当成必要步骤。但去掉它对最终效果影响很小，省下的是一次 reduce，kernel 更快。LLaMA 之后的模型基本都用了它。

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

平方和在 bf16 下精度不够，几百步后 loss 会抖，所以中间转到 fp32 算完再转回来。这点开销换稳定性很值。

## 7. RoPE

TinyGPT 的位置信息是查表来的。RoPE（Rotary Position Embedding，来自 RoFormer）换了个思路：把 q 和 k 的每两个分量当成复平面上的一个点，按 token 的位置旋转一个角度。

![RoPE 的旋转示意](rope.svg)

位置 m 的旋转角是 `m * θ`，位置 n 的旋转角是 `n * θ`，两个向量做点积时角度相减，只剩 `(m - n) * θ`。结果只跟相对距离有关。语料里"前一个词"这种关系，不应该因为句子变长就改变。

先把每个位置的 cos/sin 预计算出来：

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

这里用的是相邻配对的约定，A1 handout 和 GPT-NeoX 都是这么写的。HuggingFace 的 LLaMA 用的是前后对半配对，两者等价，别混用就行。

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

## 8. Attention

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

TinyGPT 里 qkv 是一次投影出来的，A1 拆成了三个 Linear，对照公式更直观：

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

RoPE 只加在 q 和 k 上，v 不加。位置信息只影响"谁该关注谁"这个匹配过程，不改变传递的内容。多头拆分的顺序是 `(B, S, H, head_dim)` 再 transpose 到 `(B, H, S, head_dim)`，顺序别写反。

## 9. SwiGLU

原始 Transformer 的 FFN 是 `W2(ReLU(W1(x)))`。SwiGLU 加了一路门控，多一个矩阵控制信息流：

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

`8/3` 这个数来自参数对齐：SwiGLU 有三个矩阵，想让参数量和 4 倍宽度的 ReLU FFN 接近，隐藏层宽度就得收到 `8/3 d`，`3 * d * 8/3 d = 8d²`，和 `2 * d * 4d` 相等。再向上取到 64 的倍数，让 kernel 少处理尾块：

```python
def default_d_ff(d_model):
    return 64 * math.ceil((8 / 3 * d_model) / 64)
```

ablation 要对比的 GELU FFN 是去掉门控的两矩阵版本，宽度取 `4d` 才能和 SwiGLU 参数对齐：

```python
class GELUFFN(nn.Module):
    def __init__(self, d_model, d_ff, device=None, dtype=None):
        super().__init__()
        self.w1 = Linear(d_model, d_ff, device=device, dtype=dtype)
        self.w2 = Linear(d_ff, d_model, device=device, dtype=dtype)

    def forward(self, x):
        return self.w2(F.gelu(self.w1(x)))
```

## 10. 组装完整模型

block 是 Attention 和 FFN 各带一层残差，pre-norm：

![pre-norm 残差结构](block.svg)

为了 ablation 方便，代码里留了几个开关，不用来回改：

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

post-norm 是 `norm(x + f(x))`，梯度回传要穿过每一层的 norm，底层拿到的梯度被反复缩放，层数一多就得靠 warmup 和调参硬扛。pre-norm 的残差路径是条直连通道，梯度原样回到浅层。代价是最后要补一个 norm。

完整模型：

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

注意这里没有可学习的位置 embedding 了，位置信息全在 attention 内部由 RoPE 处理。

## 11. 算参数和开销

参数量公式（无 bias）：`2VD + L * (4D² + 3D*d_ff + 2D) + D`。第一项是 embedding 和 `lm_head`，括号里是 attention 四个投影、SwiGLU 三个矩阵、两个 RMSNorm，最后是收尾的 norm。

本文的配置（V=256，D=256，L=4，d_ff=704）代进去是 3,344,640，和 `sum(p.numel() for p in model.parameters())` 的数一模一样。公式可以用来检查实现有没有漏层。

显存按每个参数 16 字节估：fp32 参数 4、梯度 4、Adam 的 m 和 v 各 4。3.34M 参数就是 53MB，CPU 都能跑。放大到 7B：`7e9 * 16 = 112GB`，还没算激活值。单卡 80G 的 H100 光放状态都不够，这就是 ZeRO、FSDP 存在的原因。

计算量按每个 token `6N` 估（前向 2N、反向 4N），N 是参数量。没算 attention 的二次项，序列长的时候会低估。用来估训练时间和买卡预算，八九不离十。

## 12. 训练

数据先不折腾 tokenizer，直接按字节读，每个字节一个 token，词表 256。字节级编码很土，但够用。

```python
with open("TinyStoriesV2-GPT4-valid.txt", "rb") as f:
    raw = f.read(8 * 1024 * 1024)
data = torch.frombuffer(bytearray(raw), dtype=torch.uint8).long()
```

取 batch 就是随机截片段，输入是 `[s, s+S)`，标签右移一位：

```python
def get_batch(data, batch_size, context_length):
    starts = torch.randint(0, len(data) - context_length - 1, (batch_size,))
    x = torch.stack([data[s:s + context_length] for s in starts])
    y = torch.stack([data[s + 1:s + 1 + context_length] for s in starts])
    return x, y
```

损失函数按 softmax 的老套路写，先减最大值再算 log-sum-exp。学习率是 warmup 加余弦退火：

```python
def cross_entropy(logits, targets):
    logits = logits - logits.max(dim=-1, keepdim=True).values
    log_probs = logits - torch.logsumexp(logits, dim=-1, keepdim=True)
    target_log_probs = log_probs.gather(-1, targets.unsqueeze(-1)).squeeze(-1)
    return -target_log_probs.mean()


def lr_at(step, max_lr, min_lr, warmup_steps, total_steps):
    if step < warmup_steps:
        return max_lr * (step + 1) / warmup_steps
    if step >= total_steps:
        return min_lr
    progress = (step - warmup_steps) / (total_steps - warmup_steps)
    return min_lr + 0.5 * (max_lr - min_lr) * (1 + math.cos(math.pi * progress))
```

正式训练前做两个便宜检查。固定一个 batch 反复训，模型能把它背下来：batch 8、序列 128，200 步 loss 从 6.06 到 0.0000。这一步能过滤掉大半低级错误，loss 卡在 5.5 附近不动，基本可以断定模型在瞎猜，去查标签有没有右移、mask 有没有写反；loss 变 nan，去查初始化和 mask。另一个是因果性，把序列后半段改掉，前半段 logits 不能变：

```python
x2 = x.clone()
x2[0, 40:] = torch.randint(0, 256, (88,))
assert (model(x)[0, :40] - model(x2)[0, :40]).abs().max() < 1e-6
```

然后正式跑：

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

`betas=(0.9, 0.95)` 把第二矩的衰减调低了。Transformer 梯度分布比较尖，默认 0.999 反应太慢。warmup 100 步再余弦退火，梯度裁剪 1.0 防止个别 batch 把参数带飞。

同一套配置在 CPU 上跑 600 步，loss 从 5.98 到 1.06：

```text
step     0 | loss 5.9772 | lr 1.00e-05
step   100 | loss 1.7271 | lr 1.00e-03
step   300 | loss 1.2439 | lr 6.89e-04
step   599 | loss 1.0607 | lr 1.00e-04
```

随机猜是 `ln(256) ≈ 5.55`，1.06 说明模型确实学到了东西。比 TinyGPT 的 0.10 高一截，因为那个是在记重复语料，这个是在 8MB 真实文本上做 next-token prediction。

A1 的正式训练要在 BPE 之后的 TinyStories 上跑，那部分放到下一篇。

## 13. 四组 ablation

A1 要求做四组消融。开关都留好了，同一份数据、同一个种子，每组 600 步：

| 实验 | 改动 | 600 步后 loss | 观察 |
|------|------|--------------|------|
| 基线 | RoPE + RMSNorm + pre-norm + SwiGLU | 1.061 | 对照组 |
| NoPE | `theta=None` | 1.505 | 差距最明显，位置信息确实关键 |
| 去掉 RMSNorm | `use_norm=False` | 1.062 | 起步 loss 是 42.7，50 步内追平 |
| post-norm | `pre_norm=False` | 1.031 | 4 层太浅，差异落在噪声里 |
| GELU FFN（参数对齐） | `use_swiglu=False`，d_ff=1024 | 1.022 | 差异也在噪声里 |
| GELU FFN（d_ff 没对齐） | `use_swiglu=False`，d_ff=704 | 1.191 | 参数少了两成，不能直接比 |

有两个结果和直觉不一样。

去掉 RMSNorm 之后，第 0 步的 loss 是 42.7，基线是 5.98。没有归一化，初始 logits 就是一团乱麻。但它很快就追平了，600 步后和基线持平。RMSNorm 在这个规模下的价值主要是训练早期把数值稳住，更深、学习率更大的时候，它避免的可能是直接发散。

post-norm 在这轮里反而略好一点（1.031 对 1.061）。讲义里说它更难训、更需要 warmup，那也要到更深的模型才看得出来。4 层太浅，这点差异不用过度解读。

短程对比还有个坑。

几百步的差异里噪声占比不小，同一配置换个种子，差别可能比配置之间还大。想判断某个设计有没有用，要么固定种子多跑几组，要么把步数拉长。看单次结果下结论，容易翻车。

## 14. 几个坑

**RoPE 的广播**。最隐蔽的一个。`token_positions` 是 `(B, S)`，q 是 `(B, H, S, d)`，cos/sin 算出 `(B, S, d)`，直接乘只有 batch=1 能跑；batch 一到 2 立刻翻脸。修法是补一个 head 维：`token_positions.unsqueeze(1)`，让 cos/sin 变成 `(B, 1, S, d)` 再乘。

**RMSNorm 的 fp32**。bf16 下平方和精度不够，几百步后 loss 会抖。归一化内部 upcast 到 fp32 再转回来，能压住大部分精度问题。

**mask 整行被遮**。因果 mask 有对角线兜底。上 padding mask 的时候要保证每行至少剩一个有效 token，不然整行 `-inf` 会算出 nan。

**`optimizer.zero_grad()` 漏掉**。梯度一直累积，loss 不降或者乱跳。排查的时候容易在模型结构里绕圈，先看这一行。

**参数量对不上**。八成是 RMSNorm 的权重没算，每层有两个，不显眼。数一遍：`L * 2 * D + D`。

## 后记

系统学习一门课程的机会并不多。上一次类似的体验还是 MIT 6.824 的 lab：看文档、写代码、跑测试，把分布式系统从纸上搬进终端。CS336 的感觉很像，只是验证标准从测试用例变成了 loss 曲线，调试对象从网络分区变成了张量形状。

正在学 CS336、或者想从工程方向往 Agent 深入的读者，希望这篇能省点时间。下一篇写 tokenizer，BPE 的合并逻辑比 attention 更绕，值得单独讲。

---

参考资料：

- [CS336: Language Modeling from Scratch](https://cs336.stanford.edu/)
- [Assignment 1: Basics](https://github.com/stanford-cs336/assignment1-basics/tree/main)
- [cs336-study（lab 仓库）](https://github.com/fengye404/cs336-study)
- [cs336-assignment（A1 实现）](https://github.com/fengye404/cs336-assignment)
- [RoFormer: Enhanced Transformer with Rotary Position Embedding](https://arxiv.org/abs/2104.09864)
- [Root Mean Square Layer Normalization](https://arxiv.org/abs/1910.07467)
- [GLU Variants Improve Transformer](https://arxiv.org/abs/2002.05202)
