# 多模态识别可信化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将图片识别从只返回标签升级为可解释、可门控、可人工修正且可复跑评估的识别流程。

**Architecture:** FastAPI 继续复用现有 CLIP、锚图原型和线性头；服务端由统一字典生成解释字段，并对题材结果做“高置信 + 非人像证据”门控。Vue 上传弹窗保留现有布局，只增加 AI 识别与人工修正的来源边界、低置信提示和本地编辑状态。回归脚本通过 HTTP 或离线服务函数跑 30 张样本，输出词表一致性、题材门控、误判和冷/热/并发耗时。

**Tech Stack:** Python 3 + FastAPI + NumPy/PIL/现有 ONNX Runtime；Vue 3 + TypeScript；PowerShell/Python 脚本；不新增依赖。

**Spec:** 用户消息中的“拍社多模态优化”要求与 2026-11-15 现状基线。

## Global Constraints

- 不加依赖；不改 `HomePage.vue` / `SpiralWall.vue` 的视觉布局，只动 AI 相关面板。
- 避开另一个会话正在修改的 `DiscoverPage.vue`、`MarketPage.vue`、`MarketPostCard.vue`、`styles.css`；若必须样式，只允许末尾追加。
- 禁用旧品牌词在产品源文件与新增脚本中必须为 0 命中。
- 不伪造模型输出；人工修改只保存在浏览器本地状态，并标注来源。
- 题材层默认不向用户展示；只有高置信且有非人像证据时才在接口返回。

## Review Focus

- 人像图的题材结果不能继续硬判成 `STILL_FOOD`；由门控测试固定该行为。
- 低于门槛的风格必须返回 `needsReview=true` 和 `confidenceSource`，界面显示“建议人工确认”。
- 人工增删标签不能改变 AI 原始数组，刷新/清空上传状态后编辑状态必须消失。
- Python 与 TypeScript 的 13 风格、9 影调、3 非人像题材中文名必须逐项一致。
- 没有 30 张真实标注样本或服务未启动时，回归脚本必须明确输出“未做的验证”，不填充虚构数字。

### Task 1: 统一标签契约与服务端解释字段

**Files:**
- Modify: `ai-classifier/labels/dictionary.json`
- Modify: `ai-classifier/pipeline/serve.py`
- Create: `ai-classifier/pipeline/label_contract.py`（若实现需要独立纯函数）

**Interfaces:**
- Produces `confidenceSource`, `needsReview`, `subjectGate`, `labelDictionaryVersion` in `/v1/classify`.
- Keeps `style`, `tone`, `subject`, `color`, `latencyMs` backward-compatible.

- [ ] 写词表一致性纯函数测试/脚本，逐项比较 Python 字典与前端契约。
- [ ] 增加留一法间隔四分位分档的来源文本和低置信阈值配置。
- [ ] 增加题材门控：题材必须达到高置信阈值，且无 portrait evidence 时只保留 `ARCHITECTURE`、`LANDSCAPE`、`STILL_FOOD`；否则返回空数组并在 `subjectGate` 写原因。
- [ ] 运行离线服务检查，确认旧字段仍在且新字段可序列化。

### Task 2: 前端 AI/人工来源边界

**Files:**
- Modify: `src/services/api.ts`
- Modify: `src/utils/aiLabels.ts`
- Modify: `src/pages/HomePage.vue`
- Modify: `src/types.ts`（仅当共享类型需要）

**Interfaces:**
- `AiClassifyResult` accepts source and review metadata without making confidence look like a guaranteed percentage.
- Local edited tags expose `{ code, label, source: 'AI' | 'HUMAN' }` to the panel.

- [ ] 写人工增删的最小状态函数，保证 AI 原始结果不可变。
- [ ] 接入风格/影调/题材可增删的本地编辑控件，保留现有上传弹窗布局。
- [ ] 低置信/门控结果显示“建议人工确认”，AI/人工来源可视区分。
- [ ] 清空、重新选择文件时重置人工修正。

### Task 3: 30 张回归与性能脚本

**Files:**
- Create: `ai-classifier/tools/eval_multimodal.py`
- Create: `ai-classifier/tools/README-multimodal.md`
- Create: `ai-classifier/reports/multimodal-2026-11-15.md`

**Interfaces:**
- `python tools/eval_multimodal.py --samples <dir> --base-url http://127.0.0.1:8100 --concurrency 4` prints JSON/CSV-like数字。
- Reports cold first request, warm single requests, concurrent-4 degradation, 30-sample confusion and portrait gate counts.

- [ ] 脚本自动发现最多 30 张样本，并记录缺样本/服务不可用。
- [ ] 以文件夹或文件名中的可选真值计算混淆；无真值时只输出预测分布。
- [ ] 专门统计 20 张人像的门控前后误判率；无法取得 20 张时报告分母，不杜撰。
- [ ] 运行脚本并把真实数字/“没做的验证”写入报告。

### Task 4: 回归验证与交付报告

**Files:**
- Modify: `AI-交接文档.md` 或新增 `ai-classifier/reports/multimodal-2026-11-15.md`

- [ ] `node node_modules/vue-tsc/bin/vue-tsc.js --noEmit -p tsconfig.app.json` 必须 EXIT 0。
- [ ] 检查禁忌词 grep 0 命中、`styles.css` 大括号平衡、git diff 未触碰受保护文件。
- [ ] 运行词表、接口、30 张回归和性能脚本，报告已验证与没做的验证。
