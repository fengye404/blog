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

我平时主要做 `Java` 服务端开发，`TermPilot` 是我业余时间写的一个端侧 `vibecoding` 项目。前期基本就是 `Codex + vibecoding` 的开发方式。功能先做出来，结构在开发过程中逐步成型，文档、脚本、协议边界也都有，但没有被系统化整理。

后来补看了 OpenAI 的 [Harness engineering](https://openai.com/zh-Hans-CN/index/harness-engineering/) 之后，我回头整理了一轮 `TermPilot`，才意识到问题不在 prompt 本身，而在工程环境。

也正因为这个背景，这次改造对我反而更有启发。它虽然发生在一个个人端侧项目里，但暴露出来的问题，并不只属于端侧开发。很多问题在已有的 `Java` 服务端仓库里同样存在，只是平时没有被这样集中地放大出来。

本文不讨论“如何从零设计一个 agent-first 项目”，只讨论一件事：一个已经在持续开发的项目，怎么往 harness engineering 的方向改。

现在回头看，harness engineering 更像一种工程设计思路。重点不在某个单点工具，而在系统怎样组织入口、约束、验证和反馈。

## 1. 先说结论：harness engineering 解决的是什么问题

对已有工程来说，harness engineering 主要解决三类问题：

1. agent 进入仓库后不知道先看什么，靠聊天补上下文。
2. 架构边界只写在文档里，违反了也没有反馈。
3. 验证依赖作者本机环境，agent 和 CI 复跑不了。

`TermPilot` 改造前基本就是这个状态。项目能继续往前走，但很依赖我自己一直在线。很多上下文存在聊天记录里，很多判断标准存在脑子里，很多验证能力存在本机环境里。

这也是 prompt engineering 的天然边界。prompt 可以提升 agent 的单次输出质量，但解决不了工程系统本身的信息分布问题。仓库入口不清晰、边界没有约束、验证无法复跑时，prompt 再精细，也只能缓解问题，不能消除问题。

因此，harness engineering 的重点很明确：把原来依赖人脑维护的那部分工程信息，逐步转成仓库内部可读取、可验证、可反馈的系统能力。

## 2. 我在 TermPilot 里做了哪些改动

### 2.1 先把入口补齐

第一步是固定 agent 进入仓库的路径。

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

这几类文件的职责是分开的：

- `AGENTS.md` 只做入口，不写成长手册。
- `ARCHITECTURE.md` 负责顶层结构和运行时关系。
- `PLANS.md` 规定复杂任务先写计划。
- `.agent/` 负责长期沉淀内部知识。

这里最重要的点只有一个：`AGENTS.md` 不能写成百科全书。它的职责不是把所有知识塞进一个文件，而是告诉 agent 先读什么、后读什么、复杂任务要不要先落 plan。入口清晰，后面的约束和验证才有意义。

### 2.2 把散落的原则收成内部真相

`TermPilot` 原来就有一些稳定的设计约束，只是没有集中表达。没有被集中表达的原则，本质上就还不是原则，只能算经验。

这次我把几条关键原则单独沉淀了下来：

- session 的 source of truth 在 `agent`
- `relay` 只保存 pairing、grant、audit 这类元数据
- 跨 runtime 共享结构统一走 `@termpilot/protocol`
- `shell` 和 `command` session 的退出语义分开处理

这些内容后来分别落到了 `AGENTS.md` 和 `.agent/*.md` 里。这样做的目的很直接：让 agent 在改代码前先拿到一组稳定约束，而不是在改完之后再靠人去纠偏。

这一步看起来像在写文档，实质上是在定义系统边界。边界一旦没有被显式表达，agent 就只能按局部合理性继续生长，最后很容易把仓库带回到“每次改动都能讲通，但整体越来越乱”的状态。

### 2.3 复杂任务先落 plan

跨模块、跨 runtime、行为有歧义的任务，我现在都会先写到 `.agent/exec-plans/` 里。

这一步解决的是“为什么这么改”。

很多复杂需求在聊天里已经分析得很清楚了，但对话结束之后，这些背景信息就跟着消失了。下一次再接手，只能重新补上下文，或者直接猜。plan 的价值就在这里：把目标、非目标、验收标准、风险、涉及模块和决策依据留在仓库里，让后续接手的人和 agent 都能看到。

对于 agent 来说，看不到的知识等于不存在。执行计划一旦进入版本控制，仓库才开始具备持续交接能力。

### 2.4 把文档约束变成检查器

只有文档，没有检查器，边界很快就会失效。因为文档只能描述规则，检查器才能执行规则。

所以我在 `TermPilot` 里补了一类结构检查，专门检查几个关键约束。在这个项目里，对应的入口是 `check:architecture`：

- `app` 不能直接 import `agent`、`relay` 源码
- 跨 runtime 共享类型必须经过 `@termpilot/protocol`
- 根 CLI 只做顶层组装
- 未分类的 repo import 默认不放行

对应脚本入口很简单：

```json
{
  "scripts": {
    "check:architecture": "node scripts/check-architecture.mjs"
  }
}
```

这种检查不需要一开始就做得很重。已有工程里，先把最关键的 20% 结构约束机械化，收益就很明显。因为从这一刻开始，边界不再依赖“记得遵守”，而是变成了“违反就会报错”。

### 2.5 把验证整理成仓库内可直接运行的入口

这一步对已有工程特别重要。

`TermPilot` 早期有一些验证脚本是“我机器上能跑”，但仓库本身表达不完整。后面我把这些入口统一收成了仓库里的标准脚本：

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

这里要强调的不是这些脚本名本身，而是背后的思路：把原来依赖个人环境的界面检查、端到端检查和兼容入口，全部收敛到仓库自己的验证路径里。这样 agent 能跑，CI 能跑，其他协作者也能跑，验证能力不再附着在某一台开发机器上。

这一步也是已有工程最容易忽略的地方。很多项目并不是没有验证，而是验证能力没有被仓库完整表达出来。对于 agent 来说，这两者几乎没有区别。

### 2.6 文档同步也进入检查

只检查代码，不检查文档，很容易把仓库重新带回混乱状态。因为知识漂移本身也是一种工程错误。

所以我加了两类文档检查。在 `TermPilot` 里，对应的是下面两个入口：

- `check:repo-docs`：检查内部文档体系是否完整
- `check:public-docs`：根据 `.agent/public-doc-map.json` 检查实现改动是否同步更新了对应文档

这个动作不复杂，但很有用。它至少能挡住一类很常见的问题：实现已经变了，文档还停在旧状态。

对 agent 工程来说，文档不是装饰物，而是运行时上下文的一部分。如果实现和文档长期漂移，agent 读到的仓库就是一个自相矛盾的系统。

### 2.7 最后接到 CI

规则只写在文档里不够，最终还是要接到 CI。

`TermPilot` 现在的 PR 级 CI 会跑：

- `verify:fast`
- build
- docs build
- runtime checks
- 独立的 `ui-smoke` job

这样 agent 改完代码之后，仓库本地能跑一遍，CI 还能再复跑一遍。到这一步，入口、约束、验证和反馈才真正闭环。

## 3. 这套改动带来的变化

这轮改造做完之后，开发方式变得很明显。

以前更像是：我把上下文讲清楚，agent 继续往下写，偏了再纠偏。  
现在更像是：agent 先按入口读仓库，再看计划和约束，改完跑对应验证，最后交给 CI 收口。

前后差别主要有三点：

1. 复杂任务的上下文不再只存在聊天记录里。
2. 架构边界开始有机械反馈，不再只靠“记得遵守”。
3. 验证能力从“作者本机能力”变成了“仓库能力”。

对我来说，这也是这轮改造最核心的收获。harness engineering 不是多写几篇文档，而是把仓库从“存放代码的地方”往“约束 agent 工作方式的系统”推进了一步。脚本、检查器、CI 都只是落地形式，核心仍然是工程系统的组织方式。

换句话说，prompt engineering 关注的是“怎么把一次任务说清楚”，harness engineering 关注的是“怎么让一个项目长期可接手、可验证、可收敛”。当 agent 开始持续参与开发时，后者才是决定上限的那部分能力。

## 4. 如果你也要改一个已有工程

如果你手里也有一个已有工程，我建议按下面这个顺序推进：

1. 先固定 agent 进入仓库的入口
2. 把内部工程知识和对外文档分层
3. 收敛几条最关键的设计约束
4. 给复杂改动补计划和决策记录
5. 先做最小可用的结构检查
6. 把常用验证整理成仓库内统一入口
7. 最后再补文档联动检查和自动化回路

不要一开始就追求“大而全”。已有工程里最有效的做法，通常是先把最容易漂移、最容易误解、最容易被 agent 误判的那部分规则固定下来。

这里有一个判断标准很实用：如果某条规则一旦被打破，就会让后续改动持续变贵，那它就值得优先机械化。通常这类规则不是业务细节，而是入口、边界、验证和交接。

如果把这个思路放回我更熟悉的 `Java` 服务端场景，落点其实也很集中：先把模块和分层边界说清楚，再固定本地运行、联调和回归入口，然后把事务、幂等、缓存一致性、消息语义、接口兼容性这类关键约束显式化，最后把单测、集成测试、契约检查、迁移校验这些关键路径沉淀成仓库内可直接运行的验证。

对服务端开发来说，harness engineering 带来的启发也很直接：不要只想着“怎么让 agent 帮我写一个 controller 或 service”，而是先把这个服务端工程整理成 agent 能进入、能判断、能验证的系统。只有这样，后面的 vibecoding 才会越来越稳，而不是越写越乱。

## 5. 最后介绍一下 TermPilot

上面这套改造，落地的对象就是 `TermPilot`。

它解决的是一个很具体的场景：电脑上已经有一条终端会话在跑，人离开工位之后，还想继续从手机查看输出、补一条命令，或者做一些简单控制。

这类场景在日常开发里很常见，比如：

- 你在电脑上跑 `Claude Code`
- 或者跑部署脚本、数据库迁移、长时间批处理
- 人离开工位后，用手机继续看会话状态

如果你想快速试一下，可以按下面的顺序启动：

1. 在一台手机可访问的机器上启动 `termpilot relay`
2. 在自己的电脑上启动 `termpilot agent`
3. 用手机浏览器打开 relay 地址，输入配对码
4. 在电脑上执行 `termpilot claude code`，或者 `termpilot run -- <command>`
5. 然后在手机上继续看同一条会话

下面这张图就是我实际跑起来的一次使用场景。电脑上已经有一条 `deploy-prod-demo` 会话在跑，手机端接入后可以继续看输出，也可以补命令和做快捷控制。

![TermPilot 移动端页面截图](./termpilot-mobile-demo.png)

如果你想直接看项目本身：

- 文档站：[https://fengye404.top/TermPilot/](https://fengye404.top/TermPilot/)
- GitHub：[https://github.com/fengye404/TermPilot](https://github.com/fengye404/TermPilot)

欢迎试用，也欢迎点个 Star。有问题或者想法，可以直接提 Issue。
