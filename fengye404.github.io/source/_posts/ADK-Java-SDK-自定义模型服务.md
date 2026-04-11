---
title: ADK-Java-SDK 自定义模型服务
typora-root-url: ./ADK-java-sdk 自定义模型服务
date: 2025-12-14 05:19:10
tags:
---

# ADK-Java-SDK 自定义模型服务

> 本文由 AI 参与创作

最近在做 Agent 构建相关的工作，而在 Agent 构建这个领域，Google 的 ADK 算是业界标杆之一。最近在学习 ADK 过程中发现，ADK 的 Python SDK 提供了 LiteLLM 快速接入第三方供应商的模型参考： https://adk.wiki/agents/models/#using-open-local-models-via-litellm ，但是 Java SDK 并未提供这样快速接入的能力，于是记录下我在 ADK Java SDK 中 proxy 第三方供应商模型的例子，以供参考。

## ADK Java SDK 模型扩展机制

ADK Java SDK 通过 `BaseLlm` 抽象类提供了模型扩展能力。要接入第三方模型服务商，只需继承该类并实现核心方法即可。

### BaseLlm 核心接口

```java
public abstract class BaseLlm {
    // 模型名称
    protected final String model;
    
    // 核心方法：生成内容
    public abstract Flowable<LlmResponse> generateContent(LlmRequest request, boolean stream);
    
    // 可选：建立实时连接（用于语音等场景）
    public abstract BaseLlmConnection connect(LlmRequest request);
}
```

关键在于实现 `generateContent` 方法，它接收一个 `LlmRequest` 请求对象，返回一个 `Flowable<LlmResponse>` 响应流。其中：

- `LlmRequest` 包含：消息历史（`contents`）、系统指令（`systemInstruction`）、工具定义（`tools`）等
- `LlmResponse` 包含：模型输出（`content`）、是否完成（`turnComplete`）、是否为部分响应（`partial`）等
- `stream` 参数决定是否使用流式输出

## 实现 DashScope 适配器

下面以阿里云 DashScope（通义千问系列模型）为例，展示如何实现一个完整的 LLM 适配器。

### 整体架构

适配器的核心工作是做好两个方向的转换：

```
┌─────────────────────────────────────────────────────────────────┐
│                        DashScopeLlm                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ADK Request ──────┬──────────────────────> DashScope Request  │
│   (LlmRequest)      │                        (GenerationParam)  │
│                     │                                           │
│   • Content[]       │  convertContentsToMessages()              │
│   • systemInstruction  extractSystemInstruction()               │
│   • tools[]         │  buildToolList()                          │
│                     ▼                                           │
│                                                                 │
│   ADK Response <────┴──────────────────────  DashScope Response │
│   (LlmResponse)                              (GenerationResult) │
│                                                                 │
│   • Content         │  convertToLlmResponse()                   │
│   • turnComplete    │  emitStreamResponse()                     │
│   • partial         │                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 核心代码实现

#### 1. 类定义与构造方法

```java
public class DashScopeLlm extends BaseLlm {
    
    private static final String ENV_API_KEY = "DASHSCOPE_API_KEY";
    
    private final String apiKey;
    private final Generation generation;

    public DashScopeLlm(String model, String apiKey) {
        super(model);
        this.apiKey = (apiKey != null) ? apiKey : getEnvApiKey();
        this.generation = new Generation();
    }

