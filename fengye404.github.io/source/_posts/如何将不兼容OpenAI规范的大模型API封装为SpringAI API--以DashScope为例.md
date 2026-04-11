---
title: 如何将不兼容OpenAI规范的大模型API封装为SpringAI API--以DashScope为例
typora-root-url: ./自定义实现 Spring AI 的 ChatModel 接口：轻松封装百炼 DashScope API
date: 2025-06-02 18:03:33
tags:
---

# 如何将不兼容OpenAI规范的大模型API封装为SpringAI API--以DashScope为例

> 引言:
>
> 在实际开发中，我们经常需要调用不同的大模型 API，而 Spring AI 提供了统一接口来简化这一过程。然而，Spring AI 并未直接支持所有模型提供方（如百炼 DashScope）。本文通过实现 `ChatModel` 接口，演示如何将任意大模型 API（以百炼为例）封装为 Spring AI 可用的模型，从而实现灵活切换和功能扩展。 

最近项目开发中经常用到 Spring AI，作为 Spring 全家桶的一员，它为 AI 生态封装了一套统一、易用的 API 规范，可以很方便地实现工具调用等特性。

同时 Spring AI 适配了一些模型提供方的 API，你可以在 spring application 配置文件中配置 url + api key 做到开箱即用。

但是美中不足的是，Spring AI 适配的模型提供方有限，目前支持的列表可以看官方文档：https://docs.spring.io/spring-ai/reference/api/chat/comparison.html

很遗憾，其中就不包含我个人平时经常用到的百炼，好消息是 spring ai alibaba 封装了百炼，你可以引入 spring ai alibaba 来直接配置 ChatClient。

“如无必要，勿增实体”--我个人不喜欢在项目中以这样的形式引入一些依赖，况且模型提供方的切换是必然的诉求，百炼有 spring ai alibaba 的支持，其他大模型 API 要怎么办呢？有没有一种方法可以直接封装任意大模型 API 为 Spring AI API？

有的兄弟，有的。Spring AI 提供了 `ChatModel` 接口，实现这个接口就可以将任意的大模型 API 封装为 Spring AI 的 API。



本文将以百炼 DashScope API 为例，介绍如何将各大模型提供商的 API 封装为 Spring AI 模型

百炼 DashScope 文档：https://help.aliyun.com/zh/model-studio/use-qwen-by-calling-api#a9b7b197e2q2v

## maven 配置

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.ai</groupId>
            <artifactId>spring-ai-bom</artifactId>
            <version>1.0.0-SNAPSHOT</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependency>
    <groupId>com.alibaba</groupId>
    <artifactId>dashscope-sdk-java</artifactId>
    <version>2.18.2</version>
</dependency>

<dependencies>
    <!-- Spring Boot Starter Web -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-web</artifactId>
    </dependency>

    <!-- Spring Boot Starter -->
    <dependency>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter</artifactId>
    </dependency>

    <!-- https://mvnrepository.com/artifact/com.alibaba/dashscope-sdk-java -->
    <dependency>
        <groupId>com.alibaba</groupId>
        <artifactId>dashscope-sdk-java</artifactId>
        <version>2.18.2</version>
    </dependency>

    <!-- https://mvnrepository.com/artifact/com.github.victools/jsonschema-generator -->
    <dependency>
        <groupId>com.github.victools</groupId>
        <artifactId>jsonschema-generator</artifactId>
        <version>4.38.0</version>
    </dependency>
</dependencies>
```

## 代码示例

### 完整代码

下面是一个实现了 ChatModel 接口的代码示例。代码中实现了 ChatModel 的 call、stream 接口且支持 function call：

```java
package top.fengye.controller.model;

