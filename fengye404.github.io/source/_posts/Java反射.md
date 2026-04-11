---
title: Java反射
typora-root-url: ./Java反射
date: 2022-04-14 15:43:07
tags:
---

# Java 反射

## 反射介绍

### 概念

- 反射机制允许程序在执行期间借助于 Reflection Api 获取任何类的内部信息（成员变量、构造器、成员方法等），并能直接操作任意对象的内部属性和方法。

- 当一个类被加载之后，就在堆内存的方法区中产生了一个相应的 Class 类型的对象（一个类只有一个Class对象），这个对象包含了完整的类的结构信息，可以通过这个对象看到类的结构。

- 加载到内存中的运行时类会缓存一段时间，在此时间之内，通过不同方式获取到的都是同一个运行时类。（即同一个Class类的对象）

### 反射相关类吧   

java.lang.Class：标识某个类加载后在堆中的对象

java.lang.reflect.Method：代表类的方法

java.lang.reflect.Field：代表类的成员变量

java.lang.reflect.Constructor：代表成员的构造方法

## Class类

1. Class 类也是类，继承 Object 类
2. Class 类的实例不是 new 出来的，而是在类被加载时由系统创建的
3. 对于某个类的 Class 类实例，内存是单例的，因为类只加载一次
4. 可以通过类的实例获取到类的 Class 实例
5. Class 实例存在于堆中

### Class类常用方法

Test类

```java
public class Test{
	public String test = "test";
    public void run(){
    }
}
```



```java
String classAllPath = "com.example.demo.Test";
//获取 Test 的 Class 对象
Class<?> aClass = Class.forName(classAllPath);

//通过 cls 创建 Test 的实例
Test test = aClass.getDeclaredConstructor().newInstance();
    
//通过反射获取属性(只能获取public)
Field testField = aClass.getField("test");
System.out.println(testField.get(test));

//通过反射给属性赋值
testField.set(test,"demo");

//通过反射调用方法
Method method = aClass.getMethod("run");
method.invoke(test);
```







```
Class类可以添加泛型
//方式一：调用运行时类的属性：class
Class clazz1 = Person.class;

//方式二：通过运行时类的对象的方法：getClass()
Person p1 = new Person();
Class clazz2 = p1.getClass();

//方式三：调用Class的静态方法：forName(String classPath)
Class.forName("com.example.demo.java.Person");//写类的全类名

//方式四：使用类加载器ClassLoader（仅作了解）
ClassLoader classLoader = ReflectionTest.class.getClassLoader();
classLoader.loadClass("com.example.demo.java.Person");
```

### 获取 Class 对象的方式

#### Class.forName()

前提：已知类的全类名，并且该类在类路径下

应用场景：用于配置文件，读取类全路径，加载类

```java
Class<?> aClass = Class.forName("com.example.demo.Test");
```

#### 类.class

前提：已知具体的类，通过类的 class 获取

应用场景：用于参数传递，比如通过反射得到对应构造器对象

```java
Class<?> aClass = Test.class;
```

#### 对象.getClass()

前提：已知某个类的实例

应用场景：通过创建好的对象，获取 Class 对象

```java
Test test = new Test();
Class<?> aClass = test.getClass();
```

#### 类加载器

```java
Test test = new Test();
ClassLoader classLoader = test.getClass().getClassLoader();
Class<?> aClass = classLoader.loadClass("com.example.demo.Test")
```

## 类加载

- 静态加载：**编译时**加载相关的类，`Person person = new Person()`
- 动态加载：**运行时**加载所需的类，`Class<?> clazz = Class.forName("Person")`

### 类加载过程：

![](http://fengye404.top/wp-content/uploads/2022/04/KRL6VBSUHE3M7P1Z8NU6.png)

#### 加载 Loading：

- 将 Java 字节码从不同数据源（class文件、jar包、网络）转化为二进制字节流加载到内存中，并为每个字节码中的类生成一个代表该类的 `java.lang.Class` 对象

#### 验证 Verification：

- 确保加载到内存中的二进制字节流符合当前 JVM 虚拟机的要求，并且不会危害 JVM 的安全

#### 准备 Preparation：

- 对静态变量分配内存并默认初始化

#### 解析 Resolution

- 将常量池内的符号引用替换为直接引用

#### 初始化 Initialization

- 编译期按照语句在源文件中出现的顺序，依次收集类中所有的静态变量的赋值和静态代码块中的语句进行合并执行（线程安全）

  例如：

  ```java
  public class Main{
  	public static void main(String[] agrs){
  		new Test();
  	}
  
  }
  
  class Test{
  	static{
  		System.out.println("static代码块被加载");
  		a = 300;
  	}
  	static int a = 100; 
  	
  	public Test(){
  		System.out.println("构造方法被调用");
  	}
  }
  
  # 执行顺序:
  # 加载Test类：
  # System.out.println("static代码块被加载");
  # int a = 300
  # a = 100
  # 构造方法调用：
  # System.out.println("构造方法被调用");
  ```

  
