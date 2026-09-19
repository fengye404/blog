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

我平时写 Java 服务端，最近一年工作里开始接触 Agent，调过不少模型 API，也看过几篇讲 Attention 的科普。但要我讲清楚 `d_model`、`num_heads`、RoPE 各自解决什么问题，我一直是含糊的。模型在我这里是个黑盒：进去一段 prompt，出来一段 token，中间发生了什么不知道。

其实这个念头攒了很久。每次看别人的模型结构图我都能跟下来，合上文档自己写又写不出来。

去年就想拆这个黑盒，一直拖到上个月。后来翻到 Stanford 的 CS336（Language Modeling from Scratch），课程大纲正合适，于是就开工了。这门课 assignment 1 要求手写 tokenizer、模型和优化器，然后在 TinyStories 上训一个能生成通顺英文的小模型。课程主页在[这里](https://stanford-cs336.github.io/spring2025/)，作业代码在 [assignment1-basics](https://github.com/stanford-cs336/assignment1-basics)。

这个系列我打算写三篇，按依赖顺序来：Transformer、tokenizer、训练与优化。这篇只讲 Transformer，从 Linear 开始一路搭到完整的 `TransformerLM`，最后跑通一个能收敛的训练循环。文中代码都在本机验证过，测试方法也一并写出来。

在跟课的同学先自己写。CS336 的 honor code 禁止直接使用别人的实现，本文是我做完之后的复盘，留给已经交了作业、或者纯粹想理解 Transformer 的工程同学。

## 1. 先看目标

整个模型做的事情可以用一句话概括：把 token id 序列映射成下一个 token 的概率分布。

数据流是这样的：

```text
token_ids                (B, S)
  → Embedding            (B, S, D)
  → N × TransformerBlock (B, S, D)
      RMSNorm → CausalSelfAttention → 残差
      RMSNorm → SwiGLU FFN          → 残差
  → RMSNorm              (B, S, D)
  → lm_head              (B, S, V)
logits                   (B, S, V)
```

B 是 batch size，S 是序列长度，D 是 `d_model`，V 是词表大小。训练时把 logits 和右移一位的 labels 做交叉熵，目标就是让每个位置的下一个 token 概率尽可能高。

下面按依赖顺序，一个零件一个零件实现。

## 2. Linear 与 Embedding

CS336 要求自己实现 Linear，不允许直接调 `nn.Linear`。原因在初始化。

PyTorch 默认的初始化对 Transformer 来说偏大，深层网络叠加之后激活值容易爆掉。原论文给的方案是按 Xavier 的思路，从标准差为 `sqrt(2 / (d_in + d_out))` 的正态分布里采样权重，并且截断在 ±3σ。截断这步是为了防止个别 outlier 权重把训练带偏。

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

权重形状是 `(out_features, in_features)`，前向时转置一下。PyTorch 里大部分层都是这个约定，跟着来就行。

Embedding 是一张查找表，初始化用标准正态截断：

```python
class Embedding(nn.Module):
    def __init__(self, num_embeddings, embedding_dim, device=None, dtype=None):
        super().__init__()
        self.weight = nn.Parameter(
            torch.empty(num_embeddings, embedding_dim, device=device, dtype=dtype)
        )
        nn.init.trunc_normal_(self.weight, mean=0.0, std=1.0, a=-3.0, b=3.0)

    def forward(self, token_ids):
        return self.weight[token_ids]
```

这种自己定义权重、手动控制初始化的写法，让我想起刚学 Java 那会第一次调线程池参数。`corePoolSize` 和 `maxPoolSize` 也是两个数各管一段，配错了表面上也能跑，压力上来才出问题。初始化同样是这个性质，训练前期看不出差别，步数多了才分得出高下。

## 3. RMSNorm

归一化层做两件事：把激活值的尺度拉回稳定范围，再乘一个可学习的缩放。LayerNorm 是减均值、除标准差；RMSNorm 省掉了减均值，只除以均方根（root mean square），也没有 bias。

少一次 reduce，kernel 更快，效果几乎不掉。LLaMA 之后的模型基本都换成了它。

```python
class RMSNorm(nn.Module):
    def __init__(self, d_model, eps=1e-5, device=None, dtype=None):
        super().__init__()
        self.eps = eps
        self.weight = nn.Parameter(torch.ones(d_model, device=device, dtype=dtype))

    def forward(self, x):
        in_dtype = x.dtype
        x = x.to(torch.float32)
        rms = torch.rsqrt(x.pow(2).mean(dim=-1, keepdim=True) + self.eps)
        return (x * rms).to(in_dtype) * self.weight
```

`rsqrt` 是 `1 / sqrt`，比先开方再除少一次算子。中间转到 fp32 是踩过坑的：模型跑 bf16 时，平方和累加的精度不够，几百步之后 loss 会开始抖。转成 fp32 算完再转回来，这点开销换稳定性很值。

## 4. 位置编码：RoPE

注意力本身对顺序不敏感：把输入 token 的顺序打乱，只要 mask 不变，每个位置拿到的输出集合是一样的。位置信息必须显式注入。

GPT-2 用的是可学习的绝对位置 embedding，把位置当成"第几个 token"查表。RoPE（Rotary Position Embedding，来自 RoFormer）换了个思路：把 q 和 k 的每两个分量看成复平面上的一个点，按 token 的位置旋转一个角度。

位置是 m 时，第 i 对分量的旋转角是 `m * θ_i`。查询向量旋转 `m * θ`，键向量旋转 `n * θ`，两者做点积时角度相减，只剩 `(m - n) * θ`。点积结果只依赖两个 token 的相对距离，跟绝对位置无关。这个性质对语言很合理："前一个词"这个关系不应该因为句子变长而改变。

先把每个位置的 `cos` 和 `sin` 预计算出来：

```python
def precompute_rope(head_dim, theta=10000.0, max_seq_len=4096):
    inv_freq = 1.0 / (theta ** (torch.arange(0, head_dim, 2).float() / head_dim))
    positions = torch.arange(max_seq_len).float()
    angles = torch.outer(positions, inv_freq)      # (S, head_dim / 2)
    angles = torch.cat([angles, angles], dim=-1)   # (S, head_dim)
    return angles.cos(), angles.sin()
```

`theta` 控制不同分量对旋转的快慢：前面的分量转得快，负责近距离区分；后面的分量转得慢，负责远距离。这和正弦位置编码的设计是一致的，RoPE 把它用在了旋转上。

应用旋转的操作分两步。`rotate_half` 把后半段挪到前面并取负，模拟复平面上乘 i 的效果：

```python
def rotate_half(x):
    x1, x2 = x.chunk(2, dim=-1)
    return torch.cat([-x2, x1], dim=-1)


def apply_rope(x, cos, sin):
    # x: (B, H, S, head_dim)，cos/sin: (S, head_dim)
    cos = cos[None, None, :, :]
    sin = sin[None, None, :, :]
    return x * cos + rotate_half(x) * sin
```

这里用的是 LLaMA、HuggingFace 的"前后对半"约定：第 i 个分量跟第 i + head_dim/2 个分量配对旋转。GPT-NeoX 用的是相邻配对，两者等价，只是排列方式不同，别混用就行。

这个相对位置性质值得写个测试确认，不然后面 RoPE 写错了很难发现：

```python
q = torch.randn(1, 1, 1, head_dim).expand(1, 1, 8, head_dim)
k = torch.randn(1, 1, 1, head_dim).expand(1, 1, 8, head_dim)
qr = apply_rope(q, cos[:8], sin[:8])
kr = apply_rope(k, cos[:8], sin[:8])

# 位置 (2, 1) 和 (5, 4) 的相对距离都是 1，点积应该相等
a = (qr[0, 0, 2] * kr[0, 0, 1]).sum()
b = (qr[0, 0, 5] * kr[0, 0, 4]).sum()
torch.testing.assert_close(a, b)   # 验证通过
```

## 5. Attention

Softmax 是第一个要小心的实现。直接指数容易溢出，标准做法是每行减去最大值再算：

```python
def softmax(x, dim=-1):
    x_max = x.max(dim=dim, keepdim=True).values
    exp = (x - x_max).exp()
    return exp / exp.sum(dim=dim, keepdim=True)
```

因为 softmax 对输入整体加常数不变，减最大值不改变结果，纯粹是为了数值稳定。

Scaled dot-product attention 的公式是 `softmax(QKᵀ / sqrt(d_k)) V`。除以 `sqrt(d_k)` 是必要的：Q 和 K 的每个分量独立时，点积的方差随 `d_k` 线性增长，不缩放的话值会很大，softmax 被推到饱和区，梯度接近 0。开方之后方差回到 1 附近。

因果 mask 是一个下三角矩阵，第 t 个位置只能看 1 到 t：

```python
def scaled_dot_product_attention(q, k, v, mask=None):
    d_k = q.shape[-1]
    scores = q @ k.transpose(-2, -1) / math.sqrt(d_k)
    if mask is not None:
        scores = scores.masked_fill(~mask, float("-inf"))
    weights = softmax(scores, dim=-1)
    return weights @ v
```

被掩掉的位置填 `-inf`，softmax 之后就是 0。这里有个前提：每一行至少有一个位置可见。因果 mask 的对角线保住了这个前提，如果是 padding mask，得保证每行至少剩一个有效 token，否则整行 `-inf` 会算出 nan。

多头注意力就是把这套东西并行跑 H 份。每个头的 `head_dim = d_model / num_heads`，q、k、v 投影出来之后 reshape 成 `(B, H, S, head_dim)`，算完再拼回去过一层输出投影：

```python
class CausalMultiHeadSelfAttention(nn.Module):
    def __init__(self, d_model, num_heads, context_length, rope_theta=10000.0, use_rope=True):
        super().__init__()
        assert d_model % num_heads == 0
        self.num_heads = num_heads
        self.head_dim = d_model // num_heads
        self.use_rope = use_rope
        self.q_proj = Linear(d_model, d_model)
        self.k_proj = Linear(d_model, d_model)
        self.v_proj = Linear(d_model, d_model)
        self.output_proj = Linear(d_model, d_model)
        cos, sin = precompute_rope(self.head_dim, theta=rope_theta, max_seq_len=context_length)
        self.register_buffer("cos", cos, persistent=False)
        self.register_buffer("sin", sin, persistent=False)

    def forward(self, x):
        B, S, _ = x.shape
        q = self.q_proj(x).reshape(B, S, self.num_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(x).reshape(B, S, self.num_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(x).reshape(B, S, self.num_heads, self.head_dim).transpose(1, 2)
        if self.use_rope:
            q = apply_rope(q, self.cos[:S], self.sin[:S])
            k = apply_rope(k, self.cos[:S], self.sin[:S])
        mask = torch.tril(torch.ones(S, S, dtype=torch.bool, device=x.device))
        out = scaled_dot_product_attention(q, k, v, mask)
        out = out.transpose(1, 2).reshape(B, S, self.num_heads * self.head_dim)
        return self.output_proj(out)
```

两个细节。RoPE 只加在 q 和 k 上，v 不加，因为位置信息只需要影响"谁该关注谁"这个匹配过程，不需要改变传递的内容。`register_buffer(..., persistent=False)` 让 cos/sin 跟着模型走 device、不进 `state_dict`，checkpoint 里不会多存两份固定数据。

多头并行的 reshape 顺序是 `(B, S, H, head_dim)` 再 transpose 到 `(B, H, S, head_dim)`。顺序别写反。用 `reshape` 而不是 `view`，因为 transpose 之后内存不连续，`view` 会报错。

## 6. FFN：SwiGLU

原始 Transformer 的 FFN 是两层线性加 ReLU：`W2(ReLU(W1(x)))`。SwiGLU 加了一个门控，用第三个矩阵控制信息流：

```python
class SwiGLU(nn.Module):
    def __init__(self, d_model, d_ff=None):
        super().__init__()
        if d_ff is None:
            d_ff = 64 * math.ceil((8 / 3 * d_model) / 64)
        self.w1 = Linear(d_model, d_ff)
        self.w2 = Linear(d_ff, d_model)
        self.w3 = Linear(d_model, d_ff)

    def forward(self, x):
        return self.w2(F.silu(self.w1(x)) * self.w3(x))
```

`d_ff` 为什么是 `8/3 * d_model`？SwiGLU 有三个矩阵，比 ReLU FFN 多一个。为了让两者的参数量接近，把隐藏层宽度从 `4d` 缩到 `8/3 d`，`3 * d * (8/3 d) = 8d²` 正好对上 `2 * d * 4d = 8d²`。再向上取到 64 的倍数，让 kernel 少处理一些尾块。

消融实验里要对比的 SiLU FFN 就是去掉门控的版本，隐藏层宽度按惯例取 `4d`：

```python
class SiLUFFN(nn.Module):
    def __init__(self, d_model, d_ff=None):
        super().__init__()
        if d_ff is None:
            d_ff = 4 * d_model
        self.w1 = Linear(d_model, d_ff)
        self.w2 = Linear(d_ff, d_model)

    def forward(self, x):
        return self.w2(F.silu(self.w1(x)))
```

## 7. 组装完整模型

先定一个配置对象，把所有会做 ablation 的开关收在一处：

```python
@dataclass
class ModelConfig:
    vocab_size: int = 10000
    context_length: int = 256
    d_model: int = 512
    num_layers: int = 4
    num_heads: int = 8
    d_ff: int | None = None
    rope_theta: float = 10000.0
    use_norm: bool = True       # False = 去掉 RMSNorm
    pre_norm: bool = True       # False = post-norm
    use_rope: bool = True       # False = NoPE
    use_swiglu: bool = True     # False = 换 SiLU FFN
    tie_embeddings: bool = False
```

Transformer block 是 Attention 和 FFN 各带一层残差。现在主流的做法是 pre-norm：先归一化再进子层，残差路径上不经过任何 norm。

```python
class TransformerBlock(nn.Module):
    def __init__(self, d_model, num_heads, d_ff, context_length, rope_theta=10000.0,
                 use_norm=True, pre_norm=True, use_rope=True, use_swiglu=True):
        super().__init__()
        norm = (lambda: RMSNorm(d_model)) if use_norm else (lambda: nn.Identity())
        self.norm1 = norm()
        self.norm2 = norm()
        self.attn = CausalMultiHeadSelfAttention(
            d_model, num_heads, context_length, rope_theta=rope_theta, use_rope=use_rope
        )
        self.ffn = SwiGLU(d_model, d_ff) if use_swiglu else SiLUFFN(d_model, d_ff)
        self.pre_norm = pre_norm

    def forward(self, x):
        if self.pre_norm:
            x = x + self.attn(self.norm1(x))
            x = x + self.ffn(self.norm2(x))
        else:
            x = self.norm1(x + self.attn(x))
            x = self.norm2(x + self.ffn(x))
        return x
```

两种 norm 位置的区别直接体现在梯度上。Post-norm 是 `norm(x + f(x))`，梯度回传时要穿过每一层的 norm，底层拿到的梯度被反复缩放，层数一多就要靠 warmup 和小心调参才能训起来。Pre-norm 的残差路径是一条从输出到输入的直连通道，梯度原样回到浅层，训练稳得多。代价是最后要补一个 norm，`ln_final` 就是干这个的。

完整的模型：

```python
class TransformerLM(nn.Module):
    def __init__(self, cfg: ModelConfig):
        super().__init__()
        self.cfg = cfg
        self.token_embeddings = Embedding(cfg.vocab_size, cfg.d_model)
        self.layers = nn.ModuleList([
            TransformerBlock(
                d_model=cfg.d_model,
                num_heads=cfg.num_heads,
                d_ff=cfg.d_ff,
                context_length=cfg.context_length,
                rope_theta=cfg.rope_theta,
                use_norm=cfg.use_norm,
                pre_norm=cfg.pre_norm,
                use_rope=cfg.use_rope,
                use_swiglu=cfg.use_swiglu,
            )
            for _ in range(cfg.num_layers)
        ])
        self.ln_final = RMSNorm(cfg.d_model) if cfg.use_norm else nn.Identity()
        self.lm_head = Linear(cfg.d_model, cfg.vocab_size)
        if cfg.tie_embeddings:
            self.lm_head.weight = self.token_embeddings.weight

    def forward(self, token_ids):
        x = self.token_embeddings(token_ids)
        for layer in self.layers:
            x = layer(x)
        x = self.ln_final(x)
        return self.lm_head(x)
```

`tie_embeddings` 是把输入 embedding 和输出投影绑成同一个矩阵。查表选词和预测下一个词本来就有点像逆操作，共享权重能省掉一份 `V * D` 的参数，在上面那个 V=10000、D=512 的配置里能省掉五分之一。GPT-2 绑了，LLaMA 没绑，两边都有大模型，属于可选项。

## 8. 算一笔账

工程同学对资源开销应该都有直觉，模型这边也有几个粗略公式。

参数量：`2VD + L * (4D² + 3D*d_ff + 2D) + D`。第一项是输入 embedding 和 `lm_head`，第二个括号里依次是 attention 的四个投影、SwiGLU 的三个矩阵、两个 RMSNorm，最后是 `ln_final`。绑权重的话省掉一个 `VD`。

上面配置（V=10000，D=512，L=4）算下来大约 2300 万参数。显存预算按"每个参数 16 字节"估：fp32 参数 4 字节、梯度 4 字节、Adam 的 m 和 v 各 4 字节。2300 万参数就是 368MB，加上激活值和临时 buffer，一张消费级显卡绰绰有余。

这个公式放大到 7B 模型就很吓人：`7e9 * 16 = 112GB`，还没算激活值。这就是为什么大模型训练必须上 ZeRO、FSDP 这类切分方案，单卡 80G 的 H100 连状态都放不下。

计算量：前向每个 token 约 `2N` FLOPs，N 是参数量；反向约 `4N`，加起来训练一个 token 约 `6N`。这是不含 attention 二次项的低估，序列长的时候 attention 开销会顶上来。用这个公式估训练时间和买卡预算，八九不离十。

## 9. 让它跑起来

### 9.1 损失函数

交叉熵自己实现一遍，逻辑和 softmax 一样，先减最大值再算 log-sum-exp：

```python
def cross_entropy(logits, targets):
    # logits: (B, S, V)，targets: (B, S)
    logits = logits - logits.max(dim=-1, keepdim=True).values
    log_probs = logits - torch.logsumexp(logits, dim=-1, keepdim=True)
    target_log_probs = log_probs.gather(-1, targets.unsqueeze(-1)).squeeze(-1)
    return -target_log_probs.mean()
```

### 9.2 学习率调度

学习率先线性 warmup，再按余弦退火到 `min_lr`：

```python
def lr_at(step, max_lr, min_lr, warmup_steps, total_steps):
    if step < warmup_steps:
        return max_lr * (step + 1) / warmup_steps
    if step >= total_steps:
        return min_lr
    progress = (step - warmup_steps) / (total_steps - warmup_steps)
    return min_lr + 0.5 * (max_lr - min_lr) * (1 + math.cos(math.pi * progress))
```

warmup 对 Transformer 基本是必需品。训练早期参数离最优点很远，第二矩估计也没稳定，一上来用大学习率容易把权重推到坏区域，之后怎么都拉不回来。

### 9.3 数据

tokenizer 留到下一篇，这里先用最简单的 byte 级编码顶上：把文本文件按字节读进来，每个字节就是一个 token，词表大小 256。字节编码序列长、效率低，但零依赖，验证模型结构足够了。

```python
text = open("tinyshakespeare.txt", "rb").read()
data = torch.frombuffer(bytearray(text), dtype=torch.uint8).long()
```

取 batch 就是从序列里随机截固定长度的片段，输入是 `[s, s+S)`，标签是右移一位的 `[s+1, s+1+S)`：

```python
def get_batch(data, batch_size, context_length):
    starts = torch.randint(0, len(data) - context_length - 1, (batch_size,))
    x = torch.stack([data[s:s + context_length] for s in starts])
    y = torch.stack([data[s + 1:s + 1 + context_length] for s in starts])
    return x, y
```

### 9.4 先过一遍 sanity check

在正式训练之前，先做两件便宜的事。

第一，固定一个 batch 反复训，模型应该能把它背下来，loss 从 `ln(V)` 掉到接近 0。我拿 batch 8、序列 64 试了 200 步，loss 从 5.95 掉到 0.0001，花了两秒。这个检查能过滤掉一大半的低级错误：如果 loss 卡在 5.5 附近不动，多半是标签没右移、mask 写反或者梯度没清零；如果 loss 变 nan，去看初始化和 mask。

第二，验证因果性：改掉序列后面的 token，前面的 logits 不能变。写起来很简单：

```python
x2 = x.clone()
x2[0, 40:] = torch.randint(0, 256, (24,))
assert (model(x)[0, :40] - model(x2)[0, :40]).abs().max() < 1e-6
```

### 9.5 正式训练

超参和循环：

```python
cfg = ModelConfig(vocab_size=256, context_length=128, d_model=256, num_layers=4, num_heads=8)
model = TransformerLM(cfg)
optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, betas=(0.9, 0.95), weight_decay=0.1)

for step in range(total_steps):
    x, y = get_batch(data, batch_size=16, context_length=cfg.context_length)
    lr = lr_at(step, 1e-3, 1e-4, warmup_steps=100, total_steps=600)
    for g in optimizer.param_groups:
        g["lr"] = lr
    logits = model(x)
    loss = cross_entropy(logits, y)
    optimizer.zero_grad()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    optimizer.step()
```

`betas=(0.9, 0.95)` 是第二矩的衰减调低了，Transformer 的梯度分布比较尖，默认的 0.999 反应太慢。`weight_decay=0.1` 是 AdamW 的解耦权重衰减，跟学习率解耦。梯度裁剪设 1.0，防止个别 batch 把参数带飞。

我在本机 CPU 上跑了 600 步，3.34M 参数的小模型，137 秒。loss 从 5.96 降到 1.49：

```text
step     0 | loss 5.960 | lr 1.00e-05 | 0.2s
step   100 | loss 2.147 | lr 1.00e-03 | 22.0s
step   300 | loss 1.668 | lr 6.89e-04 | 74.4s
step   599 | loss 1.539 | lr 1.00e-04 | 137.4s
```

拿 `ROMEO: ` 做 prompt 采样，出来的文本已经能看出单词形状：

```text
t more charry untractesed
Yet that he his betwees their lettle do gawns hour
yea Roman: him in splay prince: he hastrone,
And hath gost where wran's th
```

离通顺还远，但 `Roman`、`prince`、`hath`、`Yet` 这些词已经自己学出来了。反正那天晚上我盯着 loss 一点点往下掉，比当年等 Maven 编译还上头。

## 10. Ablation

CS336 的 A1 要求在训好的基础上做四组消融，验证每个设计的必要性。配置开关已经留好了，改一个字段跑一遍就行：

| 实验 | 改动 | 预期 |
|------|------|------|
| No RMSNorm | `use_norm=False` | 短程训练差别小，层数深或者学习率大时不稳定 |
| Post-norm | `pre_norm=False` | 同样的步数下 loss 更高，warmup 需求更强 |
| NoPE | `use_rope=False` | 依赖位置的模式学不出来，loss 明显差一截 |
| SiLU FFN | `use_swiglu=False` | 参数量接近，效果略差 |

短程对比有个坑。

几百步的差异里噪声占比不小，同一个配置两个种子跑出来的差别可能比配置之间的差别还大。判断某个设计有没有用，要么固定种子多跑几次，要么把训练步数拉长。只看单次结果就下结论，容易翻车。

## 11. 踩坑清单

**loss 变 nan**。三种可能：mask 有一行全被遮住、初始化标准差设大了、没做 warmup 直接上大学习率。先查 mask，那是概率最高的一个。

**loss 不降**。`optimizer.zero_grad()` 漏了，梯度一直在累积；或者标签忘了右移，模型在学一个不可能的任务。这两个都是看一眼代码就能发现的错，但找的时候容易在模型结构里绕圈。

**参数量和公式对不上**。八成是 RMSNorm 的权重没算进去，它们不显眼，但每层有两个。数一遍：`L * 2 * D + D`。

**bf16 下 loss 抖动**。归一化的平方和、softmax 的 exp，在这两个地方 upcast 到 fp32，能解决大部分精度问题。

**RoPE 写错**。这个最难发现，因为 loss 照样降，只是效果差一点。前面那个相对位置性质的测试一定要留着，改完 RoPE 就跑一遍。

## 12. 写在最后

写完这套代码，Transformer 对我最大的变化是从"论文里的图"变成了"一堆可以拆开的零件"。每个零件都在回答一个具体问题：初始化为的是训练起步不发散，RMSNorm 为的是尺度稳定，RoPE 为的是相对位置，mask 为的是不能偷看未来。

没有哪个是魔法。

这篇的代码都在上面，复制出去就能跑。下一篇写 tokenizer，BPE 的合并逻辑比 attention 更绕，值得单独讲。

---

参考资料：

- [CS336: Language Modeling from Scratch](https://stanford-cs336.github.io/spring2025/)
- [Assignment 1: Basics](https://github.com/stanford-cs336/assignment1-basics)
- [RoFormer: Enhanced Transformer with Rotary Position Embedding](https://arxiv.org/abs/2104.09864)
- [Root Mean Square Layer Normalization](https://arxiv.org/abs/1910.07467)
- [GLU Variants Improve Transformer](https://arxiv.org/abs/2002.05202)