import com.alibaba.dashscope.aigc.generation.GenerationOutput;
import com.alibaba.dashscope.aigc.generation.GenerationParam;
import com.alibaba.dashscope.aigc.generation.GenerationResult;
import com.alibaba.dashscope.aigc.generation.GenerationUsage;
import com.alibaba.dashscope.common.Message;
import com.alibaba.dashscope.common.Role;
import com.alibaba.dashscope.tools.*;
import com.alibaba.dashscope.utils.JsonUtils;
import io.reactivex.Flowable;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.advisor.SimpleLoggerAdvisor;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.ToolResponseMessage;
import org.springframework.ai.chat.metadata.ChatGenerationMetadata;
import org.springframework.ai.chat.metadata.ChatResponseMetadata;
import org.springframework.ai.chat.metadata.DefaultUsage;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.model.Generation;
import org.springframework.ai.chat.prompt.ChatOptions;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.model.tool.*;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.ai.tool.definition.ToolDefinition;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;
import reactor.core.publisher.Flux;
import reactor.core.scheduler.Schedulers;
import top.fengye.controller.tool.WeatherService;

import java.util.*;
import java.util.concurrent.atomic.AtomicReference;
import java.util.stream.Collectors;

/**
 * @author: FengYe
 * @date: 2025/6/5 02:40
 * @description: BailianModel
 */
@Slf4j
public class DashScopeModel implements ChatModel {

    private final ToolExecutionEligibilityPredicate toolExecutionEligibilityPredicate = new DefaultToolExecutionEligibilityPredicate();

    private final ToolCallingManager toolCallingManager = ToolCallingManager.builder().build();

    @Override
    public ChatResponse call(Prompt prompt) {
        ChatResponse chatResponse = this.internalCall(prompt);
        // 工具执行后，返回的结果再发给模型
        if (this.toolExecutionEligibilityPredicate.isToolExecutionRequired(prompt.getOptions(), chatResponse)) {
            ToolExecutionResult toolExecutionResult = this.toolCallingManager.executeToolCalls(prompt, chatResponse);
            return toolExecutionResult.returnDirect() ? ChatResponse.builder().from(chatResponse).generations(ToolExecutionResult.buildGenerations(toolExecutionResult)).build()
                    : this.internalCall(new Prompt(toolExecutionResult.conversationHistory(), prompt.getOptions()));
        } else {
            return chatResponse;
        }
    }

    private ChatResponse internalCall(Prompt prompt) {
        GenerationParam generationParam = convertDashScopeParamBuilder(prompt)
                .resultFormat(GenerationParam.ResultFormat.MESSAGE)
                .incrementalOutput(false).build();
        com.alibaba.dashscope.aigc.generation.Generation gen = new com.alibaba.dashscope.aigc.generation.Generation();
        GenerationResult res = null;
        try {
            res = gen.call(generationParam);
        } catch (Exception e) {
            log.error("DashScopeModel call error", e);
            return null;
        }
        ChatResponse chatResponse = convertDashScopeResponse(res);
        return chatResponse;
    }

    @Override
    public Flux<ChatResponse> stream(Prompt prompt) {
        AtomicReference<List<ChatResponse>> toolCall = new AtomicReference<>(new ArrayList<>());
        Flux<ChatResponse> chatResponseFlux = internalStream(prompt);

        return Flux.create(sink -> {
            chatResponseFlux.subscribe(
                    chatResponse -> {
                        if (toolExecutionEligibilityPredicate.isToolExecutionRequired(prompt.getOptions(), chatResponse)) {
                            toolCall.get().add(chatResponse);
                        }
                        sink.next(chatResponse);
                    },
                    sink::error,
                    () -> {
                        // 流式输出下，模型返回的 function call response 会分多次返回，需要 merge 一下
                        if (!toolCall.get().isEmpty()) {
                            // 1. 手动构造出 finishReason 为 toolCall 的 ChatResponse，并且推送到流中
                            ChatResponse toolCallResponse = this.mergeToolCallResponse(toolCall.get());
                            sink.next(toolCallResponse);

                            // 2. 发起调用，获取结果并推送到流中
                            ToolExecutionResult toolExecutionResult = toolCallingManager.executeToolCalls(prompt, toolCallResponse);
                            sink.next(
                                    ChatResponse.builder()
                                            .from(toolCallResponse)
                                            .metadata(ChatResponseMetadata.builder().id(UUID.randomUUID().toString()).build())
                                            .generations(ToolExecutionResult.buildGenerations(toolExecutionResult))
                                            .build()
                            );

                            if (toolExecutionResult.returnDirect()) {
                                sink.complete();
                            } else {
                                this.stream(new Prompt(toolExecutionResult.conversationHistory(), prompt.getOptions())).subscribe(
                                        sink::next,
                                        sink::error,
                                        sink::complete
                                );
                            }
                        } else {
                            sink.complete();
                        }
                    }
            );
        });
    }

