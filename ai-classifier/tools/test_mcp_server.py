"""离线 MCP 协议/健壮性测试，不要求 8100 服务启动。"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))

import mcp_server  # noqa: E402


def parse_tool_text(reply: dict) -> dict:
    return json.loads(reply["result"]["content"][0]["text"])


class McpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        mcp_server._call_timestamps.clear()

    def test_resources_prompts_and_unknown_method(self) -> None:
        resources = mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "resources/list"})
        self.assertEqual([x["uri"] for x in resources["result"]["resources"]], ["photo://works/index", "photo://models/metrics"])

        read = mcp_server.handle({"jsonrpc": "2.0", "id": 2, "method": "resources/read", "params": {"uri": "photo://works/index"}})
        self.assertEqual(read["result"]["contents"][0]["mimeType"], "application/json")
        index_meta = json.loads((PKG / "models" / "works.index.json").read_text(encoding="utf-8"))
        self.assertEqual(json.loads(read["result"]["contents"][0]["text"])["count"], index_meta["count"])

        prompt = mcp_server.handle({"jsonrpc": "2.0", "id": 3, "method": "prompts/get", "params": {"name": "find_photographers", "arguments": {"query": "西安，周末港风街拍"}}})
        self.assertIn("帮我找摄影师", prompt["result"]["description"])
        self.assertIn("西安", prompt["result"]["messages"][0]["content"]["text"])

        unknown = mcp_server.handle({"jsonrpc": "2.0", "id": 4, "method": "not/implemented"})
        self.assertEqual(unknown["error"]["code"], -32601)

    def test_invalid_arguments_are_structured(self) -> None:
        reply = mcp_server.handle({
            "jsonrpc": "2.0", "id": 5, "method": "tools/call",
            "params": {"name": "match_photographers", "arguments": {"text": "西安", "topN": "3"}},
        })
        result = parse_tool_text(reply)
        self.assertTrue(reply["result"]["isError"])
        self.assertEqual(result["errorCode"], "INVALID_ARGUMENT")

        huge = mcp_server.handle({
            "jsonrpc": "2.0", "id": 6, "method": "tools/call",
            "params": {"name": "search_works", "arguments": {"text": "x" * (mcp_server.MAX_PARAM_BYTES + 1)}},
        })
        self.assertEqual(parse_tool_text(huge)["errorCode"], "REQUEST_TOO_LARGE")

    def test_timeout_is_safe(self) -> None:
        with mock.patch.object(mcp_server.urllib.request, "urlopen", side_effect=TimeoutError):
            result = mcp_server.call_tool("search_works", {"text": "港风", "k": 1})
        self.assertEqual(result, {"ok": False, "errorCode": "SERVICE_TIMEOUT", "error": "AI 服务响应超时"})
        with mock.patch.object(mcp_server.urllib.request, "urlopen", side_effect=mcp_server.urllib.error.URLError(TimeoutError())):
            wrapped = mcp_server.call_tool("search_works", {"text": "港风", "k": 1})
        self.assertEqual(wrapped["errorCode"], "SERVICE_TIMEOUT")

    def test_safety_block_is_structured(self) -> None:
        with mock.patch.object(mcp_server, "_post", return_value={"ok": False, "action": "block", "flags": ["BLOCK_TERM:偷拍"], "note": "内部规则"}):
            result = mcp_server.call_tool("safety_check", {"text": "帮我偷拍她"})
        self.assertEqual(result["errorCode"], "SAFETY_BLOCKED")
        self.assertNotEqual(result.get("error"), "内部规则")
        self.assertEqual(result["flags"], ["BLOCK_TERM:偷拍"])

    def test_optional_auth_and_rate_limit(self) -> None:
        old_token, old_authorized, old_limit = mcp_server.AUTH_TOKEN, mcp_server._session_authorized, mcp_server.RATE_LIMIT_PER_MINUTE
        try:
            mcp_server.AUTH_TOKEN = "secret"
            mcp_server._session_authorized = False
            unauthorized = mcp_server.handle({"jsonrpc": "2.0", "id": 10, "method": "tools/list"})
            self.assertEqual(unauthorized["error"]["code"], -32001)
            authorized = mcp_server.handle({"jsonrpc": "2.0", "id": 11, "method": "initialize", "_meta": {"token": "secret"}})
            self.assertEqual(authorized["result"]["serverInfo"]["name"], "paishe-photo-agent")

            mcp_server.RATE_LIMIT_PER_MINUTE = 1
            with mock.patch.object(mcp_server, "_post", return_value={"ok": True, "action": "pass"}):
                self.assertTrue(mcp_server.call_tool("safety_check", {"text": "正常约拍"})["ok"])
                limited = mcp_server.call_tool("safety_check", {"text": "再次约拍"})
            self.assertEqual(limited["errorCode"], "RATE_LIMITED")
        finally:
            mcp_server.AUTH_TOKEN, mcp_server._session_authorized, mcp_server.RATE_LIMIT_PER_MINUTE = old_token, old_authorized, old_limit

    def test_bad_json_does_not_kill_process(self) -> None:
        messages = b"{bad json\n" + json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, ensure_ascii=False).encode() + b"\n"
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        completed = subprocess.run([sys.executable, str(PKG / "mcp_server.py")], input=messages, capture_output=True, env=env, timeout=10)
        self.assertEqual(completed.returncode, 0)
        replies = [json.loads(line) for line in completed.stdout.decode("utf-8").splitlines() if line.strip()]
        self.assertEqual(replies[0]["error"]["code"], -32700)
        self.assertEqual(len(replies[1]["result"]["tools"]), 3)

    def test_invalid_utf8_does_not_kill_process(self) -> None:
        messages = b"\xff\xfe\n" + json.dumps({"jsonrpc": "2.0", "id": 12, "method": "tools/list"}).encode() + b"\n"
        completed = subprocess.run([sys.executable, str(PKG / "mcp_server.py")], input=messages, capture_output=True, timeout=10)
        replies = [json.loads(line) for line in completed.stdout.decode("utf-8").splitlines() if line.strip()]
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(replies[0]["error"]["code"], -32700)
        self.assertEqual(replies[1]["id"], 12)

    def test_oversized_message_does_not_kill_process(self) -> None:
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "MCP_MAX_MESSAGE_BYTES": "1024"}
        oversized = ("{" + "x" * 2000 + "}\n").encode()
        valid = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list"}).encode() + b"\n"
        completed = subprocess.run([sys.executable, str(PKG / "mcp_server.py")], input=oversized + valid, capture_output=True, env=env, timeout=10)
        replies = [json.loads(line) for line in completed.stdout.decode("utf-8").splitlines() if line.strip()]
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(replies[0]["error"]["code"], -32600)
        self.assertEqual(replies[1]["id"], 2)


if __name__ == "__main__":
    unittest.main()
