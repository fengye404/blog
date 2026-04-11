---
title: RabbitMQ笔记
typora-root-url: ./RabbitMQ笔记
date: 2021-08-28 15:51:30
tags:
---

## docker安装RabbitMQ

```bash
docker run \
-d --name myrabbitmq \
-p 5672:5672 -p 15672:15672 \
-v rabbitmqData:/var/lib/rabbitmq \
-e RABBITMQ_DEFAULT_USER=username \
-e RABBITMQ_DEFAULT_PASS=password \
rabbitmq:management
```

## 几种基础模型

### 基础生产者与消费者模型

- 一对一
- 生产者生产消息后放入消息队列，消费者从队列中获得消息后进行消费。



生产者代码

```java
public class Provider {

    @Test
    public void testSendMessage() throws IOException, TimeoutException {
        //创建连接mq的连接工厂对象
        ConnectionFactory connectionFactory = new ConnectionFactory();
        //设置连接rabbitmq主机
        connectionFactory.setHost("123.56.2.36");
        //设置端口号
        connectionFactory.setPort(5672);
        //设置连接哪个虚拟主机
        connectionFactory.setVirtualHost("/ems");
        //设置访问虚拟主机的用户名和密码
        connectionFactory.setUsername("admin");
        connectionFactory.setPassword("admin");

        //获取连接对象
        Connection connection = connectionFactory.newConnection();

        //获取连接中的通道对象
        Channel channel = connection.createChannel();

        //通道绑定对应的消息队列
        //参数1:队列名称 如果队列不存在则自动创建
        //参数2:队列是否持久化 (不持久化则mq重启会被删除)
        //参数3:队列是否独占
        //参数4:是否在消费完成后自动删除队列
        //参数5:附加参数
        channel.queueDeclare("hello",true,false,false,null);

        //发布消息
        //参数1:交换机名称
        //参数2:队列名称
        //参数3:传递消息的额外设置(PERSISTENT_TEXT_PLAIN表示消息也会持久化)
        //参数4:消息的具体内容(byte数组)
        channel.basicPublish("","hello",MessageProperties.PERSISTENT_TEXT_PLAIN,"hello rabbitmq".getBytes());

        channel.close();
        connection.close();
    }
}
```

消费者代码

```java
public class Customer {
    @Test
    public void testConsume() throws IOException, TimeoutException {
        //创建连接mq的连接工厂对象
        ConnectionFactory connectionFactory = new ConnectionFactory();
        //设置连接rabbitmq主机
        connectionFactory.setHost("123.56.2.36");
        //设置端口号
        connectionFactory.setPort(5672);
        //设置连接哪个虚拟主机
        connectionFactory.setVirtualHost("/ems");
        //设置访问虚拟主机的用户名和密码
        connectionFactory.setUsername("admin");
        connectionFactory.setPassword("admin");

        //创建连接对象
        Connection connection = connectionFactory.newConnection();

        //创建通道
        Channel channel = connection.createChannel();

        //通道绑定对应的消息队列
        channel.queueDeclare("hello", true, false, false, null);

        //消费消息
        //参数1:队列名称
        //参数2:是否开启消息自动确认
        //参数3:消费时的回调接口
        channel.basicConsume("hello", true, new DefaultConsumer(channel) {
            //最后一个参数:消息队列中取出的消息
            @Override
            public void handleDelivery(String consumerTag, Envelope envelope, AMQP.BasicProperties properties, byte[] body) throws IOException {
                System.out.println(new String(body));
            }
        });
        
        //消费者一直处于监听状态，不需要关闭
    }
}
```

把其中创建连接的代码提取成工具类

```java
public class RabbitMQConnectionUtil {

    private static ConnectionFactory connectionFactory = new ConnectionFactory();

    //定义提供连接对象的方法
    public static Connection getConnection() {
        try {
            connectionFactory = new ConnectionFactory();
            //设置连接rabbitmq主机
            connectionFactory.setHost("123.56.2.36");
            //设置端口号
            connectionFactory.setPort(5672);
            //设置连接哪个虚拟主机
            connectionFactory.setVirtualHost("/ems");
            //设置访问虚拟主机的用户名和密码
            connectionFactory.setUsername("admin");
            connectionFactory.setPassword("admin");
            return connectionFactory.newConnection();
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    //关闭通道和关闭连接的方法
    public static void closeConnectionAndChanel(Channel channel, Connection connection) {
        try {
            if (channel != null)
                channel.close();
            if (connection != null)
                connection.close();
        } catch (IOException e) {
            e.printStackTrace();
        } catch (TimeoutException e) {
            e.printStackTrace();
        }
    }
}
```

