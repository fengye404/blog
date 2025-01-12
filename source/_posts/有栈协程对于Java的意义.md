---
title: 有栈协程对于Java的意义
typora-root-url: ./有栈协程对于Java的意义
date: 2025-01-06 22:10:52
tags:
---

# 有栈协程对于Java的意义

## 1.传统 Servlet 生态的线程模型

在传统的 servlet 生态中，线程模型一般是 thread per request，即每个请求分配一个线程，这个线程负责整个请求的生命周期。

有个很直观的工具：ThreadLocal--在一次请求过程中，可以在请求上游往 ThreadLocal set 一些数据，比如可以存 userId、trace 等；在请求下游时直接调用 threadLocal.get() 即可获取。

在这种线程模型中，想要承载更多请求，就需要添加更多线程。更多的线程意味着带来更多的资源占用：

- 一个 Java 线程的线程栈大小通常为 1MB，这意味着如果需要同时处理 1000 个并发连接，光线程栈的内存占用就有 1000 MB。

- Java 平台线程是由 JVM 映射到操作系统的内核线程，如果并发请求数量增多，内核线程就需要同样增加。
  - 每个内核线程需要由操作系统分配线程控制块，
  - 过多的内核线程会导致频繁的线程上下文切换，如果存在阻塞的 IO 操作，就会导致大量内核线程被阻塞

## 2.响应式线程模型

为了避免创建和阻塞过多的内核线程，我们需要一种方式提高线程利用率：当遇到某些阻塞IO操作，将线程迁移走以执行其他任务。
事实上已经有很多框架提供了这部分能力，例如 Netty、Vert.x、Quarkus。
这些框架的代码风格通常是 feture 套 feture，将异步回调操作串在一起，例如这段用 Vert.x 编写的代码：

```java
public class MainVerticle extends AbstractVerticle {
 
  @Override
  public void start(Promise<Void> startPromise) throws Exception {
    // Create a Router
    Router router = Router.router(vertx);
 
    // Mount the handler for all incoming requests at every path and HTTP method
    router.route().handler(context -> {
      // Get the address of the request
      String address = context.request().connection().remoteAddress().toString();
      // Get the query parameter "name"
      MultiMap queryParams = context.queryParams();
      String name = queryParams.contains("name") ? queryParams.get("name") : "unknown";
      // Write a json response
      context.json(
        new JsonObject()
          .put("name", name)
          .put("address", address)
          .put("message", "Hello " + name + " connected from " + address)
      );
    });
 
    // Create the HTTP server
    vertx.createHttpServer()
      // Handle every request using the router
      .requestHandler(router)
      // Start listening
      .listen(8888)
      // Print the port on success
      .onSuccess(server -> {
        System.out.println("HTTP server started on port " + server.actualPort());
        startPromise.complete();
      })
      // Print the problem on failure
      .onFailure(throwable -> {
        throwable.printStackTrace();
        startPromise.fail(throwable);
      });
  }
}
```

响应式的弊端：

- 与现有同步生态不兼容。

  如果我们的业务逻辑编写在同步的生态上，那么想要迁移到响应式的生态并不是一件容易的事。响应式框架大多是基于 eventloop 的，eventloop 中最重要的一条原则就是：不要在 eventloop 线程中执行阻塞调用。以 mysql 数据库访问为例，我们现有的同步生态都是阻塞的，想要迁移到响应式的生态，意味着我们需要按照 mysql 的协议重写一套响应式的客户端。虽然大部分响应式框架都提供了一套现有的能力（例如 vetr.x 的 [mysqlclient](https://vertx.io/docs/vertx-mysql-client/java/)），但是迁移仍然需要成本。

- 难以学习，开发不友好。

  想要使用响应式的生态，有太多概念需要学习，

## 

