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

`TermPilot` 是我在做的一个基于 `tmux` 的终端会话跨端查看与轻控制项目。它不是远程桌面，也不是传统意义上的 Web SSH，而是把本地终端会话、移动端查看、配对授权和 relay 协作这几件事，以更轻量的方式串起来。

这个项目最开始的开发方式，其实和很多个人项目差不多：我自己最熟悉系统边界，很多背景知识在脑子里；文档有一些，测试脚本也有一些，但它们更像“辅助材料”，还没有形成一套稳定的工作流。自己写代码的时候问题不大，但一旦开始让 coding agent 真正持续参与开发，问题就很快暴露出来了。

改造前，很多事情的默认路径还是“先聊、先做、靠经验兜底”。一个复杂需求过来，先靠上下文讲清楚，再让 agent 动手；如果中间哪里偏了，就继续补充说明；改完之后再人工判断哪里需要跑验证、哪里需要补文档。这个流程不能说不能用，但它本质上是“人记住一切，然后 agent 局部执行”。

有了这轮 harness 改造之后，开发方式就开始不一样了。现在更像是：先让仓库自己表达清楚边界和真相，复杂任务先留 plan，再让 agent 沿着固定入口去读、去改、去跑验证；如果它越界或者漏了同步更新，脚本和 CI 会直接报错。也就是说，原来很多靠“人脑维护”的东西，开始慢慢转成了“仓库自己维护”。

