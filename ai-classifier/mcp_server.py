"""零依赖 MCP stdio 适配器。

本进程只负责 MCP/JSON-RPC 协议适配：三个工具转发到已经运行的 FastAPI
服务，不重复实现模型或安全规则；索引和指标资源只读取旁边的只读摘要文件。

传输约定：stdin/stdout 每行一个 JSON-RPC 2.0 对象。可选配置：

    AI_SERVICE_URL                 默认 http://127.0.0.1:8100
    MCP_REQUEST_TIMEOUT_SECONDS    默认 30
    MCP_MAX_MESSAGE_BYTES         默认 262144
    MCP_MAX_PARAM_BYTES           默认 65536
    MCP_AUTH_TOKEN                为空时关闭 token 校验
    MCP_RATE_LIMIT_PER_MINUTE     0/未设置时关闭每进程限流
"""
from __future__ import annotations

from collections import deque
import hmac
import json
import os
from pathlib import Path
import socket
import sys
import time
from typing import Any
import urllib.error
import urllib.request


SERVICE = os.environ.get("AI_SERVICE_URL", "http://127.0.0.1:8100").rstrip("/")
PROTOCOL_VERSION = "2024-11-05"
SERVER_VERSION = "1.1.0"
MODEL_DIR = Path(os.environ.get("MODEL_DIR", str(Path(__file__).resolve().parent / "models")))

try:
    REQUEST_TIMEOUT_SECONDS = max(0.05, float(os.environ.get("MCP_REQUEST_TIMEOUT_SECONDS", "30")))
except ValueError:
    REQUEST_TIMEOUT_SECONDS = 30.0
try:
    MAX_MESSAGE_BYTES = max(1024, int(os.environ.get("MCP_MAX_MESSAGE_BYTES", str(256 * 1024))))
except ValueError:
    MAX_MESSAGE_BYTES = 256 * 1024
try:
    MAX_PARAM_BYTES = max(1024, int(os.environ.get("MCP_MAX_PARAM_BYTES", str(64 * 1024))))
except ValueError:
    MAX_PARAM_BYTES = 64 * 1024
AUTH_TOKEN = os.environ.get("MCP_AUTH_TOKEN", "")
try:
    RATE_LIMIT_PER_MINUTE = max(0, int(os.environ.get("MCP_RATE_LIMIT_PER_MINUTE", "0")))
except ValueError:
    RATE_LIMIT_PER_MINUTE = 0

_session_authorized = not bool(AUTH_TOKEN)
_call_timestamps: deque[float] = deque()

ERROR_INVALID_ARGUMENT = "INVALID_ARGUMENT"
ERROR_REQUEST_TOO_LARGE = "REQUEST_TOO_LARGE"
ERROR_SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
ERROR_SERVICE_TIMEOUT = "SERVICE_TIMEOUT"
ERROR_UPSTREAM = "UPSTREAM_ERROR"
ERROR_SAFETY_BLOCKED = "SAFETY_BLOCKED"
ERROR_UNAUTHORIZED = "UNAUTHORIZED"
ERROR_RATE_LIMITED = "RATE_LIMITED"


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
                "k": {"type": "integer", "description": "返回作品数，默认 5", "default": 5},
                "weights": {
                    "anyOf": [
                        {"type": "object", "additionalProperties": {"type": "number"}},
                        {"type": "null"},
                    ],
                    "description": "可选向量/标签/色彩权重",
                },
                "tags": {
                    "anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}],
                    "description": "可选中文风格标签",
                },
                "city": {"type": "string", "description": "可选城市筛选", "default": ""},
            },
            "required": ["text"],
        },
    },
    {
        "name": "safety_check",
        "description": "检查一段用户输入是否违规（偷拍/隐私、绕过平台私下交易、Prompt 注入）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string"},
                "confidence": {
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                    "description": "可选模型置信度；低于服务阈值时标记人工复核",
                },
            },
            "required": ["text"],
        },
    },
]

RESOURCES = [
    {
        "uri": "photo://works/index",
        "name": "作品索引摘要",
        "description": "作品向量索引的条数、维度、模型和来源元数据。",
        "mimeType": "application/json",
    },
    {
        "uri": "photo://models/metrics",
        "name": "模型指标摘要",
        "description": "已交付分类头和风格锚图的版本、评估指标与置信度口径。",
        "mimeType": "application/json",
    },
]

PROMPTS = [
    {
        "name": "find_photographers",
        "description": "预置“帮我找摄影师”模板，把自然语言需求交给撮合工具。",
        "arguments": [
            {"name": "query", "description": "城市、时间、预算和拍摄风格等需求", "required": True},
        ],
    },
]

