# MCP Server 交付设计

## 目的

把 `ai-classifier/mcp_server.py` 从可握手的三工具适配器升级为第三方可直接接入的 MCP stdio 服务：补齐资源与提示方法，确保工具契约和 FastAPI OpenAPI 同步，统一错误语义，并在坏输入、上游超时、可选鉴权和限流场景下保持进程存活。

## 目标与边界

- 目标：支持 `initialize`、`tools/list`、`tools/call`、`resources/list`、`resources/read`、`prompts/list`、`prompts/get`。
- 目标：暴露作品索引摘要和模型指标摘要；提供“帮我找摄影师”提示模板。
- 目标：工具失败返回 `errorCode`、稳定的用户消息和 `isError=true`，不透传 HTTP 异常文本。
- 目标：坏 JSON、超大消息/参数、未知方法、上游不可达/超时都逐条处理，进程不退出。
- 目标：`MCP_AUTH_TOKEN` 和 `MCP_RATE_LIMIT_PER_MINUTE` 默认关闭，可通过环境变量开启。
- 非目标：不引入官方 MCP SDK，不改模型或 REST 业务逻辑，不实现 completion、sampling、roots、logging、progress/cancel 等可选协议面。

## 方案

1. 在 MCP 层复制模型逻辑：排除，会造成模型行为分叉。
2. 为资源再加 REST 端点：排除，会扩大服务面且与已有索引/指标文件重复。
3. **采用**：工具继续请求 `AI_SERVICE_URL`；资源读取 MCP 进程旁的只读索引/指标摘要；契约测试从 FastAPI OpenAPI 读取并和 MCP schemas 比较。这样不改业务服务，第三方可在服务启动前读取交付元数据，工具仍保持单一模型来源。

## 接口决定

- 资源 URI 白名单为 `photo://works/index` 与 `photo://models/metrics`，只返回 JSON 文本。
- 提示名为 `find_photographers`，必填参数 `query`，生成可直接交给撮合工具的中文用户消息。
- 工具错误码包括 `INVALID_ARGUMENT`、`SERVICE_UNAVAILABLE`、`SERVICE_TIMEOUT`、`UPSTREAM_ERROR`、`SAFETY_BLOCKED`、`UNAUTHORIZED`、`RATE_LIMITED`、`REQUEST_TOO_LARGE`。
- `MCP_AUTH_TOKEN` 为空时不鉴权；开启后在 initialize 的 `_meta.token`（或后续请求的 `_meta.token`）校验一次并绑定当前 stdio 会话。
- `MCP_RATE_LIMIT_PER_MINUTE` 统计每个 stdio 进程的 `tools/call`，滑动窗口一分钟；为 `0` 或未设置时关闭。

## 验证

- 保留并扩展 `tools/test_safety_mcp.py` 三步握手/真实调用脚本。
- 新增离线 `tools/test_mcp_server.py`，覆盖坏 JSON、超大参数、超时、未知方法、工具错误码和 OpenAPI 契约漂移。
- 文档给出完整 `tools/list` 示例、一次 `tools/call` 原文、十行 Python 客户端和 command/args 配置。
