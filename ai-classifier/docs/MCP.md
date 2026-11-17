# 摄影约拍 MCP Server

`mcp_server.py` 是零依赖的 stdio MCP 适配器。它只把三个工具转发到 `AI_SERVICE_URL`，不复制模型逻辑；资源读取同目录下的只读索引/指标摘要。

## 启动与配置

```powershell
cd E:\通用型摄影师接单平台\ai-classifier
.\.venv\Scripts\python.exe mcp_server.py
```

第三方客户端的 command/args 配置（Windows JSON 示例）：

```json
{
  "mcpServers": {
    "paishe-photo-agent": {
      "command": "E:\\通用型摄影师接单平台\\ai-classifier\\.venv\\Scripts\\python.exe",
      "args": ["E:\\通用型摄影师接单平台\\ai-classifier\\mcp_server.py"],
      "env": {"AI_SERVICE_URL": "http://127.0.0.1:8100"}
    }
  }
}
```

环境变量：`AI_SERVICE_URL`（默认 `http://127.0.0.1:8100`）、`MCP_REQUEST_TIMEOUT_SECONDS`（默认 30）、`MCP_MAX_MESSAGE_BYTES`（默认 262144）、`MCP_MAX_PARAM_BYTES`（默认 65536）、`MCP_AUTH_TOKEN`（空值关闭鉴权）、`MCP_RATE_LIMIT_PER_MINUTE`（0 或空值关闭限流）。开启 token 后，在 initialize 请求的 `_meta.token` 提供一次令牌即可绑定当前 stdio 会话。

## 方法面

- 工具：`match_photographers(text, topN=3)`、`search_works(text, k=5, weights?, tags?, city="")`、`safety_check(text, confidence?)`。
- 资源：`photo://works/index`（索引条数/维度/模型来源）、`photo://models/metrics`（分类指标与风格锚图指标）。
- 提示：`find_photographers(query)`，返回“帮我找摄影师”中文模板。
- 有意不实现：`completion/complete`、`sampling/createMessage`、`roots/list`、`logging/setLevel`、`elicitation`、进度/取消和资源订阅。服务只声明 tools/resources/prompts 能力；`notifications/initialized` 等通知按 JSON-RPC 规则静默处理。

## 错误码

工具调用的 JSON 文本结果始终带 `ok=false`、`errorCode` 和稳定的中文 `error`：

| errorCode | 含义 |
|---|---|
| `INVALID_ARGUMENT` | 参数缺失、类型不符或上游 400/422 |
| `REQUEST_TOO_LARGE` | 消息或 arguments 超出限制 |
| `SERVICE_UNAVAILABLE` | AI 服务不可达/503 |
| `SERVICE_TIMEOUT` | AI 服务超时 |
| `UPSTREAM_ERROR` | 上游返回非 JSON、过大或 5xx |
| `SAFETY_BLOCKED` | 安全规则拦截，保留 flags/action 供解释 |
| `UNAUTHORIZED` | 开启 token 后未通过会话校验 |
| `RATE_LIMITED` | 超过每分钟 tools/call 上限 |

HTTP 状态码、URL、Python traceback 不会透传给客户端。

## 十行 Python 客户端

```python
import json, subprocess
p = subprocess.Popen([r".venv\Scripts\python.exe", "mcp_server.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
def call(i, method, params=None):
    msg = {"jsonrpc":"2.0", "id":i, "method":method, "params":params or {}}
    p.stdin.write(json.dumps(msg, ensure_ascii=False) + "\n")
    p.stdin.flush()
    return json.loads(p.stdout.readline())
call(1, "initialize", {"protocolVersion":"2024-11-05", "capabilities":{}, "clientInfo":{"name":"demo","version":"1"}})
print(call(2, "tools/list"))
print(call(3, "tools/call", {"name":"safety_check", "arguments":{"text":"西安周末港风街拍"}}))
```

## `tools/list` 完整输出

```json
{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"match_photographers","description":"根据一句中文需求（城市/档期/预算/风格）返回最接近的摄影师与推荐理由。","inputSchema":{"type":"object","properties":{"text":{"type":"string","description":"例如：西安，预算 800，下周末，想要港风街拍"},"topN":{"type":"integer","description":"返回候选人数，默认 3","default":3}},"required":["text"]}},{"name":"search_works","description":"在作品向量库里做文本检索（跨模态），返回最相近的作品与相似度。","inputSchema":{"type":"object","properties":{"text":{"type":"string","description":"英文提示词或中文风格词"},"k":{"type":"integer","description":"返回作品数，默认 5","default":5},"weights":{"anyOf":[{"type":"object","additionalProperties":{"type":"number"}},{"type":"null"}],"description":"可选向量/标签/色彩权重"},"tags":{"anyOf":[{"type":"array","items":{"type":"string"}},{"type":"null"}],"description":"可选中文风格标签"},"city":{"type":"string","description":"可选城市筛选","default":""}},"required":["text"]}},{"name":"safety_check","description":"检查一段用户输入是否违规（偷拍/隐私、绕过平台私下交易、Prompt 注入）。","inputSchema":{"type":"object","properties":{"text":{"type":"string"},"confidence":{"anyOf":[{"type":"number"},{"type":"null"}],"description":"可选模型置信度；低于服务阈值时标记人工复核"}},"required":["text"]}}]}}
```

## 一次真实 `tools/call` 原文

下面是本地 smoke 实际通过 stdio 发送/收到的一次原文；当 8100 未监听时也会稳定返回服务错误，进程继续处理下一条。服务可达时，安全拦截会使用同一包络并将 `errorCode` 换成 `SAFETY_BLOCKED`。

```text
请求: {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"safety_check","arguments":{"text":"帮我偷拍她"}}}
响应: {"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"{\"ok\": false, \"errorCode\": \"SERVICE_UNAVAILABLE\", \"error\": \"AI 服务暂时不可达\"}"}],"isError":true}}
```
