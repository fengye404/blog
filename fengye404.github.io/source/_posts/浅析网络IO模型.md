---
title: 浅析网络IO模型
typora-root-url: ./浅析网络IO模型
date: 2023-01-17 15:47:46
tags:
---

## 前言

I/O 泛指的是 CPU 向 I/O设备（硬盘、网卡）中读取/写入数据。而本文主要介绍的是网络 I/O，也就是借助于 Socket Api ，从网卡中读取数据。

## Unix网络编程中的五种IO模型

> 参考：[聊聊Linux 五种IO模型 - 简书 (jianshu.com)](https://www.jianshu.com/p/486b0965c296)

一个I/O操作通常分为两个阶段：

- 等待数据准备（从磁盘/网卡中读取数据到内核空间中的缓冲区）。
- 从内核空间中的缓冲区向用户空间复制数据。

### 阻塞式I/O

![img](./202212011427456.png)

假设在服务器上有一个应用需要接收客户端通过socket传递的数据。

```c
//服务端应用程序伪代码：
listen_fd = socket(domain,type,protocol);
bind(listen_fd,server_addr,server_addrlen);
listen(listen_fd,backlog);
while(1){
    //应用执行到accept的时候会被阻塞住，等待客户端的TCP连接
	accept_fd = accept(listen_id,client_addr,client_addrlen);
    //建立完TCP连接后，read会再次阻塞应用，等待客户端发送数据
	read(accept_fd,buf,nbyte);
    //客户端数据发送完毕后，才能执行逻辑操作
	logicHandle(buf);
    //逻辑操作执行完成后，才能重新监听socket
}


//客户端应用程序伪代码
fd = socket(domain,type,protocol);
//如果此时有其他客户端正在和服务端进行连接，则客户端会被阻塞在connect
connect(fd,server_addr,server_addrlen);
write(fd,buf,nbyte);
```

通过上述伪代码，不难发现阻塞I/O有如下几个问题：

1. 在同一时间，只能接收一个客户端的连接，如果应用程序是单线程的，就无法实现并发。
2. 其他客户端必须等待前一个客户端与服务端建立连接+传输数据+逻辑操作全部完成后，才能与服务端执行连接。
3. 对于服务端来说，虽然应用程序被阻塞，但是CPU任然可以执行其他操作，因此CPU利用率并不低。

对于阻塞式IO来说，如果想要提高并发能力，同时处理多个服务端请求，就需要对每个服务端的**TCP请求**新建一个线程。如果客户端较多，则会给服务端带来很大的内存和CPU压力。

### 非阻塞式I/O

![img](./202212011428391.png)

非阻塞式IO会让accept、read等系统调用不阻塞应用，而是直接返回一个值。可以通过这个值的合法性来判断是否调用成功。

```c
//服务端应用程序伪代码：
listen_fd = socket(domain,type,protocol);
bind(listen_fd,server_addr,server_addrlen);
listen(listen_fd,backlog);
while(1){
    //设置非阻塞
    setNonblocking(listen_fd);
    //接收客户端的连接，非阻塞
    accept_fd = accept(listen_fd,client_addr,client_addrlen);
    //如果返回值合法，则对其进行处理。否则继续循环调用
    if(accept_fd > 0){
        //将socket的fd添加到列表中
        fd_list.add(accept_fd);
        //socket的fd读取客户端发送的数据，
        //这里的read也是非阻塞的
        //实际上现代计算机中的read操作并不是CPU亲自执行，而是委托给DMA处理
		read(accept_fd,buf,nbyte);
    }
    
    //遍历所有的socket的fd
    for(fd in fd_list){
        //如果fd中的数据准备完毕，则进行对其进行逻辑操作
        if(read(fd,buf,nbyte) > 0){
            //这里也可以开启子线程进行逻辑处理，不过这就属于异步的范畴了
            logicHandle(buf);
        }
    }
}


//客户端应用程序伪代码
fd = socket(domain,type,protocol);
connect(fd,server_addr,server_addrlen);
write(fd,buf,nbyte);
```

上述伪代码中服务端主要任务是不断接收socket连接并接收其写入的内容，然后**轮询**判断每个socket的fd中的数据是否准备完毕，准备完毕后就执行逻辑操作。

非阻塞式IO的优点：

- 单线程即可处理多个socket连接。

非阻塞式IO的缺点：

- 需要不断进行系统调用(read函数)，导致频繁的内核态、用户态切换，因此CPU利用率反而比阻塞IO低。

### I/O复用

![img](./202212011428975.png)

IO复用即让一个线程可以监听多个IO。

#### select

select是Unix提供的一个系统调用函数，其原理与非阻塞式IO相同，只不过是将轮询fd_list的过程从用户态进行系统调用变成直接在内核态判断。select函数是阻塞的。

```c
//服务端应用程序伪代码：
listen_fd = socket(domain,type,protocol);
bind(listen_fd,server_addr,server_addrlen);
listen(listen_fd,backlog);
//设置非阻塞
setNonblocking(listen_fd);
//先用非阻塞的形式创建5个socket的fd
for(int i=0;i<5;i++){
    fd_list[i] = accept(listen_fd,client_addr[i],client_addrlen[i]);
}

while(1){
    //select会先将fd_list的引用拷贝到内核空间中
    //然后在内核空间对其不断轮询
    //如果有某个fd中存在数据，即客户端建立了连接，则select会返回
    select(fd_list_max+1,&rset,NULL,NULL,NULL);
    //此时用户态的程序并不知道哪个fd中存在数据，因此要遍历一遍
    for(int i=0;i<5;i++){
        if(FD_ISSET(fd_list[i],&rset)){
        	for(fd in fd_list){
            	read(fd,buf,nbyte);
            	logicHandle(buf);
        	} 
        }
    }
}
```

select的缺点：

- 在调用 select 的时候，需要将 fd_list 拷贝到内核空间，产生性能开销。
- 在内核态中使用轮询 fd_list 的方式进行监控，占用CPU资源。
- select 返回后，用户态并不知道是哪个 fd 准备就绪，需要再次遍历。
- select 默认只能接收1024个 fd。

#### poll

poll 和 select 类似，只是其中的数据结构实现方式不同。

#### epoll

> 参考：[图解 | 深入揭秘 epoll 是如何实现 IO 多路复用的！ (qq.com)](https://mp.weixin.qq.com/s/OmRdUgO1guMX76EdZn11UQ)

epoll 就是为了解决 poll 和 select 的问题而推出的最新的IO复用函数。

不同于 poll/select 在内核态中轮询，epoll 是基于事件回调和中断的。

epoll包含三个函数：

1. epoll_create：在内存中创建一个 `struct eventpoll` 的对象。

   eventpoll 包含三块内容：

   - **wq**：等待队列。存储阻塞在epoll上的用户进程。
   - **rbr**：红黑树，节点为 `struct epitem`。`epitem` 中有两个重要的元素：`socket_fd`、`ep_poll_callback`（`ep_poll_callback` 是一个回调函数，作用是将这个 `socket_fd` 添加到 **rdllist** 并唤醒等待队列中的元素）。
   - **rdllist**：就绪队列。存储准备就绪的 `socket_fd`。

2. epoll_ctl：注册 `socket`。

   当使用 `epoll_ctl` 注册 `socket` 的时候，内核会将 `socket` 封装为一个 epitem ，并添加到 **rbr** 中。

3. epoll_wait：获取就绪事件。就绪的事件通过参数回传。

   epoll_wait 被调用时，如果 **rdllist** 中有数据则返回；无数据则将当前线程封装后添加到 **wq** 中，并阻塞当前线程。

客户端发送数据并被 epoll 接收的流程：

1. 客户端发送数据包到网卡。网卡通过DMA把数据拷贝至内存缓冲区，拷贝完成后发送中断信号。
2. CPU接收到中断信号，通过数据包的IP和端口号找到 socket，将数据添加到 socket 中。
3. CPU触发回调函数 ep_poll_callback，将 socket 添加到 rdllist 并唤醒等待队列中的线程。
4. 线程继续执行。

epoll的优点：

- 在 socket 连接较多的情况下，性能优于 select/poll。

epoll的缺点：

- epoll是 linux2.6 内核添加的功能，而 select/poll 则是 posix 规范的接口，因此 epoll 只能用于 linux 内核，移植性较差。

#### 边缘触发和水平触发

边缘触发和水平触发是两种不同的 I/O 处理方式。它们都有各自的优缺点。

- 边缘触发（edge-triggered）模式下，选择器会在事件发生时立即触发通知，并且只会触发一次。这种方式可以确保我们在处理事件时不会错过任何数据，但是它可能会导致多次处理同一个事件。
- 水平触发（level-triggered）模式下，选择器会在事件发生时立即触发通知，但是会持续触发，直到事件处理完毕。这种方式可以避免多次处理同一个事件，但是它可能会导致数据丢失，因为我们可能在事件发生后处理数据时会错过一些数据。

通常情况下，我们应该根据具体情况来选择合适的 I/O 处理方式。对于实时性要求较高的应用，我们可以使用边缘触发模式；对于需要保证数据不丢失的应用，我们可以使用水平触发模式。

### 信号驱动I/O

![img](./202212011428863.png)

应用进程使用 sigaction 系统调用，内核立即返回，应用进程可以继续执行，也就是说等待数据阶段应用进程是非阻塞的。内核在数据到达时向应用进程发送 SIGIO 信号，应用进程收到之后在信号处理程序中调用 recvfrom 将数据从内核复制到应用进程中。

相比于非阻塞式 IO 的轮询方式，信号驱动 IO 的 CPU 利用率更高。

### 异步I/O

![img](./202212011428396.png)

进行 aio_read 系统调用会立即返回，应用进程继续执行，不会被阻塞，内核会在所有操作完成之后向应用进程发送信号。

异步 IO 与信号驱动 IO 的区别在于，异步 IO 的信号是通知应用进程 IO 完成，而信号驱动 IO 的信号是通知应用进程可以开始 IO。

## Java中的IO模型

Java中的几种IO API：

- 阻塞同步IO：BIO
- 非阻塞同步IO：NIO
- 非阻塞异步IO：AIO

BIO和NIO的本质区别在于，BIO是面向流（Stream）的，NIO是面向缓冲区（Buffer）的。

面向流意味着只能单向读取或写入数据，并且每次只能从流中写入/读取一个或多个字节，读取和写入时要阻塞至完毕；面向缓冲区则可以双向读取写入，并且数据将会被先读入到缓冲区中，然后再处理。面向缓冲相比于面向流，更加灵活。

### BIO-传统IO模型

传统IO模型：

![image-20221203053005893](./202212030530938.png)

```java
public class Solution {
    public static void main(String[] args) throws IOException {
        ServerSocket serverSocket = new ServerSocket(8080);
        while (true) {
            //阻塞监听Socket连接
            Socket socket = serverSocket.accept();
            OutputStream outputStream = socket.getOutputStream();
            InputStream inputStream = socket.getInputStream();
            System.out.println(socket.getRemoteSocketAddress() + " 连接到服务器");
            
            //每建立一个连接，就创建一个线程
            new Thread(() -> {
                try {
                    byte[] buffer = new byte[1024];
                    int len = 0;
                    //read可能会阻塞
                    while ((len = inputStream.read(buffer)) > 0) {
                        System.out.println(socket.getRemoteSocketAddress() + " 发送数据：" + new String(buffer));
                    }
                } catch (IOException e) {
                    e.printStackTrace();
                }
            }).start();
        }
    }
}
```

特点：

- 数据传输采用阻塞式IO。
- 每个连接需要独立的线程去执行读取、业务逻辑、写入的操作。
- 适用于业务逻辑耗时长，低负载、低并发的场景。

缺点：

- 服务端的并发量和线程数成正比。
- 由于每个连接都需要独立的线程去处理，因此同时可能会有大量线程被创建，然而这些线程实际上大部分是事件都处于阻塞状态（阻塞在read()）。
- 由于accept()是阻塞的，因此可能会存在后面一个连接的请求已经到达，然而前一个连接还没有建立完成，导致接收连接的线程阻塞。（举个例子，假设 ServerSocket 建立每个连接耗时4ms，那么即使CPU性能再高，也会受限于网络的瓶颈，每秒钟最多处理250个连接）

### NIO-Reactor模型

NIO中的几个概念：

- Buffer（缓冲区）

  缓冲区本质上是一块可以读写数据的内存，这块内存被包装成 NIO 的 Buffer 对象，并对外提供一系列方法用于访问该块内存。

  对应于 `java.nio.Buffer` 抽象类。

- Channel（通道）

  通道类似 BIO 中的 Stream，用于向 Buffer 中读取或写入数据。

  对应于 `java.nio.channels.Channel` 接口。

- Selector（选择器）

  选择器可以检查一个或多个通道，并确定哪些通道已经准备好进行读写。通过 Selector，一个单独的线程可以管理多个 Channel，从而管理多个连接。不过不是所有的 Channel 都可以被 Selector 复用，必须要继承了 SelectableChannel。

  对应于 `java.nio.channels.Selector` 抽象类。

NIO特点：

- 每个 Channel 对应一个 Buffer。
- 一个线程对应一个 Selector，一个 Selector 对应多个 Channel。
- Buffer 是一个内存块，底层是数组，可以切换读写模式（实际上是改变参数）。

#### Buffer

Buffer的实现类有：ByteBuffer、CharBuffer、ShortBuffer、IntBuffer、LongBuffer、FloatBuffer、DoubleBuffer。

无论是哪一种，管理方式都一致，都是通过 `allocate(int capacity)` 来获取 Buffer。

**Buffer 的几个重要属性**

- capacity：Buffer的最大容量，创建后不能更改。
- limit：缓冲区可以操作的数据大小，index 大于 limit 的数据不能读写。limit 不能为并且不能大于 capacity。在写模式下，limit 等于 capacity；在读模式下，limit 等于当前容量。
- position：下一个要读取或写入的数据的 index。
- mark：标记，可以通过 `mark()` 方法记录当前 position，然后通过 `reset()` 恢复 position 的位置。

**Buffer 的几个重要方法**

- `Buffer clear()`：清空 Buffer，读模式转变为写模式（position设为0，limit设为capacity，mark设为-1）并返回。
- `Buffer flip()`：写模式转变为读模式（limit设为position，position设为0，mark设为-1）并返回。
- `get()`：获取当前数据类型的一个数据。
- `put()`：存储当前数据类型的一个数据。

**Buffer 读写数据的步骤**

1. 写入数据。
2. 调用 `flip()` 切换读取模式。
3. 读取数据。
4. 调用 `clear()` 清除数据。

**直接缓冲区和非直接缓冲区**

- 直接缓冲区：通过 `allocate()Direct` 创建缓冲区，缓冲区建立在直接内存中。

  直接内存在IO处理时的性能更高，但申请直接内存会耗费更多性能。一般在有大量数据需要存储并且生命周期很长，或者有频繁IO操作时，适合使用直接缓冲区。

- 非直接缓冲区：通过 `allocate()` 创建缓冲区，缓冲区建立在JVM堆内存中。

#### Channel

Channel类似于BIO中的流，用于在支持 Channel 的两个结点中传递数据。但是 Channel 本身并不存储数据，需要配合 Buffer 使用。Channel 的实现类有：FileChannel、SocketChannel、ServerSocketChannel、DatagramChannel。

**获取 Channel 对象的方法**

1. 调用支持 Channel 的对象的 `getChannel()`。支持 Channel 的对象有：
   - FileInputStream
   - FileOutputStream
   - RandomAccessFile
   - DatagramSocket
   - Socket
   - ServerSocket
2. 通过 Channel 的实现类的静态方法 `open()`。
3. `Files.newByteChannel()`

**Channel 的几个重要方法**

- `int read(Buffer dst)`：从 Channel 中读取数据到 Buffer。
- `int write(Buffer src)`：将 Buffer 中的数据写入到 Channel 中。

**使用 Channel 完成文件复制的例子**

```java
public class Solution {
    public static void main(String[] args) throws IOException {
        // 利用通道完成文件的复制(非直接缓冲区)
        FileInputStream fis = new FileInputStream("a.txt");
        FileOutputStream fos = new FileOutputStream("b.txt");
        // 获取通道
        FileChannel fisChannel = fis.getChannel();
        FileChannel foschannel = fos.getChannel();

        // 通道没有办法传输数据，必须依赖缓冲区
        // 分配指定大小的缓冲区
        ByteBuffer byteBuffer = ByteBuffer.allocate(1024);

        // 将通道中的数据存入缓冲区中
        while (fisChannel.read(byteBuffer) != -1) {  // fisChannel 中的数据读到 byteBuffer 缓冲区中
            byteBuffer.flip();  // 切换成读数据模式
            // 将缓冲区中的数据写入通道
            foschannel.write(byteBuffer);
            byteBuffer.clear();  // 清空缓冲区
        }
        foschannel.close();
        fisChannel.close();
        fos.close();
        fis.close();
    }
}
```

#### Selector

Selector 是 Java NIO 中的多路复用器。将 SelectableChannel 注册到 Selector 中，就可以通过一个 Selector 监听多个 SelectableChannel。Selector 和 SelectableChannel 是多对多的关系。

**Selector的基本使用**

- 创建：`Selector.open()`。由于多路复用需要操作系统提供底层的支持，因此在不同的环境下会提供不同的 Selector 实例。例如 Windows-JDK 下会提供 `sun.nio.ch.WindowsSelectorImpl`，Linux-JDK 下会提供 `sun.nio.ch.EPollSelectorImpl`。

- 注册：

  ```java
  channel.configureBlocking(false);
  SelectionKey key = channel.register(selector, Selectionkey.OP_READ);
  ```

  注册到 Selector 的 Channel 必须是非阻塞的，否则会抛出 IllegalBlockingModeException。

  `register()` 的第二个参数表示需要监听的事件，分别为 `Connect`、`Accept`、`Read`、`Write`，如果需要监听多个事件，可以用 `|` 分隔。

- SelectionKey：

  注册后会返回 SelectionKey 的对象，这个对象表示了一个 Channel 和 一个 Selector 的对应关系。

  ```java
  key.attachment(); //返回SelectionKey的attachment，attachment可以在注册channel的时候指定。
  key.channel(); //返回该SelectionKey对应的channel。
  key.selector(); //返回该SelectionKey对应的Selector。
  key.interestOps(); //返回监听的事件的bit mask，对应channel.register()的第二个参数
  key.readyOps(); //返回已准备就绪的事件的bit mask
  ```

- 获取就绪的Channel：

  先调用 select() 获取准备就绪的通道数量。select() 相关的几个方法：

  - select()：阻塞获取就绪的通道数量。
  - select(long timeout)：阻塞获取就绪的通道数量，如果超时则返回0。
  - selectNow()：非阻塞获取就绪通道数量。

  （select() 表示从上次调用 select() 后新增了多少已准备就绪的通道）

  如果 select() 返回值不为0，说明有已准备就绪的通道，调用 selector.selectedKeys() 获取通道集合。 

**NIO基本服务端代码编写**

```java
public class Solution {
    public static void main(String[] args) throws IOException {
        Selector selector = Selector.open();
        ByteBuffer byteBuffer = ByteBuffer.allocate(1024);
        //使用一个ServerSocketChannel来负责监听accept事件
        ServerSocketChannel serverSocketChannel = ServerSocketChannel.open();
        serverSocketChannel.socket().bind(new InetSocketAddress("127.0.0.1", 8080));
        serverSocketChannel.configureBlocking(false);
        serverSocketChannel.register(selector, SelectionKey.OP_ACCEPT);
        while (true) {
            if (selector.select() == 0) {
                continue;
            }
            Set<SelectionKey> selectionKeys = selector.selectedKeys();
            Iterator<SelectionKey> iterator = selectionKeys.iterator();
            while (iterator.hasNext()) {
                SelectionKey key = iterator.next();
                if (key.isValid() && key.isAcceptable()) {
                    //监听到连接事件，则把这个连接的Channel也注册到selector中
                    SocketChannel socketChannel = ((ServerSocketChannel) key.channel()).accept();
                    socketChannel.configureBlocking(false);
                    socketChannel.register(selector, SelectionKey.OP_READ);
                } else if (key.isValid() && key.isReadable()) {
                    //监听到读取事件，则进行数据拷贝和逻辑操作
                    //这里可以创建另外的线程去处理，也可以考虑池化
                    SocketChannel socketChannel = (SocketChannel) key.channel();
                    int len = 0;
                    while ((len = socketChannel.read(byteBuffer)) > 0) {
                        byteBuffer.flip();
                        System.out.println(new String(byteBuffer.array(), 0, len));
                        byteBuffer.clear();
                    }
                }
                //处理完后移除当前的SelectionKey
                iterator.remove();
            }
        }
    }
}
```

特点：

- 由于是非阻塞IO，每当一个连接请求到达，只需要将其注册到 Selector 中，因此单线程可以一直处理连接请求。
- 读取数据和逻辑操作与BIO一样，因此NIO的优势在于对连接的处理，即在等待某个连接建立的过程中可以继续和其他请求建立连接。
- 适用于业务逻辑耗时短，高负载高并发的场景

#### Reactor模型

Reactor模型是基于 NIO 提出的一套IO模型。本质上是把上面编写的NIO服务端代码进行组件拆分和抽象化：

- Reactor：负责接收用户端连接
- Acceptor：负责建立连接
- Hispatch：负责处理请求

客户端测试代码：

```java
public class Client {
    public static void main(String[] args) {
        ByteBuffer byteBuffer = ByteBuffer.allocate(1024);
        try {
            SocketChannel socketChannel = SocketChannel.open();
            socketChannel.connect(new InetSocketAddress("127.0.0.1", 8080));
            new Thread(() -> {
                while (true) {
                    try {
                        int len = 0;
                        while ((len = socketChannel.read(byteBuffer)) > 0) {
                            byteBuffer.flip();
                            System.out.println(new String(byteBuffer.array(), 0, len));
                            byteBuffer.clear();
                        }
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                }
            }).start();

            while (true) {
                Scanner scanner = new Scanner(System.in);
                while (scanner.hasNextLine()) {
                    String s = scanner.nextLine();
                    byteBuffer.put(s.getBytes());
                    byteBuffer.flip();
                    socketChannel.write(byteBuffer);
                    byteBuffer.flip();
                }
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

##### 单Reactor单线程

单Reactor单线程实际上就是之前的NIO服务端代码。

![image-20221207001700692](./202212070017765.png)

流程：

1. Reactor 对象使用 select 监听客户端连接请求，触发事件后将其交给 dispatch() 分发
2. 如果是建立连接请求事件，则分发给 Acceptor 通过 accept() 处理连接请求事件，然后创建 Handler 处理后续事件。
3. 如果不是建立连接事件，则会分发给之前创建的 Handler 处理。
4. Handler 负责处理读取、业务逻辑、写入。

```java
public class Reactor implements Runnable {
    ServerSocketChannel serverSocketChannel;
    Selector selector;

    public Reactor(int port) {
        try {
            serverSocketChannel = ServerSocketChannel.open();
            selector = Selector.open();
            serverSocketChannel.socket().bind(new InetSocketAddress(port));
            serverSocketChannel.configureBlocking(false);
            SelectionKey selectionKey = serverSocketChannel.register(selector, SelectionKey.OP_ACCEPT);
            selectionKey.attach(new Acceptor(selector, serverSocketChannel));
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    @Override
    public void run() {
        while (true) {
            try {
                selector.select();
                Set<SelectionKey> selectionKeys = selector.selectedKeys();
                Iterator<SelectionKey> iterator = selectionKeys.iterator();
                while (iterator.hasNext()) {
                    SelectionKey selectionKey = iterator.next();
                    dispatcher(selectionKey);
                    iterator.remove();
                }
            } catch (IOException e) {
                e.printStackTrace();
            }
        }
    }

    private void dispatcher(SelectionKey selectionKey) {
        Runnable runnable = (Runnable) selectionKey.attachment();
        runnable.run();
    }
}
```

```java
public class Acceptor implements Runnable {
    private Selector selector;

    private ServerSocketChannel serverSocketChannel;

    public Acceptor(Selector selector, ServerSocketChannel serverSocketChannel) {
        this.selector = selector;
        this.serverSocketChannel = serverSocketChannel;
    }

    @Override
    public void run() {
        try {
            SocketChannel socketChannel = serverSocketChannel.accept();
            System.out.println("有客户端连接上来了," + socketChannel.getRemoteAddress());
            socketChannel.configureBlocking(false);
            SelectionKey selectionKey = socketChannel.register(selector, SelectionKey.OP_READ);
            selectionKey.attach(new Handler(socketChannel));
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

```java
public class Handler implements Runnable {
    private SocketChannel socketChannel;

    public Handler(SocketChannel socketChannel) {
        this.socketChannel = socketChannel;
    }

    @Override
    public void run() {
        try {
            ByteBuffer byteBuffer = ByteBuffer.allocate(1024);
            int len = 0;
            while ((len = socketChannel.read(byteBuffer)) > 0) {
                byteBuffer.flip();
                System.out.println(new String(byteBuffer.array(), 0, len));
                socketChannel.write(byteBuffer);
                byteBuffer.clear();
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

##### 单Reactor多线程

在上面的单Reactor单线程模型中，Handler部分执行代码都是单线程的，因此可能会导致一个Handler执行事件过久而阻塞其他的Acceptor和Handler，即服务端同时能进行逻辑处理的用户端只有一个。因此可以考虑在Handler部分加入线程池。

![image-20221207221606497](./202212072216548.png)

Reactor和Acceptor部分代码不变，Handler代码变动：

```java
public class Handler implements Runnable {

    static ExecutorService pool = Executors.newFixedThreadPool(5);
    private SocketChannel socketChannel;

    public Handler(SocketChannel socketChannel) {
        this.socketChannel = socketChannel;
    }

    @Override
    public void run() {
        System.out.println("执行Handler");
        ByteBuffer byteBuffer = ByteBuffer.allocate(1024);
        try {
            socketChannel.read(byteBuffer);
        } catch (IOException e) {
            e.printStackTrace();
        }

        pool.execute(new Process(socketChannel, byteBuffer));

        try {
            byteBuffer.flip();
            socketChannel.write(byteBuffer);
            byteBuffer.flip();
        } catch (IOException e) {
            e.printStackTrace();
        }
    }
}
```

```java
public class Process implements Runnable {

    private SocketChannel socketChannel;
    private ByteBuffer byteBuffer;

    public Process(SocketChannel socketChannel, ByteBuffer byteBuffer) {
        this.socketChannel = socketChannel;
        this.byteBuffer = byteBuffer;
    }

    @Override
    public void run() {
        //正常逻辑操作
        System.out.println("Process thread:" + Thread.currentThread().getName());
        System.out.println(new String(byteBuffer.array()));
    }
}
```

##### 主从Reactor模型

在上面的单Reactor多线程模型中，虽然把逻辑处理交给了线程池，但是读写操作还是由 Reactor（主线程）来处理。因此单个 Reactor 需要同时处理连接请求和读写，执行压力很大。于是便有了主从 Reactor 模型。其中一个Reactor负责处理连接，另一个负责处理客户端的读写。

![image-20221207221539904](./202212072215954.png)

1. Reactor 主线程 MainReactor 对象通过 Select 监控建立连接事件，收到事件后通过 Acceptor 接收，处理建立连接事件；
2. Acceptor 处理建立连接事件后，MainReactor 将连接分配 Reactor 子线程给 SubReactor 进行处理；
3. SubReactor 将连接加入连接队列进行监听，并创建一个 Handler 用于处理各种连接事件；
4. 当有新的事件发生时，SubReactor 会调用连接对应的 Handler 进行响应；
5. Handler 通过 Read 读取数据后，会分发给后面的 Worker 线程池进行业务处理；
6. Worker 线程池会分配独立的线程完成真正的业务处理，如何将响应结果发给 Handler 进行处理；
7. Handler 收到响应结果后通过 Send 将响应结果返回给 Client。



> 参考：
>
> [【并发】IO多路复用select/poll/epoll介绍_哔哩哔哩_bilibili](https://www.bilibili.com/video/BV1qJ411w7du/)
>
> [Linux的5种IO模型梳理 - 知乎 (zhihu.com)](https://zhuanlan.zhihu.com/p/127170201)
>
> [「Linux」——select和epoll详解 - 知乎 (zhihu.com)](https://zhuanlan.zhihu.com/p/179071801)
>
> [图解 | 深入揭秘 epoll 是如何实现 IO 多路复用的！ (qq.com)](https://mp.weixin.qq.com/s/OmRdUgO1guMX76EdZn11UQ)
>
> [聊聊Linux 五种IO模型 - 简书 (jianshu.com)](https://www.jianshu.com/p/486b0965c296)
>
> [java之NIO简介_爱上口袋的天空的博客-CSDN博客_java nio](https://blog.csdn.net/K_520_W/article/details/123454627)
>
> [nio.pdf (oswego.edu)](https://gee.cs.oswego.edu/dl/cpjslides/nio.pdf)
>
> [Reactor模型 - CodeBear - 博客园 (cnblogs.com)](https://www.cnblogs.com/CodeBear/p/12567022.html)