    public DashScopeLlm(String model) {
        this(model, null);
    }
}
```

构造方法支持两种方式传入 API Key：显式传入或从环境变量 `DASHSCOPE_API_KEY` 读取。

#### 2. 实现 generateContent 方法

这是适配器的核心入口，负责协调请求转换、API 调用和响应转换：

```java
@Override
public Flowable<LlmResponse> generateContent(LlmRequest request, boolean stream) {
    try {
        // 1. 转换消息历史
        List<Message> messages = buildMessageList(request);
        // 2. 转换工具定义
        List<ToolBase> tools = buildToolList(request);
        // 3. 构建 DashScope 请求参数
        GenerationParam param = buildGenerationParam(request, messages, tools);
        // 4. 执行调用
        return stream ? executeStreamCall(param) : executeBlockingCall(param);
    } catch (Exception e) {
        return Flowable.error(e);
    }
}
```

#### 3. 消息格式转换

ADK 使用 `Content` + `Part` 的消息结构，而 DashScope 使用 `Message` 结构。转换时需要处理三种类型的 Part：

- **文本**：直接拼接到 `content` 字段
- **函数调用**（FunctionCall）：转换为 `toolCalls` 列表
- **函数响应**（FunctionResponse）：转换为 `role=tool` 的消息

```java
private MessageParseResult parseContentParts(List<Part> parts) {
    MessageParseResult result = new MessageParseResult();
    
    for (Part part : parts) {
        if (part.functionCall().isPresent()) {
            // 处理函数调用
            parseFunctionCall(part.functionCall().get(), result.toolCalls);
        } else if (part.functionResponse().isPresent()) {
            // 处理函数响应
            parseFunctionResponse(part.functionResponse().get(), result.toolMessages);
        } else {
            // 处理普通文本
            part.text().ifPresent(result.textBuilder::append);
        }
    }
    return result;
}
```

#### 4. 工具定义转换

ADK 的 `FunctionDeclaration` 需要转换为 DashScope 的 `ToolFunction`：

```java
private ToolBase convertToToolFunction(FunctionDeclaration declaration) {
    FunctionDefinition.FunctionDefinitionBuilder builder = FunctionDefinition.builder()
            .name(declaration.name().orElseThrow())
            .description(declaration.description().orElse(""));

    // 转换参数 Schema
    declaration.parameters().ifPresent(params ->
            builder.parameters(convertSchemaToJson(params)));

    return ToolFunction.builder().function(builder.build()).build();
}
```

#### 5. 流式响应处理

流式调用时，需要追踪已发送的文本长度，实现增量输出：

```java
private void emitStreamResponse(FlowableEmitter<LlmResponse> emitter,
                                GenerationResult result,
                                StreamContext context) {
    var choice = result.getOutput().getChoices().get(0);
    var message = choice.getMessage();
    boolean isComplete = isFinishReasonComplete(choice.getFinishReason());

    // 提取增量内容
    List<Part> parts = extractIncrementalParts(message, context, isComplete);
    if (parts.isEmpty()) return;

    // 构建并发送响应
    LlmResponse response = buildStreamResponse(parts, isComplete);
    emitter.onNext(response);
}

private static class StreamContext {
    int emittedTextLength = 0;  // 追踪已发送的文本长度
}
```

#### 6. 响应格式转换

将 DashScope 的响应转换回 ADK 格式，包括文本和工具调用：

```java
private LlmResponse convertToLlmResponse(GenerationResult result) {
    var choice = result.getOutput().getChoices().get(0);
    var message = choice.getMessage();
    List<Part> parts = extractResponseParts(message);

    LlmResponse.Builder builder = LlmResponse.builder();
    if (!parts.isEmpty()) {
        builder.content(Content.builder()
                .role("model")
                .parts(ImmutableList.copyOf(parts))
                .build());
    }
    if ("stop".equalsIgnoreCase(choice.getFinishReason())) {
        builder.turnComplete(true);
    }
    return builder.build();
}
```

## 使用示例

完成适配器后，就可以在 ADK 中使用通义千问模型了：

```java
public class Main {
    public static void main(String[] args) {
        // 创建使用 DashScope 的 Agent
        LlmAgent agent = LlmAgent.builder()
                .name("weatherAgent")
                .description("天气查询助手")
                .instruction("你是一个天气查询助手，可以帮用户查询天气信息。")
                .model(new DashScopeLlm("qwen-plus"))  // 使用通义千问
                .tools(FunctionTool.create(Main.class, "queryWeather"))
                .build();

        // 创建 Runner 和 Session
        InMemoryRunner runner = new InMemoryRunner(agent);
        Session session = runner.sessionService()
                .createSession(runner.appName(), "user1234")
                .blockingGet();

        // 配置流式输出
        RunConfig runConfig = RunConfig.builder()
                .setStreamingMode(RunConfig.StreamingMode.SSE)
                .build();

        // 运行并处理响应
        runner.runAsync(session.userId(), session.id(),
                Content.fromParts(Part.fromText("查询下杭州天气")),
                runConfig
        ).blockingForEach(System.out::println);
    }