### 工作队列模型

- 多个消费者对应一个队列，防止消息处理费事时，消息的堆积

- 默认是轮询执行

  可以通过设置消费者每次只能消费一个消息并且手动确认消息来实现“能者多劳”

  ```java
  //每次只消费一个
  //channel.basicQos(1);
  
  //关闭消息自动确认
  
  //执行业务逻辑
  
  //手动确认消息
  //channel.basicAck(envelope.getDeliveryTag(),false);
  ```

### Fanout模型

- 生产者把消息发送到交换机，交换机再通过队列发送给消费者
- 有多个消费者，每个消费者都有自己的queue，每个queue都需要绑定到exchange(交换机)
- exchange会把消息发送到所有绑定的queue中

```java
public class Provider {
    public static void main(String[] args) throws IOException {
        //获取连接对象
        Connection connection = RabbitMQConnectionUtil.getConnection();
        Channel channel = connection.createChannel();
        //给通道声明指定交换机
        //参数1:交换机的名字
        //参数2:交换机类型
        channel.exchangeDeclare("logs", "fanout");

        for (int i = 0; i < 20; i++) {
            channel.basicPublish("logs", "", null, "test".getBytes());
        }

        RabbitMQConnectionUtil.closeConnectionAndChanel(channel, connection);
    }
}
```

```java
public class Consumer1 {
    public static void main(String[] args) throws IOException {
        Connection connection = RabbitMQConnectionUtil.getConnection();
        Channel channel = connection.createChannel();
        channel.exchangeDeclare("logs", "fanout");
        //创建临时队列
        String queueName = channel.queueDeclare().getQueue();
        //绑定交换机和队列
        channel.queueBind(queueName, "logs", "");

        channel.basicConsume(queueName, true, new DefaultConsumer(channel) {
            @Override
            public void handleDelivery(String consumerTag, Envelope envelope, AMQP.BasicProperties properties, byte[] body) throws IOException {
                System.out.println("Consumer1:" + new String(body));
            }
        });
    }
}
```

```java
public class Consumer2 {
    public static void main(String[] args) throws IOException {
        Connection connection = RabbitMQConnectionUtil.getConnection();
        Channel channel = connection.createChannel();
        channel.exchangeDeclare("logs", "fanout");
        //创建临时队列
        String queueName = channel.queueDeclare().getQueue();
        //绑定交换机和队列
        channel.queueBind(queueName, "logs", "");

        channel.basicConsume(queueName, true, new DefaultConsumer(channel) {
            @Override
            public void handleDelivery(String consumerTag, Envelope envelope, AMQP.BasicProperties properties, byte[] body) throws IOException {
                System.out.println("Consumer2:" + new String(body));
            }
        });
    }
}
```

provider生产的消息会同时发给Consumer1和Consumer2

### Routing模型(direct)

- 队列与交换机的绑定需要指定routingKey
- 消息的发送方再向exchange发消息时，也要指定routingKey
- exchange会比对routingKey，讲消息发送到对应的queue中

```java
public class Provider {
    public static void main(String[] args) throws IOException {
        Connection connection = RabbitMQConnectionUtil.getConnection();
        Channel channel = connection.createChannel();
        //给通道声明指定交换机
        //参数1:交换机的名字
        //参数2:交换机类型
        channel.exchangeDeclare("logs_direct", "direct");
        String routingKey = "info";
        channel.basicPublish("logs_direct", routingKey, null, ("这是direct模型发布的基于routingKey:" + routingKey).getBytes());
        RabbitMQConnectionUtil.closeConnectionAndChanel(channel, connection);
    }
}
```

