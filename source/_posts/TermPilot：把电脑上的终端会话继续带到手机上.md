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

最近在家写 side project，终端里经常是 `Claude Code` 或跑时间比较长的脚本、迁移。人暂时离开电脑时，我想用手机看**同一条**会话的输出，偶尔再敲几条命令；并不需要再开一条远程 shell 另起炉灶。

手机 SSH 上去再登录，得到的是新的 shell：原来的工作目录、环境变量、已经滚出来的日志、交互程序停在等什么提示，都还在旧的那条 PTY 上。`Claude Code` 一类工具的信任目录、确认框，也往往发生在当前这个终端里。

`TermPilot` 就是为这个场景写的：`relay` 提供公网入口和手机端页面，`agent` 跑在自己的电脑上，用 `tmux` 托管终端；手机浏览器连上来，看到的是这条本地会话的输出，输入也写回这条会话。

本文主要说明这几块：

1. 由哪些部分组成、各组件职责。
2. 安装与启动顺序，以及 `relay`、TLS、`tmux` 方面的依赖。
3. 配对、授权等元数据和终端内容分别存在哪里。
4. 使用上有哪些限制。
5. 和同方向的 [Happy](https://github.com/slopus/happy) 相比，收敛在哪些点上。

个人使用向：自己部署、自己的手机接自己的机器，不涉及多租户控制台一类需求。

## 组成部分

整体上可以分成三块：

- **relay**：HTTP 入口、设备配对与授权、审计相关元数据、托管移动 Web 静态资源、WebSocket 转发。
- **agent**：跑在实际干活的那台电脑上；负责本地 `tmux` 会话、输出回放、状态同步、与 `relay` 的长连接。
- **app**：移动端页面，由 `relay` 直接提供。

数据流上，终端主内容在 `agent` 侧；`relay` 负责把浏览器和 `agent` 连起来，并持久化配对、grant 等必要元数据。

本机会话需要长期附着、分离、过一会再打开还是同一条，而不是跑一条命令就结束的那种模型；`agent` 这边用 `tmux` 托管，语义直接对齐这个需求。

## 和「再开一个 shell」的差别

再开一个 shell 时，拿不到当前这条会话里已经建立好的上下文。目录、`env`、历史输出、卡在半路的交互，都绑在原来的 PTY 上。

`TermPilot` 要保证的是：手机侧看到的输出来自这条会话，键盘输入也回到这条会话；会话如何结束，跟 `tmux` 里这条会话的语义一致（例如关掉对应窗格即结束）。

桌面进入 `Claude Code` 后，安全确认仍发生在原来的终端里：

![Claude Code 安全确认截图](./claude-trust-folder.png)

## 安装与使用

### 最简启动顺序

```bash
npm install -g @fengye404/termpilot

# 部署在一台手机能访问到的机器上
termpilot relay

# 在实际使用终端的那台电脑上
termpilot agent --relay wss://your-domain.com/ws
termpilot claude code
```

不使用 `Claude Code` 时，也可以直接托管其它命令：

```bash
termpilot run -- <command>
```

首次启动 `agent` 会打印设备信息与一次性配对码。手机浏览器访问 `relay` 的 Web 地址，输入配对码完成绑定。

![agent 启动与配对码截图](./agent-pairing.png)

绑定后，手机端展示的是由 `TermPilot` 管理的那条会话：

![手机端会话截图](./mobile-session.png)

### relay、TLS 与 tmux

`relay` 必须落在手机能访问的网络路径上，常见做法是公网 VPS，或通过内网穿透得到等价可达地址。线上场景下 `agent` 与 `relay` 之间使用 `wss://`，需要可用的 TLS 证书与域名；具体参数与部署步骤见文档站。

`agent` 依赖本机安装 `tmux`，附着、分离、回放等行为都遵循 `tmux`。除 Node.js 外需保证 `tmux` 可用。

`relay` 启动示例：

![relay 启动截图](./relay-start.png)

更完整的 CLI、环境变量与排障说明：<https://fengye404.top/TermPilot/>。

## 元数据与终端内容的存放

**relay 侧持久化（默认 SQLite 即可）：**

- 配对关系、授权（grant）、审计类元数据。

**agent 侧保留：**

- 会话标题、当前工作目录、终端滚动缓冲、运行状态等。

这样做的直接结果：

1. 公网入口机器不保存终端输出的主副本。
2. 会话以 `agent` 所在机器为准；`relay` 重启或网络中断，本地 `tmux` 会话仍可保留。
3. 手机端是同步视图，而不是在云端再跑一套独立 shell。

仓库内另有设备离线、会话退出、疑似残留会话等提醒，用于减少状态误判。

## 使用上的限制

`TermPilot` **不会**自动接管系统里已有的 Terminal、iTerm 等标签页。只有由本工具创建或显式纳入管理的会话，手机端才能访问，用于收窄状态来源、避免全盘扫 PTY。

## 与 Happy 的对比

[Happy](https://github.com/slopus/happy) 面向 `Claude Code` / Codex，提供 iOS、Android、Web、端到端加密、推送、语音、多设备等能力；[self-hosting 文档](https://happy.engineering/docs/guides/self-hosting/) 中自托管需要 `happy-server`、`PostgreSQL`、`Redis` 等，形态接近完整产品。

`TermPilot` 刻意收窄：

- 手机侧为移动 Web；电脑侧为单个 `agent` 进程；公网侧为单个 `relay`。
- 元数据层默认 SQLite；会话实体在本地。
- 部署与依赖相对轻，功能覆盖面小于 Happy，适合个人、单一路径的使用半径。

两者解决的问题有重叠，但定位不同，按需求选用即可。

## 参考链接

- 文档站：<https://fengye404.top/TermPilot/>
- 源码：<https://github.com/fengye404/TermPilot>
