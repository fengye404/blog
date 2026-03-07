---
title: GitHub Profile 自动同步实践
typora-root-url: ./GitHub-Profile自动同步实践
date: 2026-03-07 18:10:00
tags:
  - GitHub
  - GitHub Actions
  - 自动化
  - AI
---

# GitHub Profile 自动同步实践

> 本文由 AI 参与创作

## 前言

最近我把 GitHub Profile 做了一轮比较彻底的整理，目标不是“好看”，而是“真实、可维护、可自动更新”。

我之前的 Profile 有几个典型问题：

1. 项目描述和仓库现状有偏差。
2. 统计图依赖第三方外链，偶发加载失败。
3. 内容更新靠手工维护，时间久了肯定过期。

这篇文章把这次改造的完整方案记录下来，后续我也会持续基于这个方案做迭代。

## 这次改造我做了什么

围绕 `github-profile` 仓库，这次我实际完成了这些工作：

1. 基于 GitHub API 拉取真实仓库信息（非 fork、活跃时间、stars/forks、主语言），重写了 Profile 的项目展示。
2. 新增双语 Profile（`README.md` + `README.zh-CN.md`）。
3. 新增自动同步脚本：`scripts/sync_profile_readme.py`。
4. 新增 GitHub Actions：`.github/workflows/sync-profile.yml`，支持手动触发 + 定时触发。
5. 增加 AI 声明：明确标注 Profile 部分内容由 AI 自动生成。
6. 统一邮箱为：`fengye4302@gmail.com`。
7. 去掉不稳定的外链统计图，改为文本统计表，避免“断图”。

## 目标拆解

我给这次改造设了三个明确目标：

- **真实性**：展示内容必须来自当前真实仓库数据。
- **稳定性**：不依赖易失效的外链展示。
- **低维护**：让更新动作自动化，尽量不手工改 README。

## 方案设计

### 1. 用一个脚本统一生成两份 README

核心脚本：`scripts/sync_profile_readme.py`

这个脚本做的事情比较直接：

- 调 GitHub API 拉用户与仓库数据。
- 筛选非 fork 仓库。
- 按优先级生成 Active Projects 和 Representative Repos。
- 统计 Profile 概览数据（仓库数、followers、stars、forks、语言）。
- 输出英文和中文两份 README。

为了降低限流风险，我也加了 `GITHUB_TOKEN` 支持：

```python
USERNAME = os.getenv("GITHUB_USERNAME", "fengye404")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()

headers = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "profile-readme-sync",
}
if GITHUB_TOKEN:
    headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
```

### 2. GitHub Actions 负责自动执行

工作流文件：`.github/workflows/sync-profile.yml`

- 手动触发：`workflow_dispatch`
- 定时触发：`cron: '0 2 * * *'`（UTC 02:00，即北京时间 10:00）
- 只在有变更时自动提交，避免空提交

核心配置如下：

```yaml
on:
  workflow_dispatch:
  schedule:
    - cron: '0 2 * * *'

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Sync profile README
        env:
          GITHUB_USERNAME: ${{ github.repository_owner }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python3 scripts/sync_profile_readme.py
```

### 3. 明确自动化来源

我在 Profile 中增加了说明，避免“内容来源不清晰”：

- 部分内容由 AI 自动生成。
- 数据由 GitHub Actions 定期同步。

这个声明不仅写在 README 里，也写入了脚本模板里，避免后续同步把这段说明冲掉。

## 为什么放弃第三方统计图

之前 `github-readme-stats` 这种外链图有时会加载失败，页面会出现断图图标，影响可读性。

这次我改成了文本统计表（例如仓库数、followers、总 stars、总 forks、主要语言），好处很明显：

- 不依赖第三方图床/接口可用性。
- 渲染稳定。
- 内容可审计，可追踪。

对技术类 Profile 来说，我更看重稳定和可信，而不是花哨展示。

## 本地调试与发布流程

在 `github-profile` 仓库中，本地可这样验证：

```bash
python3 -m py_compile scripts/sync_profile_readme.py
python3 scripts/sync_profile_readme.py
```

推送后可在 GitHub Actions 手动跑一次工作流验证：

1. 进入 Actions 页面。
2. 选择 `Sync Profile README`。
3. 点击 `Run workflow`。

如果你要启用自动提交，记得检查仓库设置：

- `Settings -> Actions -> General -> Workflow permissions`
- 需要选择 `Read and write permissions`

## 踩坑记录

这次主要遇到两个问题：

1. **GitHub API 限流（403）**
   - 原因：未带 token 的匿名请求配额较低。
   - 处理：脚本支持 `GITHUB_TOKEN`，Actions 中注入 `secrets.GITHUB_TOKEN`。

2. **统计图断图**
   - 原因：第三方统计图接口偶发不可用。
   - 处理：替换为文本统计表。

## 总结

这轮改造让我对 Profile 的定位更明确了：

- 它应该是“真实工程状态”的入口，而不是静态名片。
- 自动化的价值不只是省时间，更是避免信息过期。
- 明确标注 AI 参与，是对读者和自己负责。

后续我计划继续做两件事：

1. 把项目描述进一步和仓库 README 自动联动。
2. 在同步脚本里增加简单校验，防止异常数据直接发布。

如果你也在做 GitHub Profile 自动化维护，希望这篇实战记录对你有帮助。
