---
title: OSPP参与记录
typora-root-url: ./OSPP参与记录
date: 2024-09-29 15:58:07
tags:
---



# 前言

今年毕业前申请参与了2024年的开源之夏（OSPP），是一次很宝贵的开源项目经验，最终成功结项。写这篇博客以此记录留存。

本博客记录的内容截至日期为 2024:09:30，最终方案相比本文有变动，例如放弃 jprotobuf 方案、重构 Grpc 调用模块等。具体详见：https://github.com/alibaba/arthas/pull/2914

------

# 项目申请书

<center>项目名称：探索 Java 低资源消耗的 gRPC 实现</center>

<center>项目主导师：断岭</center>

<center>申请人：风业</center>

<center>日期：2024.06.03</center>

<center>邮箱：1129126684@qq.com</center>

------

## 项目背景

Arthas 是一个 Java 诊断工具，它允许开发人员在无需修改应用程序代码的情况下，动态地监视和解决生产环境中 Java 应用程序的问题。目前 Arthas 主要是通过交互式的命令行提供服务，此外也提供了 http api。但是 http api 比较简陋，预期通过grpc server提供服务。但是官方的 grpc 实现依赖多、运行时内存占用高，本项目旨在提供一种低资源消耗的 grpc 实现，需要支持 stream 并尽量减少外部依赖。

## 项目主要内容

1. 实现低资源消耗的 grpc 协议，需要尽量减少外部依赖，并支持双向 stream。
2. 基于上述 grpc 协议，提供一个简单的Arthas服务的实现，比如查看Jvm System Properties。
3. 实现 protobuf 的编译代码生成器，优先级不高，先用官方的生成代码也可以接受。

## 项目相关文档

- github issue地址：https://github.com/alibaba/arthas/issues/2349
- arthas 官方文档：https://arthas.aliyun.com/doc

其他开源 grpc 实现参考：

- dubbo 的 triple 实现：https://github.com/apache/dubbo/tree/3.2/dubbo-rpc/dubbo-rpc-triple
- armeria 的 grpc 实现：https://armeria.dev/docs/server-grpc
- wire 的 grpc 实现：https://github.com/square/wire

------

## 项目方案概述

参考各开源项目的 grpc 实现后，本项目方案设计如下：

1. 服务端和客户端使用 protobuf 作为IDL
2. 客户端实现可以由用户自行决定，只要符合官方 grpc 协议即可，例如可以参考 grpc-java 官方的 client 请求实例
3. 服务端不依赖 netty java 的官方实现（即 grpc-netty），因此需要实现两个部分
   1. stub 接口代码生成：参考 wire，读取 protobuf 后手动实现（可选，前期可以先手动写服务端的 stub 接口）
   2. grpc 实现：参考 grpc-netty 官方实现，主要涉及对 http2 frame 的操作

### stub 代码生成

此操作在编译期完成，预计需要在编译期依赖 wire 读取 protobuf schema，然后手动拼接文件。

参考 opentelemetry-java 中关于生成 stub 接口代码的实现：https://github.com/open-telemetry/opentelemetry-java/blob/v1.22.0/buildSrc/src/main/kotlin/io/opentelemetry/gradle/ProtoFieldsWireHandler.kt

可以使用 maven-compiler-plugin 来指定 maven 编译期间执行上述生成过程。

### gprc  实现

grpc 的实现参考 grpc-netty 的实现。grpc 本质上是 http2。

![img](./9895e16be720641411c9b27b46276724.png)

要实现 grpc，就需要实现 netty 中处理 http2 请求的一些组件：

- **Http2ConnectionDecoder**：
  - 负责解析 HTTP/2 帧，并将它们转换为 gRPC 消息。
  - 通常位于 Netty 的 `ChannelPipeline` 中，用于处理接收到的 HTTP/2 帧。
- **Http2ConnectionHandler**：
  - 负责处理 gRPC 消息，包括序列化和反序列化。
  - 通常位于 Netty 的 `ChannelPipeline` 中，用于处理 gRPC 消息。
- **Http2ConnectionListener**：
  - 负责处理 HTTP/2 连接的生命周期事件，如设置和更改流状态。
  - 通常位于 Netty 的 `ChannelPipeline` 中，用于处理 HTTP/2 连接的状态变化。

参考 grpc-netty 的实现，其中就实现了这些组件。

