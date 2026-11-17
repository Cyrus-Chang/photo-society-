# GITHUB 提交清单（2026-11-17）

> 基线 `ea0d24b` → HEAD `89e3a37`，11 批提交、共 **167 个文件**（单批明细可用 `git show --stat <hash>` 复查）。
> 体检口径：无单文件 >50MB；候选零密钥 / 零内网 IP / 零手机号（117 个文本文件全扫）。
> 远端仓库：`https://github.com/Cyrus-Chang/photo-society-.git`（**尚未配置 remote、尚未 push**）。

## 1. 批次总览

| 批 | hash | message | 文件数 |
|---|---|---|---|
| B0 | `16b4091` | chore: 忽略 pip 临时解包目录与模型权重 | 1 |
| B1 | `32a561e` | feat(ai): 约拍对话 + 数字守卫；补齐检索/撮合/安全升级 | 21 |
| B2 | `c8ff8a8` | test(ai): 可复跑评测与工具脚本 | 22 |
| B3 | `374766b` | feat(ai): 360 条约拍语料 + LoRA 训练脚本 | 2 |
| B4 | `9d10ccd` | docs(ai): 检索质量/多模态评估/MCP/来源台账 | 5 |
| B5 | `5bef2d5` | feat(ui): AI 对话弹层、以图搜摄影师、查重面板 | 17 |
| B6 | `575a5a7` | feat(ui): 约拍/接拍/资料/工作台改版与 AI 入口 | 26 |
| B7 | `e4adcc2` | feat(assets): 本地作品与两页整屏背景 | 50 |
| B8 | `1473d8b` | style: 修正层 M/N/O（背景抬层、原生下拉、标题字体） | 1 |
| B9 | `4dd42a7` | docs: 交接快照、人设样品与设计审阅 | 28 |
| B10 | `89e3a37` | docs: README 补运行环境与本地模型对话；工程说明同步 | 2 |

归属线：B1–B4 = AI 线（LoRA 对话 / 检索 / 安全 / 评测）；B5–B8 = 前端线（AI 对话层 → 页面改版 → 素材 → 样式修正层）；B9–B10 = 交付文档线；B0 = 仓库卫生。

## 2. 逐批文件清单

### B0 `chore: 忽略 pip 临时解包目录与模型权重`
- `.gitignore`（新增 `pip-unpack-*/`、`pip-install-*/`、`pip-build-tracker-*/`、`pip-ephem-wheel-cache-*/` 等；`.staging/.venv-train/`；`*.safetensors`、`*.gguf`；特意不忽略 `models/` 以免误伤 `ai-classifier/models/`）

### B1 `feat(ai): 约拍对话 + 数字守卫；补齐检索/撮合/安全升级`（AI 线核心）
- `ai-classifier/pipeline/`：`chat.py`（LoRA 约拍对话）、`serve.py`（路由）、`agent.py`、`copywriter.py`、`retrieval.py`、`safety.py`、`audit.py`、`labels.py`、`prompts.py`、`similar.py`
- `ai-classifier/mcp_server.py`
- `ai-classifier/labels/dictionary.json`、`ai-classifier/config/safety.json`
- `ai-classifier/models/`：`works.embed.npz`、`works.index.json`、`works.manifest.json`、`works.shards/shard-20261116-214742-013600.npz`

### B2 `test(ai): 可复跑评测与工具脚本`
- `ai-classifier/data/retrieval_labels.json`（**白名单唯一放行文件**）
- `ai-classifier/tools/`：`build_works_index.py`、`build_audit_index.py`、`update_work_index.py`、`eval_agent.py`、`eval_multimodal.py`、`eval_retrieval.py`、`run_safety_redteam.py`、`check_label_contract.py`、`smoke_similar_live.py`、`safety_benign_cases.jsonl`、`safety_redteam_cases.jsonl`、`test_audit.py`、`test_copywriter.py`、`test_mcp_contract.py`、`test_mcp_server.py`、`test_safety_audit.py`、`test_safety_core.py`、`test_safety_mcp.py`、`test_similar.py`

### B3 `feat(ai): 360 条约拍语料 + LoRA 训练脚本`
- `ai-classifier/distill/corpus.jsonl`
- `ai-classifier/distill/train_lora.py`

### B4 `docs(ai): 检索质量/多模态评估/MCP/来源台账`
- `ai-classifier/docs/`：`retrieval-quality.md`、`MULTIMODAL-EVAL.md`、`MCP.md`、`AI-SIMILAR-AUDIT.md`、`WORKS-SOURCES.md`

