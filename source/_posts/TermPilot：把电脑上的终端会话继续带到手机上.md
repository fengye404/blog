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

最近在家 vibe coding，家里那台电脑上经常开着 `Claude Code`、跑很长时间的脚本。人不能一直钉在显示器前：出门吃饭、躺一会儿、临时走开，我还想盯着**这条终端**的输出，确认没卡死、继续下发下一条指令，偶尔敲一条命令或干净地停掉。

目前市面上有一些类似的小玩意，但深入研究使用后，发现他们都不符合我的 taste。例如 Happy，在 GitHub 上有 1w+ star，但是体验太差，自部署太重，还需要额外下载一个 app。

我的需求很简单：

- 使用简单：最好能一行命令直接启动，同时在手机上监控终端时，我也不希望去下载一个额外的 app
- 支持自部署：要能够部署在我个人的云服务器上，而且部署简单，最好一行命令就能搞定，不要引入太多依赖
- 数据安全：数据需要存在端侧，且要有端到端加密

基于这个需求，我业余时间 vibe coding 了一个能帮我实现这种需求的小工具，并且给它取了个名字 `TermPilot`。

下面按三块写：先交代整体架构，再写怎么用起来，最后写实现上怎么把上面的需求落下来。更细的 CLI 和部署仍以文档站为准。

## 1. 整体架构

整体上分成三个 runtime：

- **relay**：HTTP 入口、设备配对与授权、审计相关元数据、托管移动 Web 静态资源、WebSocket 转发。
- **agent**：跑在家里实际干活的那台电脑上；负责本地 `tmux` 会话、输出回放、状态同步、与 `relay` 的长连接。
- **app**：移动端页面，由 `relay` 直接提供，手机用浏览器打开即可。

数据流上，终端主内容在 `agent` 侧；`relay` 负责把浏览器和 `agent` 连起来，并持久化配对、grant 等必要元数据。

和需求三条的对应关系可以直接说清楚：

**使用简单**：全局装一个包之后，`relay`、`agent` 各一条命令起进程；手机侧不需要装 app，只要浏览器能打开 `relay` 的页面。

**自部署**：`relay` 可以部署在你自己的 VPS 上；默认持久化用 SQLite，不必为这个小工具再搭 Postgres、Redis。依赖面控制在 Node.js +（`agent` 侧）`tmux` 这一档。

**数据安全**：会话标题、滚动缓冲、当前目录、运行状态等「重数据」留在 `agent` 所在机器；`relay` 只扛入口和最小元数据。链路上生产环境走 `wss://`（TLS）；若关心传输与密钥细节，以仓库和 [文档站](https://fengye404.top/TermPilot/) 的说明为准。

本机会话要支持长期附着、分离、过一会再打开还是同一条，而不是跑一条命令就结束；`agent` 用 `tmux` 托管，语义对齐「人走开一会再回来看还是同一条」。这一点在第三节里还会接到「手机看到的到底是不是桌上那条」。

## 2. 快速上手

### 2.1 安装与启动

```bash
npm install -g @fengye404/termpilot

# 部署在一台手机能访问到的机器上（常见是个人 VPS）
termpilot relay

# 在家里使用终端的那台电脑上
termpilot agent --relay wss://your-domain.com/ws
termpilot claude code
```

不使用 `Claude Code` 时，也可以直接托管其它命令：

```bash
termpilot run -- <command>
```

首次启动 `agent` 会打印设备信息与一次性配对码。手机浏览器访问 `relay` 的 Web 地址，输入配对码完成绑定。

![agent 启动与配对码截图](./agent-pairing.png)

绑定后，手机端展示的是家里机器上由 `TermPilot` 管理的那条会话：

![手机端会话截图](./mobile-session.png)

### 2.2 relay、TLS 与 tmux

`relay` 必须落在手机当前网络能访问的路径上，常见做法是公网 VPS，或通过内网穿透得到等价地址。线上场景下 `agent` 与 `relay` 之间使用 `wss://`，需要可用的 TLS 证书与域名；具体参数与部署步骤见文档站。

`agent` 依赖本机安装 `tmux`，附着、分离、回放等行为都遵循 `tmux`。除 Node.js 外需保证 `tmux` 可用。

`relay` 启动示例：

![relay 启动截图](./relay-start.png)

更完整的 CLI、环境变量与排障说明：<https://fengye404.top/TermPilot/>。

## 3. 背后的实现

这一节只回答一件事：`TermPilot` 是怎么把前言里那几条需求落到代码和部署结构上的。

### 3.1 手机看到的是不是桌上那条会话

需求是离开座位仍能盯着**同一条**终端、必要时继续输入。实现上要保证：手机侧看到的输出来自这条会话，键盘输入也写回这条会话；会话如何结束，跟 `tmux` 里这条的语义一致（例如关掉对应窗格即结束）。

桌面进入 `Claude Code` 后，信任目录、确认框仍在这条终端里完成，手机端只是同步视图，不会在云端另起一条 shell 冒充同一场景：

![Claude Code 安全确认截图](./claude-trust-folder.png)

### 3.2 relay 和 agent 各持久化什么

**relay 侧（默认 SQLite 即可）：**

- 配对关系、授权（grant）、审计类元数据。

**agent 侧：**

- 会话标题、当前工作目录、终端滚动缓冲、运行状态等。

直接后果：

1. 公网入口机器不保存终端输出的主副本，和需求里的「数据在端侧」对齐。
2. 会话以家里 `agent` 为准；`relay` 重启或网络短时中断，本地 `tmux` 会话仍可保留，手机稍后重连仍是同一条。
3. 手机端是这条会话的同步视图，不在入口机上再跑一套交互式 shell。

仓库里还有设备离线、会话退出、疑似残留会话等提醒，用来减少「以为还在跑其实早断了」的误判。

### 3.3 为什么用 tmux

要的是能挂住、能离开、能再打开还是同一条，而不是单次 `exec` 跑完就结束。`agent` 把这类会话语义交给 `tmux`，自己专注和 `relay` 同步状态与 IO。

### 3.4 刻意不做的事

`TermPilot` **不会**自动接管系统里已有的 Terminal、iTerm 等标签页。只有由本工具创建或显式纳入管理的会话，手机端才能访问。这样状态来源清晰，也避免全盘扫 PTY 带来的边界问题。

### 3.5 和 Happy 等方案相比我收在哪里

[Happy](https://github.com/slopus/happy) 面向 `Claude Code` / Codex，提供 iOS、Android、Web、端到端加密、推送、语音、多设备等能力；[self-hosting 文档](https://happy.engineering/docs/guides/self-hosting/) 里自托管需要 `happy-server`、`PostgreSQL`、`Redis` 等，形态接近完整产品。

我这边把形状收成：`relay` + `agent` + 移动 Web，元数据默认 SQLite，会话实体在本地，部署和维护都少背一层。功能覆盖面比 Happy 小，但和前言里那三条需求更贴。两者解决的问题有重叠，按自己的半径选就行。

## 参考链接

- 文档站：<https://fengye404.top/TermPilot/>
- 源码：<https://github.com/fengye404/TermPilot>
