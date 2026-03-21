---
title: 从 Prompt Engineering 到 Harness Engineering：TermPilot 的改造实践
typora-root-url: ./从Prompt-Engineering到Harness-Engineering：TermPilot的改造实践
date: 2026-03-22 04:20:16
tags:
  - AI
  - Agent
  - 工程化
  - OpenAI
  - 软件架构
---

# 从 Prompt Engineering 到 Harness Engineering：TermPilot 的改造实践

> 本文由 AI 参与创作

## 前言

`TermPilot` 是我业余时间写的一个项目，前期基本就是 `Codex + vibecoding` 的开发方式。功能先做出来，结构在开发过程中逐步成型，文档、脚本、协议边界也都有，但比较散。

后来补看了 OpenAI 的 [Harness engineering](https://openai.com/zh-Hans-CN/index/harness-engineering/) 之后，我回头整理了一轮 `TermPilot`，才意识到这件事的重点不在 prompt，而在工程环境本身。

本文不讨论“如何从零设计一个 agent-first 项目”，只聚焦一件事：一个已经在持续开发的项目，怎么往 harness engineering 的方向收。

## 1. 先说结论：harness engineering 解决的是什么问题

对已有工程来说，harness engineering 主要解决三类问题：

1. agent 进入仓库后不知道先看什么，靠聊天补上下文。
2. 架构边界只写在文档里，违反了也没有反馈。
3. 验证依赖作者本机环境，agent 和 CI 复跑不了。

`TermPilot` 改造前基本就是这个状态。项目能往前走，但很依赖我自己一直在线，很多上下文也只存在聊天记录和脑子里。

## 2. 我在 TermPilot 里做了哪些改动

### 2.1 先把入口补齐

第一步是把 agent 进入仓库的路径固定下来。

我在仓库根目录加了 `AGENTS.md`、`ARCHITECTURE.md`、`PLANS.md`，同时把内部工程知识收进 `.agent/`：

```text
AGENTS.md
ARCHITECTURE.md
PLANS.md
.agent/
  index.md
  core-beliefs.md
  runtime-boundaries.md
  known-invariants.md
  verification.md
  tech-debt-tracker.md
  exec-plans/
```

这里的分工很明确：

- `AGENTS.md` 只做入口，不写成长手册。
- `ARCHITECTURE.md` 负责顶层结构和运行时关系。
- `PLANS.md` 规定复杂任务先写计划。
- `.agent/` 负责长期沉淀内部知识。

这一步做完之后，agent 至少知道从哪里进入仓库，不用每次都靠我重新解释一遍。

### 2.2 把散落的原则收成内部真相

`TermPilot` 原来就有一些稳定的设计约束，只是没有集中表达。

这次我把几条关键原则单独沉淀了下来：

- session 的 source of truth 在 `agent`
- `relay` 只保存 pairing、grant、audit 这类元数据
- 跨 runtime 共享结构统一走 `@termpilot/protocol`
- `shell` 和 `command` session 的退出语义分开处理

这些内容后来分别落到了 `AGENTS.md` 和 `.agent/*.md` 里。这样做的目的很直接：让 agent 在改代码前先拿到一组稳定约束。

### 2.3 复杂任务先落 plan

跨模块、跨 runtime、行为有歧义的任务，我现在都会先写到 `.agent/exec-plans/` 里。

这一步的价值在于把“为什么这么改”留在仓库里。否则对话结束之后，背景信息就断掉了，后续接手成本会很高。

### 2.4 把文档约束变成检查器

只有文档，没有检查器，边界很快就会失效。

所以我在 `TermPilot` 里补了 `check:architecture`，专门检查几个关键约束：

- `app` 不能直接 import `agent`、`relay` 源码
- 跨 runtime 共享类型必须经过 `@termpilot/protocol`
- 根 CLI 只做顶层组装
- 未分类的 repo import 默认不放行

脚本入口很简单：

```json
{
  "scripts": {
    "check:architecture": "node scripts/check-architecture.mjs"
  }
}
```

这种检查不需要一开始就做得很重，先把最关键的边界机械化，收益已经很明显。

### 2.5 把验证整理成 repo-native

这一步对已有工程特别重要。

`TermPilot` 早期有一些验证脚本是“我机器上能跑”，但仓库本身表达不完整。后面我把这些入口统一收成了仓库原生脚本：

```json
{
  "scripts": {
    "verify:fast": "pnpm typecheck && pnpm check:architecture && pnpm check:repo-docs && pnpm check:public-docs",
    "verify:full": "pnpm verify:fast && pnpm build && pnpm docs:build && pnpm test:relay-storage:built && pnpm test:app-versioning:built && pnpm test:isolation:built",
    "verify:browser": "pnpm build && pnpm test:ui-smoke:built",
    "verify:e2ee": "pnpm build && pnpm test:e2ee:built"
  }
}
```

这里有两个实际动作：

1. 把 UI smoke 改成仓库里的 Playwright 脚本。
2. 把 E2EE 和烟测入口统一到 Node/TS，Python 只保留兼容包装层。

这样 agent 能跑，CI 也能跑，同一套入口不会分叉。

### 2.6 文档同步也进入检查

只检查代码，不检查文档，很容易把仓库重新带回混乱状态。

所以我加了两类文档检查：

- `check:repo-docs`：检查内部文档体系是否完整
- `check:public-docs`：根据 `.agent/public-doc-map.json` 检查实现改动是否同步更新了对应文档

这个动作不复杂，但很有用。它至少能挡住一类很常见的问题：实现已经变了，文档还停在旧状态。

### 2.7 最后接到 CI

规则只写在文档里不够，最终还是要接到 CI。

`TermPilot` 现在的 PR 级 CI 会跑：

- `verify:fast`
- build
- docs build
- runtime checks
- 独立的 `ui-smoke` job

这样 agent 改完代码之后，仓库本地能跑一遍，CI 还能再复跑一遍。

## 3. 这套改动带来的变化

这轮改造做完之后，开发方式变得很明显。

以前更像是：我把上下文讲清楚，agent 继续往下写，偏了再纠偏。  
现在更像是：agent 先按入口读仓库，再看计划和约束，改完跑对应验证，最后交给 CI 收口。

前后差别主要有三点：

1. 复杂任务的上下文不再只存在聊天记录里。
2. 架构边界开始有机械反馈，不再只靠“记得遵守”。
3. 验证能力从“作者本机能力”变成了“仓库能力”。

对我来说，这也是这轮改造最核心的收获。harness engineering 不是多写几篇文档，而是把仓库从“存放代码的地方”往“约束 agent 工作方式的系统”推进了一步。

## 4. 如果你也要改一个已有工程

我的建议是按下面这个顺序来：

1. 先补一个很短的 `AGENTS.md`
2. 把内部 agent 文档和对外文档分层
3. 收敛几条最关键的 invariants
4. 给复杂任务补计划机制
5. 先做最小可用的 `check:architecture`
6. 把验证收成 repo-native 的 `verify:*`
7. 最后再补 doc freshness 和 CI

不要一开始就追求“大而全”。已有工程里最有效的做法，通常是先把最容易漂移、最容易误解的那部分规则固定下来。

## 5. 最后介绍一下 TermPilot

`TermPilot` 主要解决的是一个很具体的场景：电脑上已经有一条终端会话在跑，你离开工位之后，还想继续从手机查看输出、补一条命令，或者做一些简单控制。

一个常见用法是这样的：

- 你在电脑上跑 `Claude Code`
- 或者跑部署脚本、数据库迁移、长时间批处理
- 人离开工位后，用手机继续看会话状态

如果你想快速试一下，可以直接按下面的顺序：

1. 在一台手机可访问的机器上启动 `termpilot relay`
2. 在自己的电脑上启动 `termpilot agent`
3. 用手机浏览器打开 relay 地址，输入配对码
4. 在电脑上执行 `termpilot claude code`，或者 `termpilot run -- <command>`
5. 然后在手机上继续看同一条会话

我实际跑了一次当前 app 端，下面这张图就是一个实际使用场景：电脑上已经有一条 `deploy-prod-demo` 会话在跑，手机端接入后可以继续看输出，也可以补命令和做快捷控制。

![TermPilot 移动端页面截图](./termpilot-mobile-demo.png)

项目地址：

- 文档站：[https://fengye404.top/TermPilot/](https://fengye404.top/TermPilot/)
- GitHub：[https://github.com/fengye404/TermPilot](https://github.com/fengye404/TermPilot)

如果你对这类场景感兴趣，欢迎来试用，也欢迎顺手点个 Star。有问题或者想法，也可以直接提 Issue。
