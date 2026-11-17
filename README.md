# 拍社 · PHOTO SOCIETY

面向中国城市的摄影师约拍平台。用户用一句话或一张参考图描述想要的画面，平台做**作品向量检索 → 摄影师撮合 → 约拍对话**；摄影师侧可以发档期、接需求、管订单。

定位是「以摄影社区为主、接单是其中一环」，所以首页是作品发现（螺旋照片墙），而不是交易列表。AI 不是外挂文案，而是嵌在检索、撮合、对话三条主链路上，并且每一步都能在界面上核对（撮合返回 `toolTrace`，对话返回 `mode` 与 `guard` 字段）。

- 前端：Vue 3 + TypeScript + Vite，页面 12 个，深浅色摄影档案视觉
- AI 服务：独立 FastAPI 进程（8100），CLIP 图像向量 + 锚图风格匹配 + 本地 LoRA 对话
- 全部模型本地推理，**不依赖任何外部大模型 API**

## 技术架构

```
┌──────────────────────────────┐
│ 浏览器 / Vue 3 SPA (5173)     │
│  pages · components · api.ts │
└──────────────┬───────────────┘
               │ /api/v1/*（Vite 代理）
┌──────────────▼───────────────┐
│ AI / BFF 服务 (FastAPI, 8100) │
│  classify · search · similar  │
│  agent  · chat  · safety      │
└──────┬───────────────┬───────┘
       │               │
┌──────▼──────┐  ┌─────▼──────────────────┐
│ CLIP + 分类头│  │ 作品向量索引 (npz 分片) │
│ 13 类锚图原型│  │ models/works.*          │
└─────────────┘  └────────────────────────┘
       │
┌──────▼────────────────────────┐
│ Qwen2.5-1.5B-Instruct + LoRA  │
│ 本地权重，仓库不含            │
└───────────────────────────────┘
```

| 层 | 选型 | 说明 |
|---|---|---|
| 前端框架 | Vue 3.5 + TypeScript 5.7 + Vite 6 | `vue-router` 4 管路由；无 UI 组件库，样式为原生 CSS（`src/styles.css` 基础层 + 页面 `scoped`） |
| 前端数据 | `src/services/api.ts` 接口优先 + `src/data/mock.ts` 回落 | 后端不可用时演示主链路仍然可走通，界面透传 `degraded` 标记而不是假装成功 |
| 服务层 | Python 3.11 + FastAPI + uvicorn | 单进程同时承担模型推理与 `/api/v1` 业务别名路由，不额外起第二个服务 |
| 图像理解 | CLIP（`clip-vit-base-patch32`） | 图像向量用于检索与相似作品；风格走 13 类**锚图原型匹配**（留一法 0.706），影调走 9 条可解释色彩规则 |
| 检索 | numpy 余弦 + `models/works.embed.npz` 分片 | 索引与清单落盘在 `ai-classifier/models/`，不依赖 FAISS，便于交付复现 |
| 撮合 Agent | 槽位解析 → 向量检索 → 档期过滤 → 排序 | 纯规则 + 检索，不调外部 LLM；返回 `toolTrace` 供前端展开核对 |
| 对话 | Qwen2.5-1.5B-Instruct + LoRA（peft，r=16 / alpha=32） | 三个摄影师人设；GPU 热推理约 2 秒/句；权重不入库 |
| 对话守卫 | 数字守卫（`mode=guard`） | 回复里出现的价格/张数若在上下文中无出处，整条作废并回落人设模板 |
| 安全 | `config/safety.json` + 三档处置 | `pass / review / block`；安全闸门在检索与模型之前，被拦的需求不进入后续链路 |
| MCP | `ai-classifier/mcp_server.py` | 仅用标准库的 stdio MCP server，把工具调用转发到 8100 |

目录约定：

```
src/                    前端（pages / components / services / data / assets）
ai-classifier/
  pipeline/             AI 服务：classify / retrieval / agent / chat / safety / copywrite
  models/               作品向量索引与清单（入库）
  labels/ config/       标签字典与安全规则
  tools/                可复跑评测与测试脚本
  distill/              LoRA 语料与训练脚本
  docs/                 AI 侧设计文档与评测口径
docs/                   提交计划、提交清单等交付文档
```

## 如何运行

### 1) 前端（5173）

```bash
npm install
npm run dev
```

可选：设置 `VITE_API_BASE_URL` 指向业务接口前缀（默认 `/api/v1`）。服务层优先调用后端接口，接口不可用时自动回退到演示数据，保证演示主链路仍然可用。

### 2) AI 服务（8100）