最开始看到 OpenAI 的 [Harness engineering](https://openai.com/zh-Hans-CN/index/harness-engineering/) 这篇文章时，我的第一反应其实很朴素：这不就是给 coding agent 补一套仓库规范吗？

后来真的在 `TermPilot` 上动手改了一轮，我发现这个理解还是太窄了。因为如果只是“补一篇 `AGENTS.md`，再加几篇说明文档”，agent 的体验确实会稍微好一点，但远远谈不上 harness engineering。agent 真正依赖的不是一份说明书，而是一整套可以工作的工程支架：它怎么进仓库、怎么判断边界、怎么跑验证、怎么复盘失败、怎么避免知识继续漂移。

这也是我后来觉得这个话题很有意思的地方。以前大家讨论得更多的是 prompt engineering，也就是怎么把一句话写对、把提示词调顺。但开始让 agent 真正在代码仓库里连续工作之后，问题重心会明显变化。真正影响效果的，往往不再是 prompt 本身，而是环境是不是清楚、边界是不是稳定、错误是不是会立刻暴露出来。

这篇文章就结合这次实战，讲讲我怎么把一个**已经存在的工程**往 harness engineering 的方向推，以及这个过程里，我对开发方式本身的理解是怎么变化的。

## 1. 我后来对 harness engineering 的理解

如果现在让我再用一句话总结，我会说：

> harness engineering 不是给 agent 多喂一点提示，而是把工程系统改造成 agent 可以稳定执行、稳定验证、稳定收敛的工作环境。

对我来说，这个概念至少包含三层意思。

第一层，是仓库必须有明确入口。agent 不能靠猜，也不能靠你临时补充上下文，它需要一条稳定的进入路径，知道先看哪里，再看哪里，复杂任务要不要先留计划。

第二层，是边界和约束要尽量机械化。只写在文档里的规则，其实仍然是软约束；真正有用的是把最重要的那些边界变成检查器、变成验证脚本、变成 CI。

第三层，是知识要版本化。一个项目里最容易丢的往往不是代码，而是“为什么这样做”的背景。如果这些东西一直只存在聊天记录或者脑子里，那 agent 接手几轮之后，仓库很快就会重新变乱。

## 2. 老项目改造难，不是因为东西少，而是因为东西太多

新项目如果从一开始就是 agent-first 的思路，很多结构可以一开始就摆正。老项目反而更麻烦，因为它通常不是“什么都没有”，而是“什么都有一点”。

`TermPilot` 改造前其实就是这种状态：有文档，但对外文档、开发说明、内部约定混在一起；有测试脚本，但有些路径对“我的机器”友好，对“这个仓库”不友好；有架构说明，但不少东西停留在“大家都知道”的层面；也有开发经验，但很多关键上下文只存在于历史聊天或者我自己的脑子里。

所以这轮改造我一开始就给自己定了几个边界：不去碰对外文档的主体结构，只补一层面向 agent 的内部工程系统；尽量把“约定”变成“检查”；尽量把“我本机能跑”变成“仓库原生能跑”；尽量把“聊过就算了”变成“留在 repo 里”。

## 3. 第一步：把“给用户看的文档”和“给 agent 看的文档”分层

这一步非常关键。

很多项目已经有 `docs/`，但那通常是用户手册、部署手册、功能介绍，默认面向人类读者。agent 需要的则是另一种信息：仓库入口在哪，代码边界怎么分，哪些原则不能碰，复杂改动怎么留痕，改完之后跑什么验证。

在 `TermPilot` 里，我没有去动现有的对外文档结构，而是在仓库根目录和 `.agent/` 目录下单独建了内部知识体系：

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

这里的思路其实很简单：`AGENTS.md` 很短，只做入口地图；`ARCHITECTURE.md` 负责顶层代码和运行时关系；`PLANS.md` 负责告诉 agent 复杂任务必须走执行计划；`.agent/` 才是真正长期积累的内部工程知识库。

也就是说，**不要把 `AGENTS.md` 写成百科全书**。它最重要的价值不是“内容多”，而是“告诉 agent 下一步该读什么”。

这也是我现在比较认同的做法：`AGENTS.md` 最好像目录，而不是像手册。真正容易变化、需要长期维护的内容，应该拆进更具体的文件里。否则它很快就会同时变成过期信息、重复信息和噪音来源。

## 4. 第二步：把架构原则收敛成可复用的内部真相

如果一个项目只有“模块很多”，却没有清晰的工程原则，那么 agent 很容易做出“局部看起来合理，整体却越来越乱”的改动。

所以我在 `TermPilot` 里做的第二件事，是把之前散落在架构说明、开发文档、历史讨论里的原则，集中成几个内部真相。

比如几个关键原则，我最后都明确写进去了：session 的 source of truth 在 `agent`，不在 `relay`；`relay` 只保存 pairing、grant、audit 这类元数据；`app` 的定位是 viewing、light input、light control，不是桌面远控；跨 runtime 的共享结构必须走 `@termpilot/protocol`；`shell` 和 `command` session 的退出语义不能混淆。这些内容后来分别沉淀进了 `AGENTS.md` 的 golden rules，以及 `.agent/core-beliefs.md`、`.agent/runtime-boundaries.md`、`.agent/known-invariants.md`。

这类文档的目标不是“解释项目为什么伟大”，而是让 agent 在改代码之前，先拿到一组不会轻易漂移的判断依据。

## 5. 第三步：复杂任务不要只存在于聊天记录里

这是我觉得最容易被忽略，但实际收益非常高的一步。

很多时候，复杂需求其实已经在聊天里分析得很清楚了，但一旦对话结束，这些背景信息就蒸发了。下一次 agent 再接手时，又得从头猜。

所以我在 `TermPilot` 里增加了 `PLANS.md` 和 `.agent/exec-plans/`，要求跨 runtime、跨模块、行为有歧义的任务，先落成执行计划再动手。

这类 plan 不需要写成 PRD，但至少要把目标、非目标、涉及模块、验收标准、风险和后续 debt 这些东西说清楚。

这个动作的价值在于，它把原本“在脑子里”的上下文，变成了仓库的一部分。

对于 agent 来说，看不到的知识就等于不存在。把 plan 版本化之后，仓库就开始具备“持续交接”的能力。

说白了，这一步解决的是“为什么这样改”而不是“改了什么”。前者如果不沉淀，后面所有维护都会越来越像考古。

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

这个检查器会扫描关键源码目录，只允许明确合法的依赖关系。比如 `app` 不能直接 import `agent` 或 `relay` 的源码，`agent`、`relay`、`app` 跨边界共享类型时必须经过 `@termpilot/protocol`，根 CLI 只允许做顶层组装，不允许把所有运行时耦合成一团，未分类的 repo import 默认也不放行，只保留显式白名单。

这类检查的意义，不在于“写一个很复杂的静态分析器”，而在于把项目最重要的架构约束机械化。只要这一步做了，agent 的行为就会自然收敛很多。对我来说，这一步最有实感的地方是：很多以前只会写在架构文档里的话，现在终于开始变成会报错的东西了。

这一点其实也是我对 harness engineering 最大的体感变化：以前我会把很多话写在文档里，希望后来的人“记得遵守”；现在更自然的思路是，能不能直接让仓库自己检查出来。

## 7. 第五步：让验证变成 repo-native，而不是“只在我电脑上能跑”

这是老项目非常常见的问题。

最初 `TermPilot` 的部分 UI 冒烟路径依赖本机 skill 路径，本质上属于“我这台机器能跑，但仓库本身没有完整表达这个能力”。这种东西对单人开发还凑合，对 agent 和 CI 都不够友好。

所以后面我做了两件事。第一，把 UI smoke 改成仓库原生的 Playwright 脚本；第二，把 E2EE 和烟测入口统一到 Node/TS 侧，旧的 Python 脚本只保留兼容包装层。

这里有个很具体的例子。最初的 UI smoke 依赖我本机的一套 skill 路径，这种东西自己用的时候问题不大，但一旦换到 agent 或 CI 环境里，基本就等于“没有”。后来我把它收敛成仓库里的 `scripts/check-ui-smoke.ts`，并把 `scripts/ui_smoke.py`、`scripts/test_e2ee.py`、`scripts/verify_e2ee.py` 变成兼容包装层，真正的入口统一走根脚本。这一步做完之后，整个验证链的感觉就完全不一样了，因为它终于属于仓库本身，而不是属于我某台机器。

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

这里我刻意把验证拆成几层：`verify:fast` 负责日常快速回路，`verify:full` 负责 CI 默认全量回路，`verify:browser` 负责浏览器烟测，`verify:e2ee` 负责跨端行为验证。原因也很简单：**不是所有改动都值得拉起最重的验证，但每种改动都应该有一条清晰的验证路径。**

后来我回过头看，这其实已经很接近 agent 时代常说的 eval 思路了。对于代码仓库来说，最实用的 eval 往往不是单独搭一套 fancy 平台，而是先把“什么改动跑什么检查”这件事整理清楚，让 agent 自己能跑，也让 CI 能复跑。

## 8. 第六步：让“文档更新”也进入自动检查

如果只检查代码正确性，不检查知识正确性，agent 最后还是会把仓库带回混乱状态。

所以我在 `TermPilot` 里加了两类和文档相关的检查：`check:repo-docs` 和 `check:public-docs`。前者主要检查内部文档体系是否完整，后者更重要，它会根据 `.agent/public-doc-map.json` 判断哪些实现目录发生了变化，以及这些变化是否触发了对应文档的同步更新。

也就是说，如果你改了某些关键实现，但没有触碰对应的公共文档，这个检查就会直接报错。

这件事看起来“有点麻烦”，但它实际上是 harness engineering 非常重要的一环：

**让知识漂移也变成可被发现的问题。**

我很喜欢这个改动的一点是，它不再默认“文档过期是正常的”。以前文档总像一个没人追责的角落；现在至少在关键路径上，它开始和实现一起被检查了。这个变化虽然不大，但很有那种工程气质上的差别。

## 9. 第七步：把这些规则放进 CI，而不是靠自觉

只要一个规则还停留在“团队约定”，它就迟早会被遗忘。

所以在 `TermPilot` 里，我新增了 PR 级别的 CI 工作流。主 job 会跑 `verify:fast`、build、文档构建和 runtime checks，另外单独拆了一个 `ui-smoke` job，在 CI 里安装 Chromium 后执行 repo-native 浏览器烟测。

这么做的好处也很直接：快回路和慢回路分离，默认 CI 不会被最重的浏览器任务拖死；浏览器路径也不再是“本机私有能力”，而是仓库自己的验证能力。

到这一步为止，agent 的工作方式就开始发生变化了。它不再是“随便改完试试看”，而是会顺着 `AGENTS.md -> 内部知识库 -> 计划 -> 验证脚本 -> CI` 这条链路工作；如果它偏离边界，仓库会自己把它拽回来。

这才是 harness 的价值。它不是让 agent “更聪明”，而是让系统对 agent 的工作方式更友好，也对错误更不宽容。

## 10. 我对这次改造的一个实际总结

如果复盘 `TermPilot` 这轮改造，我觉得最核心的变化不是“多了几份 markdown”或者“多了几条 npm script”，而是仓库的角色变了。

改造前，这个仓库更像一个存量资产库：代码在这里，文档在这里，脚本也在这里，但它们并没有形成一个对 agent 友好的闭环。改造后，这个仓库开始更像一个工作面：agent 知道从哪里进入，知道哪些信息是内部真相，知道复杂任务应该先留 plan，知道改完之后该跑什么，如果越界，仓库和 CI 会直接报错。

我自己最满意的地方也在这里。以前仓库更像是在“存东西”，现在它开始有点像在“管行为”了。

## 11. 如果你也要改一个老项目，我建议按这个顺序来

如果你手里也有一个已有工程，想往 harness engineering 的方向升级，我还是建议按一个比较克制的顺序推进：先建一个很短的 `AGENTS.md`，把内部 agent 文档和对外文档彻底分层，再把架构原则收敛成 golden rules 和 invariants；接着补 plan 机制，让复杂任务版本化，然后做最小可用的 `check:architecture`，再整理 repo-native 的 `verify:fast` / `verify:full`，最后再补 doc freshness 和 CI 级别回路。

不要一上来就追求“把所有规则都自动化”。对已有工程来说，更现实的路径是先把最关键的 20% 原则机械化，它们往往能解决 80% 的混乱。

如果非要我再补一句经验，那就是：先改最容易漂移、最容易被误解的地方。通常不是业务逻辑本身，而是边界、文档、验证和交接。

## 12. 结语

写这篇文章的时候，我越来越觉得，harness engineering 这个词之所以值得讨论，不是因为它新，而是因为它确实点中了一个变化中的工程现实：

当 agent 开始持续参与开发之后，真正决定效果上限的，往往不再是那一句 prompt 写得多漂亮，而是你的仓库有没有边界、有没有入口、有没有验证、有没有把经验沉淀成系统。

所以对我来说，这次 `TermPilot` 改造最大的收获不是“我把一套方法论落地了”，而是我开始更清楚地知道，下一步该继续补什么：更多 repo-native 的验证能力，更细的文档 freshness 规则，更强的 runtime 级可观测性和回放能力。

如果你的项目已经有一定体量，我会很建议尽早开始做这件事。因为项目越大、上下文越多、协作越复杂，harness 的价值只会越来越明显。

## 13. 最后介绍一下 TermPilot

`TermPilot` 是我在做的一个基于 `tmux` 的终端会话跨端查看与轻控制项目。它的目标不是远程桌面，也不是传统意义上的 Web SSH，而是把本地终端会话、移动端查看、配对授权和 relay 协作这几件事，以更轻量的方式串起来。

如果你对这篇文章里提到的 harness engineering 改造细节感兴趣，也欢迎直接看项目本身。文档站在 [https://fengye404.top/TermPilot/](https://fengye404.top/TermPilot/)，GitHub 在 [https://github.com/fengye404/TermPilot](https://github.com/fengye404/TermPilot)。

也欢迎大家顺手点个 Star，实际试一试；如果你在使用过程中有任何问题、想法或者改进建议，也非常欢迎提 Issue 一起讨论。
