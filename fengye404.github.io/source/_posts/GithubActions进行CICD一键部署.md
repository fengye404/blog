---
title: GithubActions进行CICD一键部署
typora-root-url: ./GithubActions进行CICD一键部署
date: 2022-09-04 15:45:37
tags:
---

### 基本概念

Github Actions 是 Github 推出的持续集成工具

1. `workflow`: 一个 `workflow` 工作流就是一个完整的过程，每个`workflow` 包含一组 `jobs`任务。
2. `job : jobs`任务包含一个或多个`job` ，每个 `job`包含一系列的 `steps` 步骤。
3. `step` : 每个 `step` 步骤可以执行指令或者使用一个 `action` 动作。
4. `action` : 每个 `action` 动作就是一个通用的基本单元。

`workflow` 必须存储在项目根路径下的 `.github/workflows` 中，每个workflow对应一个具体的 `.yml` 文件

### workflow 文件

```yml
# 工作流程的名字
name: summerbot's CI/CD

# 触发时机： push 到 main 分支
on:
  push:
    branches: [ main ]
#  pull_request:
#    branches: [main]

# 要执行的任务
jobs:
  build:
    # 配置job任务运行的虚拟机环境
    runs-on: ubuntu-latest

    # 运行步骤
    steps:
      - name: checkout
        uses: actions/checkout@v3

      - name: Set up JDK 11
        uses: actions/setup-java@v2
        with:
          java-version: '11'
          distribution: 'temurin'
          cache: 'maven'

      # 在工作目录下执行，生成的 jar 文件在 target 下
      - name: Build with Maven
        run: mvn -B -DskipTests=true package --file pom.xml

#      # secrets 需要自行在 github 仓库中设置
#      - name: Deploy jar to server
#        # 本质上是把虚拟机中 jar 包通过 secure copy 复制到远程仓库
#        uses: garygrossgarten/github-action-scp@release
#        with:
#          # 虚拟机中 jar 包的位置（就在工作目录下）
#          local: target/summerbot.jar
#          # 远程仓库中需要复制的位置
#          remote: /home/summerbot/summerbot.jar
#          host: ${{ secrets.HOST }}
#          username: ${{ secrets.SSH_USERNAME }}
#          password: ${{ secrets.SSH_PASSWORD }}

      - name: Deploy to server
        uses: easingthemes/ssh-deploy@v2.2.11
        env:
          ARGS: '-avz --delete'
          SOURCE: 'target/summerbot.jar'
          TARGET: '/home/summerbot'
          REMOTE_HOST: ${{ secrets.HOST }}
          REMOTE_USER: ${{ secrets.SSH_USERNAME }}
          SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}  # 登录服务器的私钥


      - name: Run java -jar
        # 上一个步骤执行成功后会返回 true
        if: success()
        uses: fifsky/ssh-action@master
        with:
          user: ${{ secrets.SSH_USERNAME }}
          host: ${{ secrets.HOST }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          command: screen -R summerbot -X stuff $'^C  java -jar /home/summerbot/summerbot.jar\n'
```

### workflow 文件（docker）

```yaml
name: summerbot's docker CI/CD

# 触发时机： push 到 main 分支
on:
  push:
    branches: [ main ]
  #  pull_request:
  #    branches: [main]

# 定义环境变量
# DOCKER_USER：用户名
# SERVICE_CONTAINER_NAME：summerbot-docker
env:
  IMAGE_TOTAL_NAME: ${{ secrets.DOCKER_USER }}/${{ secrets.SERVICE_CONTAINER_NAME }}
  IMAGE_TAG: latest

jobs:
  build:
    # 配置job任务运行的虚拟机环境
    runs-on: ubuntu-latest

    # 运行步骤
    steps:
      - name: checkout
        uses: actions/checkout@v2

      - name: Set up JDK 11
        uses: actions/setup-java@v2
        with:
          java-version: '11'
          distribution: 'temurin'
          cache: 'maven'

      - name: Build with Maven
        run: mvn -B package --file pom.xml

      # docker 构建多平台
      - name: Set up QEMU
        uses: docker/setup-qemu-action@v2

      # 初始化构建环境
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to DockerHub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKER_USER }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Build and push
        uses: docker/build-push-action@v3
        with:
          # 当前工作目录
          context: .
          # 构建完成后 push
          push: true
          # github 账号 tag
          tags: ${{ env.IMAGE_TOTAL_NAME }}:${{ env.IMAGE_TAG }}

      - name: executing docker container
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: ${{ secrets.SSH_USERNAME }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            docker login -u ${{ secrets.DOCKER_USER }} -p ${{ secrets.DOCKER_PASSWORD }}
            docker pull ${{ env.IMAGE_TOTAL_NAME }}:${{ env.IMAGE_TAG }}
            docker stop ${{ secrets.SERVICE_CONTAINER_NAME }}
            docker rm ${{ secrets.SERVICE_CONTAINER_NAME }}
            docker run -d \
              --name ${{ secrets.SERVICE_CONTAINER_NAME }} \
              -p 23333:8080 \
              ${{ env.IMAGE_TOTAL_NAME }}:${{ env.IMAGE_TAG }}
```



> 参考文章:
>
> [让你满意的GitHub Actions详解 - 简书 (jianshu.com)](https://www.jianshu.com/p/adf755f2ebf9)
>
> [给screen发送一个命令运行，并保持screen不退出。51CTO博客](https://blog.51cto.com/johnsteven/1323942)
>
> [论部署后端项目 | 经验分享博客 (cxy621.top)](https://hexo.cxy621.top/2021/12/09/lun-bu-shu-hou-duan-xiang-mu/#toc-heading-25)