    private Flux<ChatResponse> internalStream(Prompt prompt) {
        GenerationParam generationParam = convertDashScopeParamBuilder(prompt)
                .resultFormat(GenerationParam.ResultFormat.MESSAGE)
                .incrementalOutput(true).build();
        com.alibaba.dashscope.aigc.generation.Generation gen = new com.alibaba.dashscope.aigc.generation.Generation();
        try {
            Flux<GenerationResult> flux = Flux.from(gen.streamCall(generationParam));
            return flux.map(this::convertDashScopeResponse);
        } catch (Exception e) {
            log.error("DashScopeModel call error", e);
            return null;
        }
    }

    private ChatResponse convertDashScopeResponse(GenerationResult res) {
        GenerationOutput.Choice choice = res.getOutput().getChoices().getFirst();
        if (null == choice) {
            throw new IllegalArgumentException("output is null");
        }
        // 1.构造AssistantMessage
        List<ToolCallBase> dsTool = choice.getMessage().getToolCalls();
        AssistantMessage assistantMessage = null;
        if (CollectionUtils.isEmpty(dsTool)) {
            assistantMessage = new AssistantMessage(choice.getMessage().getContent());
        } else {
            List<AssistantMessage.ToolCall> list = dsTool.stream().map(t -> {
                ToolCallFunction toolCallFunction = (ToolCallFunction) t;
                return new AssistantMessage.ToolCall(toolCallFunction.getId(), toolCallFunction.getFunction().getName(),
                        toolCallFunction.getFunction().getName(), toolCallFunction.getFunction().getArguments());
            }).toList();

            // 按需添加
            HashMap<String, Object> properties = new HashMap<>();
            assistantMessage = new AssistantMessage(choice.getMessage().getContent(), properties, list);
        }

        // 2.构造Generation
        ChatGenerationMetadata chatGenerationMetadata = ChatGenerationMetadata.builder().finishReason(choice.getFinishReason()).build();
        Generation generation = new Generation(assistantMessage, chatGenerationMetadata);

        // 3.构造ChatResponse
        GenerationUsage dsUsage = res.getUsage();
        DefaultUsage usage = new DefaultUsage(dsUsage.getInputTokens(), dsUsage.getOutputTokens(), dsUsage.getTotalTokens());
        ChatResponseMetadata chatResponseMetadata = ChatResponseMetadata.builder()
                .usage(usage)
                .id(res.getRequestId()).build();
        return new ChatResponse(List.of(generation), chatResponseMetadata);
    }

