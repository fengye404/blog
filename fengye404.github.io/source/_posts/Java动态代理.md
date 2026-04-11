---
title: Java动态代理
typora-root-url: ./Java动态代理
date: 2022-03-12 15:40:15
tags:
---

动态代理实现：

1、JDK 动态代理

​	用 Java 反射包中的类和接口实现动态代理

2、CGLIB 动态代理

​	通过第三方库 CGLIB ，以继承类的方式实现动态代理

## JDK 代理

***由于底层机制的缘故，被代理的目标类必须实现至少一个接口***

- 创建被代理的目标类以及其实现的接口
- 创建 `InvocationHandler` 接口的实现类，在 `invoke()` 中完成要代理的功能
- 用 `Proxy.newInstance() `动态地构造出代理对象



Hello （被代理的目标类实现的接口）

```java
public interface Hello {
    void sayHello();

    int plus(int a, int b);
}
```

HelloImpl （被代理的目标类）

```java
public class HelloImpl implements Hello {

    @Override
    public void sayHello() {
        System.out.println("sayHello方法被调用");
    }

    @Override
    public int plus(int a, int b) {
        int c = a + b;
        System.out.println("plus方法被调用");
        System.out.println("返回值为" + c);
        return c;
    }
}
```

MyProxyHandler （InvocationHandler的实现类）

```java
public class MyProxyHandler implements InvocationHandler {

    private Object target = null;

    /**
     * 构造方法中传入被代理的对象
     *
     * @param target
     */
    public MyProxyHandler(Object target) {
        this.target = target;
    }

    /**
     * 需要代理的功能
     *
     * @param proxy  JDK自动创建的代理的对象
     * @param method 被代理的对象的方法（哪个方法被调用，这里的 method 就是那个方法）
     * @param args   被代理的方法的参数
     * @return
     * @throws Throwable
     */
    @Override
    public Object invoke(Object proxy, Method method, Object[] args) throws Throwable {

        //在执行目标方法前，做一系列增强操作
        before();

        System.out.println(method);

        //执行目标方法，获取返回值
        Object res = null;
        res = method.invoke(target, args);

        //在执行目标方法后，做一系列增强操作
        after();

        return res;
    }

    public void before() {
        System.out.println("before");
    }

    public void after() {
        System.out.println("after");
    }
}

```

Main （主方法）

```java
public class Main {
    public static void main(String[] args) {
        
        //通过 被代理的目标类 和 InvocationHandler的实现类
        //构造出代理对象
        HelloImpl helloImpl = new HelloImpl();
        MyProxyHandler myProxyHandler = new MyProxyHandler(helloImpl);
        Hello helloProxy = (Hello) Proxy.newProxyInstance(helloImpl.getClass().getClassLoader(),
                helloImpl.getClass().getInterfaces(),
                myProxyHandler);
        
        helloProxy.sayHello();
        System.out.println("==========");
        helloProxy.plus(1, 1);
    }
}

//输出
//before
//public abstract void Hello.sayHello()
//sayHello方法被调用
//after
//==========
//before
//public abstract int Hello.plus(int,int)
//plus方法被调用
//返回值为2
//after
```



JDK 代理生成的代理对象实际上是在原对象的基础上，给每个方法都用 `invoke()` 进行了加强

相较于静态代理，使用少量的代码就可以完成增强效果

## CGLIB 代理

需要导入jar包：核心包和依赖包（spring_core.jar已经集成了这两个包，因此，导入此包即可）

子类是在调用的时候才生成的

使用目标对象的子类的方式实现的代理，它是在内存中构建一个子类对象从而实现对目标对象功能的扩展，能够在运行时动态生成字节码，可以解决目标对象没有实现接口的问题

缺点：被final或static修饰的类不能用cglib代理，因为它们不会被拦截，不会执行目标对象的额外业务方法



>[Java 动态代理详解 - whirlys - 博客园 (cnblogs.com)](https://www.cnblogs.com/whirly/p/10154887.html#:~:text=Java 动态代理详解. 动态代理在Java中有着广泛的应用，比如Spring,AOP、Hibernate数据查询、测试框架的后端mock、RPC远程调用、Java注解对象获取、日志、用户鉴权、全局性异常处理、性能监控，甚至事务处理等。. 本文主要介绍Java中两种常见的动态代理方式：JDK原生动态代理和CGLIB动态代理。. 由于Java动态代理与java反射机制关系紧密，请读者确保已经了解了Java反射机制 )

