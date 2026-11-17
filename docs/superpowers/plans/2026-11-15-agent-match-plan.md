# 撮合 Agent 追问与可解释规划实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在不新增依赖和不破坏规则兜底的前提下，让撮合 Agent 支持受限 LLM 规划、扩展槽位、多轮追问、可解释工具链和 30+ 条回归评测。

**Architecture:** 规则解析生成规范化槽位；可选 LLM 只生成白名单 JSON 计划并经校验，失败即回退规则计划。统一执行工具并输出 `planner`、`planning`、`missingFields`、`toolTrace` 和候选对比字段。

**Tech Stack:** Python 3、FastAPI、标准库 urllib；Vue 3 + TypeScript；现有 CLIP 检索与 mock manifest。

**Spec:** `docs/superpowers/specs/2026-11-15-agent-match-design.md`

## Global Constraints
- 不新增依赖；LLM 用标准库 urllib 调 OpenAI 兼容接口。
- 不编造价格、档期、摄影师经历；无数据写“需向对方确认”。
- 前端只改 `AgentMatch.vue`、`MatchPage.vue`、`router.ts`、`src/services/api.ts`。
- 无 key 时明确写出“LLM 规划器在无 key 时不可验证”。

## Review Focus
- 缺城市或预算：返回 `missingFields` 和反问，不执行误导性推荐。
- 相对时间/预算区间：规范化为可核对结构且不丢原文。
- LLM 返回非法 JSON/越权工具：安全回退规则计划并记录原因。
- 价格数据缺失：只返回来源和“需向对方确认”。
- 库内无指定城市：保留异地候选与 warning，首位同城指标不误判。

### Task 1: 后端 Agent 规划、槽位与工具扩展
**Files:** `ai-classifier/pipeline/agent.py`, 如需接口模型则 `ai-classifier/pipeline/serve.py`
- 扩展 `parse_request` 返回 budgetMin/budgetMax、whenRange、peopleCount、theme、styleHints。
- 新增受限 LLM 计划函数、规则计划函数和白名单校验；在 `run_agent` 中记录 planner、planning latency/success/reason。
- 缺 city/budget 时提前返回 `missingFields`、`followUpQuestion` 与可核对 trace。
- 增加 `check_slot` 与 `estimate_price`；候选补齐同城/异地、档期、标签重合、向量分、沟通要点和价格来源字段。
- 验证：运行后端单测/脚本，覆盖无 key、模拟非法 LLM 响应、相对时间和 C2 文案。

### Task 2: 评测集与指标
**Files:** `ai-classifier/tools/eval_agent.py`, `.review-tmp/agent-eval.json`
- 将 CASES 扩至至少 30 条，覆盖所有新槽位、追问、安全、异地与主题。
- 统计各槽位准确率、安全、同城、planner 模式成功率、P50/P95；记录 `llmPlannerVerifiable` 与无 key 说明。
- 验证：使用项目虚拟环境运行脚本，JSON 落盘且 cases>=30。

### Task 3: 前端接口与结果呈现
**Files:** `src/services/api.ts`, `src/components/AgentMatch.vue`, `src/pages/MatchPage.vue`, `src/router.ts`
- 扩充 TypeScript 类型兼容新字段。
- 结果区增加缺槽位反问、候选对比表、沟通要点、价格来源/需确认、planner 与延迟说明。
- 保持工具 trace 可展开和 /match 路由可达，不改锁定页面。
- 验证：`npm run build`（含 vue-tsc）通过。

### Task 4: 集成验收
**Files:** `.review-tmp/agent-match-cdp.json`、`.screenshots/match-agent.png`
- 启动 FastAPI/Vite，使用无头 Edge 打开 `/match`，点击预设并提交。
- 记录页面成功、追问/候选结果、控制台与网络错误；保存截图或 CDP 日志。
- 运行评测和类型检查，汇总限制：无 key 时 LLM 规划器不可验证。
