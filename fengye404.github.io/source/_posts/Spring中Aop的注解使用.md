---
title: Spring中Aop的注解使用
typora-root-url: ./Spring中Aop的注解使用
date: 2021-09-09 15:55:34
tags:
---

## AOP的相关术语

#### 切面（Aspect）

切点+通知

#### 切点（Pointcut）

切点定义了通知功能被应用的范围。比如日志切面的应用范围就是所有接口，即所有controller层的接口方法。

#### 通知（Advice）

通知描述了切面要完成的工作以及何时执行。

- 前置通知（Before）：在目标方法调用前调用通知功能；
- 后置通知（After）：在目标方法调用之后调用通知功能，不关心方法的返回结果；
- 返回通知（AfterReturning）：在目标方法成功执行之后调用通知功能；
- 异常通知（AfterThrowing）：在目标方法抛出异常后调用通知功能；
- 环绕通知（Around）：通知包裹了目标方法，在目标方法调用之前和之后执行自定义的行为。

#### 连接点（JoinPoint）

通知功能被应用的时机。比如接口方法被调用的时候就是日志切面的连接点。

#### 引入（Introduction）

在无需修改现有类的情况下，向现有的类添加新方法或属性。

#### 织入（Weaving）

把切面应用到目标对象并创建新的代理对象的过程。

## Spring中使用注解创建切面

>相关注解：
>
>@Aspect：用于定义切面
>
>@Before：通知方法会在目标方法调用之前执行
>
>@After：通知方法会在目标方法返回或抛出异常后执行
>
>@AfterReturning：通知方法会在目标方法返回后执行
>
>@AfterThrowing：通知方法会在目标方法抛出异常后执行
>
>@Around：通知方法会将目标方法封装起来
>
>@Pointcut：定义切点表达式
>
>切点表达式：
>
>```
>execution( 方法修饰符 返回类型 方法所属的包.类名.方法名称(方法参数) )  
>"*"表示不限     ".."表示参数不限
>方法修饰符不写表示不限，不用"*" 
>```
>
>```
>//com.example.demo.controller包中所有类的public方法都应用切面里的通知
>execution(public * com.example.demo.controller.*.*(..))
>//com.example.demo.service包及其子包下所有类中的所有方法都应用切面里的通知
>execution(* com.example.demo.service..*.*(..))
>//com.example.demo.service.UserService类中的所有方法都应用切面里的通知
>execution(* com.example.demo.service.UserService.*(..))
>```

1、定义切面类Aspect

2、定义切点Pointcut

3、定义通知Advice

```java
@Aspect
@Component
@Slf4j
public class WebLogAspect {
    //表示com.example.demo.controller包下的所有方法
    @Pointcut("execution( * com.example.demo.controller.*.*(..))")
    public void myPointcut() {
    }

    @Around("myPointcut()")
    //环绕通知的限定参数：ProceedingJoinPoint
    public Object applicationLogger(ProceedingJoinPoint proceedingJoinPoint) throws Throwable {
        String methodName = proceedingJoinPoint.getSignature().getName();
        String className = proceedingJoinPoint.getTarget().getClass().toString();
        ObjectMapper objectMapper = new ObjectMapper();
        Object[] array = proceedingJoinPoint.getArgs();
        log.info("调用前:" + className + ":" + methodName + "args=" + objectMapper.writeValueAsString(array));
        //z
        Object object = proceedingJoinPoint.proceed();
        log.info("调用后:" + className + ":" + methodName + "args=" + objectMapper.writeValueAsString(array));
        return object;
    }
}
```



