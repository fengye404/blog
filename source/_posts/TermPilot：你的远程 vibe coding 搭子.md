---
title: TermPilot：你的远程 vibe coding 搭子
typora-root-url: ./TermPilot：你的远程 vibe coding 搭子
date: 2026-03-21 02:10:00
tags:
  - AI
  - Agent
  - 工程化
---

# TermPilot：你的远程 vibe coding 搭子

## 前言

最近在家 vibe coding，家里那台电脑上经常开着 `Claude Code`、跑很长时间的脚本。人不能一直钉在显示器前：出门吃饭、躺一会儿、临时走开，我还想盯着**这条终端**的输出，确认没卡死、继续下发下一条指令，偶尔敲一条命令或干净地停掉。

目前市面上有一些类似的小玩意，但深入研究使用后，发现他们都不符合我的 taste。例如 Happy，在 GitHub 上有 1w+ star，但是体验太差，自部署太重，还需要额外下载一个 app。

我的需求很简单：

- 使用简单：最好能一行命令直接启动，同时在手机上监控终端时，我也不希望去下载一个额外的 app
- 支持自部署：要能够部署在我个人的云服务器上，而且部署简单，最好一行命令就能搞定，不要引入太多依赖
- 数据安全：数据需要存在端侧，且要有端到端加密

基于这个需求，我业余时间 vibe coding 了一个能帮我实现这种需求的小工具，并且给它取了个名字 `TermPilot`。

---

## 架构设计

TermPilot 分三层跑。

**relay** 部署在公网 VPS 上，充当中转站。它做的就是这些事：HTTP 入口、WebSocket 转发、设备配对和权限管理、托管移动端的 Web 页面。值得说的是——relay 本身不存终端输出。它只抱着配对关系、访问令牌、审计日志这些元数据，然后用 SQLite 存着。

**agent** 跑在你家里那台实际干活的电脑上。这边才是真正干活的地方：管理本地的 `tmux` 会话、采集终端输出、维护会话状态。会话的所有真实数据（标题、工作目录、运行状态、输出缓冲）全部驻扎在本机的 `~/.termpilot/state.json` 和 `tmux` 进程里，永远不上云。

**app** 就是手机浏览器看到的那个 UI——React + xterm.js 。relay 直接托管这个应用，所以手机打开浏览器访问 relay 地址就能用，根本不需要装什么 app。我还做了触摸优化和 viewport 适配，添加到主屏幕的时候手感接近原生应用。

说起来，这个三层的分割是慢慢折腾出来的。一开始我想过直接让 agent 暴露一个 HTTPS 服务给手机，干掉 relay 这个中间层。但问题是 agent 跑在内网，手机要访问得通过内网穿透，而且得自己管理 agent 的证书和域名。太麻烦。你反而整一个 relay 在公网上，agent 通过 WebSocket 主动连上去，反而简单得多——relay 只需要一个正常的 HTTPS 域名就行，agent 的内网 IP 对外面的手机完全透明。

数据流是这样的：手机浏览器跟 relay 建立 WebSocket，relay 跟 agent 也建立 WebSocket，relay 在中间转发消息。中间的消息都是密文——浏览器和 agent 之间有端到端加密，relay 看到的是黑盒。

对应一下前言里那三条需求：

使用简单就是 `npm install -g @fengye404/termpilot`，然后 relay 一条命令起，agent 也一条命令起，完事。手机端根本不用装任何东西。

自部署简单是 relay 丢在 VPS 上，默认用 SQLite，一个 Node 进程撑起来。agent 侧需要 Node 和 `tmux`，就这么多。没有数据库连接池、没有 Redis、没有消息队列。

数据安全嘛，终端输出的主副本在 agent 本机，relay 既不拷一份也解不开；手机和 agent 之间走 ECDH P-256 协商密钥，然后 AES-GCM 加密所有消息。relay 就是个被蒙上眼睛的快递员。

## 快速上手

### 安装和启动

```bash
npm install -g @fengye404/termpilot
```

然后两台机器各起一个。

**relay 这边（VPS 上）：**

```bash
termpilot relay
```

