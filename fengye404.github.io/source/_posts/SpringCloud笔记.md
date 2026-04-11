---
title: SpringCloud笔记
typora-root-url: ./SpringCloud笔记
date: 2022-10-06 15:46:32
tags:
---

## 前言

### 什么是SpringCloud？

Spring Cloud 被称为构建分布式微服务系统的“全家桶”，它并不是某一门技术，而是一系列微服务解决方案或框架的有序集合。它将市面上成熟的、经过验证的微服务框架整合起来，并通过 Spring Boot 的思想进行再封装，屏蔽调其中复杂的配置和实现原理，最终为开发人员提供了一套简单易懂、易部署和易维护的分布式系统开发工具包。

虽然 Spring Cloud 提供了很强大的功能，但是并没有提供所有的实现。其中的部分中间件只提供了统一的抽象API。不同厂商结合自身中间件，提供了自己的 Spring Cloud 套件。例如 `Spring Cloud Netflix` 、`Spring Cloud Alibaba`。（Netflix由于开源策略的调整，部分组件已经开始停止维护，因此不再适用于长久使用）

### 不同SpringCloud套件的常用组件

|            |                      Spring Cloud 官方                       | Spring Cloud Netflix |     Spring Cloud Alibaba     |
| :--------: | :----------------------------------------------------------: | :------------------: | :--------------------------: |
|  配置中心  |         Spring Cloud Config/<br />Spring Cloud Vault         |       Archaius       |            Nacos             |
|  注册中心  |                              --                              |        Eureka        |            Nacos             |
|  服务调用  |          RestTemplate/<br />Spring Cloud OpenFegin           |          --          |            Dubbo             |
|  负载均衡  |                  Spring Cloud Load Balancer                  |        Ribbon        |            Dubbo             |
|  服务容错  |                              --                              |       Hystrix        |           Sentinel           |
|    网关    |                     Spring Cloud Gateway                     |         Zuul         |              --              |
|  消息队列  | Spring Cloud Stream RabbitMQ/<br />Spring Cloud Stream Kafka |          --          | Spring Cloud Stream RocketMQ |
|  事件总线  |    Spring Cloud Bus RabbitMQ/<br />Spring Cloud Bus Kafka    |          --          |  Spring Cloud Bus RocketMQ   |
|  链路追踪  |                     Spring Cloud Sleuth                      |          --          |              --              |
| 分布式事务 |                              --                              |          --          |            Seata             |
| 分布式调度 |                              --                              |          --          |          SchedulerX          |

不同套件的组件之间可以互相混合使用。 

### 版本问题

SpringCloud和SpringBoot版本

