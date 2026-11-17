# Safety Red Team and Semantic Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 ai-classifier 增加可审计的红队数据、可配置规则/CLIP 语义闸门、脱敏日志和文案输出联动，并以脚本证明漏检率与误杀率。

**Architecture:** `pipeline/safety.py` 保留兼容函数签名，新增配置加载、输入归一化、可选编码器、审计记录和规则版本。FastAPI 在安全检查处传入 `_state` 的 CLIP；红队脚本通过直接调用与服务状态分别比较纯词表和组合闸门。文案模块统一清理三种输出字段并保留已有事实校验。

**Tech Stack:** Python 3.11 标准库、现有 FastAPI/Pydantic、现有 torch/transformers CLIP；不新增依赖。

**Spec:** `docs/superpowers/specs/2026-11-15-safety-redteam-design.md`

## Global Constraints

- 不新增依赖；日志不记录明文手机号/微信号。
- 聚焦偷拍隐私、私单绕过、注入和输出泄漏；不加涉政/涉黄词表。
- 不修改 DiscoverPage、MarketPage、MarketPostCard、styles.css。
- 现有 `check_input(text, confidence=None, threshold=0.30)` 和 `sanitize_output(text)` 调用保持兼容。

## Review Focus

- 分隔符/emoji/大小写归一化后仍能命中高危语义：由 safety 单元和红队脚本覆盖。
- CLIP 未加载或编码异常时规则结果稳定且不伪造相似度：由 safety 单元覆盖。
- 多轮文本只在累计上下文升级且返回首个升级轮次：由红队脚本覆盖。
- 审计日志不含手机号/微信明文：由日志单元覆盖。
- 正常摄影需求不得被语义阈值误杀：20 条 benign 集脚本断言误杀率为 0。

### Task 1: 配置化安全核心

**Files:**
- Create: `ai-classifier/config/safety.json`
- Modify: `ai-classifier/pipeline/safety.py`
- Test: `ai-classifier/tools/test_safety_core.py`

**Interfaces:**
- `check_input(text, confidence=None, threshold=0.30, *, semantic_state=None, context=None)` returns the existing keys plus `ruleVersion`, `semantic`, and optional `auditId`/`escalatedTurn`.
- `sanitize_output(text, *, facts=None)` returns existing keys plus `factViolation` and `reasonCodes`.

- [ ] **Step 1:** Write tests for config version, normalization, semantic fallback, and output fact/contact filtering.
- [ ] **Step 2:** Run the focused tests and verify the new assertions fail.
- [ ] **Step 3:** Implement JSON mtime reload, normalization, rule matching, optional CLIP cosine, and output reason codes without changing existing call sites.
- [ ] **Step 4:** Run focused tests and verify they pass.

### Task 2: 审计与 FastAPI/Agent 接线

**Files:**
- Modify: `ai-classifier/pipeline/safety.py`
- Modify: `ai-classifier/pipeline/serve.py`
- Modify: `ai-classifier/pipeline/agent.py`
- Test: `ai-classifier/tools/test_safety_audit.py`

**Interfaces:**
- `query_audit(limit=100)` returns newest JSONL audit records.
- `/v1/safety/check` and `/api/v1/ai/safety/check` expose `ruleVersion`.

- [ ] **Step 1:** Add tests for a blocked request, redacted snippet, and query API.
- [ ] **Step 2:** Implement logging and pass `_state` to the safety gate before retrieval/LLM.
- [ ] **Step 3:** Run focused tests and the existing MCP smoke test.

### Task 3: Red-team/benign dataset and evaluator

**Files:**
- Create: `ai-classifier/tools/safety_redteam_cases.jsonl`
- Create: `ai-classifier/tools/safety_benign_cases.jsonl`
- Create: `ai-classifier/tools/run_safety_redteam.py`

**Interfaces:**
- CLI emits `redteam_summary.json`, `redteam_results.csv`, and `redteam_misses.json` under `.review-tmp/`.
- Summary contains `pure_rules` and `rules_plus_semantic` metrics, category buckets, and `semantic_status`.

- [ ] **Step 1:** Add exactly 30 dangerous cases and 20 benign cases with expected actions and multi-turn arrays.
- [ ] **Step 2:** Implement pure-rule vs combined evaluation, category metrics, first escalation turn, and redaction-safe miss output.
- [ ] **Step 3:** Run evaluator with and without CLIP and verify metrics are internally consistent.

### Task 4: Copywriter output linkage and final validation

**Files:**
- Modify: `ai-classifier/pipeline/copywriter.py`
- Modify: `ai-classifier/tools/test_copywriter.py`
- Modify: `ai-classifier/tools/test_safety_mcp.py` only if compatibility assertions need the new version field.

- [ ] **Step 1:** Add tests that a contact in tags is filtered and an invented entity fails validation.
- [ ] **Step 2:** Route all title/intro/tag values through output sanitization and preserve fact validation.
- [ ] **Step 3:** Run copywriter, safety core, red-team, and MCP checks; record results in the report.