以读取 data frame 为例，grpc-netty 中通过 io.grpc.netty.NettyServerHandler.FrameListener 实现了 io.netty.handler.codec.http2.Http2FrameAdapter，其中的 onDataRead 方法就会在读取 data frame 时触发，其简略代码如下：

io.grpc.netty.NettyServerHandler#onDataRead

```java
private void onDataRead(int streamId, ByteBuf data, int padding, boolean endOfStream)
    throws Http2Exception {
    ...
    flowControlPing().onDataRead(data.readableBytes(), padding);
    NettyServerStream.TransportState stream = serverStream(requireHttp2Stream(streamId));
    stream.inboundDataReceived(data, endOfStream);
    ...
}
```

io.grpc.internal.AbstractServerStream.TransportState#inboundDataReceived

```java
public void inboundDataReceived(ReadableBuffer frame, boolean endOfStream) {
    ...
    deframe(frame);
    if (endOfStream) {
        this.endOfStream = true;
        closeDeframer(false);
    }
}
```

io.grpc.internal.AbstractStream.TransportState#deframe

```java
protected final void deframe(final ReadableBuffer frame) {
    try {
        deframer.deframe(frame);
    } catch (Throwable t) {
        deframeFailed(t);
    }
}
```

io.grpc.internal.MessageDeframer#deframe

```java
public void deframe(ReadableBuffer data) {
	...
    deliver();
	...
}
```

io.grpc.internal.MessageDeframer#deliver

```java
private void deliver() {
    ...
    while (!stopDelivery && pendingDeliveries > 0 && readRequiredBytes()) {
        switch (state) {
            case BODY:
                processBody();
                pendingDeliveries--;
                break;
        }
    }
    ...
}
```

io.grpc.internal.MessageDeframer#processBody

```java
private void processBody() {
    // There is no reliable way to get the uncompressed size per message when it's compressed,
    // because the uncompressed bytes are provided through an InputStream whose total size is
    // unknown until all bytes are read, and we don't know when it happens.
    statsTraceCtx.inboundMessageRead(currentMessageSeqNo, inboundBodyWireSize, -1);
    inboundBodyWireSize = 0;
    InputStream stream = compressedFlag ? getCompressedBody() : getUncompressedBody();
    nextFrame = null;
    listener.messagesAvailable(new SingleMessageProducer(stream));

    // Done with this frame, begin processing the next header.
    state = State.HEADER;
    requiredLength = HEADER_LENGTH;
}
```

当接收到 data frame 后，grpc 的处理方式是将其放入缓冲区中，最终 data frame 结束后，会调用 `processBody()` 处理 body：从缓冲区中读出 inputStream，然后触发消息。

对 http2 frame 的操作可以参考 grpc-netty 实现，本方案主要修改点在于 processBody，需要替换为针对 stub 生成代码的实现，预计会考虑反射调用的处理。

