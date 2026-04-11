---
title: Java手写异步调用
typora-root-url: ./Java手写异步调用
date: 2021-12-27 15:31:59
tags:
---

# Java 手写异步调用

## 前言

今天在写 mirai 机器人的一个小功能时，遇到了这样一个需求：**机器人需要先发出一条消息，然后间隔 3 秒钟撤回这条消息** 。

~~当然mirai本身提供了现成的方法，支持异步调用~~

最朴素的想法是使用`Thread.sleep(3000)`

```java
public class Test {
    public void A() {
        System.out.println("A");
        try {
            Thread.sleep(3000);
            System.out.println("3S after");
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        System.out.println("B");
    }
    public static void main(String[] args) {
        Test test = new Test();
        test.A();
    }
}
//输出：
//A
//3S after
//B
```

但是这种方法是将方法A的调用线程(即主线程)休眠3S，如果我在主线程中多次调用这个方法，则下一次调用需要等待前一次休眠结束。这就叫阻塞。

主线程：sout(A)->等待3S->sout(B)->sout(A)->等待3S->sout(B)

显然，如果后续有其他的逻辑需要执行，那么这种方式显然不符合需求。

```java
public static void main(String[] args) {
    Test test = new Test();
    test.A();
    test.A();
}
//输出:
//A
//3s after
//B
//A
//3s after
//B
//期望输出：
//A
//A
//3s after
//B
//3s after
//B
```

## 创建线程

主线程：sout(A)->创建线程1->sout(2)->创建线程2

线程1：等待3S->sout(B)

线程2：等待3S->sout(B)

```java
public class Test {
    public void A() {
        System.out.println("A");
        Thread thread = new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    Thread.sleep(3000);
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }
                System.out.println("B");
            }
        });
        thread.start();
    }

    public static void main(String[] args) {
        Test test = new Test();
        test.A();
        test.A();
    }
}
//输出：
//A
//A
//3s after
//B
//3s after
//B
```

这种方法的缺点：

- 频繁地创建和销毁线程会占用大量的时间

- 创建线程后，无法跟踪线程的后续完成情况

## Executor框架

[Executor框架 CSDN](https://blog.csdn.net/ZHAOJING1234567/article/details/89882059?spm=1001.2101.3001.6650.2&utm_medium=distribute.pc_relevant.none-task-blog-2%7Edefault%7ECTRLIST%7Edefault-2.opensearchhbase&depth_1-utm_source=distribute.pc_relevant.none-task-blog-2%7Edefault%7ECTRLIST%7Edefault-2.opensearchhbase)

### Future 或 FutureTask

```java
public class Test {
    public void A() throws ExecutionException, InterruptedException {
        System.out.println("A");
        //阿里巴巴规范手册不建议用 Executors 创建线程池
        ExecutorService executorService = Executors.newFixedThreadPool(5);
        Future<String> future = executorService.submit(() -> {
            try {
                Thread.sleep(3000);
                System.out.println("3S after");
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
            System.out.println("B");
            return "task B completed";
        });
        //future.get()实际是阻塞的
        //System.out.println(future.get());
    }

    public static void main(String[] args) throws ExecutionException, InterruptedException {
        Test test = new Test();
        test.A();
        test.A();
    }
}

//输出：
//A
//A
//3s after
//B
//3s after
//B
```

这种方法的缺点

- 不同的 Future 之间的关系很难进行关联

- Future 的 get()方法实际上是阻塞的，直到子线程执行完毕。如果把上面代码中的注释删掉，则输出结果变为：

  ```java
  A
  3S after
  B
  task B completed
  A
  3S after
  B
  task B completed
  ```

### CompletableFuture

```Java
public class Test {
    public void A() throws ExecutionException, InterruptedException {
        System.out.println("A");
        //阿里巴巴规范手册不建议用 Executors 创建线程池
        ExecutorService executorService = Executors.newFixedThreadPool(5);
        CompletableFuture<String> completableFuture = CompletableFuture.supplyAsync(() -> {
            try {
                Thread.sleep(3000);
                System.out.println("3S after");
            } catch (InterruptedException e) {
                e.printStackTrace();
            }
            System.out.println("B");
            return "task B completed";
        }, executorService);
    }

    public static void main(String[] args) throws ExecutionException, InterruptedException {
        Test test = new Test();
        test.A();
        test.A();
    }
}

//输出：
//A
//A
//3s after
//B
//3s after
//B
```