默认占 8787 端口。生产环境需要配 TLS，参数见文档。启动的时候会打一个验证用的 token，这是 agent 连上来时候用的。

**agent 这边（家里的电脑）：**

```bash
termpilot agent --relay wss://your-domain.com/ws --token <relay-token>
```

首次启动会生成设备 ID，然后打印一个一次性的配对码。手机浏览器打开 relay 的 Web 地址，输入这个码就完成配对。

配对完成之后，在这条电脑上启动一个由 TermPilot 托管的会话：

```bash
# 比如跑 Claude Code
termpilot claude code

# 或者跑任意命令
termpilot run -- some-long-running-task
```

手机端就能看到实时输出，也能输入。

### 前置条件

relay 得部署在手机当前能访问的地方，通常是公网 VPS。agent 和 relay 之间走 `wss://`，所以需要正常的 HTTPS 证书和域名。

本地还需要 `tmux` 和 Node.js 22+。就这两样依赖。

如果不想自己配域名和证书，relay 也提供了 Docker 镜像，数据卷挂载路径在仓库的 README 里。

参数、环境变量和排障说明全在 <https://fengye404.top/TermPilot/>。

## 实现细节

### 会话连续性怎么保证

离开座位后还能看到**同一条**终端，这是核心需求。底层要对应三件事：

第一，手机看到的输出确实来自本地的 `tmux` 会话，不是另起的什么东西。

第二，手机敲的字符实际上写进了这条会话的 stdin，不是写到 relay 或浏览器缓存里。

第三，会话的生命周期跟 `tmux` 里的一样——人在本地关了这个窗格，手机端也就看不了了，不会有什么"云端残留"。

最终方案就是 agent 把会话管理完全委托给 `tmux`。创建会话用 `tmux new-session -d`，后续所有操作——写入、读取、resize、关闭——全走 `tmux` 命令。手机端看到的只是这条会话的同步视图。

拿 Claude Code 举例。你在本地电脑上 `termpilot claude code` 进入 Claude Code 的交互，然后 Claude Code 问你"信任这个目录吗"、"允许这个操作吗"，这些交互框全部出现在本地的 `tmux` 会话里。手机端看到的就是整个过程，可以继续输入。没有什么"云端版的 Claude Code" 在另一端跑。

为什么非得选 `tmux`？因为我想要会话能**挂着不动**。人走了，`tmux` 会话还在那跑。回来了，可以 attach 回去。这正好就是 `tmux` 的语义——attach、detach、reattach。agent 的工作就简化了：管理会话状态和 IO 流转，硬的逻辑都交给 `tmux`。

### 数据存放和加密

需求说"数据存端侧、端到端加密"。拆成两个层面。

**存储分割这块：**

relay 那边用 SQLite（Node 22 原生内置 `node:sqlite`，不用 ORM，直接写 SQL），只存三类数据。

一是配对关系，记录哪个设备跟哪个 agent 配过对。二是授权令牌，手机获得的 token 存这。三是审计日志，记录发生了什么操作。

这些是维持配对和权限管理必须的元数据。

agent 这边存的是真正的会话状态——会话的标题、当前工作目录、运行状态、输出缓冲这些。落在本机的 `~/.termpilot/state.json` 和 `tmux` 进程里。用文件锁防止并发写坏。

直接的效果是什么？公网上那台 relay 根本不存终端输出。relay 宕机了重启，本地 `tmux` 会话毫不受影响，继续跑。网络断了一会儿，手机重连后还是看同一条会话。

**传输加密这块：**

浏览器和 agent 之间的所有业务消息——会话列表、输出、键盘输入——全部端到端加密。

协议层用 ECDH P-256 协商共享密钥，然后用 AES-GCM 加密。加密的时候还会把设备 ID、访问令牌、请求 ID 这些当成 AAD（Additional Authenticated Data）塞进去，防止密文被挪到其他设备或其他请求上用。

relay 在中间只负责转发消息，看到的全是密文，解不开。

加密逻辑放在 `@termpilot/protocol` 这个共享包里。浏览器端优先用 Web Crypto API，Node 这边有 `@noble/curves` + `@noble/ciphers` 的纯 JS 实现兜底。

