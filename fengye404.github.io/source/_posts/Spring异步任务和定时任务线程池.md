---
title: Spring异步任务和定时任务线程池
typora-root-url: ./Spring异步任务和定时任务线程池
date: 2022-10-19 15:47:11
tags:
---

## 前言

我们都知道在Spring中，想要启用异步任务和定时任务非常简单，只要在配置类或者启动类上添加`@EnableAsync`和`@EnableScheduling`，然后在对应方法上添加`@Async`和`@Schedule`即可。那么`@Async`和`@Schedule`默认是在什么线程池中运行的呢？默认的线程池是什么配置？如何修改其配置？如何自定义线程池？

## 异步任务执行器 TaskExecutor

异步任务执行器的接口是 `TaskExecutor` 。

```java
@FunctionalInterface
public interface TaskExecutor extends Executor {
	@Override
	void execute(Runnable task);
}
```

`TaskExecutor` 继承了 JDK 的 `Executor`（即平时经常使用的 `ExecutorService` 的父接口）。`TaskExecutor` 有很多实现类，Spring Boot默认提供的实现类是 `ThreadPoolTaskExecutor`，默认的配置：

核心线程数：8，最大线程数：Integet.MAX_VALUE，队列使用LinkedBlockingQueue，队列容量：Integet.MAX_VALUE，空闲线程保留时间：60s，线程池拒绝策略：AbortPolicy。

### 修改默认线程池配置

在 SpringBoot 中可以通过 application.properties 修改其配置

```properties
#核心线程数
spring.task.execution.pool.core-size=200
#最大线程数
spring.task.execution.pool.max-size=1000
#空闲线程保留时间
spring.task.execution.pool.keep-alive=3s
#队列容量
spring.task.execution.pool.queue-capacity=1000
#线程名称前缀
spring.task.execution.thread-name-prefix=my-task-thread-pool-
```

### 自定义线程池

#### 添加自定义线程池

可以添加一个Executor的实现类的Bean，同时在使用 `@Aysnc` 时指定调用哪个线程池执行。例如：

```java
@Configuration
public class TaskExecutorConfig {
    @Bean
    public Executor myTaskAsyncPool() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        //核心线程池大小
        executor.setCorePoolSize(10);
        //最大线程数
        executor.setMaxPoolSize(100);
        //队列容量
        executor.setQueueCapacity(1000);
        //活跃时间
        executor.setKeepAliveSeconds(60);
        //线程名字前缀
        executor.setThreadNamePrefix("MyExecutor-");
 
        // setRejectedExecutionHandler：当pool已经达到max size的时候，如何处理新任务
        // CallerRunsPolicy：不在新线程中执行任务，而是由调用者所在的线程来执行
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(60);
        executor.initialize();
        return executor;
    }
}

@Service
public class TestService{
    @Aysnc("myTaskAsyncPool")
    public void test(){
        System.out.println("test");
    }
}
```

#### 修改默认线程池

如果想把添加的线程池作为默认执行的线程池而不用每次都在 `@Async` 时指定，可以实现 AsyncConfigurer 接口。

```java
@Configuration
public class TaskExecutorConfig implements AsyncConfigurer {
    @Override
    public Executor getAsyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        //核心线程池大小
        executor.setCorePoolSize(10);
        //最大线程数
        executor.setMaxPoolSize(100);
        //队列容量
        executor.setQueueCapacity(1000);
        //活跃时间
        executor.setKeepAliveSeconds(60);
        //线程名字前缀
        executor.setThreadNamePrefix("MyExecutor-");
 
        // setRejectedExecutionHandler：当pool已经达到max size的时候，如何处理新任务
        // CallerRunsPolicy：不在新线程中执行任务，而是由调用者所在的线程来执行
        executor.setRejectedExecutionHandler(new ThreadPoolExecutor.CallerRunsPolicy());
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(60);
        executor.initialize();
        return executor;
    }
}

@Service
public class TestService{
    @Aysnc
    public void test(){
        System.out.println("test");
    }
}
```

## 定时任务执行器 TaskScheduler

