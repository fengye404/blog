---
title: Docker笔记
typora-root-url: ./Docker笔记
date: 2022-01-28 15:36:36
tags:
---

## 镜像命令

查看本机所有镜像

```java
docker images
参数:
-a		列出所有镜像（默认自带）
-q		只显示镜像id
```

搜索镜像

```
docker search 镜像名
参数:
-s 指定值		列出收藏数不少于指定值的镜像
--no-trunc	  显示完整的镜像信息
```

下载镜像

```
docker pull 镜像名[:TAG]
```

删除镜像

```
docker rmi 镜像名
参数:
-f			强制删除
```

加载.tar镜像文件到本地docker仓库

```
docker load -i 镜像文件名
```



------

## 容器命令

运行镜像，新建容器并启动

```
docker run 镜像名
参数:
--name                         为容器起别名
-d                             在后台启动容器
-p 主机端口号:容器端口号           映射端口号       
例: docker run -d --name mytomcat -p 8081:8080 tomcat
```

查看正在运行的容器

```
docker ps
参数:
-a      查看正在运行的容器和历史运行过的容器
-q      静默模式,只显示容器编号
```

停止|关闭|重启容器

```
docker start 容器名或id    -------开启容器
docker restart 容器名或id  -------重启容器
docker stop 容器名或id     -------正常停止容器
docker kill 容器名或id     -------立即停止容器
```

删除容器

```
docker rm 容器名或id
参数:
-f            强制删除正在运行的容器
```

查看容器内服务日志

```
docker logs 容器名或id
参数:
-f              实时输出日志
-t              加入时间戳
--tail n        显示日志最后n行
```

查看容器内的进程

```
docker top 容器名或id
```

进入容器

```
docker exec -it 容器名或id bash
exit            退出容器
```

主机与容器进行文件传输

```
docker cp 主机文件 容器名(或id):容器路径  -------将主机文件复制到容器内部
docker cp 容器名(或id):容器文件 主机路径  -------将容器文件复制到主机内部
```

查看容器内部细节

```
docker inspect 容器名或id
```

将容器打包成镜像

```
docker commit -m "描述信息" -a "作者" 容器名或id 镜像名:标签
```

将镜像保存成一个.tar文件

```
docker save 镜像名称:标签 -o 文件名
```



------

## 数据卷操作

数据卷的作用：实现容器与宿主机之间的数据共享

特点：

1. 对数据卷的修改会立即影响容器
2. 对数据卷的修改不会影响镜像
3. 容器被删除后，数据卷也会一直存在

### 数据卷命令

创建数据卷

```
docker volume create 卷名
```

查看所有数据卷

```
docker volume ls
```

查看某个数据卷的细节

```
docker volume inspect 卷名
```

删除数据卷

```
docker volume prune    ------自动删除所有未使用的数据卷
docker volume rm 卷名   ------删除指定数据卷
```

### 把数据卷挂载到容器中

自定义数据卷目录

```
docker run 镜像名
-v 主机目录(绝对路径):容器内目录[:ro]   加:ro表示只读，即容器不能对目录进行写的操作，容器影响不到主机
主要用于向容器中同步数据，docker会把容器内目录中的数据全部替换为主机目录中的数据
```

自动数据卷目录

```
docker run 镜像名
-v 自定义卷名:容器内目录
主要用于把容器中的数据取出，docker会自动在主机中创建一个目录作为卷并把容器中目录的内容全部复制到该新建目录下
```

## 常用服务的安装

### docker安装mysql

下载mysql镜像

```
docker pull mysql
```

创建并运行mysql镜像，并指定环境变量和数据卷

```
docker run -e MYSQL_ROOT_PASSWORD=root -p 3306:3306 --name mysql01 -v mysqldata:/var/lib/mysql -d mysql

参数解释：
-e MYSQL_ROOT_PASSWORD=root 
表示指定mysql数据库的root用户的密码为root

-v mysqldata:/var/lib/mysqlmysql
表示创建一个mysqldata数据卷来存储mysql的数据
mysql存储数据文件目录在/var/lib/mysql
```

## Dockerfile

