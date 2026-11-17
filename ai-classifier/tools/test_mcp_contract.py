"""MCP tool schemas must track the FastAPI request models."""
from __future__ import annotations

import sys
from pathlib import Path
import unittest

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))

import mcp_server  # noqa: E402
from pipeline.serve import app  # noqa: E402


def _schema_shape(schema: dict) -> dict:
    properties = {}
    for name, value in schema.get("properties", {}).items():
        properties[name] = {key: value[key] for key in ("type", "default", "anyOf") if key in value}
    return {"type": schema.get("type"), "properties": properties, "required": schema.get("required", [])}


def _mcp_shape(tool: dict) -> dict:
    return _schema_shape(tool["inputSchema"])


class McpContractTests(unittest.TestCase):
    def test_mcp_tool_schemas_match_fastapi_openapi(self) -> None:
        openapi = app.openapi()["components"]["schemas"]
        expected = {
            "match_photographers": "AgentRequest",
            "search_works": "TextRequest",
            "safety_check": "SafetyRequest",
        }
        tools = {tool["name"]: tool for tool in mcp_server.TOOLS}
        self.assertEqual(set(tools), set(expected))
        for name, model_name in expected.items():
            self.assertEqual(_mcp_shape(tools[name]), _schema_shape(openapi[model_name]))

    def test_mcp_tool_paths_match_rest_surface(self) -> None:
        self.assertEqual({name: value[0] for name, value in mcp_server._TOOL_PATHS.items()}, {
            "match_photographers": "/v1/agent/match",
            "search_works": "/v1/search",
            "safety_check": "/v1/safety/check",
        })