    @Annotations.Schema(name = "queryWeather", description = "查询天气")
    public static Map<String, String> queryWeather(
            @Annotations.Schema(name = "city", description = "城市") String city) {
        return Map.of("city", city, "weather", "晴，温度 30");
    }
}
```

## 适配其他模型服务商

基于同样的思路，你可以轻松适配其他模型服务商：

| 服务商 | SDK | 核心转换点 |
|--------|-----|-----------|
| OpenAI | openai-java | ChatCompletionRequest ↔ LlmRequest |
| Azure OpenAI | azure-ai-openai | 同 OpenAI，增加 deployment 配置 |
| 百度文心 | wenxin-sdk | ChatRequest ↔ LlmRequest |
| 智谱 AI | zhipu-sdk | ChatCompletionRequest ↔ LlmRequest |

关键是理解 ADK 的数据结构（`Content`、`Part`、`FunctionCall`、`FunctionResponse`），并将其与目标 SDK 的数据结构进行正确映射。

## 总结

ADK Java SDK 虽然没有像 Python SDK 那样提供 LiteLLM 的开箱即用支持，但其 `BaseLlm` 抽象类设计良好，扩展起来并不复杂。核心工作就是做好两个方向的格式转换：

1. **请求转换**：ADK 的 `LlmRequest` → 目标 SDK 的请求格式
2. **响应转换**：目标 SDK 的响应格式 → ADK 的 `LlmResponse`

## 完整代码

```java
package top.fengye;

import com.alibaba.dashscope.aigc.generation.Generation;
import com.alibaba.dashscope.aigc.generation.GenerationParam;
import com.alibaba.dashscope.aigc.generation.GenerationResult;
import com.alibaba.dashscope.common.Message;
import com.alibaba.dashscope.common.Role;
import com.alibaba.dashscope.tools.FunctionDefinition;
import com.alibaba.dashscope.tools.ToolBase;
import com.alibaba.dashscope.tools.ToolCallBase;
import com.alibaba.dashscope.tools.ToolCallFunction;
import com.alibaba.dashscope.tools.ToolFunction;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jdk8.Jdk8Module;
import com.google.adk.models.BaseLlm;
import com.google.adk.models.BaseLlmConnection;
import com.google.adk.models.LlmRequest;
import com.google.adk.models.LlmResponse;
import com.google.common.collect.ImmutableList;
import com.google.common.collect.ImmutableMap;
import com.google.genai.types.Content;
import com.google.genai.types.FunctionCall;
import com.google.genai.types.GenerateContentConfig;
import com.google.genai.types.Part;
import com.google.genai.types.Schema;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import io.reactivex.rxjava3.core.BackpressureStrategy;
import io.reactivex.rxjava3.core.Flowable;
import io.reactivex.rxjava3.core.FlowableEmitter;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

/**
 * 阿里云 DashScope 大模型适配器。
 * <p>
 * 该类实现了 Google ADK 框架的 {@link BaseLlm} 接口，将阿里云 DashScope API 无缝集成到 ADK 工作流中。
 * 支持普通调用和流式调用两种模式，并完整支持 Function Calling 能力。
 * </p>
 *
 * <h3>使用示例：</h3>
 * <pre>{@code
 * // 使用环境变量中的 API Key
 * DashScopeLlm llm = new DashScopeLlm("qwen-plus");
 *
 * // 显式指定 API Key
 * DashScopeLlm llm = new DashScopeLlm("qwen-max", "your-api-key");
 * }</pre>
 *
 * @author fengye
 * @see BaseLlm
 */
public class DashScopeLlm extends BaseLlm {

    // ============================= 常量定义 =============================

    /** 环境变量名：DashScope API Key */
    private static final String ENV_API_KEY = "DASHSCOPE_API_KEY";

    /** JSON 序列化器，支持 JDK8 Optional 类型 */
    private static final ObjectMapper MAPPER = new ObjectMapper().registerModule(new Jdk8Module());

    /** 角色标识：模型 */
    private static final String ROLE_MODEL = "model";

    /** 结束原因：正常停止 */
    private static final String FINISH_REASON_STOP = "stop";

    /** 结束原因：工具调用 */
    private static final String FINISH_REASON_TOOL_CALLS = "tool_calls";

