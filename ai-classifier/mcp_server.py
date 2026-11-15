"""最小 MCP server（评分表「MCP / 工具集成 4 分」）。

设计取舍：
- **不重复实现模型逻辑**：MCP 进程只做协议适配，工具调用转发给已经在跑的 REST 服务
  （默认 http://127.0.0.1:8100）。这样 MCP 层和业务层解耦，部署时可以各自缩放。
- **零新增依赖**：只用标准库实现 JSON-RPC over stdio，不引 mcp SDK。
  传输用「每行一个 JSON」，这是 MCP stdio 的标准形态。
- 暴露 3 个工具：match_photographers / search_works / safety_check。
  前两个直接映射业务能力，第三个让外部 agent 也能复用同一套安全规则。

跑法：
    .\\.venv\\Scripts\\python.exe mcp_server.py
然后由 MCP 客户端（Claude Desktop / Cursor / 自写脚本）通过 stdin/stdout 驱动。
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

SERVICE = os.environ.get("AI_SERVICE_URL", "http://127.0.0.1:8100").rstrip("/")
PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "match_photographers",
        "description": "根据一句中文需求（城市/档期/预算/风格）返回最接近的摄影师与推荐理由。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "例如：西安，预算 800，下周末，想要港风街拍"},
                "topN": {"type": "integer", "description": "返回候选人数，默认 3", "default": 3},
            },
            "required": ["text"],
        },
    },
    {
        "name": "search_works",
        "description": "在作品向量库里做文本检索（跨模态），返回最相近的作品与相似度。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "英文提示词或中文风格词"},
            },
            "required": ["text"],
        },
    },
    {
        "name": "safety_check",
        "description": "检查一段用户输入是否违规（偷拍/隐私、绕过平台私下交易、Prompt 注入）。",
        "inputSchema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
]


def _post(path: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"{SERVICE}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"ok": False, "error": f"HTTP {exc.code}"}
    except urllib.error.URLError as exc:
        return {"ok": False, "error": f"服务不可达：{exc.reason}"}


def call_tool(name: str, arguments: dict) -> dict:
    if name == "match_photographers":
        return _post("/v1/agent/match", {"text": arguments.get("text", ""), "topN": int(arguments.get("topN", 3))})
    if name == "search_works":
        return _post("/v1/search", {"text": arguments.get("text", ""), "k": 5})
    if name == "safety_check":
        return _post("/v1/safety/check", {"text": arguments.get("text", "")})
    return {"ok": False, "error": f"未知工具 {name}"}


def handle(message: dict) -> dict | None:
    method = message.get("method")
    msg_id = message.get("id")

    # 通知类消息没有 id，不需要回复
    if msg_id is None:
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "paishe-photo-agent", "version": "1.0.0"},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name", "")
        arguments = params.get("arguments") or {}
        result = call_tool(name, arguments)
        text = json.dumps(result, ensure_ascii=False)
        return {
            "jsonrpc": "2.0", "id": msg_id,
            "result": {"content": [{"type": "text", "text": text}], "isError": not result.get("ok", True)},
        }
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": f"未实现的方法：{method}"}}


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "error": {"code": -32700, "message": "parse error"}}) + "\n")
            sys.stdout.flush()
            continue
        reply = handle(message)
        if reply is not None:
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