定时任务执行器的接口是 `TaskScheduler` 。`ThreadPoolTaskScheduler` 是它的一个重要实现，也是SpringBoot提供的默认定时任务线程池。需要注意的是，SpringBoot提供的 `ThreadPoolTaskScheduler` 默认线程池大小为1，因此如果不对定时任务线程池进行额外配置，定时任务都是串行排队执行的。在某些场景下可能导致定时任务并没有按时执行等情况。当然，也可以配合@Async，将定时任务都提交给异步线程池去执行，但是可能会遇到新的问题，例如：

```java
@Component
public class TestTask {
    @Scheduled(cron = "*/5 * * * * ?")
    public void test1() throws InterruptedException {
        Thread.sleep(10000);        //模拟定时任务执行时长
    }
 
    @Scheduled(cron = "*/5 * * * * ?")
    public void test2() {
		//普通任务
    }
}
```

在上面的代码中，如果希望test1()之间是串行排队执行的话，即上一个test1()执行完之后，再执行下一个test1()，@Async就无法实现了。但是配置了定时任务线程池后，由于每个定时任务是由同一个线程来执行的，因此可以实现这样的需求。

### 修改默认线程池配置

```properties
spring.task.scheduling.pool.size=10
spring.task.scheduling.thread-name-prefix=my-scheduling-thread-pool-
```

### 自定义默认线程池

直接添加一个新的 `TaskScheduler` 的 Bean，覆盖 Spring 默认提供的 `ThreadPoolTaskScheduler` :

```java
@Configuration
public class TaskScheduleConfig{
    @Bean
    public TaskScheduler getAsyncExecutor() {
        ThreadPoolTaskScheduler threadPoolTaskScheduler  = new ThreadPoolTaskScheduler();
        // 配置线程池大小
        threadPoolTaskScheduler.setPoolSize(10);
        // 设置线程名
        threadPoolTaskScheduler.setThreadNamePrefix("my-scheduling-thread-pool-");
    }
}
```

或者实现 `SchedulingConfigurer` ，向其中注册新的 `TaskScheduler` :

```java
@Configuration
public class ScheduleConfig implements SchedulingConfigurer {

    @Override
    public void configureTasks(ScheduledTaskRegistrar taskRegistrar) {
        taskRegistrar.setScheduler(taskScheduler());
    }

    @Bean
    public TaskScheduler taskScheduler() {
        ThreadPoolTaskScheduler threadPoolTaskScheduler = new ThreadPoolTaskScheduler();
        // 配置线程池大小
        threadPoolTaskScheduler.setPoolSize(10);
        // 设置线程名
        threadPoolTaskScheduler.setThreadNamePrefix("my-scheduling-thread-pool-");
        return threadPoolTaskScheduler;
    }
}
```

## 易混淆概念

几个容易混淆的概念：

- `Executor`：JDK提供的用于封装 **线程（池）执行某个操作** 的执行器接口
- `ExecutorService`：JDK提供的对 `Executor` 进一步封装的接口，用于执行普通线程池任务
- `ScheduledExecutorService`：JDK提供的对 `Executor` 进一步封装的接口，用于执行定时任务
- `ThreadPoolExecutor`：JDK提供的 `ExecutorService` 的实现类，也是`Executors.newFixedThreadPool(10)`之类的Executors工具类的返回
- `ScheduledThreadPoolExecutor`：JDK提供的 `ExecutorService` 的实现类



- `TaskExecutor`：Spring提供的用于封装异步任务线程池的执行器接口，本质和 `Executor` 相同
- `TaskSchedule`：Spring提供的用于封装定时任务线程池的执行器接口
- `ThreadPoolTaskExecutor`：Spring提供的 `TaskExecutor` 的实现类，本质也是对 `ThreadPoolExecutor` 的封装
- `ThreadPoolTaskScheduler`：Spring提供的 `TaskSchedule` 的实现类，本质也是对 `ScheduledThreadPoolExecutor` 的封装





> 参考：[默认线程池 – Spring Boot教程(21) | 闷瓜蛋子的BLOG (fookwood.com)](https://fookwood.com/spring-boot-tutorial-21-executor)