    /** 工具调用 JSON 模板 */
    private static final String TOOL_CALL_JSON_TEMPLATE =
            "{\"id\":\"%s\",\"type\":\"function\",\"function\":{\"name\":\"%s\",\"arguments\":\"%s\"}}";

    // ============================= 成员变量 =============================

    /** DashScope API Key */
    private final String apiKey;

    /** DashScope 生成服务客户端 */
    private final Generation generation;

    // ============================= 构造方法 =============================

    /**
     * 使用指定模型和 API Key 创建 DashScope LLM 实例。
     *
     * @param model  模型名称，如 "qwen-plus"、"qwen-max" 等
     * @param apiKey API Key，若为 null 则从环境变量 {@value ENV_API_KEY} 获取
     * @throws IllegalStateException 当 apiKey 为 null 且环境变量未设置时抛出
     */
    public DashScopeLlm(String model, String apiKey) {
        super(model);
        this.apiKey = (apiKey != null) ? apiKey : getEnvApiKey();
        this.generation = new Generation();
    }

    /**
     * 使用指定模型创建 DashScope LLM 实例，API Key 从环境变量获取。
     *
     * @param model 模型名称
     * @throws IllegalStateException 当环境变量 {@value ENV_API_KEY} 未设置时抛出
     */
    public DashScopeLlm(String model) {
        this(model, null);
    }

    // ============================= 公开方法 =============================

    /**
     * 生成内容响应。
     * <p>
     * 根据请求参数调用 DashScope API，支持普通调用和流式调用两种模式。
     * </p>
     *
     * @param request 请求参数，包含消息历史、工具定义、系统指令等
     * @param stream  是否使用流式调用
     * @return 响应流，流式调用时返回多个部分响应，普通调用时返回单个完整响应
     */
    @Override
    public Flowable<LlmResponse> generateContent(LlmRequest request, boolean stream) {
        try {
            List<Message> messages = buildMessageList(request);
            List<ToolBase> tools = buildToolList(request);
            GenerationParam param = buildGenerationParam(request, messages, tools);

            return stream ? executeStreamCall(param) : executeBlockingCall(param);
        } catch (Exception e) {
            return Flowable.error(e);
        }
    }

    /**
     * 建立实时连接（当前不支持）。
     *
     * @param request 请求参数
     * @return 永远不会返回，总是抛出异常
     * @throws UnsupportedOperationException 总是抛出此异常
     */
    @Override
    public BaseLlmConnection connect(LlmRequest request) {
        throw new UnsupportedOperationException("实时连接功能暂不支持");
    }

    // ============================= 参数构建 =============================

    /**
     * 构建 DashScope 请求参数。
     */
    private GenerationParam buildGenerationParam(LlmRequest request, List<Message> messages, List<ToolBase> tools) {
        GenerationParam.GenerationParamBuilder<?, ?> builder = GenerationParam.builder()
                .model(request.model().orElse(model()))
                .messages(messages)
                .apiKey(apiKey)
                .resultFormat(GenerationParam.ResultFormat.MESSAGE);

        if (!tools.isEmpty()) {
            builder.tools(tools);
        }

        return builder.build();
    }

    /**
     * 构建消息列表，包含系统指令和历史消息。
     */
    private List<Message> buildMessageList(LlmRequest request) {
        List<Message> messages = convertContentsToMessages(request.contents());
        extractSystemInstruction(request).ifPresent(instruction ->
                messages.add(0, Message.builder()
                        .role(Role.SYSTEM.getValue())
                        .content(instruction)
                        .build())
        );
        return messages;
    }

    /**
     * 从请求配置中提取系统指令。
     */
    private Optional<String> extractSystemInstruction(LlmRequest request) {
        return request.config()
                .flatMap(GenerateContentConfig::systemInstruction)
                .flatMap(Content::parts)
                .map(parts -> parts.stream()
                        .map(part -> part.text().orElse(""))
                        .filter(text -> !text.isEmpty())
                        .collect(Collectors.joining("\n")))
                .filter(text -> !text.isEmpty());
    }

    /**
     * 构建工具列表。
     */
    private List<ToolBase> buildToolList(LlmRequest request) {
        return request.config()
                .flatMap(GenerateContentConfig::tools)
                .orElse(ImmutableList.of())
                .stream()
                .filter(tool -> tool.functionDeclarations().isPresent())
                .flatMap(tool -> tool.functionDeclarations().get().stream())
                .map(this::convertToToolFunction)
                .collect(Collectors.toList());
    }

