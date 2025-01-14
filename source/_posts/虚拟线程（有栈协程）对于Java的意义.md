---
title: 虚拟线程（有栈协程）对于Java的意义
typora-root-url: ./虚拟线程（有栈协程）对于Java的意义
date: 2025-01-06 22:10:52
tags:
---

# 虚拟线程（有栈协程）对于Java的意义

## 1.传统同步线程模型

在传统的 servlet 生态中，线程模型一般是 thread per request，即每个请求分配一个线程，这个线程负责整个请求的生命周期。

有个很直观的理解：ThreadLocal--在一次请求过程中，可以在请求上游往 ThreadLocal set 一些数据，比如可以存 userId、trace 等；在请求下游时直接调用 threadLocal.get() 即可获取。

![image-20221203053005893](./202212030530938.png)

在这种线程模型中，想要承载更多请求，就需要添加更多线程。更多的线程意味着带来更多的资源占用：

- 一个 Java 线程的线程栈大小通常为 1MB，这意味着如果需要同时处理 1000 个并发连接，光线程栈的内存占用就有 1000 MB。

- Java 平台线程本质上是由 JVM 映射到操作系统的内核线程，如果并发请求数量增多，内核线程就需要同样增加。
  - 每个内核线程需要由操作系统分配线程控制块，
  - 过多的内核线程会导致频繁的线程上下文切换，如果存在阻塞的 IO 操作，就会导致大量内核线程被阻塞

## 2.异步&响应式线程模型

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

操作系统中的线程模式大致可以分为三种：

- 内核线程模式：程序的线程和操作系统提供的内核线程是 1:1 的关系
- 用户线程模式：程序的线程和操作系统提供的内核线程是 n:1 的关系
- 混合线程模式：程序的线程和操作系统提供的内核线程是 n:m 的关系

实际上在 java 中，用户线程模型出现早于内核线程。Linux 2.6 之前，操作系统只能提供单线程能力，java 使用的是一种名为“绿色”线程的用户线程模型：将主线程运行在 JVM 中，程序中创建用户线程执行多个任务，本质上是单核并发。

后来随着多核技术的兴起，Linux 也提供了多线程的能力，这时“绿色”线程的劣势就暴露出来了，它本质上还是只能使用操作系统的单核进行并发，无法充分利用多核进行并行操作，并且所有的线程阻塞、调度逻辑都需要由 java 实现，而不能使用操作系统的能力。

此时 java 就抛弃了这种古早的线程模型，转为了内核线程模式。

然而内核线程模式也有缺点，创建、销毁涉及操作系统资源的分配和管理，上下文切换涉及系统调用、用户态与内核态的切换，而且一个系统中同时存在的线程数量也有上限。

随着并发量的提高，java 中重新提供用户线程模型的诉求日益增加，于是就有了 jdk21 带来的虚拟线程。

## 4.无栈协程和有栈协程

从概念上来看，虚拟线程属于用户线程模型，并且可以被视为协程的一种实现。

协程是一个轻量化、用户态的执行单元，它可以模拟线程的执行上下文。与传统的线程相比，协程在等待 I/O 等操作时能够被挂起，让载体线程去执行其他协程任务，从而提高资源利用率。

在响应式编程模型中，我们通过异步事件的方式不断切换执行的方法，目的也是在保持线程的活跃性而非阻塞。虽然响应式编程允许在回调函数的作用域中附带上下文信息，但这种方式在复杂场景中可能导致“回调地狱”，使得代码的可读性和可维护性下降。

相对而言，协程无论是有栈协程还是无栈协程，都能够附带清晰的上下文信息，允许在更大的作用域内管理状态和控制流。这种结构化的上下文管理使得协程在编写异步代码时更加直观和易于维护。

### 以 kotlin-coroutine 为例的无栈协程

看这段 kotlin 代码：

```kotlin
package org.example

import kotlinx.coroutines.*

suspend fun fetchData(token : String): String {
    println("当前fetchData执行线程为:${Thread.currentThread()}")
    delay(1000) // 模拟阻塞
    return "$token:success"
}

suspend fun requestToken(): String {
    println("当前requestToken执行线程为:${Thread.currentThread()}")
    delay(1000) // 模拟阻塞
    return "token"
}

fun main() = runBlocking {
    launch {
        var token = requestToken();
        var fetchData = fetchData(token)
        println(fetchData)
    }
    println("当前main执行线程为:${Thread.currentThread()}")
    delay(5000) // 模拟主线程其他逻辑
}

// 调用结果为
// 当前main执行线程为:Thread[main,5,main]
// 当前requestToken执行线程为:Thread[main,5,main]
// 当前fetchData执行线程为:Thread[main,5,main]
/token:success
```

这段代码中，用 `suspend` 关键字定义了两个可被挂起的方法 `fetchData`，在这个方法中通过 `delay` 模拟了耗时的阻塞操作。在主线程中，调用 `fetchData` 后，`fetchData` 中执行到阻塞逻辑时，该方法就会被挂起，并让出线程控制权，以便其他协程或任务可以在同一线程上并发执行；当阻塞结束后，将恢复 `fetchData` 方法，并且继续向下执行。

上述代码看起来和平时的同步阻塞代码几乎一致，甚至在 idea 中可以像同步代码一样 step by step 地 debug。

但是，看似美好的背后，其实是 kotlin 提供的类库能力和 CPS 变换的语法糖。

这段代码实际等价于：

```kotlin
package org.example

import kotlinx.coroutines.*

fun fetchData(token: String, callback: (String) -> Unit) {
    println("当前fetchData执行线程为:${Thread.currentThread()}")
    GlobalScope.launch {
        delay(1000) // 模拟阻塞
        callback("$token:success")
    }
}

fun requestToken(callback: (String) -> Unit) {
    println("当前requestToken执行线程为:${Thread.currentThread()}")
    GlobalScope.launch {
        delay(1000) // 模拟阻塞
        callback("token")
    }
}

fun main() = runBlocking {
    requestToken { token ->
        fetchData(token) { fetchDataResult ->
            println(fetchDataResult)
        }
    }
    println("当前main执行线程为:${Thread.currentThread()}")
    delay(5000) // 模拟主线程其他逻辑
}
```

可以看到，kotlin 中 `suspend` 







我们都知道 kotlin 早在 jdk21 之前就提供了协程的实现。提到协程，大多数人第一反应可能会想到 go 提供的 goroutine，这是一种在 go runtime 底层提供的能力，但是在 jdk21 之前，显然 jvm 底层没有提供这种能力，所以 kotlin 的 coroutine 实际上是一种 CPS 变换的语法糖。



在 jdk21 到来之前，我们有除了异步响应式编程以外的解决方案吗？我们可能会想到 

不妨来看看 kotlin，同样作为基于 jvm 的语言，可以说是 java 异父异母的亲兄弟。

在 jdk21 之前，kotlin 就已经提供了协程的实现。但是与 go 提供的 goroutine 不同，goroutine 在运行时底层提供了

### 有栈协程

JDK21 为 java 引入了虚拟线程。虚拟线程实际上是用户线程的一种体现



参考：

> https://juejin.cn/post/7181664513559625788#heading-3