    private GenerationParam.GenerationParamBuilder<?, ?> convertDashScopeParamBuilder(Prompt prompt) {
        List<org.springframework.ai.chat.messages.Message> messages = prompt.getInstructions();
        ChatOptions options = prompt.getOptions();
        if (null == options) {
            throw new IllegalArgumentException("options is null");
        }

        // 1. 处理大模型 options
        GenerationParam.GenerationParamBuilder<?, ?> paramBuilder = GenerationParam.builder()
                .apiKey(System.getenv("DASHSCOPE_API_KEY"))
                .model(options.getModel())
                .topK(options.getTopK())
                .topP(options.getTopP())
                .maxTokens(options.getMaxTokens())
                .incrementalOutput(false)
                .resultFormat(GenerationParam.ResultFormat.MESSAGE);

        if (Objects.nonNull(options.getTemperature())) {
            paramBuilder.temperature(options.getTemperature().floatValue());
        }
        if (Objects.nonNull(options.getFrequencyPenalty())) {
            paramBuilder.repetitionPenalty(options.getFrequencyPenalty().floatValue());
        }
        if (Objects.nonNull(options.getStopSequences())) {
            paramBuilder.stopStrings(options.getStopSequences());
        }

        // 2. 处理大模型 message
        paramBuilder.messages(messages.stream().map(message -> {
            switch (message.getMessageType()) {
                case USER:
                    return List.of(Message.builder()
                            .role(Role.USER.getValue())
                            .content(message.getText())
                            .build());
                case SYSTEM:
                    return List.of(Message.builder()
                            .role(Role.SYSTEM.getValue())
                            .content(message.getText())
                            .build());
                case ASSISTANT:
                    AssistantMessage assistantMessage = (AssistantMessage) message;
                    List<ToolCallBase> tooCalls = new ArrayList<>();
                    if (assistantMessage.hasToolCalls()) {
                        AssistantMessage.ToolCall toolCall = assistantMessage.getToolCalls().getFirst();
                        ToolCallFunction toolCallFunction = new ToolCallFunction();
                        toolCallFunction.setId(toolCall.id());
                        ToolCallFunction.CallFunction callFunction = toolCallFunction.new CallFunction();
                        callFunction.setName(toolCall.name());
                        callFunction.setArguments(toolCall.arguments());
                        toolCallFunction.setFunction(callFunction);
                        tooCalls.add(toolCallFunction);
                    }
                    return List.of(Message.builder()
                            .role(Role.ASSISTANT.getValue())
                            .content(message.getText())
                            .toolCalls(tooCalls)
                            .build());
                case TOOL:
                    ToolResponseMessage toolResponseMessage = (ToolResponseMessage) message;
                    return toolResponseMessage.getResponses().stream().map(toolResponse -> Message.builder()
                            .role(Role.TOOL.getValue())
                            .toolCallId(toolResponse.id())
                            .name(toolResponse.name())
                            .content(toolResponse.responseData())
                            .build()).toList();
                default:
                    throw new IllegalArgumentException("Invalid messageType: " + message.getMessageType());
            }
        }).flatMap(List::stream).collect(Collectors.toList()));

        // 3.处理大模型 functionCall
        if (options instanceof ToolCallingChatOptions toolCallingChatOptions) {
            List<ToolBase> dashscopeFunctions = new ArrayList<>();
            List<ToolCallback> toolCallbacks = toolCallingChatOptions.getToolCallbacks();
            toolCallbacks.forEach(toolCallback -> {
                ToolDefinition toolDefinition = toolCallback.getToolDefinition();
                dashscopeFunctions.add(ToolFunction.builder().function(FunctionDefinition.builder()
                        .name(toolDefinition.name())
                        .description(toolDefinition.description())
                        .parameters(JsonUtils.parseString(toolDefinition.inputSchema()).getAsJsonObject())
                        .build()
                ).build());
            });
            paramBuilder.tools(dashscopeFunctions);
        }


        return paramBuilder;
    }

    private ChatResponse mergeToolCallResponse(List<ChatResponse> responseList) {
        // 1. 单个 function call 拆分为多个 response 的情况，需要拼接 merge 一下，否则后续 toolCallingManager 调用会失败
        // 例如 response1.arguments = {"location": "  response2.arguments = 杭州"}
        // 拼接后 response.arguments = {"location": "杭州"}
        List<AssistantMessage.ToolCall> toolCallList = new ArrayList<>();
        String mergeToolName = "";
        String mergeArguments = "";
        String mergeId = "";
        for (ChatResponse response : responseList) {
            if (response.getResult().getOutput().getToolCalls().get(0).id() != null) {
                mergeId = mergeId + response.getResult().getOutput().getToolCalls().get(0).id();
            }
            if (response.getResult().getOutput().getToolCalls().get(0).arguments() != null) {
                mergeArguments = mergeArguments + response.getResult().getOutput().getToolCalls().get(0).arguments();
            }
            if (response.getResult().getOutput().getToolCalls().get(0).name() != null) {
                mergeToolName = mergeToolName + response.getResult().getOutput().getToolCalls().get(0).name();
            }

            if (response.hasFinishReasons(Set.of("tool_calls"))) {
                toolCallList.add(
                        new AssistantMessage.ToolCall(mergeId, "function", mergeToolName, mergeArguments)
                );
                mergeId = "";
                mergeToolName = "";
                mergeArguments = "";
            }
        }

        // 2. 一次流中有多个 function call，merge一下
        return ChatResponse.builder()
                .from(responseList.get(0))
                .generations(List.of(
                        new Generation(
                                new AssistantMessage("", Collections.emptyMap(), toolCallList),
                                ChatGenerationMetadata.builder().finishReason("toolCall").build()
                        )
                ))
                .build();
    }


