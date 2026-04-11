---
title: nps搭建内网穿透
typora-root-url: ./nps搭建内网穿透
date: 2022-02-10 15:38:45
tags:
---

### 前言

最近在玩 MC ，买了个 腾讯云2核4G 的服务器跑 MC 服务端，但是 mod 加多了之后还是有点卡，于是就用了个老的电脑搭建服务器，之前的买的服务器用来搭建内网穿透服务端。

一开始使用的是 frp ，后来被安利了 nps，因为有 web gui ，使用起来更友好一点。

### 客户端

服务端是买的 腾讯云2核4G 服务器

centos7 x86_64

##### 下载

```shell
wget https://github.com/ehang-io/nps/releases/download/v0.26.10/linux_amd64_server.tar.gz
```

##### 解压

```shell
tar -zxvf linux_amd64_server.tar.gz
```

##### 安装

```shell
./nps install
```

##### 启动

```
nps start
```

启动后就可以访问了，默认： http://ip:8080

### 服务端

客户端是老的笔记本

windows10 64

手动下载解压后，文件结构

```shell
    │ npc.exe
    │
    └─conf
            multi_account.conf
            npc.conf
```

##### 启动

配置文件启动

```
.\npc.exe -config=[npc.conf的路径]
```

### NPS 搭建 MC 服务端的栗子

服务端新建客户端

![img](http://fengye404.top/wp-content/uploads/2022/03/35JFL@@OI1ANATO7LACGM-1.png)



修改客户端配置文件 npc.conf

```
[common]
server_addr=服务端IP:8024   ## 客户端命令中的 -server
conn_type=tcp
vkey=0u9xlw0311yelu4s      ## 客户端命令中的 -vkey
auto_reconnection=true
max_conn=1000
flow_limit=1000
rate_limit=1000
basic_username=11
basic_password=3
web_username=user
web_password=1234
crypt=true
compress=true
#pprof_addr=0.0.0.0:9999
disconnect_timeout=60

[health_check_test1]
health_check_timeout=1
health_check_max_failed=3
health_check_interval=1
health_http_url=/
health_check_type=http
health_check_target=127.0.0.1:8083,127.0.0.1:8082

[health_check_test2]
health_check_timeout=1
health_check_max_failed=3
health_check_interval=1
health_check_type=tcp
health_check_target=127.0.0.1:8083,127.0.0.1:8082

[mcsm]
mode=tcp
target_addr=127.0.0.1:23333    # MCSM web页面
server_port=10000

[mc]
mode=tcp
target_addr=127.0.0.1:25565    # MC
server_port=10001

[mcsm daemon]
mode=tcp
target_addr=127.0.0.1:24444    # MCSM 的守护进程
server_port=10002
```

MCSM 新建守护进程

ip 填 nps 服务端的 ip

![img](http://fengye404.top/wp-content/uploads/2022/03/L8INDAXU8V94Q9OACKE.png)