```powershell
cd ai-classifier
$env:HF_HUB_OFFLINE="1"; $env:TRANSFORMERS_OFFLINE="1"
.\.venv\Scripts\python.exe -m uvicorn pipeline.serve:app --host 127.0.0.1 --port 8100
```

冷启动约 45 秒（torch + CLIP）。内部接口：`POST /v1/classify`、`POST /v1/classify-base64`、`POST /v1/embed`、`GET /v1/health`、`GET /v1/models`。

> ⚠️ `ai-classifier/.venv` 里的 torch **必须是 CUDA 版（2.7.0+cu128）**：装成 CPU 版不会报错，但本地对话会退化成 12–20 秒/句；CUDA 版实测 0.9–2.0 秒/句。重建 venv 时**先装 CUDA 版 torch**，再装其余依赖。

### 3) 对话模型（本地 LoRA，仓库不含权重）

仓库里**不含**模型权重（约 3 GB），需自行训练：

```powershell
# 训练（cwd = 仓库根；约 4–5 分钟，8 GB 显存够用）
.\.staging\.venv-train\Scripts\python.exe ai-classifier\distill\train_lora.py
# 产物：.staging\models\paishe-chat-merged\（合并后的完整模型，约 2.96 GB）

# 启动 AI 服务前指向产物
$env:CHAT_MODEL_DIR="<仓库根>\.staging\models\paishe-chat-merged"
```

> 实验记录：360 条 × 5 epoch 那版验证 loss 4.44、会编价格，判定不合格已回滚；线上使用 90 条 × 8 epoch 那版。

### 运行环境要求（2026-11-17 实测）

| 项 | 要求 | 说明 |
|---|---|---|
| Node | 20+ | 前端 `npm i && npm run dev`（5173） |
| Python | 3.11 | AI 服务用 `ai-classifier/.venv` |
| **torch** | **必须是 CUDA 版（2.7.0+cu128）** | ⚠️ 装成 `+cpu` 版时，本地对话模型退化成 **12–20 秒/句**；CUDA 版实测 **0.9–2.0 秒/句**。重建 venv 时先装 CUDA 版 torch，再装其余依赖 |
| GPU | 8 GB 显存够用 | RTX 5050 Laptop 实测：CLIP + 对话模型同时驻留约 3.3 GB |
| 模型权重 | **不入库**（3 GB 起） | 仓库只带训练脚本与语料；权重需本地下载或自己训（见下） |


## 已实现页面

- 首页：四屏作品优先发现页（螺旋照片墙 + 平台说明 + 能力亮点 + 邀约入口）
- AI 筛作品：地点、场景、作品选择、匹配理由、作者与档期
- 作品详情：约 TA、确认时间和价格的弹窗
- 摄影师主页：作品集、档期、认证信息
- 拍摄集市：需求帖、档期帖、搭子帖及关系标签
- 我的约拍：订单状态和时间线
- 摄影师工作台：接单开关、发布档期、作品集
- 发布入口：需求 / 档期 / 搭子三种类型

## 接口映射

`src/services/api.ts` 对应后端设计中的 `/api/v1/ai/work-search`、`/works/{id}`、`/photographers/{id}`、`/posts`、`/bookings` 等 REST 接口。接口响应支持统一 `{ code, message, data, requestId }` 包装。

---

## 仓库合规声明

- **密钥只走环境变量，不进仓库**。仓库内不含任何本地环境文件、token、密码或第三方付费凭据；`.gitignore` 已排除本地环境文件。
- **训练数据与外部数据集不入库**（`ai-classifier/data/`、`ai-classifier/external/`、`ai-classifier/cache/`）：锚图与公开数据集许可不齐，仅保留可复现的模型产物 `ai-classifier/models/`。
- `node_modules/`、`dist/`、`.venv/`、`素材/`、`.spiral-ref/` 等依赖、构建产物与非交付物均不入库。

## 环境变量

| 变量 | 作用 | 归属 |
|---|---|---|
| `VITE_API_BASE_URL` | 前端业务接口前缀，默认 `/api/v1` | 前端（构建期注入） |
| `AI_SERVICE_URL` | AI 模型服务地址，默认 `http://127.0.0.1:8100` | 前端 / BFF |
| `CHAT_MODEL_DIR` | 本地对话模型目录，指向 `.staging\models\paishe-chat-merged` | 仅 AI 服务读取 |
| `HF_HUB_OFFLINE` / `TRANSFORMERS_OFFLINE` | 置 `1` 时只用本地缓存的 CLIP 权重 | AI 服务 |
| `CHAT_DEVICE` / `CHAT_TEMPERATURE` | 对话推理设备与采样温度（当前 `cuda` / `0.7`） | AI 服务 |