| 保留字                 | 作用                                                         |
| ---------------------- | ------------------------------------------------------------ |
| FROM                   | 当前镜像是基于哪个镜像  第一个指令必须事FROM                 |
| MAINTAINER(deprecated) | 镜像维护者的姓名和邮箱地址                                   |
| RUN                    | 构建镜像时需要运行的指令                                     |
| EXPOSE                 | 当前容器对外暴露出的端口号                                   |
| WORKDIR                | 指定在创建容器后，终端默认登录进来的工作目录，一个落脚点     |
| ENV                    | 用来在构建镜像的过程中设置环境变量                           |
| ADD                    | 将主机目录下的文件拷贝进镜像且ADD命令会自动处理URL和解压tar包 |
| COPY                   | 类似于ADD，拷贝文件和目录到镜像中<br/>将从结构上下文目录中<原路径>的文件/目录复制到新的一层的镜像的<目标路径>位置 |
| VOLUME                 | 容器数据卷，用于数据保存和持久化工作                         |
| CMD                    | 指定一个容器启动时要运行的命令<br/>Dockerfile中可以有多个CMD指令，但只有最后一个生效，CMD会被docker run命令行参数中指定的程序替换 |
| ENTRYPOINT             | 指定一个容器启动时要运行的命令<br/>ENTRYPOINT的目的和CMD一样，都是在指定容器启动程序及其参数 |

### FROM

- 基于哪个镜像构建新的镜像，在构建时会自动从docker hub拉取base镜像

- 必须作为Dockerfile的第一个指令出现

- 语法

  ```dockerfile
  FROM <image>
  FROM <image>[:<tag>]
  ```

### EXPOSE

- 用来指定构建的镜像在运行为容器时对外暴露的端口

- 语法

  ```
  EXPOSE <port>[/tcp|/udp]
  EXPOSE 80/tcp    如果没有显示指定，则默认为tcp
  EXPOSE 80/udp
  ```

### WORKDIR

- 指定在创建容器后，终端默认登录进来的工作目录

- 为Dockerfile中的RUN、CMD、ENTRYPOINT、COPY、ADD指定工作目录

- 可以指定绝对路径，如果路径不存在则会创建目录

- 可以使用多个WORKDIR命令，如果指定相对路径则是在上一个WORKDIR后的相对路径

- 语法

  ```
  WORKDIR <dir>
  WORKDIR /data     绝对路径/data
  WORKDIR aa		  相对路径，/data下的aa，即/data/aa
  ```

### COPY

- 用来将context目录中的指定文件复制到镜像指定目录中

- 语法

  ```dockerfile
  COPY <src> <dir>
  COPY hom* /mydir/        通配符
  COPY hom?.text /mydir/	 通配符添加多个文件
  COPY home.text relativeDir/   可以指定相对路径
  COPY home.text /absoluteDir/  可以指定绝对路径
  ```

### ADD

- 和COPY一样

- 不同之处在于如果要复制的对象是个.tar压缩包，则会自动解压。如果复制的对象是个URL，则会自动下载

- 语法

  ```dockerfile
  ADD <src> <dir>
  ADD url /dir
  ADD test.tar /dir
  ```

### VOLUME

- 用来定义容器运行时可以挂载到主机上的目录

- 语法

  ```
  VOLUME /data
  ```

### ENV

- 用来为镜像设置环境变量，这个值将出现在构建阶段中后续

- 引用的时候用$<key>

- 语法

  ```dockerfile
  ENV <key> <value>
  ENV <key>=<value>...
  ```

### RUN

- RUN指令将在当前镜像之上的新层中执行并提交结果

- 在docker build时运行

- 生成的提交镜像将用于Dockerfile的下一步

- 语法

  ```dockerfile
  RUN <command>
  RUN ["<executeable>","<param1>","<param2>",...]
  RUN ["/bin/bash","-c","<executeable>","<param1>","<param2>",...]
  ```

### CMD

- 与RUN类似

- 在docker run时运行

- CMD 指令的首要目的在于为启动的容器指定默认要运行的程序，程序运行结束，容器也就结束；注意: CMD 指令指定的程序可被 docker run 命令行参数中指定要运行的程序所覆盖。 

- Dockerfile中只能有一条CMD指令，如果有多条，则只有最后一条生效

- 语法

  ```
  CMD <command>
  RUN ["<executeable>","<param1>","<param2>",...]
  CMD ["<param1>","<param2>",...] 该写法是为 ENTRYPOINT 指令指定的程序提供默认参数；
  ```

### ENTRYPOINT

- 与CMD类似

- 在docker run时运行

- 不会被docker run的命令行参数指定的指令覆盖

- 语法

  ```
  ENTRYPOINT <command>
  ENTRYPOINT ["<executeable>","<param1>","<param2>",...]
  ```

## Docker Compose









