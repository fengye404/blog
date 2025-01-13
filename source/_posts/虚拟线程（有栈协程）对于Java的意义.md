---
title: 虚拟线程（有栈协程）对于Java的意义
typora-root-url: ./虚拟线程（有栈协程）对于Java的意义
date: 2025-01-06 22:10:52
tags:
---

# 虚拟线程（有栈协程）对于Java的意义

## 1.传统 Servlet 生态的线程模型

在传统的 servlet 生态中，线程模型一般是 thread per request，即每个请求分配一个线程，这个线程负责整个请求的生命周期。

有个很直观的工具：ThreadLocal--在一次请求过程中，可以在请求上游往 ThreadLocal set 一些数据，比如可以存 userId、trace 等；在请求下游时直接调用 threadLocal.get() 即可获取。

![image-20221203053005893](./202212030530938.png)

在这种线程模型中，想要承载更多请求，就需要添加更多线程。更多的线程意味着带来更多的资源占用：

- 一个 Java 线程的线程栈大小通常为 1MB，这意味着如果需要同时处理 1000 个并发连接，光线程栈的内存占用就有 1000 MB。

- Java 平台线程本质上是由 JVM 映射到操作系统的内核线程，如果并发请求数量增多，内核线程就需要同样增加。
  - 每个内核线程需要由操作系统分配线程控制块，
  - 过多的内核线程会导致频繁的线程上下文切换，如果存在阻塞的 IO 操作，就会导致大量内核线程被阻塞

## 2.响应式线程模型

为了避免创建和阻塞过多的内核线程，我们需要一种方式提高线程利用率：当遇到某些阻塞IO操作，将线程迁移走以执行其他任务。

这里贴一张 netty 中的 eventloop 调用逻辑图，帮助理解：

![image-20250112202644115](./image-20250112202644115.png)

在这种模式中，线程不存在上下文切换的开销，同时单个线程按照 Reactor 模型也可以服务多个连接&请求。

事实上已经有很多框架提供了这部分能力，例如 Netty、Vert.x、Quarkus。

这些框架的代码风格通常是 feture 套 feture，将异步回调操作串在一起，例如这段用 Vert.x 的示例代码：

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

- 概念众多，**难以理解**。想要使用响应式的生态，有很多概念需要学习，此外代码层层嵌套，势必会形成回调地域，难以维护。
- **无堆栈信息**。响应式的 api 都是基于事件回调的，当产生阻塞 IO 时，注册完回调后，原有的调用栈栈帧就被弹出了；当阻塞 IO 结束后，触发回调时，就已经失去了原有的堆栈上下文。这意味着如果在这过程中发生异常，我们将无法使用类似 stacktrace 的方式定位调用来源和调用上下文。此外，在 IDE 中也无法进行 step by step 的 debug，我们往往需要把断点打在某个回调中。
- **与现有同步生态不兼容**，体现在两方面：
  - 现有的阻塞调用需要全部重写：如果我们的业务逻辑编写在同步的生态上，那么想要迁移到响应式的生态并不是一件容易的事。响应式框架大多是基于 eventloop 的，eventloop 中最重要的原则就是：**不要阻塞 eventloop**。以 mysql 数据库访问为例，我们现有的同步生态都是阻塞的，想要迁移到响应式的生态，意味着我们需要按照 mysql 的协议重写一套响应式的客户端。虽然大部分响应式框架都提供了一套现有的能力（例如 vetr.x 的 [mysqlclient](https://vertx.io/docs/vertx-mysql-client/java/)），但是迁移仍然需要成本。
  - 线程上下文失效：在响应式的编程模型下，一个线程本质上会在多个请求之间交错处理。这很好理解，当 A 请求先到达后，线程优先执行 A 请求的逻辑；此时线程 B 到达，进入了阻塞队列等待线程处理；当线程处理 A 请求到一半，A 进入了阻塞 IO，那么线程将会切换到 B 请求执行逻辑。此时，一些基于 threadlocal 的线程上下文变量就将失效，我们无法保证某个线程“专一”于一个请求。

## 3.内核线程和用户线程

我们都知道操作系统中有三线程模式：

- 内核线程模式：程序的线程和操作系统提供的内核线程是 1:1 的关系
- 用户线程模式：程序的线程和操作系统提供的内核线程是 n:1 的关系
- 混合线程模式：程序的线程和操作系统提供的内核线程是 n:m 的关系

实际上在 java 中，用户线程模型出现早于内核线程。Linux 2.6 之前，操作系统只能提供单线程能力，java 使用了是一种名为“绿色”线程的用户线程模型：将主线程运行在 JVM 中，程序中创建用户线程执行多个任务，本质上是单核并发。

后来随着多核技术的兴起，Linux 也提供了多线程的能力，这时“绿色”线程的劣势就暴露出来了，它本质上还是只能使用操作系统的单核进行并发，无法充分利用多核进行并行操作，并且所有的线程阻塞、调度逻辑都需要由 java 实现，而不能使用操作系统的能力。

此时 java 就抛弃了这种古早的线程模型，转为了内核线程模式。

JDK21 为 java 引入了虚拟线程。虚拟线程实际上是用户线程的一种体现



参考：

> https://juejin.cn/post/7181664513559625788#heading-3
