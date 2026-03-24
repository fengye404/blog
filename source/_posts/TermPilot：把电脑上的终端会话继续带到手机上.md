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

## 1. 整体架构

TermPilot 分三个运行时：`relay`、`agent`、`app`。

**relay** 跑在一台手机能访问到的机器上，通常是个人 VPS。它做这几件事：HTTP 入口、设备配对和授权管理、WebSocket 中转、托管移动端 Web 页面。relay 本身不存终端输出，只保留配对关系、授权令牌、审计日志这些元数据，默认用 SQLite，不需要额外搭 Postgres 或 Redis。

**agent** 跑在家里实际干活的那台电脑上。它管理本地的 `tmux` 会话，负责终端输出的采集和回放，维护会话状态（标题、工作目录、运行状态），并通过 WebSocket 长连接和 relay 保持同步。会话的主数据存在这台机器上的 `~/.termpilot/state.json`，不上云。

**app** 是移动端页面，React + xterm.js 做终端渲染，构建产物直接由 relay 托管。手机浏览器打开 relay 地址就能用，不需要下载独立客户端。做了触摸优化和 viewport 适配，支持添加到主屏幕，手感接近原生应用。

数据流很直观：手机浏览器 ↔ relay ↔ agent。终端内容始终在 agent 侧产生和存储，relay 只负责把两端连起来，中间走的是端到端加密的密文。

拿前言里那三条需求来对应：

- **使用简单**：`npm install -g @fengye404/termpilot`，relay 和 agent 各一条命令拉起来。手机端不用装 app，浏览器打开就行。
- **自部署简单**：relay 丢在 VPS 上，默认 SQLite，一个 Node 进程就够。agent 侧需要 Node 和 `tmux`，没有其他依赖。
- **数据安全**：终端输出的主副本在 agent 本机，relay 不存也不解密；浏览器和 agent 之间用 ECDH P-256 + AES-GCM 做端到端加密。

## 2. 快速上手

### 2.1 安装与启动

```bash
npm install -g @fengye404/termpilot
```

然后在两台机器上各起一个进程。

**relay（部署在 VPS 上）：**

```bash
termpilot relay
```

relay 默认监听 8787 端口。线上部署需要配 TLS，具体参数见文档站。

![relay 启动截图](./relay-start.png)

**agent（家里的电脑上）：**

```bash
termpilot agent --relay wss://your-domain.com/ws
```

首次启动会生成设备 ID 和一次性配对码。手机浏览器打开 relay 的 Web 地址，输入配对码就完成绑定。

![agent 启动与配对码截图](./agent-pairing.png)

绑定之后，在这台电脑上启动一个被 TermPilot 托管的会话：

```bash
# 跑 Claude Code
termpilot claude code

# 或者跑任意命令
termpilot run -- <command>
```

手机端就能看到这条会话的实时输出，也能继续输入。

![手机端会话截图](./mobile-session.png)

### 2.2 几个前置条件

- **relay 的网络可达性**：relay 必须部署在手机当前网络能访问到的地方，常见做法是公网 VPS，或者通过内网穿透拿到等价地址。agent 和 relay 之间走 `wss://`，需要有效的 TLS 证书和域名。
- **tmux**：agent 依赖本机的 `tmux` 来托管会话，除 Node.js 外需要确保 `tmux` 已安装。
- **Docker**：relay 也提供了 Docker 镜像，可以用 `docker run` 直接拉起来，数据卷挂载路径见仓库 README。

更完整的 CLI 参数、环境变量和排障说明：<https://fengye404.top/TermPilot/>。

## 3. 背后的实现

这一节展开讲 TermPilot 怎么把前言里那几条需求落到具体实现上。

### 3.1 会话连续性：手机看到的是不是桌上那条

需求是离开座位后仍能盯着**同一条**终端，必要时继续输入。这件事要保证三点：

1. 手机侧看到的输出来自这条 `tmux` 会话，不是另起的 shell。
2. 手机侧的键盘输入写回的也是这条会话。
3. 会话的生命周期和 `tmux` 里这条会话一致——窗格关了就是结束，不会有"云端残留"。

agent 创建会话时实际执行的是 `tmux new-session -d`，后续所有操作——输入、输出采集、resize、kill——都通过 `tmux` 命令完成。手机端只是这条会话的同步视图，不会在 relay 或浏览器侧另起一条交互式 shell。

