---
title: 部署Grafana+Prometheus+Exporter
typora-root-url: ./部署Grafana+Prometheus+Exporter
date: 2023-04-28 15:50:12
tags:
---

## Grafana

```shell
docker run -d --name=grafana --network host grafana/grafana-enterprise
```

## Prometheus

下载并解压

```shell
wget https://github.com/prometheus/prometheus/releases/download/v2.42.0/prometheus-2.42.0.linux-amd64.tar.gz

tar xvfz prometheus-*.tar.gz
```

给 prometheus 配置 systemd 启动，默认运行端口为 9090

```
vim /usr/lib/systemd/system/prometheus.service


[Unit]
Description=prometheus

[Service]
WorkingDirectory=/home/fengye/prometheus/prometheus-2.42.0.linux-amd64

# 工作目录
ExecStart=/home/fengye/prometheus/prometheus-2.42.0.linux-amd64./prometheus --storage.tsdb.path=../data --config.file=./prometheus.yml
# 执行此 daemon 的指令或脚本程序

Restart=on-failure
# 非正常退出时重启

[Install]
WantedBy=multi-user.target
# 设置服务在开机时启动


systemctl enable prometheus
```

## Node Exporter

下载并解压

```shell
wget https://github.com/prometheus/node_exporter/releases/download/v1.5.0/node_exporter-1.5.0.linux-amd64.tar.gz

tar xvfz node_exporter-*.tar.gz
```

给 node_exporter 配置 systemd 启动，默认运行端口为 9100

```
vim /usr/lib/systemd/system/node_exporter.service


[Unit]
Description=node_exporter

[Service]ExecStart=/home/fengye/node_exporter/node_exporter-1.5.0.linux-amd64/node_exporter
# 执行此 daemon 的指令或脚本程序

Restart=on-failure
# 非正常退出时重启

[Install]
WantedBy=multi-user.target
# 设置服务在开机时启动


systemctl enable node_exporter
```

在 prometheus.yml 文件中追加监控 node_exporter 的配置

```
vim /home/fengye/prometheus/prometheus-2.42.0.linux-amd64/prometheus.yml

在 scrape_configs 选项中追加
  - job_name: "node"
    static_configs:
      - targets: ["localhost:9100"]
```

重启 prometheus

```
systemctl restart prometheus
```

## MySQL Exporter

下载并解压

```shell
wget https://github.com/prometheus/mysqld_exporter/releases/download/v0.14.0/mysqld_exporter-0.14.0.linux-amd64.tar.gz

tar xvfz mysqld_exporter-*.tar.gz
```

在 MySQL 中创建新用户（注意，必须创建新用户，不能直接用 root 用户，否则获取不到数据）

```mysql
CREATE USER 'mysqld_exporter'@'localhost' IDENTIFIED BY 'mysqld_exporter'

GRANT PROCESS, REPLICATION CLIENT, SELECT ON *.* TO 'mysqld_exporter'@'localhost';
```

创建配置文件

```
vim /home/fengye/mysql_exporter/mysqld_exporter-0.14.0.linux-amd64/my.cnf


[client]
host=localhost
user=mysqld_exporter
password=mysqld_exporter
port=3306
```

给 mysql_exporter 配置 systemd 启动，默认运行端口为 9104

```shell
vim /usr/lib/systemd/system/mysql_exporter.service


[Unit]
Description=mysql_exporter

[Service]
ExecStart=/home/fengye/mysql_exporter/mysqld_exporter-0.14.0.linux-amd64/mysqld_exporter --config.my-cnf=/home/fengye/mysql_exporter/mysqld_exporter-0.14.0.linux-amd64/my.cnf
# 执行此 daemon 的指令或脚本程序

Restart=on-failure
# 非正常退出时重启

[Install]
WantedBy=multi-user.target
# 设置服务在开机时启动


systemctl enable mysql_exporter
```

在 prometheus.yml 文件中追加监控 mysql_exporter 的配置

```
vim /home/fengye/prometheus/prometheus-2.42.0.linux-amd64/prometheus.yml

在 scrape_configs 选项中追加
  - job_name: "mysql"
    static_configs:
      - targets: ["localhost:9104"]
```

重启 prometheus

```shell
systemctl restart prometheus
```

## RocketMQ Exporter

下载并解压

```
wget 
```