    public static void main(String[] args) {
        DefaultToolCallingChatOptions options = new DefaultToolCallingChatOptions();
        options.setModel("qwen-max");
        ChatClient chatClient = ChatClient.builder(new DashScopeModel())
                .defaultAdvisors(new SimpleLoggerAdvisor())
                .defaultOptions(options)
                .defaultTools(new WeatherService()).build();

        chatClient.prompt().user("杭州天气怎么样").stream().content().subscribe(System.out::println);
        System.out.println(chatClient.prompt().user("杭州天气怎么样").call().content());
    }
}

```

Tool 示例代码：

```java
public class WeatherService {
    @Tool(name = "获取当前天气", description = "获取当前天气信息")
    public String getCurrentWeather(@ToolParam(description = "城市名称") String location) {
        return location+"今天的天气并不好，雨夹雪";
    }
}
```

实现了 ChatModel 后，在使用时，只需要将自定义实现的 ChatModel 对象作为参数传入 ChatClient 即可。

提前配置好环境变量，运行 DashScopeModel 后，将会在控制台输出：

```shell
"杭州今天的天气并不好，雨夹雪"
杭州今天的
天气并不好
，有雨夹雪
。请确保携带雨具
并注意保暖！
杭州今天的天气并不好，有雨夹雪。请确保携带雨具并注意保暖。
```

### 解析

ChatModel 是 Spring AI 定义的接口：

```java
public interface ChatModel extends Model<Prompt, ChatResponse>, StreamingChatModel {

    default String call(String message) {
       Prompt prompt = new Prompt(new UserMessage(message));
       Generation generation = call(prompt).getResult();
       return (generation != null) ? generation.getOutput().getText() : "";
    }

    default String call(Message... messages) {
       Prompt prompt = new Prompt(Arrays.asList(messages));
       Generation generation = call(prompt).getResult();
       return (generation != null) ? generation.getOutput().getText() : "";
    }

    @Override
    ChatResponse call(Prompt prompt);

    default ChatOptions getDefaultOptions() {
       return ChatOptions.builder().build();
    }

    default Flux<ChatResponse> stream(Prompt prompt) {
       throw new UnsupportedOperationException("streaming is not supported");
    }

}
```

我们代码中实现了其中的 call、stream 方法，方法的本质内容实际上就是将 DashScope API 的参数转化为 Spring AI 的参数，因此这里只解析其中的几个关键点：

#### call 执行逻辑

call 方法中的 ToolExecutionEligibilityPredicate 和 ToolCallingManager 起什么作用？

```java
@Override
public ChatResponse call(Prompt prompt) {
    ChatResponse chatResponse = this.internalCall(prompt);
    // 工具执行后，返回的结果再发给模型
    if (this.toolExecutionEligibilityPredicate.isToolExecutionRequired(prompt.getOptions(), chatResponse)) {
        ToolExecutionResult toolExecutionResult = this.toolCallingManager.executeToolCalls(prompt, chatResponse);
        return toolExecutionResult.returnDirect() ? ChatResponse.builder().from(chatResponse).generations(ToolExecutionResult.buildGenerations(toolExecutionResult)).build()
                : this.internalCall(new Prompt(toolExecutionResult.conversationHistory(), prompt.getOptions()));
    } else {
        return chatResponse;
    }
}
```

这两个类是 Spring AI 提供的工具类，分别用于判断当前返回的 ChatResponse 是否需要工具调用，以及发起工具调用并将其转为 ChatResponse。

我们可以在 Spring AI 官方实现的一些 ChatModel 中看到类似的写法，例如 OllamaChatModel（已省去无关代码）：

```java
public class OllamaChatModel implements ChatModel {
    ...
	private final ToolCallingManager toolCallingManager;
	private final ToolExecutionEligibilityPredicate toolExecutionEligibilityPredicate;
    
	@Override
	public ChatResponse call(Prompt prompt) {
		// Before moving any further, build the final request Prompt,
		// merging runtime and default options.
		Prompt requestPrompt = buildRequestPrompt(prompt);
		return this.internalCall(requestPrompt, null);
	}