完整模板见仓库根目录 [`.env.example`](.env.example)：复制为 `.env`（或按需导出），不填任何真实密钥也能跑起来。

> 项目**未接入大模型 API**：文案生成走 `serve.py` 的模板兜底（`mode=rule`），对话走本地 LoRA 模型。不存在任何外部 LLM 密钥。

## AI 能力（前端真实调用，不是占位）

前端只打 `/api/v1/*`；开发期由 `vite.config.ts` 把 `/api` 代理到 8100 的薄 BFF 层（同一进程加别名路由，不新增第二个服务）。

| 前端入口 | 接口 | 说明 |
|---|---|---|
| 首页第 1 屏「把你的现场放进螺旋」→ 弹窗 | `POST /api/v1/ai/classify` | 真图识别：风格 13 类（留一法 0.706）+ 影调 9 条规则；题材 3 类内测不展示 |
| 弹窗内「生成介绍」 | `POST /api/v1/ai/copywrite` | 分类标签 → 3 个标题 + 简介 + 标签；**未接入大模型 API**，固定返回 `mode=rule` 模板兜底，不伪装模型输出 |
| `/match` 撮合台 | `POST /api/v1/ai/agent/match` | 一句话需求 → 解析槽位 → 向量检索（53 张作品）→ 查档期 → 候选摄影师 + 理由；返回 `toolTrace` 可展开核对 |
| `/photographers/:id`「先聊两句」<br>/`/market` 详情「AI 帮我回一句」 | `POST /api/v1/ai/chat/reply` | **本地 Qwen2.5-1.5B-Instruct + LoRA**，三套摄影师人设（话少型 / 话多型 / 谨慎型）；`mode=model` 走模型（GPU 热推理约 2 秒/句）、`mode=guard` 表示模型编了上下文里没有的数字被拦下并回落模板、`mode=fallback` 表示模型未就绪 |
| 作品详情「同风格」/ 以图搜摄影师 | `POST /api/v1/ai/similar` | 向量检索约 50 张作品索引（当前 53 张），相似作品顺藤摸瓜找到对应摄影师 |
| 作品查重审计 | `GET /api/v1/works/audit` | 作品重复度审计面板（WorkAuditPanel），给出重复/近重复报告 |
| 诊断 | `GET /api/v1/ai/health`、`GET /api/v1/ai/agent/status` | 模型版本、风格留一法准确率、索引条数 |
| 安全闸门 | `POST /api/v1/ai/safety/check` | 三档处置：`pass` / `review`（转人工）/ `block`；撮合与文案链路都过这道闸 |

实测（无头 Edge + CDP，非估算）：

- 识别：单张 380–1140ms，例：`赛博 62% / 蓝调 21%` + `低调`；
- 撮合：`西安，预算 800，下周末，想要港风街拍` → 3 位候选，同城优先，异地标 `crossCity`，库内无该城市时返回 `warnings`；
- 作品向量索引 **44 条**（另有 6 张 unsplash 外链未纳入，已如实记录）；6 类城市分布：北京 15 / 南京 11 / 西安 11 / 上海 6。

**Agent 可复跑评测**（`ai-classifier/tools/eval_agent.py`，12 条人工标注需求，跑一次约 10 秒）：

| 指标 | 结果 |
|---|---|
| 槽位解析：城市 / 预算 / 风格 | **100% / 100% / 100%**（12/12） |
| 安全判定（pass·review·block 三档） | **100%**（含偷拍、私单、Prompt 注入、私房转人工） |
| 指定城市时首位候选同城 | **100%**（4 条可判定；其余城市库内无图，标为无法判定、不计入分母） |
| 端到端延迟 | P50 **42.8ms**，最慢 76.2ms |

> 评测口径写在这里，是为了避免"我们自己说好"——任何人都能复跑 `tools/eval_agent.py` 得到同一组数字。

## 本地小模型对话（2026-11-16 新增）

- **基座**：`Qwen2.5-1.5B-Instruct` + LoRA 微调（r=16 / alpha=32），GPU 热推理约 2 秒/句
- **语料**：`ai-classifier/distill/corpus.jsonl`，人工撰写的约拍对话（三个人设均衡）
- **训练与启动**：见上文「如何运行」第 3 段

**数字守卫（`mode=guard`）**：小样本模型会编价格，所以回复里出现 `¥数字` / `数字+元|块|起|张|人|小时|天` / 3–4 位裸数字时，只要在 context 里找不到出处，整条回复作废、回落到人设模板，并在响应里标 `guard: [...]`。前端据此显示「已拦下模型编的数字」。

