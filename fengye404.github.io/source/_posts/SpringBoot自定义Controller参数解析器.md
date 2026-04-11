---
title: SpringBoot自定义Controller参数解析器
typora-root-url: ./SpringBoot自定义Controller参数解析器
date: 2022-4-2 15:41:09
tags:
---

# SpringBoot自定义Controller参数解析器(HandlerMethodArgumentResolver)

正文省略一万字（

> 参考：
>
> [HandlerMethodArgumentResolver(一)：Controller方法入参自动封装器（将参数parameter解析为值）【享学Spring MVC】 - 云+社区 - 腾讯云 (tencent.com)](https://cloud.tencent.com/developer/article/1497760)
>
> [HandlerMethodArgumentResolver(二)：Map参数类型和固定参数类型【享学Spring MVC】 - 云+社区 - 腾讯云 (tencent.com)](https://cloud.tencent.com/developer/article/1497783)
>
> [HandlerMethodArgumentResolver(三)：基于HttpMessageConverter消息转换器的参数处理器【享学Spring MVC】 - 云+社区 - 腾讯云 (tencent.com)](https://cloud.tencent.com/developer/article/1497399)
>
> [HandlerMethodArgumentResolver(四)：自定参数解析器处理特定应用场景，介绍PropertyNamingStrategy的使用【享学Spring MVC】 - 云+社区 - 腾讯云 (tencent.com)](https://cloud.tencent.com/developer/article/1497397)

