# 实验源码与复现

这份目录保存预训练篇实际使用的脚本；训练在 Mac Studio 上运行，使用 MPS float32。它们是本次实验副本，未修改课程仓库的实现。

## 环境

Python 3.12.14，依赖见 requirements.txt。脚本默认工作目录是自身所在目录，部分配置固定为本文的小模型。

## 数据

- TinyStories: roneneldan/TinyStories，revision f54c09fd23315a6f9c86f9dc80f725de7d8f9c64。
  将 TinyStoriesV2-GPT4-train.txt、TinyStoriesV2-GPT4-valid.txt 分别下载到 data/train.txt、data/valid.txt，然后运行 prepare.py。
- OpenWebText: stanford-cs336/owt-sample，revision 488afadefc224407de5645a3c8c53b64ed923537。
  prepare_owt.py 下载、训练 tokenizer、预编码。下载命令使用本机 127.0.0.1:7897 代理；其他环境应移除 --proxy 参数或使用自己的代理。
- 两套 BPE 各自在训练集前 10,000 篇文档上训练，vocab=10,000；原始 tokenizer 随文章资源保存，便于固定词表复查。
- 数据文件和模型 checkpoint 体积较大，保留在执行机器，未混入文章资源。

## 执行

先运行 run.py 生成基线，再运行 evaluate_final.py 得到完整验证结果。run.py 从零训练，不能覆盖已有基线目录。

suite.py 读取已有基线，顺序执行学习率、消融、权重共享、batch 和 OWT。result.json 存在时跳过该项；experiment.py 可从对应 resume.pt 恢复。batch_retune.py 等待 SUITE_DONE.json 后补跑 batch 的学习率复验。不要同时启动两份队列。

单轮示例：

```sh
.venv/bin/python experiment.py --name custom-run --lr .003 --tokens 40960000
```

运行结果在 runs/<name>/ 下，包括 config.json、metrics.jsonl、result.json、samples.json 和 checkpoint。每组最终验证结果应以 result.json 为准。

verify_training.py 运行课程提供的 AdamW、学习率、交叉熵、梯度裁剪和 checkpoint 断言；sgd_toy.py 运行文中的 SGD 小实验。

## 图与统计

文章资源 experiments/ 保存全部轻量日志和结果，不含训练数据与 checkpoint。plot_experiments.py 从这些日志生成曲线；plot_loss.py 生成首轮基线曲线。曲线按累计 token 和训练循环耗时绘制，不把提前发散当成完成训练。

完整验证将数据切为不重叠的 256-token 窗口并丢弃尾部不足一窗部分。抽样验证固定 20 个 batch，每个 32×256 token，seed=2026。不同数据集使用独立词表，loss 不做跨数据集排名。

24 GiB 是本次 MPS 训练进程的分配预算，用于给机器原有服务留空间；batch 探测不代表整机 128 GB 内存的物理极限。