    /**
     * 将 ADK 函数声明转换为 DashScope 工具函数。
     */
    private ToolBase convertToToolFunction(com.google.genai.types.FunctionDeclaration declaration) {
        FunctionDefinition.FunctionDefinitionBuilder builder = FunctionDefinition.builder()
                .name(declaration.name().orElseThrow(() ->
                        new IllegalArgumentException("函数名称不能为空")))
                .description(declaration.description().orElse(""));

        declaration.parameters().ifPresent(params ->
                builder.parameters(convertSchemaToJson(params)));

        return ToolFunction.builder().function(builder.build()).build();
    }

    // ============================= 调用执行 =============================

    /**
     * 执行阻塞式调用。
     */
    private Flowable<LlmResponse> executeBlockingCall(GenerationParam param) throws Exception {
        GenerationResult result = generation.call(param);
        return Flowable.just(convertToLlmResponse(result));
    }

    /**
     * 执行流式调用。
     */
    private Flowable<LlmResponse> executeStreamCall(GenerationParam param) {
        param.setIncrementalOutput(false);
        StreamContext context = new StreamContext();

        return Flowable.create(emitter ->
                        generation.streamCall(param).subscribe(
                                result -> emitStreamResponse(emitter, result, context),
                                error -> emitter.onError((Throwable) error),
                                emitter::onComplete
                        ),
                BackpressureStrategy.BUFFER
        );
    }

    /**
     * 流式上下文，用于跟踪增量文本输出。
     */
    private static class StreamContext {
        int emittedTextLength = 0;
    }

    /**
     * 发送流式响应。
     */
    private void emitStreamResponse(FlowableEmitter<LlmResponse> emitter,
                                    GenerationResult result,
                                    StreamContext context) {
        var output = result.getOutput();

        // 处理无 choices 的简单文本响应
        if (output == null || output.getChoices() == null || output.getChoices().isEmpty()) {
            if (output != null && output.getText() != null) {
                emitter.onNext(buildPartialTextResponse(output.getText()));
            }
            return;
        }

        // 处理标准 choices 响应
        var choice = output.getChoices().get(0);
        var message = choice.getMessage();
        boolean isComplete = isFinishReasonComplete(choice.getFinishReason());

        List<Part> parts = extractIncrementalParts(message, context, isComplete);
        if (parts.isEmpty()) {
            return;
        }

        LlmResponse response = buildStreamResponse(parts, isComplete);
        emitter.onNext(response);
    }

    /**
     * 判断是否为完成状态。
     */
    private boolean isFinishReasonComplete(String reason) {
        return FINISH_REASON_STOP.equalsIgnoreCase(reason)
                || FINISH_REASON_TOOL_CALLS.equalsIgnoreCase(reason);
    }

    /**
     * 提取增量内容部分。
     */
    private List<Part> extractIncrementalParts(Message message, StreamContext context, boolean isComplete) {
        List<Part> parts = new ArrayList<>();

        // 提取增量文本
        String content = message.getContent();
        if (content != null && content.length() > context.emittedTextLength) {
            String incrementalText = content.substring(context.emittedTextLength);
            parts.add(Part.fromText(incrementalText));
            context.emittedTextLength = content.length();
        }

        // 完成时提取工具调用
        if (isComplete && message.getToolCalls() != null) {
            message.getToolCalls().stream()
                    .map(this::convertToFunctionCallPart)
                    .filter(Optional::isPresent)
                    .map(Optional::get)
                    .forEach(parts::add);
        }

        return parts;
    }

    /**
     * 构建部分文本响应。
     */
    private LlmResponse buildPartialTextResponse(String text) {
        return LlmResponse.builder()
                .content(Content.builder()
                        .role(ROLE_MODEL)
                        .parts(Part.fromText(text))
                        .build())
                .partial(true)
                .build();
    }

    /**
     * 构建流式响应。
     */
    private LlmResponse buildStreamResponse(List<Part> parts, boolean isComplete) {
        LlmResponse.Builder builder = LlmResponse.builder()
                .content(Content.builder()
                        .role(ROLE_MODEL)
                        .parts(ImmutableList.copyOf(parts))
                        .build());

        return isComplete
                ? builder.turnComplete(true).build()
                : builder.partial(true).build();
    }

