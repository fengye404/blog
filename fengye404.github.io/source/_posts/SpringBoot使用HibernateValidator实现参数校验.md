---
title: SpringBoot使用HibernateValidator实现参数校验
typora-root-url: ./SpringBoot使用HibernateValidator实现参数校验
date: 2021-09-10 15:54:52
tags:
---

## Hibernate Validator

### 依赖

Hibernate Validator是Spring Boot集成的参数校验框架；

但从Spring Boot 2.3版本开始默认移除了校验功能，如果想要开启的话需要添加如下依赖。

```
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-validation</artifactId>
</dependency>
```

### 常用注解

- @Null：被注释的属性必须为null；
- @NotNull：被注释的属性不能为null；
- @AssertTrue：被注释的属性必须为true；
- @AssertFalse：被注释的属性必须为false；
- @Min：被注释的属性必须大于等于其value值；
- @Max：被注释的属性必须小于等于其value值；
- @Size：被注释的属性必须在其min和max值之间；
- @Pattern：被注释的属性必须符合其regexp所定义的正则表达式；
- @NotBlank：被注释的字符串不能为空字符串；
- @NotEmpty：被注释的属性不能为空；
- @Email：被注释的属性必须符合邮箱格式。
- @PastOrPresent：必须是过去或现在的时间

### 使用注解实现校验

pojo类：

```java
@Data
@AllArgsConstructor
@NoArgsConstructor
public class Account {
    private int id;
    @NotNull(message = "用户名不能为空")
    private String username;
    @NotNull(message = "密码不能为空")
    private String password;
    @NotNull(message = "角色不能为空")
    private String role;
    private Date createTime;
    private boolean enable;

    public Account(String username, String password, String role, Date createTime, boolean enable) {
        this.username = username;
        this.password = password;
        this.role = role;
        this.createTime = createTime;
        this.enable = enable;
    }
}
```

controller类：

```java
@RestController
public class AccountController {

    @Autowired
    private JwtUtil jwtUtil;
    @Autowired
    AccountService accountService;

    @PostMapping("register")
    //添加注解@Valid开启校验
    public Account register(@Valid @RequestBody Account account) {
        return accountService.register(account);
    }
}
```

当传入参数不符合参数规范时，会抛出异常。在这个框架中有个默认的异常处理类DefaultHandlerExceptionResolver。

当传入的json中的username为空，异常信息：

>2021-09-10 15:40:25.749  WARN 22228 --- [nio-8080-exec-2] .w.s.m.s.DefaultHandlerExceptionResolver : Resolved [org.springframework.web.bind.MethodArgumentNotValidException: Validation failed for argument [0] in public com.example.demo.pojo.Account com.example.demo.controller.AccountController.register(com.example.demo.pojo.Account): [Field error in object 'account' on field 'username': rejected value [null]; codes [NotNull.account.username,NotNull.username,NotNull.java.lang.String,NotNull]; arguments [org.springframework.context.support.DefaultMessageSourceResolvable: codes [account.username,username]; arguments []; default message [username]]; default message [用户名不能为空]] ]

### 自定义异常处理

```java
@RestControllerAdvice
@Slf4j
public class GlobalExceptionHandler {
    
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public Result<ResultCode> handlerValidationException(MethodArgumentNotValidException e) {
        log.error("参数校验异常", e);
        //流处理，获取错误信息
        String messages = e.getBindingResult().getAllErrors().stream()
                .map(ObjectError::getDefaultMessage)
                .collect(Collectors.joining("\n"));
        return Result.failure(messages);
    }
}
```

### 级联校验

```java
public class Employee{
    @Null
    private Integer id;
    @NotNull
    private String name;
    @Valid
    private Department department;
    @Valid
    private List<Group> groups;
    //或者可以这样写：
    //private List<@Valid Group> groups;
}
```

在级联的属性上要加@Valid

### 在其他地方实现校验

@Valid加在Controller中，抛出的异常是`MethodArgumentNotValidException`

而加在其他地方，抛出的异常却是`ConstraintViolationException`

在做全局异常处理的时候要注意区别。

### 分组校验

例如上面的Employee类，我们想要它在不同的情况下有不同的校验规则，这时就需要用到分组校验

1、创建一个分组类，里面添加一些内部接口

```java
public class ValidationGroups {
    public interface insertNeed {
    }

    public interface selectNeed {
    }

    public interface updateNeed {
    }
}
```

2、为不同的情况添加不同的分组

```java
public class Employee{
    
    //用之前的结构来表示分组
    @Null(groups = ValidationGroups.insertNeed.class)
    @NotNull(groups = ValidationGroups.selectNeed.class)
    private Integer id;
    
    //一个注解可以s
    @NotNull(groups = ValidationGroups.insertNeed.class,ValidationGroups.selectNeed.class)
    private String name;
    
    @Valid(groups = ValidationGroups.insertNeed.class)
    private Department department;
    
    @Valid(groups = ValidationGroups.insertNeed.class)
    private List<Group> groups;
}
```

3、在需要校验时用@Validated标识需要使用的分组规则

```java
@RestController
public class AccountController {

    @PostMapping("test")
    public void test(@RequestBody @Validated(ValidationGroups.insertNeed.class) Employee Employee) {
        ...
    }
}
```

