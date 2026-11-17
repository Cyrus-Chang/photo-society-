# MCP Server 交付 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 将零依赖 stdio MCP server 补齐为可供第三方使用的工具、资源、提示、错误、健壮性、鉴权限流和示例交付物。

**Architecture:** `mcp_server.py` 保持标准库 JSON-RPC 适配层。工具参数与 FastAPI OpenAPI 的三个请求模型一一对应并转发到 `AI_SERVICE_URL`；资源读取 MCP 旁的白名单 JSON 摘要；测试通过 OpenAPI 对比和本地 HTTP stub 验证，不改模型逻辑。

**Tech Stack:** Python 标准库；现有 FastAPI/Pydantic OpenAPI（仅测试读取）；pytest 或 unittest。

**Spec:** `docs/superpowers/specs/2026-11-15-mcp-server-design.md`

## Global Constraints

- 不加依赖（不引官方 mcp SDK）。
- 不改模型逻辑，MCP 层只做适配。
- 不碰 DiscoverPage/MarketPage/MarketPostCard/styles.css 及其他会话中的无关改动。
- `AI_SERVICE_URL` 默认 `http://127.0.0.1:8100`。
- 鉴权和限流默认关闭。

## Review Focus

- 非对象 JSON、坏 JSON、超大行：逐条返回协议错误并继续处理。
- 参数类型/缺失/超大：返回 `INVALID_ARGUMENT` 或 `REQUEST_TOO_LARGE`，不抛 traceback。
- urllib 超时、连接拒绝、非 JSON/HTTP 错误：返回稳定错误码，不泄露异常文本。
- token 会话与一分钟限流：开启后拒绝未授权/超额调用，关闭时不改变现有行为。
- FastAPI 请求模型字段/default/required 变更：契约测试失败。

### Task 1: MCP protocol surface and safe adapter

**Files:**
- Modify: `ai-classifier/mcp_server.py`
- Test: `ai-classifier/tools/test_mcp_server.py`

**Interfaces:**
- Produces `TOOLS`, `RESOURCES`, `PROMPTS`, `handle(message)`, `call_tool(name, arguments)`, and stdio `main()` with stable JSON-RPC responses.

- [x] **Step 1: Add failing tests** for `resources/list`, `resources/read`, `prompts/list`, `prompts/get`, unknown method, invalid tool arguments, and malformed/oversized input.
- [x] **Step 2: Implement exact schemas and dispatch**; include `k` and nullable `confidence` in tool schemas, resource whitelist, prompt template, and capabilities.
- [x] **Step 3: Add bounded parsing and safe upstream wrapper** with configurable timeout/size limits and stable error codes.
- [x] **Step 4: Add optional token session check and sliding-window call limiter**, both disabled by default.
- [x] **Step 5: Run offline tests and verify process survives multiple bad lines.

### Task 2: Contract drift and smoke coverage

**Files:**
- Modify: `ai-classifier/tools/test_safety_mcp.py`
- Create: `ai-classifier/tools/test_mcp_contract.py`

**Interfaces:**
- Consumes `mcp_server.TOOLS` and `pipeline.serve.app.openapi()`.
- Produces an assertion that MCP tool properties/defaults/required fields match `AgentRequest`, `TextRequest`, and `SafetyRequest`.

- [x] **Step 1: Add OpenAPI projection assertions** for the three request models.
- [x] **Step 2: Extend smoke script** to include all handshake methods and print raw request/response examples while preserving the existing safety report.
- [x] **Step 3: Run targeted tests with `ai-classifier/.venv/Scripts/python.exe`.

### Task 3: Third-party documentation and examples

**Files:**
- Create: `ai-classifier/docs/MCP.md`
- Modify: `README.md` MCP section

**Interfaces:**
- Documents environment variables, error codes, intentionally unimplemented methods, complete `tools/list` output, one raw `tools/call`, a ten-line Python client, and command/args configuration.

- [x] **Step 1: Write copyable client/config examples** using the repository paths and stdio line protocol.
- [x] **Step 2: Document resources/prompts/auth/limits and non-implemented methods.
- [x] **Step 3: Run smoke script and paste observed raw exchange into the delivery doc.

### Task 4: Final verification

- [x] Run `python -m unittest discover tools -p "test_mcp*.py"` from `ai-classifier` venv (the venv does not include pytest).
- [x] Run `python tools/test_safety_mcp.py`; it exits zero and emits the raw call exchange. The sandbox cannot bind localhost sockets, so the attempted upstream call reports `SERVICE_UNAVAILABLE`.
- [x] Inspect `git diff --` only for MCP files/docs; unrelated frontend files remain outside this change.
