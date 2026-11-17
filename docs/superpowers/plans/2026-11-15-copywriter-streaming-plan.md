# 作品文案流式闭环实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为拍社上传弹窗补齐可观测、可校验、可降级的 LLM 文案生成和 SSE 逐字渲染。

**Architecture:** `pipeline/prompts.py` 提供版本化 prompt，`pipeline/copywriter.py` 统一同步/SSE 生成逻辑、schema/事实校验、重试、日志和指标；FastAPI 暴露同步、SSE、metrics 三个端点；前端 `api.ts` 消费 SSE，`HomePage.vue` 增量写入上传简介。

**Tech Stack:** FastAPI、标准库 `urllib`/`json`/`logging`、Vue 3 + TypeScript `ReadableStream`。

**Spec:** `docs/superpowers/specs/2026-11-15-copywriter-streaming-design.md`

## Global Constraints

- 不加依赖；继续使用标准库 urllib。
- Prompt 必须禁止编造时间、地点、人物身份/关系、拍摄经过。
- titles 正好 3 条且每条 ≤12 字；intro ≤60 字；tags 正好 5 条。
- 失败重试 2 次；超时、无 key、schema/事实失败最终降级 rule。
- 前端只改上传弹窗相关代码和 `ai-copy-panel` 末尾样式。

## Review Focus

- 无 key 时结果必须明确 `mode=rule`、降级原因和 `degraded=true`；冒烟脚本覆盖。
- 模型返回少字段、超长字段或非 JSON 时必须重试并最终降级；用 mock 调用验证。
- 未提供的日期、地名、人名、器材必须拒稿；20 条对抗样例报告拒稿率。
- SSE 重试不能把失败尝试的半截文本重复到 UI；`reset` 事件和前端回调覆盖。
- token/ms 与 promptVersion 必须随结果和 metrics 暴露；脚本输出 P50/P95。

### Task 1: 后端生成与验证

**Files:** `ai-classifier/pipeline/prompts.py`, `ai-classifier/pipeline/copywriter.py`, `ai-classifier/pipeline/serve.py`

- [x] 抽离版本化 prompt。
- [x] 实现 schema、事实校验、2 次重试、错误码、rule 降级和 token/ms 日志。
- [x] 增加 `/v1/copywrite/stream`、`/v1/copywrite/metrics` 及 BFF 别名。

### Task 2: 前端 SSE 渲染

**Files:** `src/services/api.ts`, `src/pages/HomePage.vue`, `src/styles.css`

- [x] 增加 `writeCopyStream` 和 SSE parser。
- [x] 上传弹窗逐字更新简介，结束后落完整结果；重试时清空半截文本。
- [x] 只在 `ai-copy-panel` 末尾追加流式状态样式。

### Task 3: 可复跑验证

**Files:** `ai-classifier/tools/test_copywriter.py`

- [x] 无 key 冒烟输出 mode、model、耗时、tokens。
- [x] 跑 20 条事实对抗样例并输出拒稿率。
- [x] 输出延迟和 token P50/P95；另用 mock 验证 schema 失败后第二次尝试成功。
