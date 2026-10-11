---
title: 128G 满血版 M5 Max Mac Studio 运行 Qwen3.8-Flash-Next 最佳实践报告
typora-root-url: ./qwen38-flash-next-m5max-benchmark
date: 2026-10-11 12:15:52
tags:
  - LLM
  - Qwen
  - MLX
  - 本地部署
---

前段时间 Qwen 发布了 Qwen3.8-27B、Qwen3.8-flash-next 两个小模型，在 AA 的排行榜单上，甚至超过了了半年前的各家旗舰模型（比如 Opus 4.6、Kimi 2.6、GLM-5.2）

![Artificial Analysis Intelligence Index (11 Oct '26)](<./Artificial Analysis Intelligence Index (11 Oct '26)-1708780.png>)

难道本地小模型真王朝了？！不过很遗憾我手上只有一台 4080s 的显卡，12G 显存只能勉强跑一跑 Qwen3.8-27B 的量化版，而且这种稠密模型的推理速度实在是感人。正巧 9 月苹果最新的 Mac Studio 要发布了，我必须得下一单尝尝咸淡（对不起买不起更贵的 M5 Ultra 了😭）

![29507d3f4de2f9c0cfb87bbc622dad4f](./29507d3f4de2f9c0cfb87bbc622dad4f.png)

昨天到货后，马上迫不及待跑了一下 Qwen3.8-Flash-Next。这次我测试的两个目标是：

