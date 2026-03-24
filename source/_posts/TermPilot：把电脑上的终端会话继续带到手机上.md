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

`TermPilot` 是一组很小的端侧工具：`relay` 提供公网入口和手机端 Web，`agent` 跑在你自己的电脑上，用 `tmux` 托管终端会话。手机浏览器连上来，看到的是同一条本地会话的输出，键盘输入也回到这条会话。

最近主要在家里写。典型情况是电脑已经开着 `Claude Code`、部署脚本、迁移或批处理，人走开一会儿，任务还在跑。手机上我通常只看几眼输出，确认没卡死，偶尔敲一条命令，或者把它停干净。

从一开始就是按个人使用收敛的：自己开发、自己部署、手机接自己的机器。不碰团队协作、多租户控制台之类，只处理一件事：会话已经在跑了，换一块屏幕接着用。

## SSH 再开一条会话也接不上现场

手机上的 SSH 客户端很多，登录上去再开一个 shell 不难。缺的是你已经跑了一半的那条上下文。

目录、`env`、前面滚过的日志、交互式工具停在等确认——都挂在原来的 PTY 上。`Claude Code` 这类流程里，信任目录、确认框往往就发生在当前这个终端里。换一条会话，等于换了一个现场。

我想保留的是：输出和控制都落在同一条本地受管会话上。手机不是替代桌面终端，只是多一块屏、偶尔输入几句。

桌面进 `Claude Code` 后，安全确认仍在原来的终端上下文里：

![Claude Code 安全确认截图](./claude-trust-folder.png)

我自己在意的就三点：输出来自这条会话，控制写回这条会话，会话怎么结束也跟这条走（比如 `tmux` 里窗格关掉就真关掉）。这样才算「继续」。

## 在家自用怎么起

自己在家里用，命令可以写得很短：

```bash
npm install -g @fengye404/termpilot

# 一台手机能访问到的机器
termpilot relay

# 你自己的电脑
termpilot agent --relay wss://your-domain.com/ws
termpilot claude code
```

不跑 `Claude Code` 也可以直接托管别的命令：

```bash
termpilot run -- <command>
```

第一次起 `agent` 会打出设备信息和一次性配对码。手机浏览器打开 `relay` 的 Web 地址，把码填进去，和这台电脑绑在一起。

![agent 启动与配对码截图](./agent-pairing.png)

绑好之后，手机看到的是这台机器上由 `TermPilot` 管着的那条会话：

![手机端会话截图](./mobile-session.png)

我日常就是桌面扛长会话，手机扫输出、偶尔插一句。

### relay 放哪、TLS、本机 tmux

`relay` 得落在手机能访问到的网络上，一般是公网机器，或者内网穿透之后等价的入口。线上用法里 `agent` 连 `relay` 走 `wss://`，要有可用的 TLS 证书和域名，具体步骤在文档站。

`agent` 这边除了 Node.js，还要本机有 `tmux`。附着、分离、回放都按 `tmux` 的行为来，没有或版本太旧就先装好。

CLI、环境变量、排障见文档站：<https://fengye404.top/TermPilot/>。

## 配对在 relay，会话内容在电脑

配对码解决的是：哪台手机可以接哪台 `agent`。绑定关系、授权、审计这类元数据由 `relay` 持久化；默认长期跑 SQLite 就够，不必为这个小工具再起一套 Postgres。

会话标题、当前目录、终端滚动缓冲、运行状态这些留在 `agent` 那台机器。`relay` 只做 HTTP 入口、WebSocket 转发和最小元数据，不把终端输出当主存储。

这样拆主要是：公网入口少背一点数据；会话以 `agent` 为准，`relay` 断了或重启，本地会话还在；手机拿到的是同步视图，不是在云端复制一套 shell。

仓库里还有设备离线、会话退出、疑似残留会话等提醒，减少「以为还在跑其实早没了」这种错觉。

## 和 Happy

GitHub 上的 [Happy](https://github.com/slopus/happy) 已经做得很完整：面向 `Claude Code` / Codex 的移动和 Web 客户端，iOS、Android、Web、端到端加密、推送、语音、多设备切换都有。官方 [self-hosting](https://happy.engineering/docs/guides/self-hosting/) 也写得很细。

自托管要起 `happy-server`，配 `PostgreSQL`、`Redis`，Docker Compose 里常见是一起上，文档里还有企业网、Kubernetes 的延伸，整体是按完整产品在走。

Happy 的能力我认，我这边只想拆得更轻：手机 Web、电脑上一个 `agent`、公网一个 `relay`，`relay` 侧 SQLite 存配对和审计，会话本体仍在本地，部署和维护都少背一点东西。Happy 覆盖的面更广，我日常够用的那一块用不上那么多，所以单独收了这么一个小工具。

## relay、agent 和移动端页面

当前是三个部分：

- `relay`：HTTP、配对与授权、审计元数据、托管移动 Web、WebSocket 转发
- `agent`：本机 `tmux`、输出回放、状态同步、连 `relay` 的长连接
- `app`：移动页面，静态资源由 `relay` 提供

后端用 `tmux` 的原因前面已经说了：要的是能挂住、能离开、能再回来的长会话，不是跑完就结束的单次命令。

`relay` 启动大致是这样：

![relay 启动截图](./relay-start.png)

设计上我刻意限死：`TermPilot` 不会去接管系统里已有的 Terminal / iTerm 标签。只有它创建或显式纳入管理的会话，手机才能接，避免状态来源摊得太大。

## 小结

如果你也是在家写东西、桌上长期挂着一条会话，离开座位时只想用手机接着看，又能自己维护 `relay` 和 TLS，不需要多租户控制台，`TermPilot` 这种收得很窄的形态也许够用。

一句话：`TermPilot` 干的是把电脑上已经跑起来的那条终端会话，继续带到手机上。

- 文档站：<https://fengye404.top/TermPilot/>
- GitHub：<https://github.com/fengye404/TermPilot>