_TOOL_PATHS = {
    "match_photographers": ("/v1/agent/match", "topN", 3),
    "search_works": ("/v1/search", "k", 5),
    "safety_check": ("/v1/safety/check", "confidence", None),
}


def _json_size(value: Any) -> int:
    try:
        return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    except (TypeError, ValueError, RecursionError):
        return MAX_PARAM_BYTES + 1


def _tool_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}],
        "isError": not bool(result.get("ok", True)),
    }


def _tool_error(code: str, message: str, *, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"ok": False, "errorCode": code, "error": message}
    if extra:
        result.update(extra)
    return result


def _rpc_error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


def _resource_error(msg_id: Any, message: str, code: int = -32004) -> dict[str, Any]:
    return _rpc_error(msg_id, code, message)


def _safe_upstream_error(code: str) -> dict[str, Any]:
    messages = {
        ERROR_SERVICE_UNAVAILABLE: "AI 服务暂时不可达",
        ERROR_SERVICE_TIMEOUT: "AI 服务响应超时",
        ERROR_UPSTREAM: "AI 服务返回了不可用响应",
    }
    return _tool_error(code, messages[code])


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    """POST JSON and turn every transport/protocol failure into a safe result."""
    request = urllib.request.Request(
        f"{SERVICE}{path}",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            raw = response.read(MAX_MESSAGE_BYTES + 1)
        if len(raw) > MAX_MESSAGE_BYTES:
            return _safe_upstream_error(ERROR_UPSTREAM)
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            return _safe_upstream_error(ERROR_UPSTREAM)
        return data
    except urllib.error.HTTPError as exc:
        if exc.code in (408, 504):
            return _safe_upstream_error(ERROR_SERVICE_TIMEOUT)
        if exc.code == 503:
            return _safe_upstream_error(ERROR_SERVICE_UNAVAILABLE)
        if exc.code in (400, 422):
            return _tool_error(ERROR_INVALID_ARGUMENT, "AI 服务拒绝了参数")
        return _safe_upstream_error(ERROR_UPSTREAM)
    except (TimeoutError, socket.timeout):
        return _safe_upstream_error(ERROR_SERVICE_TIMEOUT)
    except urllib.error.URLError as exc:
        if isinstance(getattr(exc, "reason", None), (TimeoutError, socket.timeout)):
            return _safe_upstream_error(ERROR_SERVICE_TIMEOUT)
        return _safe_upstream_error(ERROR_SERVICE_UNAVAILABLE)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _safe_upstream_error(ERROR_UPSTREAM)
    except OSError:
        return _safe_upstream_error(ERROR_SERVICE_UNAVAILABLE)
    except Exception:
        # The stdio process must remain available even if urllib changes behavior.
        return _safe_upstream_error(ERROR_UPSTREAM)


def _validate_arguments(name: str, arguments: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(arguments, dict):
        return None, _tool_error(ERROR_INVALID_ARGUMENT, "arguments 必须是 JSON 对象")
    if _json_size(arguments) > MAX_PARAM_BYTES:
        return None, _tool_error(ERROR_REQUEST_TOO_LARGE, "请求参数过大")

    text = arguments.get("text")
    if not isinstance(text, str) or not text.strip():
        return None, _tool_error(ERROR_INVALID_ARGUMENT, "text 必须是非空字符串")
    normalized: dict[str, Any] = {"text": text}

    if name == "match_photographers":
        top_n = arguments.get("topN", 3)
        if isinstance(top_n, bool) or not isinstance(top_n, int):
            return None, _tool_error(ERROR_INVALID_ARGUMENT, "topN 必须是整数")
        normalized["topN"] = top_n
    elif name == "search_works":
        k = arguments.get("k", 5)
        if isinstance(k, bool) or not isinstance(k, int):
            return None, _tool_error(ERROR_INVALID_ARGUMENT, "k 必须是整数")
        normalized["k"] = k
        weights = arguments.get("weights")
        if weights is not None:
            if not isinstance(weights, dict) or any(
                isinstance(value, bool) or not isinstance(value, (int, float)) for value in weights.values()
            ):
                return None, _tool_error(ERROR_INVALID_ARGUMENT, "weights 必须是数字字典或 null")
            weights = {str(key): float(value) for key, value in weights.items()}
        normalized["weights"] = weights
        tags = arguments.get("tags")
        if tags is not None and (not isinstance(tags, list) or any(not isinstance(value, str) for value in tags)):
            return None, _tool_error(ERROR_INVALID_ARGUMENT, "tags 必须是字符串数组或 null")
        normalized["tags"] = tags
        city = arguments.get("city", "")
        if not isinstance(city, str):
            return None, _tool_error(ERROR_INVALID_ARGUMENT, "city 必须是字符串")
        normalized["city"] = city
    elif name == "safety_check":
        confidence = arguments.get("confidence")
        if confidence is not None:
            if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
                return None, _tool_error(ERROR_INVALID_ARGUMENT, "confidence 必须是数字或 null")
            confidence = float(confidence)
        normalized["confidence"] = confidence
    else:
        return None, _tool_error(ERROR_INVALID_ARGUMENT, f"未知工具：{name}")
    return normalized, None


def _allow_call() -> bool:
    if RATE_LIMIT_PER_MINUTE <= 0:
        return True
    now = time.monotonic()
    while _call_timestamps and now - _call_timestamps[0] >= 60:
        _call_timestamps.popleft()
    if len(_call_timestamps) >= RATE_LIMIT_PER_MINUTE:
        return False
    _call_timestamps.append(now)
    return True


def call_tool(name: str, arguments: Any) -> dict[str, Any]:
    if name not in _TOOL_PATHS:
        return _tool_error(ERROR_INVALID_ARGUMENT, f"未知工具：{name}")
    if not _allow_call():
        return _tool_error(ERROR_RATE_LIMITED, "调用过于频繁，请稍后再试")
    normalized, validation_error = _validate_arguments(name, arguments)
    if validation_error:
        return validation_error
    assert normalized is not None
    path, optional_name, default = _TOOL_PATHS[name]
    # Keep every REST body field aligned with its Pydantic request model.
    payload = {"text": normalized["text"]}
    payload[optional_name] = normalized.get(optional_name, default)
    if name == "search_works":
        payload.update({"weights": normalized.get("weights"), "tags": normalized.get("tags"), "city": normalized.get("city", "")})
    result = _post(path, payload)

    if result.get("errorCode"):
        return result
    if result.get("action") == "block" or result.get("blocked") is True:
        # Preserve explainable safety fields, but replace any upstream wording.
        extra = {key: result[key] for key in ("action", "flags", "blocked", "note") if key in result}
        return _tool_error(ERROR_SAFETY_BLOCKED, "请求被安全策略拦截", extra=extra)
    if result.get("ok") is False:
        return _safe_upstream_error(ERROR_UPSTREAM)
    return result


def _read_json_file(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {"ok": False, "errorCode": ERROR_UPSTREAM, "error": "资源暂时不可用"}
    return value if isinstance(value, dict) else {"ok": False, "errorCode": ERROR_UPSTREAM, "error": "资源格式无效"}


def read_resource(uri: str) -> dict[str, Any] | None:
    if uri == "photo://works/index":
        return _read_json_file(MODEL_DIR / "works.index.json")
    if uri == "photo://models/metrics":
        models: dict[str, Any] = {}
        for path in sorted(MODEL_DIR.glob("*.metrics.json")):
            value = _read_json_file(path)
            if value.get("ok") is False and value.get("errorCode"):
                continue
            models[path.name.removesuffix(".metrics.json")] = value
        style = _read_json_file(MODEL_DIR / "style.anchors.json")
        result: dict[str, Any] = {"models": models}
        if style.get("ok") is not False:
            result["styleAnchors"] = style
        return result
    return None


def _prompt_text(query: str) -> str:
    return (
        "帮我找摄影师。请根据以下需求，优先考虑城市、时间、预算和拍摄风格，"
        "只引用工具返回的真实作品和档期，不要编造价格或联系方式：\n\n" + query
    )


def _request_token(message: dict[str, Any]) -> str | None:
    direct = message.get("_meta")
    params = message.get("params")
    nested = params.get("_meta") if isinstance(params, dict) else None
    for meta in (direct, nested):
        if isinstance(meta, dict):
            token = meta.get("token")
            if isinstance(token, str):
                return token
    if isinstance(params, dict) and isinstance(params.get("token"), str):
        return params["token"]
    return None


def _authorized(message: dict[str, Any]) -> bool:
    global _session_authorized
    if not AUTH_TOKEN or _session_authorized:
        return True
    supplied = _request_token(message)
    if isinstance(supplied, str) and hmac.compare_digest(supplied, AUTH_TOKEN):
        _session_authorized = True
        return True
    return False


def handle(message: Any) -> dict[str, Any] | None:
    if not isinstance(message, dict):
        return _rpc_error(None, -32600, "Invalid Request")
    msg_id = message.get("id")
    method = message.get("method")
    if not isinstance(method, str):
        return None if "id" not in message else _rpc_error(msg_id, -32600, "Invalid Request")
    if "jsonrpc" in message and message.get("jsonrpc") != "2.0":
        return None if "id" not in message else _rpc_error(msg_id, -32600, "Invalid Request")
    if "params" in message and _json_size(message.get("params")) > MAX_PARAM_BYTES:
        if method == "tools/call" and "id" in message:
            return {"jsonrpc": "2.0", "id": msg_id, "result": _tool_result(_tool_error(ERROR_REQUEST_TOO_LARGE, "请求参数过大"))}
        return None if "id" not in message else _rpc_error(msg_id, -32602, "请求参数过大")
    if not _authorized(message):
        if "id" not in message:
            return None
        if method == "tools/call":
            return {"jsonrpc": "2.0", "id": msg_id, "result": _tool_result(_tool_error(ERROR_UNAUTHORIZED, "未授权的 MCP 会话"))}
        return _rpc_error(msg_id, -32001, "未授权的 MCP 会话")
    if "id" not in message:
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False},
                },
                "serverInfo": {"name": "paishe-photo-agent", "version": SERVER_VERSION},
            },
        }
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = message.get("params")
        if not isinstance(params, dict):
            result = _tool_error(ERROR_INVALID_ARGUMENT, "params 必须是 JSON 对象")
        else:
            result = call_tool(params.get("name", ""), params.get("arguments") or {})
        return {"jsonrpc": "2.0", "id": msg_id, "result": _tool_result(result)}
    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"resources": RESOURCES}}
    if method == "resources/read":
        params = message.get("params")
        uri = params.get("uri") if isinstance(params, dict) else None
        if not isinstance(uri, str):
            return _resource_error(msg_id, "uri 必须是字符串", -32602)
        data = read_resource(uri)
        if data is None:
            return _resource_error(msg_id, "未知资源 URI")
        if data.get("ok") is False and data.get("errorCode"):
            return _resource_error(msg_id, "资源暂时不可用", -32005)
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"contents": [{"uri": uri, "mimeType": "application/json", "text": json.dumps(data, ensure_ascii=False)}]},
        }
    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"prompts": PROMPTS}}
    if method == "prompts/get":
        params = message.get("params")
        name = params.get("name") if isinstance(params, dict) else None
        if name != "find_photographers":
            return _rpc_error(msg_id, -32602, "未知提示模板")
        arguments = params.get("arguments") if isinstance(params, dict) else {}
        query = arguments.get("query") if isinstance(arguments, dict) else None
        if not isinstance(query, str) or not query.strip():
            return _rpc_error(msg_id, -32602, "query 必须是非空字符串")
        if len(query.encode("utf-8")) > MAX_PARAM_BYTES:
            return _rpc_error(msg_id, -32602, "query 过大")
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "description": "帮我找摄影师",
                "messages": [{"role": "user", "content": {"type": "text", "text": _prompt_text(query)}}],
            },
        }
    return _rpc_error(msg_id, -32601, f"未实现的方法：{method}")