拿 `Claude Code` 场景来说，桌面进入 `Claude Code` 后，信任目录、安全确认框这些交互仍然在这条终端里完成。手机端看到的就是这个过程：

![Claude Code 安全确认截图](./claude-trust-folder.png)

为什么选 `tmux` 而不是直接 exec？因为我要的是会话能**挂住**——人走了它还在跑，回来还能接上。这正好是 `tmux` session 的语义：附着、分离、再附着。agent 把会话管理交给 `tmux`，自己只负责和 relay 之间同步状态和 IO。

### 3.2 数据安全：存在哪、怎么加密

需求里说"数据存端侧、端到端加密"，实现上拆成两层。

**第一层：持久化的分割**

relay 侧（默认 SQLite，不用 ORM，直接 Node 22 内置 `node:sqlite` + 手写 SQL）只存三类东西：

- 配对关系（`relay_pairing_codes`）
- 授权令牌（`relay_client_grants`）
- 审计日志（`relay_audit_events`）

这些是维持配对和授权必须的元数据。

agent 侧存的是会话实体：标题、当前工作目录、运行状态、终端滚动缓冲。它们落在本机的 `~/.termpilot/state.json` 和 `tmux` 进程里，有文件锁防并发写坏。

直接后果：公网入口机器上不存终端输出的主副本。relay 重启或网络短暂中断，本地 `tmux` 会话不受影响，手机重连后还是同一条。

**第二层：传输加密**

浏览器和 agent 之间的业务消息——会话列表、终端输出、键盘输入——全部走端到端加密。协议层用 ECDH P-256 协商共享密钥，消息用 AES-GCM 加密。加密时还会把 `deviceId`、`accessToken`、`reqId` 序列化后作为 AAD（Additional Authenticated Data）传入，防止跨设备或跨请求的密文被挪用。

relay 在中间只做消息转发，看到的是密文，解不开内容。

加密实现放在 `@termpilot/protocol` 这个共享包里，浏览器端优先走 Web Crypto API，Node 侧在需要时用 `@noble/curves` + `@noble/ciphers` 的纯 JS 路径兜底。

### 3.3 输出同步：增量还是全量

agent 按动态间隔通过 `tmux capture-pane` 抓取当前屏幕内容（含最近 2000 行历史），和上一帧 buffer 做对比。如果新 buffer 是旧 buffer 的扩展（前缀一致，只多了尾部内容），就发一帧 `append`，只传增量部分；否则发 `replace`，传完整内容。这样在大缓冲场景下能显著减少重复传输。

每帧带一个递增的 `seq`。手机端如果发现 seq 不连续——比如网络断了一会儿——就向 agent 发 `session.replay`，带上自己最后收到的 `afterSeq`。agent 侧维护了一个内存环形缓冲（每个会话最多 40 帧），能补回缺失的帧；如果断层太久或者缺了首帧 replace，就重新 `capture-pane` 打一帧 replace 发过去。

这个机制让手机端在网络抖动之后能自动补齐中间的输出，而不是只看到最新一屏。

### 3.4 设备配对

配对流程用一次性配对码完成：

1. agent 启动后向 relay 申请配对码（HTTP POST，需 agent token 认证），同时 relay 会校验该 agent 确实在线。
2. 配对码格式是去掉易混淆字符后的字母数字组合，类似 `XXX-XXXX`，有效期默认 10 分钟。
3. 手机浏览器打开 relay 地址，输入配对码。浏览器端同时生成一对 ECDH 密钥，把公钥随配对码一起提交。
4. relay 验证配对码有效且未被使用后，签发一个 `accessToken`，返回 agent 的公钥。配对码标记为已兑换，SQLite 端用 `begin immediate` 事务防并发双花。
5. 配对完成后，浏览器和 agent 各自持有对方的公钥，后续所有业务消息走端到端加密。

整个过程不需要手动交换密钥或扫二维码，输入一个短码就够了。多个浏览器可以分别配对同一台 agent，daemon 会对每个 `accessToken` 各自加密推送，天然支持多终端同时查看。

## 总结

TermPilot 提供了一套让你能在任何地方通过 `relay` 访问已有终端会话的能力，如果你也有类似的需求或者使用场景，欢迎体验试用。如果体验中遇到任何 BUG、新需求，也欢迎来我的 github 仓库页提 Issue。

## 参考链接

- 文档站：<https://fengye404.top/TermPilot/>
- 源码：<https://github.com/fengye404/TermPilot>