1. **[Qwen3.8-Flash-Next-REAP-288-MLX-4bit](https://huggingface.co/sh0wie/Qwen3.8-Flash-Next-REAP-288-MLX-4bit)**：社区作者 sh0wie 提供的专家剪枝版本，每层保留 512 个专家中的 288 个，并使用 4-bit 量化。全套下载约 73.52 GB，主要优势是占用空间更小，下面简称 **REAP**。
2. **[Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit)**：社区作者 ddalcu 提供的混合量化版本，保留全部 512 个专家，专家权重主要使用 4-bit，Attention 等部分使用 8-bit。全套下载约 107.33 GB，配合 mlx-serve 运行，下面简称 **mixed**。

> 目前个人本地模型推理在成本上完全没有任何优势，如果不是为了学习研究，目前阶段不建议购买任何本地推理机器。
>
> 为什么我不买 DGX Spark？因为我认为 Mac Studio 的功耗更低，日常使用更舒服，且保值率更高，而且目前 DGX Spark 虽然有 CUDA 生态的优势，的统一内存带宽只有 **273** **GB/s**，在 decode 时是一个短板，只能说未来提升空间很大，可以期待一下 DGX Spark 2代。

## 1. 模型部署

机器配置前面已经贴过了：18 核 CPU、40 核 GPU、128G 统一内存，系统是 macOS 27.0。两个模型对应的推理引擎如下：

| 模型 | 推理引擎 |
| --- | --- |
| REAP | mlx-vlm 0.7.6 / MLX 0.32.3 |
| mixed | mlx-serve 26.10.1 |

### 推理框架

这次用 MLX，主要是因为前面选的两个模型已经有配套的运行实现，量化权重、ngram 加载和 MTP 都能沿用作者提供的方案。MLX 是 Apple 开源的机器学习框架，CPU 和 GPU 可以访问同一份数组，不需要在两者之间显式搬运数据；这里的 mlx-vlm、mlx-serve 则负责模型加载和推理服务。[MLX 官方说明](https://github.com/ml-explore/mlx#mlx)

Mac 上也有其他选择：

| 方案 | 特点 | 这次的取舍 |
| --- | --- | --- |
| MLX + 配套推理引擎 | 面向 Apple Silicon，提供 Python 接口；这两个模型包已有对应实现 | 直接使用作者适配好的权重和功能，方便复测 |
| llama.cpp | 支持 Metal 加速、GGUF 模型和多种量化精度，也支持 CPU/GPU 混合推理 | 换用它需要对应的 GGUF 权重，并核对这个模型的架构和 MTP 支持 |
| PyTorch + MPS | 通过 Metal 在 Apple GPU 上运行 PyTorch，适合沿用和修改 PyTorch 模型代码 | 量化算子和模型所需功能仍要逐项确认，不能把 CUDA 部署命令直接搬过来 |

llama.cpp 的 Apple Silicon 支持和量化方案见[项目说明](https://github.com/ggml-org/llama.cpp#description)，MPS 的工作方式见 [Apple 的 PyTorch 文档](https://developer.apple.com/metal/pytorch/)。这轮没有做同一份模型、同一精度下的跨框架测速，所以这里只说明部署选择；后面的速度差别是两套完整方案的差别。

### 量化精度

再看精度。这里的 4-bit、8-bit 指权重的存储位数，位数越少，权重占用越小。我们还要给长上下文和系统留内存，所以不能只看模型能不能加载进去。

按 mixed 作者给出的约 180B 完整权重口径，先用“参数量 × 位数 ÷ 8”粗算一下：

| 权重精度 | 理论权重体积 | 对这台 128G 机器的影响 |
| --- | ---: | --- |
| BF16 / FP16，16-bit | 360 GB | 无法全部常驻内存 |
| 8-bit | 180 GB | 全部常驻仍超出容量 |
| 6-bit | 135 GB | 还没算运行开销，就已经接近整机容量 |
| 4-bit | 90 GB | 才有较多空间留给上下文和运行开销 |

这里用十进制 GB，假设所有权重采用同一位数，包含 ngram 和 MTP。实际量化还要保存分组缩放参数，部分层也会保留更高精度；ngram 又可以按需从 SSD 读取，所以这张表是体积估算，实际内存占用看下一节。[模型组成说明](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit#what-is-different-about-this-model) · [MLX 量化格式](https://ml-explore.github.io/mlx/build/html/python/_autosummary/mlx.core.quantize.html)

**这次选 4-bit 为主，是为了在 128G 内存里跑长上下文。** mixed 把占大头的路由专家压到 4-bit，Attention、共享专家和输出层等用 8-bit，路由器、归一化等保留 BF16。REAP 则在 4-bit 量化之外，再减少专家数量，因此体积更小。两者具体设置见 [mixed 精度表](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit#widths)和 [REAP 模型说明](https://huggingface.co/sh0wie/Qwen3.8-Flash-Next-REAP-288-MLX-4bit)。

位数减少也会引入量化误差。同样的位数下，怎么量化也有影响：mixed 作者报告，新 iQ 包与旧包体积相同，对 BF16 输出的 top-1 一致率从 87.9% 提升到 88.6%，KLD 中位数从 0.0066 降到 0.0052（越低代表输出分布越接近）。这是作者测得的输出接近程度，不是任务正确率，也不是我们这轮的实测。[作者对比](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit#qwen38-flash-next-for-mlx-serve-4-bit-experts-8-bit-rest)

我们没有把同一模型的 4-bit、6-bit、8-bit 全部测一遍，因此还不能判断各档精度损失多少、速度相差多少。下面先看这两套实际跑过的配置。

### Ngram 表与内存映射

下载模型时会发现，里面还有一张很大的 **ngram embedding 表**。它根据相邻 token 的组合查出向量，mixed 版本将它单独放在 `ngram_table.bin` 中，光这一个文件就有约 32 GB。

如果把整张表都加载进内存，会挤掉不少留给上下文和其他应用的空间。这次两个模型都用了 **mmap（内存映射）**：文件放在 SSD 上，用到哪部分就读取哪部分，读过的文件页由 macOS 缓存。这样就不用让整张表始终常驻内存。

| 配置 | REAP | mixed |
| --- | --- | --- |
| ngram 加载方式 | `ple_storage`，SSD mmap | `ngram_table.bin`，SSD mmap |
| 相关设置 | `cache_rows=0` | 关闭 `ple-gpu`，设置 `MLX_SERVE_NGRAM_WARM=0` |
| MLX 缓存上限 | 4 GiB | 8 GiB |

`MLX_SERVE_NGRAM_WARM=0` 是关闭整表后台预热，避免主动把整张表读进系统缓存。mmap 仍然会占用一部分内存，只是文件页可以由系统按需回收。

### MTP 推测解码

这次还分别测了开启和关闭 **MTP（Multi-Token Prediction，多 token 预测）**的情况。它在这里用于推测解码：先由预测模块提出后面几个 token，再交给主模型验证。如果一次能接收多个 token，就有机会比逐个生成更快。

不过，预测和验证也有开销，所以开了不一定更快。REAP 还需要额外加载约 5.24 GB 的预测模型（drafter），mixed 的模型包里已经带了对应权重。后面我们直接看两种模式的速度差别。

> 整理文章时，mixed 作者已经[推荐新的 iQ 版本](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit#qwen38-flash-next-for-mlx-serve-4-bit-experts-8-bit-rest)，旧包停止更新。下面的数据对应这次实际测过的 mixed-4-8bit，新版还没有在本机复测。

## 2. 内存占用

先看内存。测速时活动监视器里 REAP 的 Python 进程大约占 49 GB，比下载下来的文件小不少。前面说的 ngram 按需加载就是原因之一，所以不能直接用模型文件大小来判断运行时占用。

下面是整个测速过程中，**MLX 记录到的最高内存分配量**：

| 方案 | MLX 最高分配量 |
| --- | ---: |
| REAP | 55.46 GB |
| REAP + MTP | 60.68 GB |
| mixed | 80.64 GB |
| mixed + MTP | 84.30 GB |

这轮始终只加载一个大模型、处理一个请求，两套方案都能跑完接近 256K 的输入。mixed 普通模式最高约 81 GB，开 MTP 后约 84 GB；REAP 则分别约 55 GB 和 61 GB，能给其他应用多留一些空间。

这些数值不包含整机所有占用，也不能和活动监视器里的进程内存直接相加。测试期间没有采样到新增的 Swapouts（内存换出）记录；如果还要同时开其他模型或应用，就要另外留出余量。

## 3. 推理性能

我平时会用到 200K 左右的上下文，所以这次没有只测几百个 token，而是从 512 一直测到了接近 256K，看看输入变长后会掉多少速度。

### 测试方法

输入分为八档：512、4,096、16,384、32,768、65,536、131,072、200,000 和 261,632 token。最后一档给 262,144 token 的窗口留了一部分输出空间，下面简称 **256K 档**。

中文、英文取固定的 Wikipedia 文本，代码取 CPython 3.12.0 标准库源码，按需要的长度截取。每份输入前、中、后各放一个校验码，让模型先找出来，再分析内容，顺便检查长输入里的信息能不能被读到。

两个模型各测普通模式和 MTP 模式，32K 及以下重复三次，64K 及以上重复两次，共 240 个独立测试项。每次最多输出 256 token，`temperature=0`，关闭思考和前缀缓存；输入按每批 1,024 token 处理，也就是 `prefill chunk=1024`。

这里先区分一下 **Prefill 和 Decode**：把一大段内容发给模型后，模型要先处理这些输入，这一步叫 Prefill；随后开始往外生成回答，叫 Decode。表里的 tok/s 就是每秒处理或生成的 token 数。

所以看长上下文性能，要同时看**多久开始回答，以及开始后输出多快**。只看 Decode，很容易忽略前面处理长文的等待时间。

### 测试结果

![中文、英文和代码在不同输入长度下的 Prefill 与 Decode 速度](./speed-curves.png)

图中实线是普通模式，虚线是 MTP，误差棒表示各轮的最小值到最大值。下面列出全部八档结果，数值取同一档中文、英文、代码全部轮次的中位数。首 token 时间从发出请求开始计算，也包含分词等开销。

| 输入档位 | 方案 | Prefill（tok/s） | Decode（tok/s） | 首 token 时间（秒） |
| --- | --- | ---: | ---: | ---: |
| 512 | REAP | 1,141.3 | 43.5 | 0.5 |
| 512 | REAP + MTP | 1,177.3 | 42.9 | 0.4 |
| 512 | mixed | 1,580.5 | 66.8 | 0.3 |
| 512 | mixed + MTP | 1,557.5 | 94.3 | 0.3 |
| 4K | REAP | 1,285.6 | 39.3 | 3.2 |
| 4K | REAP + MTP | 1,308.5 | 46.1 | 3.1 |
| 4K | mixed | 2,183.5 | 62.4 | 1.9 |
| 4K | mixed + MTP | 2,175.9 | 95.2 | 1.9 |
| 16K | REAP | 1,262.7 | 38.1 | 13.0 |
| 16K | REAP + MTP | 1,268.2 | 43.1 | 12.9 |
| 16K | mixed | 2,144.0 | 61.3 | 7.6 |
| 16K | mixed + MTP | 2,147.3 | 91.1 | 7.6 |
| 32K | REAP | 1,241.2 | 35.5 | 26.4 |
| 32K | REAP + MTP | 1,221.9 | 41.5 | 26.9 |
| 32K | mixed | 2,131.0 | 61.3 | 15.4 |
| 32K | mixed + MTP | 2,045.1 | 83.8 | 16.0 |
| 64K | REAP | 1,096.9 | 31.0 | 60.3 |
| 64K | REAP + MTP | 1,091.2 | 30.7 | 60.6 |
| 64K | mixed | 1,827.6 | 59.8 | 36.6 |
| 64K | mixed + MTP | 2,060.7 | 92.7 | 31.8 |
| 128K | REAP | 1,086.9 | 25.1 | 120.8 |
| 128K | REAP + MTP | 1,083.8 | 24.4 | 121.2 |
| 128K | mixed | 1,922.8 | 58.4 | 68.5 |
| 128K | mixed + MTP | 1,969.2 | 79.0 | 66.6 |
| 200K | REAP | 1,047.5 | 20.9 | 191.2 |
| 200K | REAP + MTP | 1,044.9 | 19.0 | 191.6 |
| 200K | mixed | 1,855.5 | 56.3 | 108.0 |
| 200K | mixed + MTP | 1,892.6 | 74.8 | 105.9 |
| 256K | REAP | 970.8 | 17.8 | 269.8 |
| 256K | REAP + MTP | 995.1 | 15.1 | 263.2 |
| 256K | mixed | 1,856.5 | 56.0 | 141.1 |
| 256K | mixed + MTP | 1,823.3 | 74.5 | 143.9 |

**长上下文下，mixed 的优势比较明显。**普通模式在 200K 和 256K 两档都能保持约 56 tok/s，REAP 则降到了约 21 和 18 tok/s。mixed 处理输入也更快：200K 输入约等 108 秒开始回答，REAP 约等 191 秒。

不过，256K 输入即使用 mixed，也要等约 141 秒才开始输出。这次关掉了前缀缓存，每次都得重新处理整段输入；日常多轮对话如果能复用历史缓存，等待时间需要另外测，不能直接套这张表。

### MTP 性能对比

mixed 在 200K 档从 56.3 提升到 74.8 tok/s，约快了 33%，256K 档也差不多。但首 token 时间基本没变，也就是说，它主要加快的是**开始回答之后的输出速度**。

REAP 的结果正好相反：两个长输入档位都变慢了，还多占了约 5 GB 内存。**按这轮结果，mixed 可以开 MTP 试试，REAP 跑长上下文时就保持普通模式。**

我还对比了相同输入下的首轮完整回答。REAP 开关 MTP 的 24 份回答全部逐字一致，mixed 只有 3 份一致。输出不同不等于质量下降，不过如果需要复现普通模式的回答，就不要在两种模式之间切换。



## 附：测试配置

### 硬件环境

| 项目 | 配置 |
| --- | --- |
| 机器 | Mac Studio，Apple M5 Max |
| CPU / GPU | 18 核 / 40 核 |
| 统一内存 | 128 GiB |
| 系统 | macOS 27.0 |

### 引擎配置

| 项目 | REAP | mixed |
| --- | --- | --- |
| 模型 | sh0wie/Qwen3.8-Flash-Next-REAP-288-MLX-4bit | ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit |
| 固定版本 | [668f31b](https://huggingface.co/sh0wie/Qwen3.8-Flash-Next-REAP-288-MLX-4bit/tree/668f31bcc56bf9400e64c9463445eee47597c2d9) | [3191916](https://huggingface.co/ddalcu/Qwen3.8-Flash-Next-MLX-Serve-mixed-4-8bit/tree/31919167b2e4549167cd4729b782f3155e75b686) |
| 引擎版本 | mlx-vlm 0.7.6 / MLX 0.32.3 | mlx-serve 26.10.1 |
| Ngram 加载 | SSD mmap，`ple_storage` | SSD mmap，`ngram_table.bin` |
| Ngram 设置 | `cache_rows=0` | 关闭 `ple-gpu`，`MLX_SERVE_NGRAM_WARM=0` |
| MLX 缓存上限 | 4 GiB | 8 GiB |
| MTP | 关闭、开启各测一轮完整档位 | 关闭、开启各测一轮完整档位 |

### 测试参数

| 项目 | 设置 |
| --- | --- |
| 同时加载模型 / 并发请求 | 1 / 1 |
| 目标输入长度（token） | 512、4,096、16,384、32,768、65,536、131,072、200,000、261,632 |
| 上下文窗口 | 262,144 token |
| 最大输出长度 | 256 token |
| Temperature / Seed | 0 / 42 |
| 思考模式 / 前缀缓存 | 关闭 / 关闭 |
| Prefill 分块 | 1,024 token |
| 重复次数 | 32K 及以下每项 3 次，64K 及以上每项 2 次 |
| 独立测速项 | 240 项 |
| 服务重启 | 每个上下文批次重启 |
| 系统文件缓存 | 不强制清空 |
| 中文语料 | Wikimedia Wikipedia `20231101.zh`，前 100 条训练文本 |
| 英文语料 | Wikimedia Wikipedia `20231101.en`，前 100 条训练文本 |
| 代码语料 | CPython v3.12.0，`Lib/*.py` 按路径排序，排除 test 目录 |