| Release Train                                                | Boot Version                          |
| :----------------------------------------------------------- | :------------------------------------ |
| [2021.0.x](https://github.com/spring-cloud/spring-cloud-release/wiki/Spring-Cloud-2021.0-Release-Notes) aka Jubilee | 2.6.x, 2.7.x (Starting with 2021.0.3) |
| [2020.0.x](https://github.com/spring-cloud/spring-cloud-release/wiki/Spring-Cloud-2020.0-Release-Notes) aka Ilford | 2.4.x, 2.5.x (Starting with 2020.0.3) |
| [Hoxton](https://github.com/spring-cloud/spring-cloud-release/wiki/Spring-Cloud-Hoxton-Release-Notes) | 2.2.x, 2.3.x (Starting with SR5)      |
| [Greenwich](https://github.com/spring-projects/spring-cloud/wiki/Spring-Cloud-Greenwich-Release-Notes) | 2.1.x                                 |
| [Finchley](https://github.com/spring-projects/spring-cloud/wiki/Spring-Cloud-Finchley-Release-Notes) | 2.0.x                                 |
| [Edgware](https://github.com/spring-projects/spring-cloud/wiki/Spring-Cloud-Edgware-Release-Notes) | 1.5.x                                 |
| [Dalston](https://github.com/spring-projects/spring-cloud/wiki/Spring-Cloud-Dalston-Release-Notes) | 1.5.x                                 |

SpringCloudAlibaba和SpringCloud版本

> [版本说明 · alibaba/spring-cloud-alibaba Wiki (github.com)](https://github.com/alibaba/spring-cloud-alibaba/wiki/版本说明)

### SpringCloud环境搭建

**版本选择：**

​	SpringCloud：Hoxton.SR12

​	SpringBoot：2.3.12.RELEASE

​	SpringCloudAlibaba：2.2.9.RELEASE

**引入maven依赖**

```xml
<properties>
    <java.version>11</java.version>
    <spring-cloud.version>Hoxton.SR12</spring-cloud.version>
    <spring-cloud-alibaba.version>2.2.9.RELEASE</spring-cloud-alibaba.version>
</properties>

<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.cloud</groupId>
            <artifactId>spring-cloud-dependencies</artifactId>
            <version>${spring-cloud.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
        <dependency>
            <groupId>com.alibaba.cloud</groupId>
            <artifactId>spring-cloud-alibaba-dependencies</artifactId>
            <version>${spring-cloud-alibaba.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>
```

## 服务注册中心

### Eureka

属于 Spring Cloud Netflix 套件。不推荐：1、最新版本停止更新。2、注册中心的Server端还需要手动编写。

### Consul

服务端由 HashiCorp 公司用 Go 语言开发。不需要编写代码开发，只需要下载启动即可向其中注册服务。客户端由 Spring Cloud 提供。

#### 服务端

**下载安装**

```shell
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://rpm.releases.hashicorp.com/RHEL/hashicorp.repo
sudo yum -y install consul
```

**运行**

```shell
consul agent -dev -client 0.0.0.0
```

- `-dev` 表示以开发模式运行，是单节点。也可以用 `-server` 以服务模式运行，需要配置多节点。
- `-client 0.0.0.0` 表示外网访问

#### 客户端

**pom.xml 需要导入两个新依赖**

```xml
<dependency>
	<groupId>org.springframework.cloud</groupId>
	<artifactId>spring-cloud-starter-consul-discovery</artifactId>
</dependency>
<!-- 这个包是用做健康度监控的-->
<dependency>
	<groupId>org.springframework.boot</groupId>
	<artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
```

**修改配置文件 application.properties** 

```properties
server.port=8080
spring.application.name=consul-demo-1

# 指定注册的服务名
spring.cloud.consul.discovery.service-name=consul-demo
# 指定consul的ip和port
spring.cloud.consul.host=192.168.71.128
spring.cloud.consul.port=8500
# 是否使用ip注册。默认为false，使用hostname注册
spring.cloud.consul.discovery.prefer-ip-address=true
```

**启动类添加注解**

```java
@SpringBootApplication
@EnableDiscoveryClient
public class ConsulDemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(ConsulDemoApplication.class, args);
    }
}
```

**访问web管理页面**

启动SpringBoot，进入consul web页面（默认端口8500）查看当前注册的服务 

![image-20220924032449140](./202209240324263.png)

### Nacos

#### 服务端

**下载安装**

```shell
wget https://github.com/alibaba/nacos/releases/download/2.1.1/nacos-server-2.1.1.tar.gz

tar -xvf nacos-server-2.1.1.tar.gz
```

**启动**

```shell
cd nacos/bin

#启动 standalone表示单机模式，非集群
sh startup.sh -m standalone

#关闭
sh shutdown.sh
```

**访问web管理页面**

`http://192.168.71.128:8848/nacos`，默认用户名密码都是nacos

![image-20221003165237312](./202210031652418.png)

#### 客户端

**添加依赖**

```xml
<dependency>
    <groupId>com.alibaba.cloud</groupId>
    <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
</dependency>
```

**修改配置文件**

```properties
server.port=8088
spring.application.name=nacos-discovery-demo

# nacos server总地址，编写了这项即代表服务注册和配置管理都用这个地址（前提是同时引入了服务注册和配置管理依赖）
spring.cloud.nacos.server-addr=192.168.71.128:8848
# spring.cloud.nacos.discovery.server-addr=${spring.cloud.nacos.server-addr}

# 注册时的服务名
spring.cloud.nacos.discovery.service=nacos-discovery-demo
```

**入口类上的 @EnableDiscoveryClient 注解可加可不加**

启动服务查看效果：![image-20221004221453650](./202210042214781.png)

> 踩坑：nacos2.0之后添加了gRPC的通信方式，服务端和客户端需要额外开两个端口。默认为服务注册端口偏移1000和1001，即9848和9849

## 负载均衡组件

### Ribbon

Ribbon 是 Spring Cloud Netflix 中的一个负载均衡组件。Ribbon会根据所调用的服务的名称去服务注册中心获取对应的服务列表，并将服务列表在本地进行缓存，并且按照负载均衡策略进行调用。

consul client / nacos client 中自带 Ribbon 的依赖。

Ribbon 中提供了三种使用方式：DiscoveryClient、LoadBalanceClient、@LoadBalance。

**DiscoveryClient**

```java
@Autowired
private DiscoveryClient discoveryClient;

public void test(){
    //获取服务列表
    List<ServiceInstance> products = discoveryClient.getInstances("consul-demo");
    for (ServiceInstance product : products) {
      log.info("服务主机:[{}]",product.getHost());
      log.info("服务端口:[{}]",product.getPort());
      log.info("服务地址:[{}]",product.getUri());
      log.info("====================================");
}
```

**LoadBalanceClient**

```java
@Autowired
private LoadBalancerClient loadBalancerClient;

public void test(){
    //根据负载均衡策略选取某一个服务调用
    ServiceInstance product = loadBalancerClient.choose("consul-demo");
    log.info("服务主机:[{}]",product.getHost());
    log.info("服务端口:[{}]",product.getPort());
    log.info("服务地址:[{}]",product.getUri());
}
```

**@LoadBalance**

```java
//1.加在创建 RestTemplate Bean 的方法上
@Bean
@LoadBalanced
public RestTemplate getRestTemplate(){
  return new RestTemplate();
}

//2.注入RestTemplate
@Autowired
private RestTemplate restTemplate;

public void test(){
    //3.直接通过服务名调用
	String forObject = restTemplate.getForObject("http://consul-demo/test", String.class);
}
```

**修改负载均衡策略**

```properties
server.port=8082
spring.application.name=ribbon-demo

spring.cloud.consul.discovery.service-name=ribbon-demo
spring.cloud.consul.host=192.168.71.128
spring.cloud.consul.port=8500
spring.cloud.consul.discovery.prefer-ip-address=true

# 固定写法：
# {服务名}.ribbon.NFLoadBalancerRuleClassName=com.netflix.loadbalancer.{负载均衡策略}
# 表示当前这个服务访问调用其他服务时的负载均衡策略
consul-demo.ribbon.NFLoadBalancerRuleClassName=com.netflix.loadbalancer.RandomRule
```

Ribbon中提供的几种负载均衡策略：

- RoundRobinRule（轮训策略）：按顺序循环选择。
- RandomRule（随机策略）：随机选择。
- AvailabilityFilteringRule（可用过滤策略）：会先过滤由于多次访问故障而处于断路器跳闸状态的服务，还有并发的连接数量超过阈值的服务，然后对剩余的服务列表按照轮询策略进行访问。

- WeightedResponseTimeRule（响应时间加权策略）：根据平均响应的时间计算所有服务的权重，响应时间越快服务权重越大被选中的概率越高，刚启动时如果统计信息不足，则使用RoundRobinRule策略，等统计信息足够会切换回去。

- RetryRule（重试策略）：先按照RoundRobinRule的策略获取服务，如果获取失败则在制定时间内进行重试，获取可用的服务。

- BestAviableRule（最低并发策略）：会先过滤掉由于多次访问故障而处于断路器跳闸状态的服务，然后选择一个并发量最小的服务。

## 服务调用组件

### RestTemplate

需要直接通过写死的路径调用服务，虽然简单易用，但是可拓展性低。

### OpenFeign

由 Spring Cloud 官方推出的，基于 Netflix 的 Feign 进行二次封装开发的服务调用组件。OpenFeign 是一个声明式的伪 Http 客户端。OpenFeign 还支持 SpringMVC 的注解，支持可插拔的编码器和解码器，默认集成了 Ribbon。

#### 基础使用

例如要调用的接口（在 `consul-demo` 模块中）：

```java
@RestController
public class DemoController {
    @GetMapping("/test")
    public String test() {
        return "demo1";
    }
}
```

**添加依赖**

```xml
<dependency>
	<groupId>org.springframework.cloud</groupId>
	<artifactId>spring-cloud-starter-openfeign</artifactId>
</dependency>
```

**修改配置文件**

```properties
server.port=8083
spring.application.name=openfeign-demo

spring.cloud.consul.discovery.service-name=openfeign-demo
spring.cloud.consul.host=192.168.71.128
spring.cloud.consul.port=8500
spring.cloud.consul.discovery.prefer-ip-address=true
```

**启动类添加注解**

```java
@SpringBootApplication
@EnableDiscoveryClient
@EnableFeignClients
public class OpenFeignDemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(OpenFeignDemoApplication.class, args);
    }
}
```

**编写 OpenFeignClint 接口**

```java
//需要调用的服务的名称
@FeignClient("consul-demo")
public interface ConsulDemo1Client {
    //注解中填需要调用的接口的path
    @GetMapping("/test")
    String test();//返回值类型要和调用的接口的返回值类型一样
}
```

**直接调用 OpenFeignClint 接口**

```java
@RestController
public class DemoController {
    @Autowired
    private ConsulDemoClient consulDemoClient;

    @GetMapping("/test1")
    public String openFeignTest1() {
        //直接调用，发现默认用了轮询的负载均衡
        //说明OpenFeign集成了Ribbon
        return consulDemoClient.test();
    }
}
```

#### 传递参数

##### Get传递参数

###### query传参

需要调用的接口（在 `consul-demo` 模块中）

```java
@RestController
public class DemoController {
	@GetMapping("/paramTest1")
	//接口上的@RequestParam("name")可以省略
	public String paramTest1(@RequestParam("name") String name) {
		System.out.println(name);
		return "demo1";
	}
}
```

client

```java
//需要调用的服务的名称
@FeignClient("consul-demo")
public interface ConsulDemoClient {
    @GetMapping("/paramTest1")
    //client上的@RequestParam("name")不能省略，并且一定要写value属性
    String paramTest1(@RequestParam("name") String name);
}
```

调用client

```java
@RestController
public class DemoController {
    @Autowired
    private ConsulDemoClient consulDemoClient;

    @GetMapping("/test2")
    public String openFeignTest2(){
        return consulDemoClient.paramTest1("hello");
    }
}
```

###### path传参

需要调用的接口（在 `consul-demo` 模块中）

```java
@RestController
public class DemoController {
    @GetMapping("/paramTest2/{name}")
    public String paramTest2(@PathVariable("name") String name) {
        System.out.println(name);
        return "demo1";
    }
}
```

client

```java
//需要调用的服务的名称
@FeignClient("consul-demo")
public interface ConsulDemoClient {
    @GetMapping("/paramTest2/{name}")
    String paramTest2(@PathVariable("name") String name);
}
```

调用client

```java
@RestController
public class DemoController {
    @Autowired
    private ConsulDemoClient consulDemoClient;

    @GetMapping("/test3")
    public String openFeignTest3(){
        return consulDemoClient.paramTest2("hello");
    }
}
```

##### Post参数传递

###### json传参

需要调用的接口（在 `consul-demo` 模块中）

```java
@RestController
public class DemoController {
    @PostMapping("/postTest1")
    public String postTest1(@RequestBody Person person){
        return person.toString();
    }
}
```

client

```java
//需要调用的服务的名称
@FeignClient("consul-demo")
public interface ConsulDemoClient {
    @PostMapping("/postTest1")
    //待调用的接口是用@RequestBody即json接收参数的，因此调用的时候也要用@RequestBody
    String postTest1(@RequestBody Person person);
}
```

调用client

```java
@RestController
public class DemoController {
    @Autowired
    private ConsulDemoClient consulDemoClient;

    @GetMapping("/test4")
    public String openFeignTest4() {
        return consulDemoClient.postTest1(new Person("hello", 1));
    }
}
```

###### form传参

需要调用的接口（在 `consul-demo` 模块中）

```java
@RestController
public class DemoController {
    @PostMapping("/postTest1")
    public String postTest1(@RequestBody Person person){
        return person.toString();
    }
}
```

client

```java
//需要调用的服务的名称
@FeignClient("consul-demo")
public interface ConsulDemoClient {
    @PostMapping("/postTest1")
    //待调用的接口是用@RequestBody即json接收参数的，因此调用的时候也要用@RequestBody
    String postTest1(@RequestBody Person person);
}
```

调用client

```java
@RestController
public class DemoController {
    @Autowired
    private ConsulDemoClient consulDemoClient;

    @GetMapping("/test4")
    public String openFeignTest4() {
        return consulDemoClient.postTest1(new Person("hello", 1));
    }
}
```

#### 其他设置

##### 超时处理

默认情况下，OpenFeign进行调用时，如果1S未响应，则会直接报错。

```properties
feign.client.config.consul-demo.connectTimeout=5000  		
#配置指定服务连接超时时间

feign.client.config.consul-demo.readTimeout=5000		  	
#配置指定服务连接超时时间

#feign.client.config.default.connectTimeout=5000  		
#配置指定服务连接超时时间

#feign.client.config.default.readTimeout=5000			
#配置指定服务连接超时时间
```

##### 日志

开启日志

```properties
feign.client.config.consul-demo.loggerLevel=full  
#开启指定服务日志展示

#feign.client.config.default.loggerLevel=full  
#全局开启服务日志展示

logging.level.top.fengye.client=debug    
#指定feign调用客户端对象所在包,必须是debug级别
```

##### 负载均衡策略

openfeign 内置了 ribbon，因此配置负载均衡方法和 ribbon 相同

## 服务网关

网关（网关=路由转发+拦截器）作用：

- 统一所有微服务入口，实现请求路由转发和负载均衡。
- 在网关中对请求进行校验、鉴权等操作。

### Spring Cloud Gateway

#### 基础使用

**引入依赖**

> 注意 SpringCloudGateway 是基于webflux的，与传统的MVC冲突，因此需要排除 Spring-Boot-Stater-Web 依赖或者在配置文件中指定`spring.main.web-application-type=reactive`

```xml
<!--引入gateway网关依赖-->
<dependency>
  <groupId>org.springframework.cloud</groupId>
  <artifactId>spring-cloud-starter-gateway</artifactId>
</dependency>
```

**配置路由转发规则**

1. 在配置文件中配置

   ```yaml
   server:
     port: 8084
   spring:
     main:
       web-application-type: reactive
     application:
       name: springcloud-gateway-demo
     cloud:
       consul:
         discovery:
           service-name: springcloud-gateway-demo
           prefer-ip-address: true
         host: 192.168.71.128
         port: 8500
       gateway:
         routes:
           - id: user  # 路由id，没有固定规则但是需要唯一，建议和服务名对应
             uri: http://localhost:8080
             # SpringCloud Gateway 也集成了Ribbon，配置负载均衡策略的方式也相同
             # 如果需要负载均衡，可以写成 uri: lb://服务名
             predicates:
               - Path=/user/**
               
   
           - id: admin  #路由对象唯一标识
             uri: http://localhost:8081
             predicates:
               - Path=/admin/test,/admin/demo
   ```

2. 在配置类中配置

   ```java
   @Configuration
   public class GatewayConfig {
       @Bean
       public RouteLocator customRouteLocator(RouteLocatorBuilder builder) {
           return builder.routes()
                   .route("user",
                           r -> r.path("/user/**")
                                   .uri("http://localhost:8080"))
                   .route("admin",
                           r -> r.path("/admin/test","/admin/demo")
                                   .uri("http://localhost:8081"))
                   .build();
       }
   }
   ```

#### 断言

在之前的基础使用中，配置文件里配置了一项 `predicate` ，中文翻译叫断言，即路由转发的条件。

如果同时配置了多种predicate，则表示 `与` ，即全部满足时才触发。

除了之前介绍的 **Path** ，其他几种常用的predicate：

1. **After/Before/Between**：在指定时刻后/前/之间转发。例如 `After=2022-10-13T21:57:33.993+08:00[Asia/Shanghai]` 表示匹配时间为 `2022-10-13 21:57:33.993` 后/前/之间的请求。用 Between 的话则用 `,` 隔开两个时间。

2. **Host**：根据主机名进行匹配转发。例如 `Host=**.fengye404.top` 表示匹配域名为 `**.fengye404.top` 的请求。

3. **Method**：匹配指定的Http方法。例如 `Method=GET,POST` 表示匹配 GET 和 POST。

4. **Cookie**：请求包含指定的Cookie，并且其值等于指定的值（或满足指定的正则表达式）。例如 `Cookie=name,123` 表示匹配包含指定的Cookie并且其内容等于123的请求。

5. **Header**：与Cookie一致，区别在于匹配的是请求头。

6. **Query**：与Cookie一致，区别在于匹配的是请求参数。

7. **Weight**：这个断言不是匹配规则，而是负载均衡权重。例如有如下配置：

   ```yaml
   spring:
     cloud:
       gateway:
         routes:
           - id: user-1
             uri: http://localhost:8080
             predicates:
               - Path=/user/**
               - Weight=user,2
               
           - id: user-2 
             uri: http://localhost:8081
             predicates:
               - Path=/user/**
   			- Weight=user,1
               
   ```

   则表示三个请求，有两个会发送到user-1，一个会发送到user-2。

#### 过滤器

SpringCloud-Gateway中的过滤器和Spring中的过滤器类似。可以用于参数校验、权限校验、流量监控、日志输出、协议转换等。

##### 内置过滤器

使用方式同predicate。

```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: user-1
          uri: http://localhost:8080
          predicates:
            - Path=/user/**
          filters:
            - AddRequestHeader=token, 123
```

常见的内置过滤器：

1. **AddRequestHeader**：添加请求头。例如：`AddRequestHeader=token, 123`
2. **AddRequestParameter**：添加请求参数。
3. **AddResponseHeader**：添加响应头。
4. **PrefixPath**：添加前缀。例如：`PrefixPath=/test`
5. **StripPrefix**：去掉前缀。

##### 自定义全局过滤器

```java
@Configuration
public class CustomGlobalFilter implements GlobalFilter, Ordered {
    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        //相当于servlet的HttpRequest对象
        ServerHttpRequest request = exchange.getRequest();

        //相当于servlet的HttpRequest对象
        ServerHttpResponse response = exchange.getResponse();

        //相当于servlet filter的doFilter，即继续向后执行其他的filter
        System.out.println("请求发送前执行...");
        Mono<Void> filter = chain.filter(exchange);
        System.out.println("响应回来后执行...");

        return filter;
    }

    @Override
    //过滤器执行顺序，默认按照自然顺序。即 1 在 2之前执行
    //如果返回的是 -1 则表示在所有过滤器之前执行
    public int getOrder() {
        return 0;
    }
}
```

## 配置中心

配置中心顾名思义，就是将配置统一管理。日后需要修改某个服务的配置时，只需要在配置中心修改，即可让服务的每个实例自动同步，省去手动修改配置文件。

### Spring Cloud Config

Spring Cloud Config 的配置文件一般可以给Github等代码托管平台管理，需要修改配置文件时只需要到代码托管平台修改即可。

Spring Cloud Config 组件分为两块：server和client。server负责从代码托管平台将配置文件同步到本地仓库；client集成在服务中，负责在服务启动时从server同步配置文件。

#### Server

引入依赖

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-config-server</artifactId>
</dependency>
```

启动类添加注解

```java
@SpringBootApplication
@EnableDiscoveryClient
//添加为统一配置中心
@EnableConfigServer
public class SpringCloudcConfigServerDemoApplication {
    public static void main(String[] args) {
        SpringApplication.run(SpringCloudcConfigServerDemoApplication.class, args);
    }
}
```

修改配置文件

```yaml
server:
  port: 8085
spring:
  application:
    name: springcloud-config-server-demo
  cloud:
    consul:
      discovery:
        service-name: springcloud-config-server-demo
        prefer-ip-address: true
      host: 192.168.71.128
      port: 8500
  config:
    server:
      git:
        # 仓库url
        uri: https://gitee.com/fengye404/spring-cloud-config-test.git
        # 分支
        default-label: master
        username: ******
        password: ******
```

> 指定本地仓库位置
>
> spring.cloud.config.server.git.basedir=/localresp	
>
> 一定要是一个空目录,在首次会将该目录清空

#### Client

**引入依赖**

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-config-server</artifactId>
</dependency>
```

**在远程仓库中编写application.properties**

例如创建了两个配置文件：

springcloudconfigclientdemo-dev.properties

```properties
server.port=8086
spring.application.name=springcloud-config-client-demo

# 测试用例子
name=dev
```

springcloudconfigclientdemo-prod.properties

```properties
server.port=8085
spring.application.name=springcloud-config-client-demo

# 测试用例子
name=prod
```

**编写bootstrap.properties**

因为使用了配置中心，所以服务本地并没有application.properties，而bootstrap.properties用于指定这个服务作为配置中心的微服务的一些基础信息，例如注册中心地址、配置中心服务名等

```properties
# 注册中心的配置信息必须要写在服务自身的配置文件中
spring.cloud.consul.discovery.service-name=springcloud-config-client-demo
spring.cloud.consul.discovery.prefer-ip-address=true
spring.cloud.consul.host=192.168.71.128
spring.cloud.consul.port=8500


# 让当前服务去注册中心去找 config server
spring.cloud.config.discovery.enabled=true
# 告诉当前服务，config server的服务id
spring.cloud.config.discovery.service-id=springcloud-config-server-demo
# 指定从哪个分支拉取配置
spring.cloud.config.label=master
# 指定拉取的配置文件的名称
spring.cloud.config.name=springcloudconfigclientdemo
# 指定拉取的配置文件的环境
spring.cloud.config.profile=dev

# 上述配置表示去拉取springcloudconfigclientdemo-dev.properties
```

#### 手动刷新配置文件

使用配置中心的好处在于，如果后期一个服务有多个实例在运行，此时需要修改这个服务的配置文件，就不需要一个个地手动给每个实例修改，而只需要修改配置中心中的配置文件，再由每个实例去刷新配置文件即可。

**接口类上添加注解**

```java
@RestController
@RefreshScope
@Slf4j
public class TestController {
    @Value("${name}")
    private String name;
    @GetMapping("/test/test")
    public String test(){
      log.info("当前加载配置文件信息为:[{}]",name);
      return name;
    }
}
```

**配置文件添加web暴露**

```properties
management.endpoints.web.exposure.include=*          
#开启所有web端点暴露
```

**手动调用刷新配置接口完成刷新**

```shell
curl -X POST http://localhost:9099/actuator/refresh
```

### Nacos

Nacos 作为统一配置中心，会自行创建版本库，因此不需要借助其他代码托管平台。 

#### Server

和前面的服务注册中心的 nacos server 一样启动即可

#### Client

**在 Server 添加配置文件**

![image-20221005223117406](./202210052231518.png)

Data ID即文件名，Nacos强制要求文件名需要带有环境名。例如 `application-prod.properties` 中的prod。

**修改配置文件**

```xml
<dependency>
    <groupId>com.alibaba.cloud</groupId>
    <artifactId>spring-cloud-starter-alibaba-nacos-discovery</artifactId>
</dependency>
<dependency>
    <groupId>com.alibaba.cloud</groupId>
    <artifactId>spring-cloud-starter-alibaba-nacos-config</artifactId>
</dependency>
```

**编写bootstrap.properties**

```properties
# 注册时的服务名
spring.cloud.nacos.discovery.service=nacos-config-demo

# nacos server总地址，编写了这项即代表服务注册和配置管理都用这个地址（前提是引入了服务注册/配置管理依赖）
# spring.cloud.nacos.discovery.server-addr=${spring.cloud.nacos.server-addr}
# spring.cloud.nacos.config.server-addr=${spring.cloud.nacos.server-addr}
spring.cloud.nacos.server-addr=192.168.71.128:8848

# 当前服务所属的 namespace 的id，不填则为 public
spring.cloud.nacos.config.namespace=public
# 当前服务所属的 group ，默认为 DEFAULT_GROUP
spring.cloud.nacos.config.group=DEFAULT_GROUP


# nacos server 中的 data id = prefix + environment + file-extension

# 第一种获取配置文件的方式：
# name = prefix + environment
spring.cloud.nacos.config.name=application-prod
spring.cloud.nacos.config.file-extension=properties

# 第二种获取配置文件的方式：
# spring.cloud.nacos.config.prefix=nacos_config_demo
# spring.cloud.nacos.config.environment=prod
# spring.cloud.nacos.config.file-extension=properties
```

#### 自动刷新配置

```java
@RestController
//接口上添加注解实现自动刷新
@RefreshScope
public class TestController {

    @Value("${test-attribute}")
    private String testAttribute;

    @GetMapping("/test")
    public String test() {
        return testAttribute;
    }
}
```

#### 数据持久化

nacos的配置文件默认存放在nacos内置的derby数据库中。推荐在生产情况下，使用MySQL数据库来持久化

**创建并初始化数据库**

数据库编码必须为UFT-8。初始化的sql文件为nacos安装目录中的conf/nacos-mysql.sql。

**修改nacos配置文件**

配置文件为nacos安装目录中的conf/properties。

```properties
spring.datasource.platform=mysql

db.num=1
db.url.0=jdbc:mysql://127.0.0.1:3306/nacos?characterEncoding=utf8&connectTimeout=1000&socketTimeout=3000&autoReconnect=true&useUnicode=true&useSSL=false&serverTimezone=UTC
db.user.0=用户名
db.password.0=密码
```

然后重启nacos即可。注意修改持久化数据库后，原来的配置文件不会自动导入到新数据库中，记得手动备份导入。
