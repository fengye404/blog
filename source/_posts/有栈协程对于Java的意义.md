---
title: 有栈协程对于Java的意义
typora-root-url: ./有栈协程对于Java的意义
date: 2025-01-06 22:10:52
tags:
---

# 有栈协程对于Java的意义

## 1.传统 Servlet 生态的线程模型

在传统的 servlet 生态中，线程模型一般是 thread per request，即每个请求分配一个线程，这个线程负责整个请求的生命周期。
有个很直观的媒介：ThreadLocal--在一次请求过程中，可以在请求上游往 ThreadLocal set 一些数据，比如可以存 userId、trace 等；在请求下游时直接调用 threadLocal.get() 即可获取。
在这种线程模型中，想要承载更多请求，就需要添加更多线程。Java 平台线程由 JVM 映射到操作系统的内核线程，一个 Java 线程的线程栈大小通常为 1MB，此外，如果并发请求数量增多，内核线程就需要同样增加，过多的内核线程会导致频繁的线程上下文切换，如果存在阻塞的IO操作，就会导致大量内核线程被阻塞，浪费内存资源用于无意义的存储线程栈和线程控制块。
在 Linux 中可以用 ulimit -s 命令查看一个线程栈的大小，通常为 8192k，在
一个内核线程的成本大小？fdrvggg

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



## 3.

