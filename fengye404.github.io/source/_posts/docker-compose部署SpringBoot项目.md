---
title: docker-compose部署SpringBoot项目
typora-root-url: ./docker-compose部署SpringBoot项目
date: 2022-04-23 15:44:03
tags:
---

# docker-compose部署SpringBoot项目

## 简介

docker-compose 是 Docker 官方的开源项目，主要用于实现对 Docker 容器集群的快速编排。

用户可以通过 `docker-compose.yml` 来定义一组相关联的容器作为一个项目(`project`)

docker-compose的两个概念:

- 服务(`service`)：应用的容器
- 项目(`project`)：一组关联的服务组成，在 `docker-compose.yml` 中定义

## 安装

下载最新版的docker-compose文件 (截止2022.1.28)

```shell
sudo curl -L https://github.com/docker/compose/releases/download/v2.2.3/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
```

*下载慢换国内源

[DaoCloud | Docker 极速下载](http://get.daocloud.io/#install-compose)

```shell
sudo curl -L https://get.daocloud.io/docker/compose/releases/download/v2.2.3/docker-compose-`uname -s`-`uname -m` -o /usr/local/bin/docker-compose
```


添加可执行权限

```shell
sudo chmod +x /usr/local/bin/docker-compose
```

检查是否安装成功

```shell
[root@fengye]docker-compose --version
Docker Compose version v2.2.3
```

## 编写docker-compose.yml文件

模板：

```yaml
version: "3.7"
services:

  example:                     #服务名称
    image: tomcat:8.0-jre8     #使用的镜像
    container_name: example_container_name    #容器启动时的名字
    ports:                     #容器端口映射，前面的是主机端口
      - "8080:8080"
    volumes:                   #容器中的哪个路径和宿主中的路径进行数据卷映射
      - /root/apps:/usr/local/tomcat/webapps     #手动映射
      - tomcatwebapps:/usr/local/tomcat/webapps  #自动创建数据卷映射，需要在后面声明数据卷
    networks:                  #指定容器启动使用的网桥
      - aa
    command: xxxxx             #用于覆盖容器默认启动指令
    envoriment:                #指定容器启动时的环境参数
      - xxxxx=xxxx
       #env_file:                 使用环境变量文件，书写格式和环境参数相同
        #  - ./xxx.env
    depends_on:                #设置这个服务依赖的服务名称（即启动优先级）
      - xxxxx
    #sysctls:                  #修改容器内部参数
    #  - xxxx=xxxx
    
volumes:
   tomcatwebapps:
   #external:       默认卷名会带上项目名(yml文件所在文件夹名)，
   #  true          可以声明使用外部以存在的卷
networks:
   aa:                #创建逻辑同volume
```

## 启动

```shell
docker-compose up -d
# -d 表示后台启动
```

## 实例

初始文件结构：

```
.
`-- freshcup
    |-- data
    |   |-- mysql
    |   |   `-- initsql
    |   |       `-- freshcup.sql
    |   `-- redis
    |       `-- conf
    |           `-- redis.conf
    |-- docker-compose.yml
    |-- Dockerfile
    `-- freshcup.jar
```

Dockerfile：

```dockerfile
FROM adoptopenjdk/openjdk11:alpine-slim

WORKDIR /app

COPY freshcup.jar .

EXPOSE 10101

CMD ["java" ,"-jar" ,"freshcup.jar"]
```

docker-compose.yml文件：

```yaml
version: "3.7"

services:

  freshcup:                        #自己写的web服务
    build:                         #根据指定的Dockerfile构建镜像
      context:  .                  #指定dockerfile所在目录作为docker构建镜像的context环境
      dockerfile: Dockerfile       #指定dockerfile的文件，默认为Dockerfile
    container_name: freshcup
    ports:
      - "10000:10101"
    networks:
      - freshcup
    depends_on:
      - mysql
      - redis

  mysql:
    image: mysql:5.7.34
    container_name: freshcup_mysql
    ports:
      - "10001:3306"
    environment:
      - MYSQL_ROOT_PASSWORD=root
      - MYSQL_DATABASE=freshcup
    volumes:
      - ./data/mysql/initsql:/docker-entrypoint-initdb.d    #用于初始化mysql数据库
      - ./data/mysql/db:/var/lib/mysql                      #mysql数据文件挂载
      - ./data/mysql/conf:/etc/mysql                        #mysql配置文件挂载
      - ./data/mysql/log:/var/log/mysql                     #mysql日志文件挂载
    networks:
      - freshcup

  reids:
    image: redis:6.2
    container_name: freshcup_redis
    ports:
      - "10002:6379"
    volumes:
      - ./data/redis/db:/data                                    #redis数据文件挂载
      - ./data/redis/conf/redis.conf:/etc/redis/redis.conf       #redis配置文件挂载
    command:
      - sh
      - -c
      - |
        redis-server /etc/redis/redis.conf                       
        redis-server --requirepass *********
        redis-server --appendonly yes

networks:
  freshcup:
```

踩坑：command指令如果有多条，不能使用这种形式：

```yaml
command:
  - "redis-server --appendonly yes"      #开启AOF持久化
  - "redis-server --requirepass *****"   #设置redis密码
```

解决方案：[docker-compose command 执行多条指令](https://blog.csdn.net/whatday/article/details/108863389)

## docker-compose常用命令

### UP

格式为`docker-compose up [options] [service]`

```x86asm
docker-compose up    对整个项目操作启动
docker-compose up -d 后台启动
```

### Down

停止和删除容器、网络、卷、镜像

```x86asm
docker-compose down 关闭所有容器
docker-compose down 服务id 关闭某一个服务
```

### Exec

进入某个服务的内部

```bash
docker-compose exec [服务id] bash
```

### ps

列出当前项目所有运行的服务

```
 docker-compose ps 
```

### restart

重启服务

```undefined
docker-compose restart [服务id]
```

### stop

停止服务

```bash
 docker-compose stop [服务id]
```

### rm

删除停止状态的整个项目或者某个服务

```bash
 docker-compose rm [服务id]
```

强制删除

```bash
 docker-compose rm -f [服务id]
```

### top

查看整个项目所有服务的进程或者某个指定服务的进程

```bash
docker-compose top [服务id]
```

### unpause

恢复处于暂停状态中的服务

```bash
docker-compose unpause [服务id]
```

### pause

暂停所有服务或者某一个服务

```bash
docker-compose pause [服务id]
```

### logs

查看容器的日志

```bash
docker-compose  logs [服务id]
```

查看实时日志

```bash
docker-compose  logs  -f [服务id]
```