    // ============================= 消息转换 =============================

    /**
     * 将 ADK Content 列表转换为 DashScope Message 列表。
     */
    private List<Message> convertContentsToMessages(List<Content> contents) {
        List<Message> messages = new ArrayList<>();

        for (Content content : contents) {
            String role = content.role().orElse("user");
            List<Part> parts = content.parts().orElse(ImmutableList.of());

            MessageParseResult parseResult = parseContentParts(parts);
            addParsedMessages(messages, role, parseResult);
        }

        return messages;
    }

    /**
     * 消息解析结果，包含文本、工具调用和工具响应。
     */
    private static class MessageParseResult {
        final StringBuilder textBuilder = new StringBuilder();
        final List<ToolCallBase> toolCalls = new ArrayList<>();
        final List<Message> toolMessages = new ArrayList<>();
    }

    /**
     * 解析 Content 中的各类 Part。
     */
    private MessageParseResult parseContentParts(List<Part> parts) {
        MessageParseResult result = new MessageParseResult();

        for (Part part : parts) {
            if (part.functionCall().isPresent()) {
                parseFunctionCall(part.functionCall().get(), result.toolCalls);
            } else if (part.functionResponse().isPresent()) {
                parseFunctionResponse(part.functionResponse().get(), result.toolMessages);
            } else {
                part.text().ifPresent(result.textBuilder::append);
            }
        }

        return result;
    }

    /**
     * 解析函数调用并添加到工具调用列表。
     */
    private void parseFunctionCall(FunctionCall functionCall, List<ToolCallBase> toolCalls) {
        String id = functionCall.id().orElse("call_" + System.currentTimeMillis());
        String name = functionCall.name().orElse("");
        String args = escapeJsonString(toJson(functionCall.args().orElse(ImmutableMap.of())));

        try {
            String json = String.format(TOOL_CALL_JSON_TEMPLATE, id, name, args);
            ToolCallFunction toolCall = com.alibaba.dashscope.utils.JsonUtils.fromJson(json, ToolCallFunction.class);
            toolCalls.add(toolCall);
        } catch (Exception ignored) {
            // 解析失败时忽略该工具调用
        }
    }

    /**
     * 解析函数响应并添加到工具消息列表。
     */
    private void parseFunctionResponse(com.google.genai.types.FunctionResponse response, List<Message> toolMessages) {
        Message message = Message.builder()
                .role("tool")
                .content(response.response().map(this::toJson).orElse("{}"))
                .name(response.name().orElse(""))
                .toolCallId(response.id().orElse(""))
                .build();
        toolMessages.add(message);
    }

    /**
     * 将解析结果添加到消息列表。
     */
    private void addParsedMessages(List<Message> messages, String role, MessageParseResult result) {
        String text = result.textBuilder.toString();

        if (!result.toolCalls.isEmpty()) {
            // 带工具调用的助手消息
            Message.MessageBuilder builder = Message.builder()
                    .role(Role.ASSISTANT.getValue())
                    .toolCalls(result.toolCalls);
            if (!text.isEmpty()) {
                builder.content(text);
            }
            messages.add(builder.build());
        } else if (!text.isEmpty()) {
            // 纯文本消息
            messages.add(Message.builder()
                    .role(mapRole(role))
                    .content(text)
                    .build());
        }

        // 添加工具响应消息
        messages.addAll(result.toolMessages);
    }

    /**
     * 将 ADK 角色映射为 DashScope 角色。
     */
    private String mapRole(String adkRole) {
        return switch (adkRole) {
            case "model", "assistant" -> Role.ASSISTANT.getValue();
            case "system" -> Role.SYSTEM.getValue();
            default -> Role.USER.getValue();
        };
    }

    // ============================= 响应转换 =============================

