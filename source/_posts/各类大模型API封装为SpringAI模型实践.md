---
title: 各类大模型API封装为SpringAI模型实践
typora-root-url: ./各类大模型API封装为SpringAI模型实践
date: 2025-06-02 18:03:33
tags:
---

# 各类大模型API封装为SpringAI模型实践

最近项目开发中经常用到 Spring AI，作为 Spring 全家桶的一员，它为 AI 生态封装了一套统一、易用的 API 规范。

同时 Spring AI 适配了一些模型提供方的 API，你可以在 spring application 配置文件中配置 url + api key 做到开箱即用。

但是美中不足的是，Spring AI 适配的模型提供方有限，目前支持的列表可以看官方文档：https://docs.spring.io/spring-ai/reference/api/chat/comparison.html

很遗憾，其中就不包含我个人平时经常用到的百炼，好消息是 spring ai alibaba 封装了百炼，你可以引入 spring ai alibaba 来直接配置 ChatClient。

“如无必要，勿增实体”--我个人不喜欢在项目中以这样的形式引入一些依赖，况且模型提供方的切换是必然的诉求，百炼有 spring ai alibaba 的支持，其他大模型 API 要怎么办呢？有没有一种方法可以直接封装任意大模型 API 为 Spring AI API？

有的兄弟，有的。Spring AI 提供了 ChatModel 接口，实现这个接口就可以将任意的大模型 API 封装为 Spring AI 的 API。

## 百炼DashScope

文档：https://help.aliyun.com/zh/model-studio/use-qwen-by-calling-api#a9b7b197e2q2v

maven 配置

```xml
<dependency>
    <groupId>com.alibaba</groupId>
    <artifactId>dashscope-sdk-java</artifactId>
    <!-- 请将 'the-latest-version' 替换为最新版本号：https://mvnrepository.com/artifact/com.alibaba/dashscope-sdk-java -->
    <version>the-latest-version</version>
</dependency>
```
