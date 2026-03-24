---
title: TermPilot：把电脑上的终端会话继续带到手机上
typora-root-url: ./TermPilot：把电脑上的终端会话继续带到手机上
date: 2026-03-21 02:10:00
tags:
  - AI
  - Agent
  - 工程化
---

# TermPilot：把电脑上的终端会话继续带到手机上

> 本文由 AI 参与创作

## 前言

最近在家里写 `TermPilot`。场景很简单：自己的电脑上挂着一条终端会话，任务还在跑，人暂时不在电脑前，我想在手机上接着看，必要时补一条命令，或者直接停掉。

这个项目从一开始就偏个人使用。它更适合在家里自己开发、自己部署、自己用自己的设备接自己的机器。

## 1. 先看怎么用

如果只是自己在家里用，最短路径其实很简单：

```bash
npm install -g @fengye404/termpilot

# 一台手机能访问到的机器
termpilot relay

# 你自己的电脑
termpilot agent --relay wss://your-domain.com/ws
termpilot claude code
```

如果你不是跑 `Claude Code`，也可以直接托管别的命令：

```bash
termpilot run -- <command>
```

第一次启动 `agent` 的时候，会打印设备信息和一次性配对码。手机浏览器打开 relay 地址，把这个码输进去，就能绑到这台电脑上。

![agent 启动与配对码截图](./agent-pairing.png)

配完对之后，手机端看到的就是这台机器上那条会话本身：

![手机端会话截图](./mobile-session.png)

我自己最常用的就是这条链路。电脑上开 `Claude Code`，或者挂着别的长任务，手机端只负责继续看、补一点轻操作。

完整文档我也单独放了一套文档站：<https://fengye404.top/TermPilot/>。如果你想直接看部署、CLI 和排障，可以从那边进。

## 2. 我为什么会想做这个

这个需求基本就是在家自己写东西时冒出来的。

比如晚上在家写 side project，电脑上挂着 `Claude Code`、部署脚本、迁移或者批处理。人去厨房弄点吃的，或者临时离开一会儿，任务没停。这时候我在手机上真正想做的事情其实很少，就是看一眼输出，确认它是不是还在跑，有没有卡住，必要时补一条命令或者直接中断。

麻烦在于，上下文已经在原来的终端里了。目录切好了，前面的输出已经滚出来了，命令也跑到一半了。有些确认和交互语义，也都挂在这条会话上。

所以我想保留的不是“远程登录一台机器”的能力，而是“继续接回原来那条会话”的能力。

比如桌面端进入 `Claude Code` 后，安全确认还是发生在原来的终端上下文里：

![Claude Code 安全确认截图](./claude-trust-folder.png)

我比较在意的是这件事的一致性：

- 输出来自同一条本地会话
- 控制动作写回同一条本地会话
- 会话退出也跟着这条受管理会话自己的语义走

## 3. 和 Happy 的对比

GitHub 上的 [Happy](https://github.com/slopus/happy) 其实已经做得很完整了。它的仓库首页写得很清楚：这是给 Claude Code 和 Codex 用的 mobile and web client，有 iOS、Android、Web、端到端加密、push、语音和设备切换这些能力。官方 self-hosting 文档也给到了单独的 [Happy Server 部署说明](https://happy.engineering/docs/guides/self-hosting/)。

所以我做 `TermPilot`，不是因为 Happy 不强，恰恰是因为它已经很完整了。

对我自己来说，Happy 现在这套形态还是偏重了一点。它官方 self-hosting 页面虽然最近还更新过，页面上写的是最后更新于 `2026-03-23`，但按这份文档的当前路径，自部署还是要单独起 `happy-server`，配 `PostgreSQL` 和 `Redis`，Docker Compose 里也是这两个依赖一起上，后面甚至还给了 corporate network 和 Kubernetes 的部署方式。

这不是说它不好。它只是明显更像一个完整产品。

而 `TermPilot` 这边，我故意把东西压得很短：

- 手机端就是一个移动 Web 页面
- 电脑端就是 `agent`
- 公网入口就是 `relay`
- relay 默认用 SQLite，只存配对、grant 和审计元数据
- 真正的会话标题、cwd、状态和输出都留在 agent 所在电脑
- 额外需要准备的东西基本就是 `Node.js` 和 `tmux`

这套东西更像“我在家里自己写项目，自己给自己搭一个能用的入口”，而不是“我准备上一套更完整的移动协作系统”。这也是它相对 Happy 我更在意的地方：更轻，形状更窄，自己部署的时候心智负担更低。

## 4. 现在的实现

当前实现分成三个 runtime：

- `relay`：部署在一台手机能访问到的机器上，负责 HTTP 入口、配对、授权、审计元数据和 WebSocket 中转
- `agent`：运行在你自己的电脑上，负责本地会话、`tmux` 生命周期、输出回放和状态同步
- `app`：移动端 Web 页面，由 `relay` 直接托管

会话后端现在用的是 `tmux`。原因也很直接：我要的是一条可以附着、分离、继续查看的长期会话，而不是一次性的命令执行器。

服务器端先启动 `relay`：

![relay 启动截图](./relay-start.png)

这里有一条边界我收得比较硬：session 的 source of truth 在 `agent`，不在 `relay`。当前仓库里，`relay` 默认只持久化 pairing、grant、audit 这类最小元数据，长期运行默认也是 SQLite；会话标题、cwd、状态细节和终端输出都留在电脑侧。

这样做的好处也很直接：

- relay 负责入口和转发，不背终端主数据
- agent 才是本地会话的真实持有者
- 手机端看到的就是这条会话的状态和输出

另外仓库里也补了后台提醒相关能力，比如设备离线、会话退出和疑似残留会话的提醒。

还有一条边界我在这里顺手提一下：`TermPilot` 不会自动导入任意 Terminal 或 iTerm 标签页。只有由 `TermPilot` 创建或管理的会话，手机端才能继续访问。

## 5. 结语

如果你的使用场景和我差不多，就是在家里自己写项目，电脑上挂着一条长期任务，离开电脑时只想在手机上继续看着它，那 `TermPilot` 这种收得比较窄的形态可能就够了。

它的核心其实就一句话：把电脑上已经跑起来的那条终端会话，继续带到手机上。

项目地址：

- 文档站：https://fengye404.top/TermPilot/
- GitHub：https://github.com/fengye404/TermPilot