### 输出同步的取舍

agent 每隔一段时间用 `tmux capture-pane` 抓取当前屏幕（包括最近 2000 行历史），拿新输出和上一帧的缓冲对比。

如果新的是旧的直接扩展（前缀完全一样，只是尾部多了内容），就作为 `append` 消息只发增量部分。否则作为 `replace` 发完整内容。这样大缓冲的场景下能显著减少重复数据。

每帧都有一个递增的 `seq` 号。手机端如果发现 seq 断了（比如网络中断一会儿），就向 agent 发请求要求回放，带上自己最后收到的 `afterSeq`。

agent 维护了一个内存环形缓冲，每个会话最多保 40 帧，能补回缺失的部分。如果断层太久或者压根没收到首帧 replace，就重新 `capture-pane` 生成一帧新的 replace。

这样网络抖动之后手机端能自动补上中间缺掉的输出，不会只看到最新一屏。

### 设备配对

配对流程用一个一次性码完成。

agent 启动后向 relay 申请一个配对码（HTTP，需要 relay token 认证）。relay 那边验证这个 agent 确实在线，然后生成一个码。格式是去掉易混淆字符的字母数字，有点像 `ABC-DEFG` 这样，有效期默认 10 分钟。

用户在手机浏览器上输入这个码。浏览器同时生成自己的 ECDH 密钥对，把公钥和配对码一起提交。

relay 验证配对码有效且没被用过之后，签发一个 `accessToken`，把 agent 的公钥返回给浏览器。配对码标记为已兑现，用 SQLite 的 `begin immediate` 事务防止并发双花。

配对完成。浏览器和 agent 各自持有对方的公钥，后续业务消息全部端到端加密。

整个过程不需要手动交换密钥或者扫二维码，输入一个短码就完事。多个浏览器可以分别配对同一个 agent，daemon 会对每个 token 各自加密消息，天然支持多终端同时看。

说实话做这个配对流程的时候我纠结过 token 的有效期。太短了（比如 5 分钟）用户可能没输入完就过期；太长了（比如一小时）被人拿着码去试配对的风险就大。后来就定成了 10 分钟，加上 relay 这边限流，觉得够了。但有时候还是会听到有人说"我的码刚好过期了"这样的埋怨，这个暂时没想到更优雅的解决方案。

## 现在跑起来什么样

装好之后基本就是 `termpilot relay` 加 `termpilot agent --relay ...`，然后在 agent 这边 `termpilot claude code` 或 `termpilot run -- <command>`，手机浏览器打开 relay 地址就看到实时的终端。

输入也是直接在手机的虚拟键盘上打，Ctrl、Cmd 这类组合键有专门的按钮。做了针对触摸的调整，不至于一个不小心 Ctrl+C 就打错了。

界面的主要部分就是 xterm.js 的终端窗口，下面一row 是快捷按钮。左边一个按钮能切会话（如果你同时开了好几条的话），右边一个能重连。顶部显示会话状态和 agent 是否在线。

整体的感觉是轻量级。relay 占用的资源基本可以忽略，agent 侧就看 `tmux` 会话的输出缓冲大小，一般的使用不会是瓶颈。

## 后续方向

现在能用的功能基本就这些。有个想加的是录屏功能——在 agent 侧记录所有的终端操作（带时间戳），后来可以在手机上回放。但这个需要改一下消息协议，工作量有点大，暂时搁在 backlog 里面。

还有一个是支持共享会话。目前配对是一一对应的，一个 token 对应一个浏览器。如果想让多个人同时看同一条会话（比如结对编程的时候），需要加一个共享链接机制。但多人编辑的权限管理会很复杂，还没想好怎么设计。

如果你也有类似的需求或者现在就想试试，项目开源在 GitHub 上。有 BUG、新想法、或者就是想吐槽体验，欢迎提 Issue。

## 相关链接

- 文档站：<https://fengye404.top/TermPilot/>
- GitHub：<https://github.com/fengye404/TermPilot>
- NPM：<https://www.npmjs.com/package/@fengye404/termpilot>