> 守卫只是把编造拦下来，**不等于对话不产生幻觉**——小样本模型仍会编细节（英文混入、编档期），演示时只问训过的场景（问价 / 档期 / 风格 / 地点 / 收尾）。



## AI 安全（不是词表堆砌，按真实风险面设计）

摄影约拍平台的真实风险不是"涉政涉黄"，而是：**偷拍 / 隐私**、**绕过平台私下交易**、**Prompt 注入**、**输出泄漏联系方式**。处置分三档，全部可解释：

| 档位 | 触发 | 行为 |
|---|---|---|
| `pass` | 无命中 | 直接放行 |
| `review` | 命中低危词（私房/更衣/肖像权…）或模型置信度低于阈值 | 转人工复核，不拦断 |
| `block` | 命中高危词（偷拍/不让对方知道/私下转账/绕过平台）或注入模式（忽略以上指令、system prompt…） | 直接拒绝并说明原因 |

输出侧另有一道：文案里出现手机号、微信号、外链、邮箱一律替换为「（已隐藏联系方式）」。撮合 Agent 的安全门在**最前面**——被拦的需求既不进检索也不进 LLM。

## MCP 接入（工具集成）

`ai-classifier/mcp_server.py` 零依赖（只用标准库）的 stdio MCP server，暴露三个工具、两个只读资源和一个提示模板：

- `match_photographers(text, topN)` — 一句话撮合
- `search_works(text, k, weights, tags, city)` — 作品向量检索
- `safety_check(text, confidence)` — 复用同一套安全规则
- 资源 `photo://works/index`、`photo://models/metrics`
- 提示 `find_photographers(query)` — 预置“帮我找摄影师”模板

它**不重复实现模型逻辑**，只做协议适配并转发到 `AI_SERVICE_URL`（默认 8100），部署时两层可各自缩放。客户端把 command 指向 `.venv\Scripts\python.exe` + 该文件即可。鉴权（`MCP_AUTH_TOKEN`）和每分钟限流（`MCP_RATE_LIMIT_PER_MINUTE`）默认关闭，坏 JSON、超大参数和上游超时会逐条返回稳定错误而不会让进程退出。完整配置、错误码、完整 `tools/list` 和客户端代码见 [`ai-classifier/docs/MCP.md`](ai-classifier/docs/MCP.md)。

## 模型指标的诚实口径
- **风格（13 类 · 锚图原型匹配）**：留一法准确率 **0.706**，同批图零样本 **0.331**，随机基线 0.077。风格属于分布外概念，文本 prompt 覆盖不到，必须靠参考图——这是本项目最可讲的一个数字。
- **题材（3 类 · 冻结 CLIP + 线性头）**：`val macro-F1 0.9881 / test 1.0000`，但**只有建筑 / 风景 / 美食三类**，且测试集存在同 query 近邻跨集，该数字是上限；对人像会误判，**不在界面暴露，标注「内测中」**。
- **影调（9 条色彩规则）**：无监督、零标注，不报准确率，只讲可解释。

## 现状口径（2026-11-17 更新）

- 约拍页 `/discover` 已改为**真实向量检索**（不再是静态演示数据）：命中 53 张作品索引，卡片上标「命中标签 / 色彩接近」；检索服务不可用时回落本地关键词并把 `degraded` 透传给界面。
- `/market` 已改名「接拍」，拆「想被拍的 / 搭子」两个口径；摄影师档期帖不进这页。
- AI 对话已在两个入口上线（摄影师页「先聊两句」、接拍详情「AI 帮我回一句」），走本地模型 + 数字守卫。
- 约拍/接拍两页使用整屏背景（雪原星轨 / 星云）+ Canvas 粒子，`prefers-reduced-motion` 下退化为静态帧。
- 仍有限制（如实标注）：**未配置 LLM API key**，所以 `copywrite` 走 `mode=rule` 模板兜底，不是模型生成；对话模型小样本下仍会编造，靠 `guard` 拦截而非根治。

## 团队信息

| 项 | 内容 |
|---|---|
| 队伍 / 项目名称 | 拍社 PHOTO SOCIETY |
| 参赛赛事 | 传智杯（赛道：待填） |
| 成员与分工 | 待填：姓名 · 角色（前端 / AI / 设计 / 文档）· 负责模块 |
| 联系方式 | 待填：队长邮箱或手机 |
| 仓库地址 | https://github.com/Cyrus-Chang/photo-society- |

> 开发历程可直接看提交历史：`git log --date=short --pretty='%ad %s'`。项目从 2026-11-14 的前端骨架起步，11-15 打通模型服务与撮合 Agent，11-16 训完 LoRA 并接入对话，11-17 完成业务页与仓库交付。