### B5 `feat(ui): AI 对话弹层、以图搜摄影师、查重面板`
- `src/components/`：`ChatSheet.vue`（AI 对话弹层）、`AgentMatch.vue`、`StyleFinder.vue`（以图搜摄影师）、`WorkAuditPanel.vue`（查重审计）、`WorkCoveragePanel.vue`、`PageAtmosphere.vue`、`WallpaperLayer.vue`、`WallpaperPicker.vue`、`SpiralWall.vue`、`SceneShare.vue`、`IdentityModal.vue`、`StartBookingPrompt.vue`、`BookingFilterModal.vue`、`MarketPostCard.vue`、`BaseModal.vue`
- `src/services/api.ts`、`src/types.ts`

### B6 `feat(ui): 约拍/接拍/资料/工作台改版与 AI 入口`
- `src/pages/`：`HomePage.vue`、`DiscoverPage.vue`、`MarketPage.vue`、`PhotographerPage.vue`、`CirclePage.vue`、`MatchPage.vue`、`OrdersPage.vue`、`ProfilePage.vue`、`PublishPage.vue`、`StudioPage.vue`、`LoginPage.vue`、`WorkDetailPage.vue`
- `src/App.vue`、`src/router.ts`、`src/data/mock.ts`
- `src/utils/`：`media.ts`、`aiLabels.ts`、`bookingFlow.ts`、`imageTools.ts`、`personalize.ts`、`popSound.ts`、`profile.ts`、`session.ts`、`account.ts`

### B7 `feat(assets): 本地作品与两页整屏背景`
- `src/assets/works/*.webp`（50 张：ts 12、ume 15、yiwu 10、milky-way / prayer-flags / tiananmen 等）
- `src/assets/bg/`：`discover-star-trail.webp`、`market-nebula.webp`、`.gitkeep`
- `public/works/unsplash/w-001.jpg` … `w-006.jpg`

### B8 `style: 修正层 M/N/O（背景抬层、原生下拉、标题字体）`
- `src/styles.css`（多轮追加栈整文件提交，248 KB）

### B9 `docs: 交接快照、人设样品与设计审阅`
- `docs/`：`SUBMIT-PLAN.md`、`safety-redteam-report-2026-11-15.md`
- `docs/superpowers/plans/`（6 个）+ `docs/superpowers/specs/`（6 个）——用户拍板**入库**
- `design-frontend-page/`（SKILL.md、agents/openai.yaml、references/ 5 个）
- 根目录：`AI-人设样品_2026-11-16.md`、`新窗口交接_2026-11-16_身份与资料链接.md`、`新窗口交接提示词_2026-11-15_第五轮_总协调.md`、`…第六轮_约拍集市UI.md`、`…第七轮_约拍接拍.md`、`…第八轮_视觉收尾.md`、`…第九轮_AI聊天与背景.md`、`…第十轮_玻璃UI与LoRA.md`

### B10 `docs: README 补运行环境与本地模型对话；工程说明同步`
- `README.md`、`ENGINEERING.md`
- （2026-11-17 15:10 二次修订：删除「接入大模型 API」表述，「如何运行」重排为三段，能力表补以图搜 / 查重审计——将随收尾 commit 入库）

## 3. 故意没提交的东西及原因

| 项 | 原因 |
|---|---|
| `.staging/`（基座模型 3GB、合并模型 2.96GB、torch wheel 3.18GB、训练 venv，共 19.4GB） | 体积可重建；仓库只留训练脚本 `distill/train_lora.py` + 语料 + README「如何获取/训练」说明 |
| `pip-unpack-*` 等 51 个临时目录（87.8MB） | pip 装包残留垃圾，已物理删除并写进 .gitignore |
| `ai-classifier/data/`（68MB 数据集，仅放行 `retrieval_labels.json`） | 整体忽略 + 单文件白名单，锚图/数据集许可不齐 |
| `ai-classifier/.venv/`（1.3GB，torch 必须 CUDA 版 2.7.0+cu128） | 可重建；CUDA 要求已写进 README |
| `.spiral-ref/`、`.review-tmp/`、`.screenshots/`、`node_modules/`、`dist/` | 调试/依赖/构建产物 |
| **剩余 15 项工作区改动**（`business.py`、`photographer-availability.json`、`serve.py`、`ChatSheet.vue`、三个页面、`api.ts`、`mock.ts`、`types.ts`、`media.ts`、`styles.css`、索引重建产物） | 「约拍/接拍业务后端」任务**进行中半成品**，等完成后作为 B11 提交，不混入本次基线推送 |
| `mechanism-design/` | 目录内只有空文件夹，git 不跟踪 |

## 4. push 三条命令（由你本人执行，需要账号凭据）

```bash
git remote add origin https://github.com/Cyrus-Chang/photo-society-.git
git branch -M main
git push -u origin main
```

> push 前先 `git status --short` 确认剩余 15 项半成品还在工作区（未提交状态不会上传，属正常）。
> 后续该任务完成后：走 B11 批次提交（styles.css / serve.py 整文件），再普通 `git push` 即可。