def _write_reply(reply: dict[str, Any]) -> None:
    encoded = (json.dumps(reply, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    output = getattr(sys.stdout, "buffer", None)
    if output is not None:
        output.write(encoded)
        output.flush()
    else:
        sys.stdout.write(encoded.decode("utf-8"))
        sys.stdout.flush()


def main() -> int:
    input_stream = getattr(sys.stdin, "buffer", sys.stdin)
    for raw_line in input_stream:
        if isinstance(raw_line, bytes):
            if len(raw_line) > MAX_MESSAGE_BYTES:
                _write_reply(_rpc_error(None, -32600, "请求消息过大"))
                continue
            try:
                line = raw_line.decode("utf-8").rstrip("\r\n")
            except UnicodeDecodeError:
                _write_reply(_rpc_error(None, -32700, "Parse error"))
                continue
        else:
            line = raw_line.rstrip("\r\n")
        if not line.strip():
            continue
        try:
            if len(line.encode("utf-8")) > MAX_MESSAGE_BYTES:
                _write_reply(_rpc_error(None, -32600, "请求消息过大"))
                continue
            message = json.loads(line)
        except (UnicodeEncodeError, json.JSONDecodeError, RecursionError):
            _write_reply(_rpc_error(None, -32700, "Parse error"))
            continue
        try:
            reply = handle(message)
        except Exception:
            # A single malformed request must never terminate the stdio server.
            reply = _rpc_error(message.get("id") if isinstance(message, dict) else None, -32000, "内部错误")
        if reply is not None:
            _write_reply(reply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
