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

OpenAI 在 [Harness engineering](https://openai.com/zh-Hans-CN/index/harness-engineering/) 这篇文章里讲了一件很重要的事：

**未来不是“人类写代码，AI 打辅助”，而是“人类定义意图、边界和约束，Agent 在这个支架里执行”。**

很多人看到这里，第一反应是给仓库加一个 `AGENTS.md`，再写几篇文档。

这当然有用，但如果只做到这一步，离 harness engineering 还差得很远。因为 agent 真正需要的不是一份“说明书”，而是一套可以直接工作的工程支架：

1. 它要知道从哪里开始读仓库。
2. 它要知道哪些文档是内部真相，哪些文档是给用户看的。
3. 它要知道哪些架构边界不能碰。
4. 它要能自己跑验证、复现问题、判断改动有没有破坏系统。
5. 它改完代码之后，还要能被 CI 和规则系统兜住。

最近我正好把自己的一个已有项目 `TermPilot` 做了一轮这样的改造。这个项目本来就已经有比较完整的架构说明、开发文档和测试脚本，但它更偏“人类开发者友好”，还不是“agent 可以稳定接手”的状态。

这篇文章就结合这次实战，讲讲如何把一个**已经存在的工程**，逐步改造成符合 harness engineering 思想的项目。

## 1. 先说结论：harness engineering 不是“多写文档”

如果只用一句话概括，我现在对 harness engineering 的理解是：

> 不是给 agent 写一本操作手册，而是把整个工程系统改造成 agent 能读懂、能操作、能验证、能持续收敛的工作环境。

所以一个仓库是否真正具备 harness engineering，不是看有没有 `AGENTS.md`，而是看下面这些东西是否同时存在：

1. 有统一入口。
2. 有内部知识库。
3. 有可执行约束。
4. 有 repo-native 的验证回路。
5. 有 CI 级别的自动反馈。
6. 有文档漂移的控制机制。

如果这些没有连起来，那么 agent 读到的就只是“建议”，不是“支架”。

## 2. 老项目改造最容易踩的坑

新项目从一开始按 agent-first 的方式设计，相对简单。已有工程反而更难，因为一般都会有这些历史包袱：

1. 文档很多，但分不清哪些是内部工程知识，哪些是用户文档。
2. 约束都写在架构图和 README 里，但没有机械检查。
3. 验证脚本能跑，但依赖个人本机环境，换台机器就废。
4. CI 只做 build，不做“架构回归”和“知识回归”。
5. 聊天里讨论过很多决策，但仓库里没有沉淀。

`TermPilot` 在改造前，其实已经解决了“有没有文档”和“有没有测试”的问题，但没有解决“agent 如何稳定消费这些东西”的问题。

所以我这轮改造的目标很明确：

1. 不重构用户文档站。
2. 单独建立一套内部 agent 文档体系。
3. 把架构原则变成检查器。
4. 把验证路径变成仓库原生能力。
5. 把文档同步要求拉进自动检查。

## 3. 第一步：把“给用户看的文档”和“给 agent 看的文档”分层

这一步非常关键。

很多项目已经有 `docs/`，但那通常是用户手册、部署手册、功能介绍，默认面向人类读者。agent 需要的则是另一种信息：

1. 仓库入口在哪。
2. 代码边界怎么分。
3. 哪些原则绝对不能破坏。
4. 复杂改动应该怎么留痕。
5. 改完之后跑什么验证。

在 `TermPilot` 里，我没有去碰原来的 VitePress 文档站，而是在仓库根目录和 `.agent/` 目录下单独建了内部知识体系：

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

这里的设计思路是：

1. `AGENTS.md` 很短，只做入口地图。
2. `ARCHITECTURE.md` 负责顶层代码和运行时关系。
3. `PLANS.md` 负责告诉 agent 复杂任务必须走执行计划。
4. `.agent/` 才是真正长期积累的内部工程知识库。

也就是说，**不要把 `AGENTS.md` 写成百科全书**。它最重要的价值不是“内容多”，而是“告诉 agent 下一步该读什么”。

## 4. 第二步：把架构原则收敛成可复用的内部真相

如果一个项目只有“模块很多”，却没有清晰的工程原则，那么 agent 很容易做出“局部看起来合理，整体却越来越乱”的改动。

所以我在 `TermPilot` 里做的第二件事，是把之前散落在架构说明、开发文档、历史讨论里的原则，集中成几个内部真相。

比如这几个原则非常关键：

1. session 的 source of truth 在 `agent`，不在 `relay`。
2. `relay` 只保存 pairing、grant、audit 这类元数据。
3. `app` 的定位是 viewing、light input、light control，不是桌面远控。
4. 跨 runtime 的共享结构必须走 `@termpilot/protocol`。
5. `shell` 和 `command` session 的退出语义不能混淆。

这些内容分别沉淀到了：

1. `AGENTS.md` 里的 golden rules。
2. `.agent/core-beliefs.md`
3. `.agent/runtime-boundaries.md`
4. `.agent/known-invariants.md`

这类文档的目标不是“解释项目为什么伟大”，而是让 agent 在改代码之前，先拿到一组不会轻易漂移的判断依据。

## 5. 第三步：复杂任务不要只存在于聊天记录里

这是我觉得最容易被忽略，但实际收益非常高的一步。

很多时候，复杂需求其实已经在聊天里分析得很清楚了，但一旦对话结束，这些背景信息就蒸发了。下一次 agent 再接手时，又得从头猜。

所以我在 `TermPilot` 里增加了 `PLANS.md` 和 `.agent/exec-plans/`，要求跨 runtime、跨模块、行为有歧义的任务，先落成执行计划再动手。

这类 plan 不需要写成 PRD，但至少要有：

1. 目标。
2. 非目标。
3. 涉及模块。
4. 验收标准。
5. 风险和回滚点。
6. 后续 debt。

这个动作的价值在于，它把原本“在脑子里”的上下文，变成了仓库的一部分。

对于 agent 来说，看不到的知识就等于不存在。把 plan 版本化之后，仓库就开始具备“持续交接”的能力。

## 6. 第四步：把文档里的边界，升级成检查器

这是从“有文档”走向“有 harness”最关键的一步。

如果架构边界只写在文档里，那么 agent 违反边界的成本很低，因为它不会立刻收到反馈。真正有效的方法是把边界变成脚本和 CI 规则。

在 `TermPilot` 里，我加了一个 `check:architecture`：

```json
{
  "scripts": {
    "check:architecture": "node scripts/check-architecture.mjs"
  }
}
```

这个检查器会扫描关键源码目录，只允许明确合法的依赖关系，例如：

1. `app` 不能直接 import `agent` 或 `relay` 的源码。
2. `agent`、`relay`、`app` 跨边界共享类型时，必须经过 `@termpilot/protocol`。
3. 根 CLI 只允许做顶层组装，不允许把所有运行时耦合成一团。
4. 未分类的 repo import 默认不放行，只保留显式白名单。

这类检查的意义，不在于“写一个很复杂的静态分析器”，而在于把项目最重要的架构约束机械化。只要这一步做了，agent 的行为就会自然收敛很多。

## 7. 第五步：让验证变成 repo-native，而不是“只在我电脑上能跑”

这是老项目非常常见的问题。

最初 `TermPilot` 的部分 UI 冒烟路径依赖本机 skill 路径，本质上属于“我这台机器能跑，但仓库本身没有完整表达这个能力”。这种东西对单人开发还凑合，对 agent 和 CI 都不够友好。

所以后面我做了两件事：

1. 把 UI smoke 改成仓库原生的 Playwright 脚本。
2. 把 E2EE 和烟测入口统一到 Node/TS 侧，旧的 Python 脚本只保留兼容包装层。

最终根脚本整理成了这样：

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

这里我刻意把验证拆成了几层：

1. `verify:fast` 负责日常快速回路。
2. `verify:full` 负责 CI 默认全量回路。
3. `verify:browser` 负责浏览器烟测。
4. `verify:e2ee` 负责跨端行为验证。

这么拆的原因很简单：**不是所有改动都值得拉起最重的验证，但每种改动都应该有一条清晰的验证路径。**

## 8. 第六步：让“文档更新”也进入自动检查

如果只检查代码正确性，不检查知识正确性，agent 最后还是会把仓库带回混乱状态。

所以我在 `TermPilot` 里加了两类和文档相关的检查：

1. `check:repo-docs`
2. `check:public-docs`

前者主要检查内部文档体系是否完整，后者更重要，它会根据 `.agent/public-doc-map.json` 判断：

1. 哪些实现目录发生了变化。
2. 这些变化是否触发了对应公共文档的同步更新。

也就是说，如果你改了某些关键实现，但没有触碰对应的公共文档，这个检查就会直接报错。

这件事看起来“有点麻烦”，但它实际上是 harness engineering 非常重要的一环：

**让知识漂移也变成可被发现的问题。**

## 9. 第七步：把这些规则放进 CI，而不是靠自觉

只要一个规则还停留在“团队约定”，它就迟早会被遗忘。

所以在 `TermPilot` 里，我新增了 PR 级别的 CI 工作流，主要做两件事：

1. 跑 `verify` job，覆盖 `verify:fast`、build、docs build 和 runtime checks。
2. 单独跑 `ui-smoke` job，安装 Chromium 后执行 repo-native 浏览器烟测。

这么做有两个好处：

1. 快回路和慢回路分离，默认 CI 不会被最重的浏览器任务拖死。
2. 浏览器路径不再是“本机私有能力”，而是仓库自己的验证能力。

到这一步为止，agent 的工作方式就开始发生变化了：

1. 它不是“随便改完试试看”。
2. 它会顺着 `AGENTS.md -> 内部知识库 -> 计划 -> 验证脚本 -> CI` 这条链路工作。
3. 如果它偏离边界，仓库会自己把它拽回来。

这才是 harness 的价值。

## 10. 我对这次改造的一个实际总结

如果复盘 `TermPilot` 这轮改造，我觉得最核心的变化不是新增了多少文件，而是仓库的角色变了。

改造前，仓库更像是：

1. 代码集合。
2. 文档集合。
3. 几条测试命令。

改造后，仓库开始变成：

1. agent 的入口地图。
2. 内部工程知识库。
3. 执行计划的落点。
4. 架构边界的机械检查器。
5. 仓库原生的验证环境。
6. 文档和实现的一致性约束系统。

换句话说，**以前仓库是在“存东西”，现在仓库开始“约束行为”了。**

## 11. 如果你也要改一个老项目，我建议按这个顺序来

如果你手里也有一个已有工程，想往 harness engineering 的方向升级，我建议按下面这个顺序推进：

1. 先建 `AGENTS.md`，但只写入口，不写大全。
2. 把内部 agent 文档和用户文档彻底分层。
3. 把架构原则收敛成 golden rules 和 invariants。
4. 增加 plan 机制，让复杂任务版本化。
5. 先做最小可用的 `check:architecture`。
6. 再整理 repo-native 的 `verify:fast` / `verify:full`。
7. 最后补 doc freshness 和 CI 级别回路。

不要一上来就追求“把所有规则都自动化”。对已有工程来说，更现实的路径是先把最关键的 20% 原则机械化，它们往往能解决 80% 的混乱。

## 12. 结语

我现在越来越认同一个判断：

未来工程师最重要的能力之一，不再只是“把功能写出来”，而是**把系统设计成 agent 能持续接手、持续收敛、持续演化的形态**。

这就是我理解的 harness engineering。

它不是一个新术语的包装，也不是“仓库里多放几个 markdown 文件”。它真正改变的是工程的重心：

1. 从“人直接实现”转向“人设计执行环境”。
2. 从“经验约束”转向“系统约束”。
3. 从“聊天上下文”转向“仓库内版本化知识”。

如果你的项目已经有一定体量，我会非常建议尽早开始做这件事。因为项目越大，agent 越强，这套支架的重要性只会越来越高。

## 13. 最后介绍一下 TermPilot

`TermPilot` 是我在做的一个基于 `tmux` 的终端会话跨端查看与轻控制项目。它的目标不是远程桌面，也不是传统意义上的 Web SSH，而是把本地终端会话、移动端查看、配对授权和 relay 协作这几件事，以更轻量的方式串起来。

如果你对这篇文章里提到的 harness engineering 改造细节感兴趣，也欢迎直接看项目本身：

1. 文档站：[https://fengye404.top/TermPilot/](https://fengye404.top/TermPilot/)
2. GitHub：[https://github.com/fengye404/TermPilot](https://github.com/fengye404/TermPilot)

也欢迎大家顺手点个 Star，实际试一试；如果你在使用过程中有任何问题、想法或者改进建议，也非常欢迎提 Issue 一起讨论。
