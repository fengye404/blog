---
title: RestTemplate的简单使用
typora-root-url: ./RestTemplate的简单使用
date: 2021-09-18 15:53:35
tags:
---

### 什么是RestTemplate

>RestTemplate 是 Spring 提供的一个Http请求工具。它支持常见的Rest请求方案的模板，例如 GET 请求、POST 请求、PUT 请求、DELETE 请求以及一些通用的请求执行方法 exchange 以及 execute。
>
>说白了，它的功能就类似 HttpClient。
>
>在Spring项目中，使用 RestTemplate 发送 Http 请求无疑比 HttpClient 更加方便。
>
>（但由于 RestTemplate 是阻塞、同步的，因此在面对大批请求时可能会有性能损失。因此在Spring5.x 以后，出现了 `WebClient` 来替代 RestTemplate）

### 发起Get请求

get请求都需要在url后面手动拼接上参数

#### getForObject

获取响应对象

```java
@RestController
public class UserController {

    @Autowired
    RestTemplate restTemplate;

    @Bean
    public RestTemplate getRestTemplate() {
        return new RestTemplate();
    }

    @GetMapping("/id")
    public User getById(Integer id) {
        User user = new User(id, "username", "password", "role");
        return user;
    }
    
    @GetMapping("/test")
    public User getTest(Integer id) {
        //请求的url,注意后面要手动拼接上请求参数
        String url = "http://localhost:8080/id?id={id}";
        //请求参数
        Map<String, Object> params = Map.of("id", 1);
        //getForObject的第二个参数是返回值的类型
        User user = restTemplate.getForObject(url, User.class, params);
        System.out.println("RestTemplate调用/id接口");
        return user;
    }
}
```

#### getForEntity

获取响应对象、http状态码、请求头等详细信息

```java
@RestController
public class UserController {

    @Autowired
    RestTemplate restTemplate;

    @Bean
    public RestTemplate getRestTemplate() {
        return new RestTemplate();
    }

    @GetMapping("/id")
    public User getById(Integer id) {
        User user = new User(id, "username", "password", "role");
        return user;
    }

    @GetMapping("/test")
    public User getTest(Integer id) {
        String url = "http://localhost:8080/id?id={id}";
        Map<String, Object> params = Map.of("id", 1);
        ResponseEntity<User> responseEntity = restTemplate.getForEntity(url, User.class, params);
        System.out.println("RestTemplate调用/id接口");
        
		//额外获取的信息
        HttpStatus statusCode = responseEntity.getStatusCode();
        int statusCodeValue = responseEntity.getStatusCodeValue();
        HttpHeaders headers = responseEntity.getHeaders();

        //getBody()可以获取响应对象
        return responseEntity.getBody();
    }
}
```

### 发起Post请求

#### postForObject

##### 传递key/value形式的参数

与Get请求不同，Post请求中传参的Map必须是MultiValueMap

```java
@RestController
public class UserController {

    @Autowired
    RestTemplate restTemplate;

    @Bean
    public RestTemplate getRestTemplate() {
        return new RestTemplate();
    }

    @PostMapping("/id")
    public User postUser(int id, String username, String password, String role) {
        return new User(id, username, password, role);
    }
    
//也可以这也获取参数
//但是不能加@RequestBody注解，因为传递的参数不是放在body里的
//    @PostMapping("/id")
//    public User postUser(User user) {
//        return user;
//    }

    @PostMapping("/test")
    public User postTest() {
        String url = "http://localhost:8080/id";
        MultiValueMap<String, Object> params = new LinkedMultiValueMap<>();
        params.add("id", 1);
        params.add("username", "username");
        params.add("password", "password");
        params.add("role", "role");
        User user = restTemplate.postForObject(url, params, User.class);
        System.out.println("RestTemplate调用/id接口");
        return user;
    }
}
```

##### 传递json数据

```java
@RestController
public class UserController {

    @Autowired
    RestTemplate restTemplate;

    @Bean
    public RestTemplate getRestTemplate() {
        return new RestTemplate();
    }

    @PostMapping("/id")
    public User postUser(@RequestBody User user) {
        return user;
    }

    @PostMapping("/test")
    public User postTest() {
        String url = "http://localhost:8080/id";
        User params = new User(1, "username", "password", "role");
        User user = restTemplate.postForObject(url, params, User.class);
        System.out.println("RestTemplate调用/id接口");
        return user;
    }
}
```

#### postForEntity

postForEntity 和 postForObject 的区别就相当于 getForEntity 与 getForObject 的区别

不再赘述

#### postForLocation(不常用)

postForLocation 方法的返回值是一个 Uri 对象，因为 POST 请求一般用来添加数据，有的时候需要将刚刚添加成功的数据的 URL 返回来，此时就可以使用这个方法，一个常见的使用场景如用户注册功能，用户注册成功之后，可能就自动跳转到登录页面了，此时就可以使用该方法。

**注意：postForLocation 方法返回的 Uri 实际上是指响应头的 Location 字段，所以，provider 中 register 接口的响应头必须要有 Location 字段（即请求的接口实际上是一个重定向的接口），否则 postForLocation 方法的返回值为null。**



> 参考博客：https://blog.csdn.net/jinjiniao1/article/details/100849237
>
> [Java RestTemplate传递参数 - 威威超酷 - 博客园 (cnblogs.com)](https://www.cnblogs.com/wwct/p/12325173.html)