    /**
     * 将 DashScope 响应转换为 ADK 响应。
     */
    private LlmResponse convertToLlmResponse(GenerationResult result) {
        var output = result.getOutput();

        // 处理无 choices 的简单响应
        if (output == null || output.getChoices() == null || output.getChoices().isEmpty()) {
            if (output != null && output.getText() != null) {
                return buildPartialTextResponse(output.getText());
            }
            return LlmResponse.builder().build();
        }

        // 处理标准 choices 响应
        var choice = output.getChoices().get(0);
        var message = choice.getMessage();
        List<Part> parts = extractResponseParts(message);

        LlmResponse.Builder builder = LlmResponse.builder();
        if (!parts.isEmpty()) {
            builder.content(Content.builder()
                    .role(ROLE_MODEL)
                    .parts(ImmutableList.copyOf(parts))
                    .build());
        }
        if (FINISH_REASON_STOP.equalsIgnoreCase(choice.getFinishReason())) {
            builder.turnComplete(true);
        }

        return builder.build();
    }

    /**
     * 从消息中提取响应部分。
     */
    private List<Part> extractResponseParts(Message message) {
        List<Part> parts = new ArrayList<>();

        // 提取文本内容
        String content = message.getContent();
        if (content != null && !content.isEmpty()) {
            parts.add(Part.fromText(content));
        }

        // 提取工具调用
        if (message.getToolCalls() != null) {
            message.getToolCalls().stream()
                    .map(this::convertToFunctionCallPart)
                    .filter(Optional::isPresent)
                    .map(Optional::get)
                    .forEach(parts::add);
        }

        return parts;
    }

    /**
     * 将工具调用转换为 FunctionCall Part。
     */
    private Optional<Part> convertToFunctionCallPart(ToolCallBase toolCall) {
        if (!(toolCall instanceof ToolCallFunction functionCall) || functionCall.getFunction() == null) {
            return Optional.empty();
        }

        String name = functionCall.getFunction().getName();
        String arguments = functionCall.getFunction().getArguments();

        if (name == null || name.isEmpty()) {
            return Optional.empty();
        }

        return parseArguments(arguments).map(argsMap ->
                Part.builder()
                        .functionCall(FunctionCall.builder()
                                .id(toolCall.getId())
                                .name(name)
                                .args(argsMap)
                                .build())
                        .build()
        );
    }

    /**
     * 解析参数 JSON 字符串为 Map。
     */
    private Optional<Map<String, Object>> parseArguments(String arguments) {
        if (arguments == null || arguments.isEmpty()) {
            return Optional.of(ImmutableMap.of());
        }

        String trimmed = arguments.trim();
        if (!trimmed.startsWith("{") || !trimmed.endsWith("}")) {
            return Optional.empty();
        }

        try {
            Map<String, Object> argsMap = MAPPER.readValue(arguments, new TypeReference<>() {});
            return Optional.of(argsMap);
            } catch (Exception e) {
                return Optional.empty();
            }
        }

    // ============================= Schema 转换 =============================

    /**
     * 将 ADK Schema 转换为 JSON 对象。
     */
    private JsonObject convertSchemaToJson(Schema schema) {
        JsonObject json = new JsonObject();

        schema.type().ifPresent(type -> json.addProperty("type", type.toString()));
        schema.description().ifPresent(desc -> json.addProperty("description", desc));

        schema.properties().ifPresent(properties -> {
            JsonObject propsJson = new JsonObject();
            properties.forEach((key, value) -> propsJson.add(key, convertSchemaToJson(value)));
            json.add("properties", propsJson);
        });

        schema.required()
                .filter(required -> !required.isEmpty())
                .ifPresent(required -> {
                    JsonArray requiredArray = new JsonArray();
                    required.forEach(requiredArray::add);
                    json.add("required", requiredArray);
                });

        return json;
    }

    // ============================= 工具方法 =============================

    /**
     * 从环境变量获取 API Key。
     */
    private static String getEnvApiKey() {
        String key = System.getenv(ENV_API_KEY);
        if (key == null || key.isEmpty()) {
            throw new IllegalStateException("环境变量 " + ENV_API_KEY + " 未设置");
        }
        return key;
    }

    /**
     * 将 Map 序列化为 JSON 字符串。
     */
    private String toJson(Map<String, Object> map) {
        try {
            return MAPPER.writeValueAsString(map);
        } catch (Exception e) {
            return "{}";
        }
    }

    /**
     * 转义 JSON 字符串中的特殊字符。
     */
    private String escapeJsonString(String json) {
        return json.replace("\\", "\\\\").replace("\"", "\\\"");
    }
}
```