此外，对于 http2 frame 的操作，netty 还给出了更好的方式，后续可以考虑：[Http2FrameCodecBuilder (Netty API Reference (4.1.110.Final))](https://netty.io/4.1/api/io/netty/handler/codec/http2/Http2FrameCodecBuilder.html)

## 规划

- **阶段一：研究 netty 实现 grpc 协议（7.1 - 8.15）**
  - 第一周：阅读 grpc-netty 源码，了解 netty 对于 http2 的封装。
  - 第二周、第三周：使用 netty 实现 grpc 协议一元调用。
  - 第四周：继续参考 grpc-netty 源码，了解双向流、异常处理的实现。
  - 第五周、第六周：完成 grpc 双向流的实现。
- **阶段二：研究 stub 代码生成部分（8.15 - 8.30）**
  - 第一周：阅读 opentelemetry-java 相关实现，了解 protobuf 的 schema、了解 java 代码生成。
  - 第二周：实现 stub 代码生成。
- **阶段三：使用 grpc 实现 arthas 中的部分功能（9.1 - 9.15）**
  - 第一周：阅读 arthas 的相关源码，了解其实现。
  - 第二周：利用 gprc 实现其中的部分功能。
- **阶段四：完成结项报告和 pr/mr 提交（9.16 - 9.30）**
  - 第一周：为项目编写 readme 文档，便于后续维护修改。
  - 第二周：完成结项报告和 pr/mr 提交。

## 其他

这是我第一次参与到大型的开源项目中来，感谢 ospp 提供了这个机会，十分期待能够给开源社区提供贡献，并积累相关经验，学习更多知识。另外我对 arthas 非常感兴趣，平时的日常开发中也经常使用，如果以后有机会，希望能够继续投入到开源社区的工作中，为开源社区做贡献。

# 结项报告

## 项目信息

### 项目介绍

Arthas 是一个 Java 诊断工具，它允许开发人员在无需修改应用程序代码的情况下，动态地监视和解决生产环境中 Java 应用程序的问题。目前 Arthas 主要是通过交互式的命令行提供服务，此外也提供了 http api。但是 http api 比较简陋，预期通过grpc server提供服务。但是官方的 grpc 实现依赖多、运行时内存占用高，本项目旨在提供一种低资源消耗的 grpc 实现，需要支持 stream 并尽量减少外部依赖。

本项目主要完成了以下内容

1. 实现低资源消耗的 grpc 协议，需要尽量减少外部依赖，并支持双向 stream。
2. 实现 protobuf 的序列化和反序列化

### 方案描述

参考各开源项目的 grpc 实现后，本项目方案设计如下：

1. 服务端和客户端使用 protobuf 作为 IDL
2. 客户端实现可以由用户自行决定，只要符合官方 grpc 协议即可，例如可以参考 grpc-java 官方的 client 请求实例
3. 服务端不依赖 netty java 的官方实现（即 grpc-netty），因此需要实现两个部分
   1. protobuf 的序列化和反序列化，参考 protobuf
   2. grpc 的请求处理，包括一元请求和双向流请求，参考 grpc-netty

### 时间规划

- **阶段一：研究 netty 实现 grpc 协议（7.1 - 8.15）**
  - 第一周：阅读 grpc-netty 源码，了解 netty 对于 http2 的封装。
  - 第二周、第三周：使用 netty 实现 grpc 协议一元调用。
  - 第四周：继续参考 grpc-netty 源码，了解双向流、异常处理的实现。
  - 第五周、第六周：完成 grpc 双向流的实现。
- **阶段二：研究 stub 代码生成部分（8.15 - 8.30）**
  - 第一周：阅读 opentelemetry-java 相关实现，了解 protobuf 的 schema、了解 java 代码生成。
  - 第二周：实现 stub 代码生成。
- **阶段三：使用 grpc 实现 arthas 中的部分功能（9.1 - 9.15）**
  - 第一周：阅读 arthas 的相关源码，了解其实现。
  - 第二周：利用 gprc 实现其中的部分功能。
- **阶段四：完成结项报告和 pr/mr 提交（9.16 - 9.30）**
  - 第一周：为项目编写 readme 文档，便于后续维护修改。
  - 第二周：完成结项报告和 pr/mr 提交。

## 项目进度

### 已完成工作

截至930，该项目已完成：

1. protobuf 的序列化和反序列化实现及其单元测试
2. 解析 grpc 协议格式
3. netty 实现 grpc 的一元请求和流失请求处理

本项目未使用除 protobuf 以外的任何外部依赖

### 实现记录

#### protobuf 序列化

实现 protobuf 的序列化和反序列化大致有两种思路

1. 参考 java grpc maven plugin，将解析逻辑实现在生成的 stub 中
2. 参考 jprotobuf，将解析逻辑实现在运行时

从本质上来看两种实现方式，其实都是建立 protobuf 字段类型到 java 字段类型的映射，然后处理映射逻辑实现序列化。但是两者实现的方式却不同，【1】是读取 protobuf，在编译期生成 java 代码，java 代码中实现 protobuf 的序列化和反序列化；【2】是根据定义的 java 对象，通过对对象的代理中的逻辑实现 protobuf 序列化和反序列化。

这两种方式各有优劣：

1. 逻辑上更符合直觉，但是有两个问题：【1】需要读取 protobuf 定义文件并解析其内容，这方面的库较少，可能需要手动解析；【2】需要处理编译期操作
2. 类似于 “先射箭后画靶”，需要人工从已知的 protobuf 定义文件中解析内容，然后编写 java 类

最终采用了方案2，因为成本更低，且有开源库 jprotobuf 参考。

**实现原理**

- 定义 protobuf 到 java 字段类型的映射关系

- 定义代理类模板

  ```html
  ${package}
  
  import java.io.Serializable;
  <!-- $BeginBlock imports -->
  import ${importBlock};
  <!-- $EndBlock imports -->
  
  public class ${className} implements ${codecClassName}<${targetProxyClassName}>, Serializable {
  	public static final long serialVersionUID = 1L;
  
      public byte[] encode(${targetProxyClassName} target) throws IOException {
          CodedOutputStreamCache outputCache = CodedOutputStreamCache.get();
          doWriteTo(target, outputCache.getCodedOutputStream());
          return outputCache.getData();
      }
  
      public void doWriteTo(${targetProxyClassName} target, CodedOutputStream output)
              throws IOException {
          <!-- $BeginBlock encodeFields -->
          ${dynamicFieldType} ${dynamicFieldName} = null;
          if (!ProtoBufUtil.isNull(${dynamicFieldGetter})) {
              ${dynamicFieldName} = ${dynamicFieldGetter};
              ${encodeWriteFieldValue}
          }
          <!-- $EndBlock encodeFields -->
      }
  
      public ${targetProxyClassName} decode(byte[] bb) throws IOException {
          CodedInputStream input = CodedInputStream.newInstance(bb, 0, bb.length);
          return readFrom(input);
      }
  
      public int size(${targetProxyClassName} target) throws IOException {
          int size = 0;
          <!-- $BeginBlock encodeFields -->
          ${dynamicFieldType} ${dynamicFieldName} = null;
          if (!ProtoBufUtil.isNull(${dynamicFieldGetter})) {
              ${dynamicFieldName} = ${dynamicFieldGetter};
              size += ${sizeDynamicString}
          }
          <!-- $EndBlock encodeFields -->
          return size;
      }
   
      public ${targetProxyClassName} readFrom(CodedInputStream input) throws IOException {
          ${targetProxyClassName} target = new ${targetProxyClassName}();
          
          ${initListMapFields}
  
          <!-- $BeginBlock enumFields -->
          ${enumInitialize};
          <!-- $EndBlock enumFields -->
          try {
              boolean done = false;
              ProtobufCodec codec = null;
              while (!done) {
                  int tag = input.readTag();
                  if (tag == 0) {
                      break;
                  }
                  <!-- $BeginBlock decodeFields -->
                  if (tag == ${decodeOrder}) {
                      ${objectDecodeExpress}
                      ${decodeFieldSetValue}
                      ${objectDecodeExpressSuffix}
                      continue;
                  }
                  ${objectPackedDecodeExpress}
                  <!-- $EndBlock decodeFields -->               
                  
                  input.skipField(tag);
              }
          } catch (com.google.protobuf.InvalidProtocolBufferException e) {
              throw e;
          } catch (java.io.IOException e) {
              throw e;
          }
          return target;
      }
  }
  ```

- 根据 protobuf 手动编写对应的 java 类

- 运行时为指定的类实现代理，通过开源库 MiniTemplator 解析并填充内容

#### http2 格式解析

grpc 是基于 netty 的，想要实现 grpc 协议，就必须要先解析 http2 协议格式。

netty 中提供了非常简单的操作 http2 frame 的方式：[Http2FrameCodecBuilder (Netty API Reference (4.1.110.Final))](https://netty.io/4.1/api/io/netty/handler/codec/http2/Http2FrameCodecBuilder.html)。

代码实现如下：

```java
public class Http2Handler extends SimpleChannelInboundHandler<Http2Frame> {

    @Override
    public void channelRead(ChannelHandlerContext ctx, Object msg) throws Exception {
        super.channelRead(ctx, msg);
    }

    @Override
    protected void channelRead0(ChannelHandlerContext ctx, Http2Frame frame) throws IOException {
        if (frame instanceof Http2HeadersFrame) {
            handleGrpcRequest((Http2HeadersFrame) frame, ctx);
        } else if (frame instanceof Http2DataFrame) {
            handleGrpcData((Http2DataFrame) frame, ctx);
        }
    }

    @Override
    public void exceptionCaught(ChannelHandlerContext ctx, Throwable cause) {
        cause.printStackTrace();
        ctx.close();
    }
}
```

在 `channelRead0` 中，netty 用 Http2Frame 封装了 http2 的 frame，简化了 http2 frame 的解析操作。

#### grpc 请求解析

接收到了 http2Frame 后，需要将其解析为 grpc 请求。

> https://github.com/grpc/grpc/blob/master/doc/PROTOCOL-HTTP2.md 定义了 http2 中 grpc 协议的一些基本格式

![image-20240929001524840](./image-20240929001524840-1735632468022-3.png)

可以看到 grpc 实际上就是在 http2 的 body 中塞入了一些 grpc 包头和业务数据。那么要解析 grpc 协议，实际上只需要解析 http2 协议，在此基础上解析 grpc 包头即可。

代码中将 grpc 请求封装为一个类来处理：

```java
public class GrpcRequest {

    /**
     * 请求对应的 streamId
     */
    private Integer streamId;

    /**
     * 请求的 service
     */
    private String service;

    /**
     * 请求的 method
     */
    private String method;

    /**
     * 二进制数据，可能包含多个 grpc body，每个 body 都带有 5 个 byte 的前缀，分别是 boolean compressed - int length
     */
    private ByteBuf byteData;

    /**
     * 二进制数据的长度
     */
    private int length;

    /**
     * 请求class
     */
    private Class<?> clazz;

    /**
     * 是否是 grpc 流式请求
     */
    private boolean stream;

    /**
     * 是否是 grpc 流式请求的第一个data
     */
    private boolean streamFirstData;


    public GrpcRequest(Integer streamId, String path, String method) {
        this.streamId = streamId;
        this.service = path;
        this.method = method;
        this.byteData = ByteUtil.newByteBuf();
    }

    public void writeData(ByteBuf byteBuf) {
        byte[] bytes = ByteUtil.getBytes(byteBuf);
        if (bytes.length == 0) {
            return;
        }
        byte[] decompressedData = decompressGzip(bytes);
        if (decompressedData == null) {
            return;
        }
        byteData.writeBytes(ByteUtil.newByteBuf(decompressedData));
    }

    /**
     * 读取部分数据
     *
     * @return
     */
    public byte[] readData() {
        if (byteData.readableBytes() == 0) {
            return null;
        }
        boolean compressed = byteData.readBoolean();
        int length = byteData.readInt();
        byte[] bytes = new byte[length];
        byteData.readBytes(bytes);
        return bytes;
    }

    public void clearData() {
        byteData.clear();
    }

    private byte[] decompressGzip(byte[] compressedData) {
        boolean isGzip = (compressedData.length > 2 && (compressedData[0] & 0xff) == 0x1f && (compressedData[1] & 0xff) == 0x8b);
        if (isGzip) {
            try {
                InputStream byteStream = new ByteArrayInputStream(compressedData);
                GZIPInputStream gzipStream = new GZIPInputStream(byteStream);
                byte[] buffer = new byte[1024];
                int len;
                ByteArrayOutputStream out = new ByteArrayOutputStream();
                while ((len = gzipStream.read(buffer)) != -1) {
                    out.write(buffer, 0, len);
                }
                return out.toByteArray();
            } catch (IOException e) {
                System.err.println("Failed to decompress GZIP data: " + e.getMessage());
            }
            return null;
        } else {
            return compressedData;
        }
    }

    private ByteBuf decompressGzip(ByteBuf byteBuf) {
        byte[] compressedData = ByteUtil.getBytes(byteBuf);
        boolean isGzip = (compressedData.length > 2 && (compressedData[0] & 0xff) == 0x1f && (compressedData[1] & 0xff) == 0x8b);
        if (isGzip) {
            try {
                InputStream byteStream = new ByteArrayInputStream(compressedData);
                GZIPInputStream gzipStream = new GZIPInputStream(byteStream);
                byte[] buffer = new byte[1024];
                int len;
                ByteArrayOutputStream out = new ByteArrayOutputStream();
                while ((len = gzipStream.read(buffer)) != -1) {
                    out.write(buffer, 0, len);
                }
                return ByteUtil.newByteBuf(out.toByteArray());
            } catch (IOException e) {
                System.err.println("Failed to decompress GZIP data: " + e.getMessage());
            }
            return null;
        } else {
            return byteBuf;
        }
    }
}
```

#### grpc 请求路由调用

将 grpc 数据读取出来后，配合前面的 protobuf 序列化部分，就可以将请求数据转化为具体的请求对象。

获取到请求对象后，需要将请求路由到具体的调用方法。

在一次请求的 http2 header frame 中，用 `:path` header 值存储了调用的路径，通过路径即可调用到具体的方法：

```java
public class GrpcDispatcher {

    private static final String GRPC_SERVICE_PACKAGE_NAME = "com.taobao.arthas.grpc.server.service.impl";

    private Map<String, MethodHandle> grpcMethodInvokeMap = new HashMap<>();

    private Map<String, Boolean> grpcMethodStreamMap = new HashMap<>();

    public void loadGrpcService() {
        List<Class<?>> classes = ReflectUtil.findClasses(GRPC_SERVICE_PACKAGE_NAME);
        for (Class<?> clazz : classes) {
            if (clazz.isAnnotationPresent(GrpcService.class)) {
                try {
                    // 处理 service
                    GrpcService grpcService = clazz.getAnnotation(GrpcService.class);
                    Object instance = clazz.getDeclaredConstructor().newInstance();

                    // 处理 method
                    MethodHandles.Lookup lookup = MethodHandles.lookup();
                    Method[] declaredMethods = clazz.getDeclaredMethods();
                    for (Method method : declaredMethods) {
                        if (method.isAnnotationPresent(GrpcMethod.class)) {
                            GrpcMethod grpcMethod = method.getAnnotation(GrpcMethod.class);
                            MethodHandle methodHandle = lookup.unreflect(method);
                            String grpcMethodKey = generateGrpcMethodKey(grpcService.value(), grpcMethod.value());
                            grpcMethodInvokeMap.put(grpcMethodKey, methodHandle.bindTo(instance));
                            grpcMethodStreamMap.put(grpcMethodKey, grpcMethod.stream());
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }
    }

    private String generateGrpcMethodKey(String serviceName, String methodName) {
        return serviceName + "." + methodName;
    }

    public GrpcResponse execute(String serviceName, String methodName, Object arg) throws Throwable {
        MethodHandle methodHandle = grpcMethodInvokeMap.get(generateGrpcMethodKey(serviceName, methodName));
        MethodType type = grpcMethodInvokeMap.get(generateGrpcMethodKey(serviceName, methodName)).type();
        Object execute = methodHandle.invoke(arg);
        GrpcResponse grpcResponse = new GrpcResponse();
        grpcResponse.setClazz(type.returnType());
        grpcResponse.writeResponseData(execute);
        return grpcResponse;
    }

    public GrpcResponse execute(GrpcRequest request) throws Throwable {
        String service = request.getService();
        String method = request.getMethod();
        // protobuf 规范只能有单入参
        request.setClazz(getRequestClass(request.getService(), request.getMethod()));
        ProtobufCodec protobufCodec = ProtobufProxy.getCodecCacheSide(request.getClazz());
        Object decode = protobufCodec.decode(request.readData());
        return this.execute(service, method, decode);
    }

    /**
     * 获取指定 service method 对应的入参类型
     *
     * @param serviceName
     * @param methodName
     * @return
     */
    public Class<?> getRequestClass(String serviceName, String methodName) {
        //protobuf 规范只能有单入参
        return Optional.ofNullable(grpcMethodInvokeMap.get(generateGrpcMethodKey(serviceName, methodName))).orElseThrow(() -> new RuntimeException("The specified grpc method does not exist")).type().parameterArray()[0];
    }

    public void checkGrpcStream(GrpcRequest request) {
        request.setStream(
                Optional.ofNullable(grpcMethodStreamMap.get(generateGrpcMethodKey(request.getService(), request.getMethod())))
                        .orElse(false)
        );
        request.setStreamFirstData(true);
    }
}
```

#### grpc 请求响应

处理完请求后，需要将请求响应给客户端，这里可以 wireshark 抓包 http2 frame，观察一次正常的 grpc 请求会包含什么内容。

wireshark 抓包观察：

![image-20240818210447615](./image-20240818210447615-1735632505978-5.png)

![image-20240818210501661](./image-20240818210501661-1735632509942-7.png)

![image-20240818210514779](./image-20240818210514779-1735632517726-9.png)

![image-20240818210522123](./image-20240818210522123-1735632521652-11.png)

![image-20240818210530001](./image-20240818210530001-1735632525719-13.png)

![image-20240818210549107](./image-20240818210549107-1735632529711-15.png)

![image-20240818210558027](./image-20240818210558027-1735632532683-17.png)

在上图中可以发现一次 grpc 请求的请求响应过程大概如下：

1. 客户端向服务端发送 http2 frame，其中附带了一个 header 和一个 data
2. 客户端向服务端发送一个空的 data frame，表示流结束（end stream）
3. 服务端向客户端发送 ping
4. 客户端响应服务端 pong
5. 服务端响应客户端请求，其中附带了一个 heade
6. 服务端响应客户端请求，其中附带了一个 data 和一个 header
7. 客户端发送 RST_STREAM，结束请求

其中 34 netty 会自动处理，主要看请求的接受和发送。

client 发送请求时，除了正常的附带数据的 http2 data frame 外，还会附带一个标识流结束的 http2 data frame；server 响应请求时，还会附带两个 header。 

```java
private void handleGrpcData(Http2DataFrame dataFrame, ChannelHandlerContext ctx) throws IOException {
    GrpcRequest grpcRequest = dataBuffer.get(dataFrame.stream().id());
    grpcRequest.writeData(dataFrame.content());

    if (grpcRequest.isStream()) {
        // 流式调用，即刻响应
        try {
            GrpcResponse response = new GrpcResponse();
            byte[] bytes = grpcRequest.readData();
            while (bytes != null) {
                ProtobufCodec protobufCodec = ProtobufProxy.getCodecCacheSide(grpcDispatcher.getRequestClass(grpcRequest.getService(), grpcRequest.getMethod()));
                Object decode = protobufCodec.decode(bytes);
                response = grpcDispatcher.execute(grpcRequest.getService(), grpcRequest.getMethod(), decode);

                // 针对第一个响应发送 header
                if (grpcRequest.isStreamFirstData()) {
                    ctx.writeAndFlush(new DefaultHttp2HeadersFrame(response.getEndHeader()).stream(dataFrame.stream()));
                    grpcRequest.setStreamFirstData(false);
                }
                ctx.writeAndFlush(new DefaultHttp2DataFrame(response.getResponseData()).stream(dataFrame.stream()));

                bytes = grpcRequest.readData();
            }

            grpcRequest.clearData();

            if (dataFrame.isEndStream()) {
                ctx.writeAndFlush(new DefaultHttp2HeadersFrame(response.getEndStreamHeader(), true).stream(dataFrame.stream()));
            }
        } catch (Throwable e) {
            processError(ctx, e, dataFrame.stream());
        }
    } else {
        // 非流式调用，等到 endStream 再响应
        if (dataFrame.isEndStream()) {
            try {
                GrpcResponse response = grpcDispatcher.execute(grpcRequest);
                ctx.writeAndFlush(new DefaultHttp2HeadersFrame(response.getEndHeader()).stream(dataFrame.stream()));
                ctx.writeAndFlush(new DefaultHttp2DataFrame(response.getResponseData()).stream(dataFrame.stream()));
                ctx.writeAndFlush(new DefaultHttp2HeadersFrame(response.getEndStreamHeader(), true).stream(dataFrame.stream()));
            } catch (Throwable e) {
                processError(ctx, e, dataFrame.stream());
            }
        }
    }
}
```

对于一元调用，需要在收到 end stream 的 frame 时才响应；对于双向 stream 调用，则每次都需要响应。

#### 结果验证

![a925910e3a991ae54592d2f4c26a7a2](./a925910e3a991ae54592d2f4c26a7a2.png)

![1128115203a1559176da16aa96e1ce3](./1128115203a1559176da16aa96e1ce3.png)

开发完毕后，使用 apifox 针对服务发起调用，验证结果符合预期；

此外也在项目中提供了针对于 protobuf 序列化的单元测试和 grpc 请求的测试方法。经验证，同样符合测试预期。

### 后续计划

1. 在项目编写过程中主要考虑的问题是去除外部依赖，对于性能优化研究的还不够深入。后续需要继续深入优化性能。
2. 由于时间问题，只是提供了一个实现了 grpc 协议的处理框架，但是并未实现某个具体的 arthas 功能。后续需要继续深入实现 arthas 的功能。
3. 对于某些 grpc 实现细节还没有深入研究，例如 gzip 的解析、http2 协议的升级等等。后续需要继续投入。

## 个人总结

在这次项目过程中，我深入了解了 HTTP/2 和 gRPC 协议，学习了如何使用 Wireshark 抓包以观察二进制数据，同时掌握了 Netty 的编写与使用。此外，在借鉴 jprotobuf 的过程中，我对 Java 编译的相关知识也有了更深刻的认识。在编写 gRPC 调用路由的过程中，我更深入地理解了 Java 的方法句柄及其应用。这是我首次参与大型开源项目，借此机会，我不仅提升了自己的技术能力，也拓宽了视野。衷心感谢 OSPP 提供的这个宝贵机会，让我在实践中受益良多。