	private ChatResponse internalCall(Prompt prompt, ChatResponse previousChatResponse) {
		OllamaApi.ChatRequest request = ollamaChatRequest(prompt, false);
		ChatModelObservationContext observationContext = ChatModelObservationContext.builder()
			.prompt(prompt)
			.provider(OllamaApiConstants.PROVIDER_NAME)
			.build();
		ChatResponse response = ChatModelObservationDocumentation.CHAT_MODEL_OPERATION
			.observation(this.observationConvention, DEFAULT_OBSERVATION_CONVENTION, () -> observationContext,
					this.observationRegistry)
			.observe(() -> {
				OllamaApi.ChatResponse ollamaResponse = this.chatApi.chat(request);
				List<AssistantMessage.ToolCall> toolCalls = ollamaResponse.message().toolCalls() == null ? List.of()
						: ollamaResponse.message()
							.toolCalls()
							.stream()
							.map(toolCall -> new AssistantMessage.ToolCall("", "function", toolCall.function().name(),
									ModelOptionsUtils.toJsonString(toolCall.function().arguments())))
							.toList();
				var assistantMessage = new AssistantMessage(ollamaResponse.message().content(), Map.of(), toolCalls);
				ChatGenerationMetadata generationMetadata = ChatGenerationMetadata.NULL;
				if (ollamaResponse.promptEvalCount() != null && ollamaResponse.evalCount() != null) {
					generationMetadata = ChatGenerationMetadata.builder()
						.finishReason(ollamaResponse.doneReason())
						.build();
				}
				var generator = new Generation(assistantMessage, generationMetadata);
				ChatResponse chatResponse = new ChatResponse(List.of(generator),
						from(ollamaResponse, previousChatResponse));
				observationContext.setResponse(chatResponse);
				return chatResponse;
			});

		if (this.toolExecutionEligibilityPredicate.isToolExecutionRequired(prompt.getOptions(), response)) {
			var toolExecutionResult = this.toolCallingManager.executeToolCalls(prompt, response);
			if (toolExecutionResult.returnDirect()) {
				// Return tool execution result directly to the client.
				return ChatResponse.builder()
					.from(response)
					.generations(ToolExecutionResult.buildGenerations(toolExecutionResult))
					.build();
			}
			else {
				// Send the tool execution result back to the model.
				return this.internalCall(new Prompt(toolExecutionResult.conversationHistory(), prompt.getOptions()),
						response);
			}
		}

		return response;
	}
    ...
}
```

当我们使用 function call 请求大模型，大模型当然不会自行发起请求，而是会从我们给出的 function call 工具列表中根据语义选择其一，并填入合适的参数，将结果返回，如下图：

![image-20250715022912919](./image-20250715022912919.png)

此时我们拿到的 ChatResponse 还并不是最终的结果，我们还要判断返回的结果中是否存在 function call（在 Spring AI）新 API 中改为 toolCall；若存在，则需再调用工具后，将工具结果和初次调用大模型返回的 ChatResponse 一同喂给大模型，此时才算是完成一次真正的 function call。

- ToolExecutionEligibilityPredicate：判断 ChatResponse 是否需要发起 function call
- ToolCallingManager：和 @Tool 注解联动，通过反射发起调用；也可以自定义调用逻辑

#### stream & merge 执行逻辑

```java
@Override
public Flux<ChatResponse> stream(Prompt prompt) {
    AtomicReference<List<ChatResponse>> toolCall = new AtomicReference<>(new ArrayList<>());
    Flux<ChatResponse> chatResponseFlux = internalStream(prompt);

    return Flux.create(sink -> {
        chatResponseFlux.subscribe(
            chatResponse -> {
                if (toolExecutionEligibilityPredicate.isToolExecutionRequired(prompt.getOptions(), chatResponse)) {
                    toolCall.get().add(chatResponse);
                }
                sink.next(chatResponse);
            },
            sink::error,
            () -> {
                // 流式输出下，模型返回的 function call response 会分多次返回，需要 merge 一下
                if (!toolCall.get().isEmpty()) {
                    // 1. 手动构造出 finishReason 为 toolCall 的 ChatResponse，并且推送到流中
                    ChatResponse toolCallResponse = this.mergeToolCallResponse(toolCall.get());
                    sink.next(toolCallResponse);

                    // 2. 发起调用，获取结果并推送到流中
                    ToolExecutionResult toolExecutionResult = toolCallingManager.executeToolCalls(prompt, toolCallResponse);
                    sink.next(
                        ChatResponse.builder()
                        .from(toolCallResponse)
                        .metadata(ChatResponseMetadata.builder().id(UUID.randomUUID().toString()).build())
                        .generations(ToolExecutionResult.buildGenerations(toolExecutionResult))
                        .build()
                    );

                    if (toolExecutionResult.returnDirect()) {
                        sink.complete();
                    } else {
                        this.stream(new Prompt(toolExecutionResult.conversationHistory(), prompt.getOptions())).subscribe(
                            sink::next,
                            sink::error,
                            sink::complete
                        );
                    }
                } else {
                    sink.complete();
                }
            }
        );
    });
}
```

Stream 执行逻辑和 call 类似，但需要注意一些流式输出场景下的特殊情况，例如大模型流式返回结果可能如下：

```java
- ChatResponse [metadata={ id: de580ceb-f99a-965d-9178-d5d72e0c603f, usage: DefaultUsage{promptTokens=198, completionTokens=16, totalTokens=214}, rateLimit: org.springframework.ai.chat.metadata.EmptyRateLimit@5d8b8b2f }, generations=[Generation[assistantMessage=AssistantMessage [messageType=ASSISTANT, toolCalls=[ToolCall[id=call_82327cff2ce5432fbd5b5f, type=获取当前天气, name=获取当前天气, arguments={"location": "]], textContent=, metadata={messageType=ASSISTANT}], chatGenerationMetadata=DefaultChatGenerationMetadata[finishReason='null', filters=0, metadata=0]]]]
    
- ChatResponse [metadata={ id: de580ceb-f99a-965d-9178-d5d72e0c603f, usage: DefaultUsage{promptTokens=198, completionTokens=18, totalTokens=216}, rateLimit: org.springframework.ai.chat.metadata.EmptyRateLimit@7c32eed }, generations=[Generation[assistantMessage=AssistantMessage [messageType=ASSISTANT, toolCalls=[ToolCall[id=, type=null, name=null, arguments=杭州"}]], textContent=, metadata={messageType=ASSISTANT}], chatGenerationMetadata=DefaultChatGenerationMetadata[finishReason='tool_calls', filters=0, metadata=0]]]]
```

大模型的流式返回，可能会将 tool call 的 name、arguments 等参数拆分为多个 ChatResponse，因此需要额外做 merge 处理：

```java
private ChatResponse mergeToolCallResponse(List<ChatResponse> responseList) {
    // 1. 单个 function call 拆分为多个 response 的情况，需要拼接 merge 一下，否则后续 toolCallingManager 调用会失败
    // 例如 response1.arguments = {"location": "  response2.arguments = 杭州"}
    // 拼接后 response.arguments = {"location": "杭州"}
    List<AssistantMessage.ToolCall> toolCallList = new ArrayList<>();
    String mergeToolName = "";
    String mergeArguments = "";
    String mergeId = "";
    for (ChatResponse response : responseList) {
        if (response.getResult().getOutput().getToolCalls().get(0).id() != null) {
            mergeId = mergeId + response.getResult().getOutput().getToolCalls().get(0).id();
        }
        if (response.getResult().getOutput().getToolCalls().get(0).arguments() != null) {
            mergeArguments = mergeArguments + response.getResult().getOutput().getToolCalls().get(0).arguments();
        }
        if (response.getResult().getOutput().getToolCalls().get(0).name() != null) {
            mergeToolName = mergeToolName + response.getResult().getOutput().getToolCalls().get(0).name();
        }

        if (response.hasFinishReasons(Set.of("tool_calls"))) {
            toolCallList.add(
                new AssistantMessage.ToolCall(mergeId, "function", mergeToolName, mergeArguments)
            );
            mergeId = "";
            mergeToolName = "";
            mergeArguments = "";
        }
    }

    // 2. 一次流中有多个 function call，merge一下
    return ChatResponse.builder()
        .from(responseList.get(0))
        .generations(List.of(
            new Generation(
                new AssistantMessage("", Collections.emptyMap(), toolCallList),
                ChatGenerationMetadata.builder().finishReason("toolCall").build()
            )
        ))
        .build();
}
```
