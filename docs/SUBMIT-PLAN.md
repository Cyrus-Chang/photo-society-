# 提交计划（2026-11-17 13:xx 盘点）

> 目标：把 `ea0d24b` 之后的未提交改动拆成可回滚的批次，**先本地提交、暂不推送**。
> 任何人执行前先跑 `git status --short` 确认没有新变动掺进来。

## 0. 现状（2026-11-17 实测）

- HEAD `ea0d24b`，分支 `main`，**没有配置 remote**。
- 未提交 **153 项**（原先 201 项，其中 48 项是 pip 在仓库根留下的 `pip-unpack-*` 临时目录，已在 `.gitignore` 补规则，共 51 个目录 / 87.8 MB，**不入库**）。
- 若全部提交：**138 个文件 / 6.2 MB / 最大单文件 0.4 MB**，无 >50MB 文件。
- 已确认不会入库的大目录：`.staging/`(19.4GB)、`.spiral-ref/`(749MB)、`.review-tmp/`(297MB)、`.screenshots/`(51MB)、`node_modules/`(97MB)、`dist/`(30MB)、`ai-classifier/.venv/`(1.3GB)、`ai-classifier/data/`(68MB，仅 `retrieval_labels.json` 白名单)。
- 候选里没有 `.env` / key / token / pem。

## 1. 已做的仓库卫生修改

| 文件 | 改了什么 |
|---|---|
| `.gitignore` | 新增 `pip-unpack-*/ pip-install-*/ pip-build-tracker-*/ pip-ephem-wheel-cache-*/ pip-metadata-*/ pip-target-*/`；新增 `.staging/.venv-train/`、`*.safetensors`、`*.gguf`。⚠️ 特意**不写** `models/`，否则会把要入库的 `ai-classifier/models/` 一起忽略掉 |
| `README.md` | 新增「运行环境要求」（torch 必须 CUDA 版，否则对话 12–20 秒/句）、「本地小模型对话」整节、AI 能力表补 `chat/reply` 与 `mode=guard`；索引 44→53；「现状口径」重写为 2026-11-17 版本 |

## 2. 批次（按顺序执行，每批一次 commit）

| # | 批次 | 文件（精确路径） | message |
|---|---|---|---|
| B0 | 仓库卫生 | `.gitignore` | `chore: 忽略 pip 临时解包目录与模型权重` |
| B1 | AI 服务核心 | `ai-classifier/pipeline/{chat,serve,agent,copywriter,retrieval,safety}.py`、`ai-classifier/mcp_server.py`、`ai-classifier/labels/`、`ai-classifier/config/`、`ai-classifier/models/` | `feat(ai): 约拍对话 + 数字守卫；补齐检索/撮合/安全升级` |
| B2 | AI 工具与评测 | `ai-classifier/tools/`、`ai-classifier/data/retrieval_labels.json` | `test(ai): 可复跑评测与工具脚本` |
| B3 | 蒸馏与训练 | `ai-classifier/distill/corpus.jsonl`、`ai-classifier/distill/train_lora.py` | `feat(ai): 360 条约拍语料 + LoRA 训练脚本` |
| B4 | AI 文档 | `ai-classifier/docs/` | `docs(ai): 检索质量/多模态评估/MCP/来源台账` |
| B5 | 前端 AI 层 | `src/components/`、`src/services/api.ts`、`src/types.ts` | `feat(ui): AI 对话弹层、以图搜摄影师、查重面板` |
| B6 | 前端页面 | `src/pages/`、`src/App.vue`、`src/router.ts`、`src/data/`、`src/utils/` | `feat(ui): 约拍/接拍/资料/工作台改版与 AI 入口` |
| B7 | 素材 | `src/assets/`、`public/works/` | `feat(assets): 本地作品与两页整屏背景` |
| B8 | 样式 | `src/styles.css` | `style: 修正层 M/N/O（背景抬层、原生下拉、标题字体）` |
| B9 | 交付文档 | `docs/`、`design-frontend-page/`、根目录 `新窗口交接提示词_*.md`、`新窗口交接_*.md`、`AI-人设样品_2026-11-16.md` | `docs: 交接快照、人设样品与设计审阅` |
| B10 | 项目文档 | `README.md`、`ENGINEERING.md` | `docs: README 补运行环境与本地模型对话；工程说明同步` |

> `src/styles.css` 是多轮追加栈（修正层 A–O），只能整文件放一批，不要拆。

## 3. 明确不入库

| 项 | 原因 |
|---|---|
| `.staging/`（模型 3GB + 合并模型 2.96GB + torch wheel 3.18GB + 训练 venv） | 体积，可重建；仓库只留训练脚本与语料 |
| `pip-unpack-*` 等 51 个目录 | pip 临时垃圾 |
| `ai-classifier/.venv/`、`.staging/.venv-train/` | 可重建 |
| `ai-classifier/data/`（除 `retrieval_labels.json`） | 68MB 数据集，许可不齐 |
| `.spiral-ref/`、`.review-tmp/`、`.screenshots/`、`node_modules/`、`dist/` | 调试与构建产物 |

## 4. 推送（由用户本人执行，需要账号凭据）

```bash
git remote add origin <你的仓库地址>
git branch -M main
git push -u origin main
```