```java
public class Consumer1 {
    public static void main(String[] args) throws IOException {
        Connection connection = RabbitMQConnectionUtil.getConnection();
        Channel channel = connection.createChannel();
        //通道声明交换机及交换机的类型
        channel.exchangeDeclare("logs_direct", "direct");
        //创建一个临时队列
        String queueName = channel.queueDeclare().getQueue();
        //基于routingKey绑定队列和交换机
        channel.queueBind(queueName, "logs_direct", "error");

        channel.basicConsume(queueName, true, new DefaultConsumer(channel) {
            @Override
            public void handleDelivery(String consumerTag, Envelope envelope, AMQP.BasicProperties properties, byte[] body) throws IOException {
                System.out.println("Consumer1:" + new String(body));
            }
        });
    }
}
```

```java
public class Consumer2 {
    public static void main(String[] args) throws IOException {
        Connection connection = RabbitMQConnectionUtil.getConnection();
        Channel channel = connection.createChannel();
        //通道声明交换机及交换机的类型
        channel.exchangeDeclare("logs_direct", "direct");
        //创建一个临时队列
        String queueName = channel.queueDeclare().getQueue();
        //基于routingKey绑定队列和交换机
        channel.queueBind(queueName, "logs_direct", "info");
        channel.queueBind(queueName, "logs_direct", "error");

        channel.basicConsume(queueName, true, new DefaultConsumer(channel) {
            @Override
            public void handleDelivery(String consumerTag, Envelope envelope, AMQP.BasicProperties properties, byte[] body) throws IOException {
                System.out.println("Consumer2:" + new String(body));
            }
        });
    }
}
```

### Routing模型(topic)

- 与direct类似
- 不同之处在于topic类型的exchange可以让queue在绑定routingKey的时候使用通配符
- 这种模型的routingKey一般由几个单词组成，多个单词之间用'.'分隔，例如`message.info`
- 通配符：`*`匹配一个词，`#`匹配多个词(包括0个)

```java
public class Provider {
    public static void main(String[] args) throws IOException {
        Connection connection = RabbitMQConnectionUtil.getConnection();
        Channel channel = connection.createChannel();
        //给通道声明指定交换机
        //参数1:交换机的名字
        //参数2:交换机类型
        channel.exchangeDeclare("logs_topic", "topic");
        String routingKey = "user.save";
        channel.basicPublish("logs_topic", routingKey, null, ("这是direct模型发布的基于routingKey:" + routingKey).getBytes());
        RabbitMQConnectionUtil.closeConnectionAndChanel(channel, connection);
    }
}
```

```java
public class Consumer1 {
    public static void main(String[] args) throws IOException {
        Connection connection = RabbitMQConnectionUtil.getConnection();
        Channel channel = connection.createChannel();
        //通道声明交换机及交换机的类型
        channel.exchangeDeclare("logs_topic", "topic");
        //创建一个临时队列
        String queueName = channel.queueDeclare().getQueue();
        //基于routingKey绑定队列和交换机
        channel.queueBind(queueName, "logs_topic", "user.*");

        channel.basicConsume(queueName, true, new DefaultConsumer(channel) {
            @Override
            public void handleDelivery(String consumerTag, Envelope envelope, AMQP.BasicProperties properties, byte[] body) throws IOException {
                System.out.println("Consumer1:" + new String(body));
            }
        });
    }
}
```

```java
public class Consumer2 {
    public static void main(String[] args) throws IOException {
        Connection connection = RabbitMQConnectionUtil.getConnection();
        Channel channel = connection.createChannel();
        //通道声明交换机及交换机的类型
        channel.exchangeDeclare("logs_topic", "topic");
        //创建一个临时队列
        String queueName = channel.queueDeclare().getQueue();
        //基于routingKey绑定队列和交换机
        channel.queueBind(queueName, "logs_topic", "*.save");

        channel.basicConsume(queueName, true, new DefaultConsumer(channel) {
            @Override
            public void handleDelivery(String consumerTag, Envelope envelope, AMQP.BasicProperties properties, byte[] body) throws IOException {
                System.out.println("Consumer2:" + new String(body));
            }
        });
    }
}
```

## 整合SpringBoot

1、引入依赖

```markdown
<dependency>
	<groupId>org.springframework.boot</groupId>
	<artifactId>spring-boot-starter-amqp</artifactId>
</dependency>
```

2、application.yml配置

```java
spring:
  rabbitmq:
    host: 123.56.2.36
    port: 5672
    username: admin
    password: admin
    virtual-host: /ems
```

### 剩下的以后再更新(

11111
