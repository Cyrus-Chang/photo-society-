# 拍社 · 摄影师约拍平台

这是根据 `前端架构与内容优化.md` 与 `后端架构设计.md` 生成的 Vue 3 + TypeScript + Vite 前端 MVP。

## 启动

```bash
npm install
npm run dev
```

如果 Spring Boot API 已启动，可以设置 `VITE_API_BASE_URL` 指向接口前缀（默认 `/api/v1`）。服务层会优先调用后端接口，接口不可用时自动回退到演示数据，保证比赛演示主链路仍然可用。

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
| `LLM_BASE_URL` | LLM 兼容接口地址，如千问 `https://dashscope.aliyuncs.com/compatible-mode/v1` | **仅 AI 服务读取** |
| `LLM_MODEL` | 模型名，如 `qwen-plus` / `deepseek-chat` | 仅 AI 服务读取 |
| `LLM_API_KEY` | 大模型密钥 | **仅 AI 服务读取，绝不注入前端** |

> ⚠️ 不要把 `LLM_API_KEY` 写成 `VITE_` 前缀：`VITE_*` 会在构建期打进前端产物，等于把密钥发给所有访问者。前端只允许出现不含密钥的 `VITE_API_BASE_URL`。

## AI 服务（`ai-classifier/`）

```powershell
cd ai-classifier
$env:HF_HUB_OFFLINE="1"; $env:TRANSFORMERS_OFFLINE="1"
.\.venv\Scripts\python.exe -m uvicorn pipeline.serve:app --host 127.0.0.1 --port 8100
```

冷启动约 45 秒（torch + CLIP）。内部接口：`POST /v1/classify`、`POST /v1/classify-base64`、`POST /v1/embed`、`GET /v1/health`、`GET /v1/models`。

## AI 能力（前端真实调用，不是占位）

前端只打 `/api/v1/*`；开发期由 `vite.config.ts` 把 `/api` 代理到 8100 的薄 BFF 层（同一进程加别名路由，不新增第二个服务）。

| 前端入口 | 接口 | 说明 |
|---|---|---|
| 首页第 1 屏「把你的现场放进螺旋」→ 弹窗 | `POST /api/v1/ai/classify` | 真图识别：风格 13 类（留一法 0.706）+ 影调 9 条规则；题材 3 类内测不展示 |
| 弹窗内「生成介绍」 | `POST /api/v1/ai/copywrite` | 分类标签 → 3 个标题 + 简介 + 标签；配 key 走千问/DeepSeek 兼容接口，未配 key 明确返回 `mode=rule` 模板兜底，不伪装模型输出 |
| `/match` 撮合台 | `POST /api/v1/ai/agent/match` | 一句话需求 → 解析槽位 → 向量检索（44 张作品）→ 查档期 → 候选摄影师 + 理由；返回 `toolTrace` 可展开核对 |
| 诊断 | `GET /api/v1/ai/health`、`GET /api/v1/ai/agent/status` | 模型版本、风格留一法准确率、索引条数、LLM 是否已配置 |
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

> 配置真实 LLM：设 `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`（千问默认 `https://dashscope.aliyuncs.com/compatible-mode/v1` + `qwen-plus`，DeepSeek 换成 `https://api.deepseek.com/v1` + `deepseek-chat` 即可，代码不动）。密钥只给 Python 服务读，前端永远不碰。

## AI 安全（不是词表堆砌，按真实风险面设计）

摄影约拍平台的真实风险不是"涉政涉黄"，而是：**偷拍 / 隐私**、**绕过平台私下交易**、**Prompt 注入**、**输出泄漏联系方式**。处置分三档，全部可解释：

| 档位 | 触发 | 行为 |
|---|---|---|
| `pass` | 无命中 | 直接放行 |
| `review` | 命中低危词（私房/更衣/肖像权…）或模型置信度低于阈值 | 转人工复核，不拦断 |
| `block` | 命中高危词（偷拍/不让对方知道/私下转账/绕过平台）或注入模式（忽略以上指令、system prompt…） | 直接拒绝并说明原因 |

输出侧另有一道：文案里出现手机号、微信号、外链、邮箱一律替换为「（已隐藏联系方式）」。撮合 Agent 的安全门在**最前面**——被拦的需求既不进检索也不进 LLM。

## MCP 接入（工具集成）

`ai-classifier/mcp_server.py` 零依赖（只用标准库）的 stdio MCP server，暴露三个工具：

- `match_photographers(text, topN)` — 一句话撮合
- `search_works(text)` — 作品向量检索
- `safety_check(text)` — 复用同一套安全规则

它**不重复实现模型逻辑**，只做协议适配并转发到 `AI_SERVICE_URL`（默认 8100），部署时两层可各自缩放。客户端把 command 指向 `.venv\Scripts\python.exe` + 该文件即可。

## 模型指标的诚实口径
- **风格（13 类 · 锚图原型匹配）**：留一法准确率 **0.706**，同批图零样本 **0.331**，随机基线 0.077。风格属于分布外概念，文本 prompt 覆盖不到，必须靠参考图——这是本项目最可讲的一个数字。
- **题材（3 类 · 冻结 CLIP + 线性头）**：`val macro-F1 0.9881 / test 1.0000`，但**只有建筑 / 风景 / 美食三类**，且测试集存在同 query 近邻跨集，该数字是上限；对人像会误判，**不在界面暴露，标注「内测中」**。
- **影调（9 条色彩规则）**：无监督、零标注，不报准确率，只讲可解释。

## 现状口径（2026-11-15 第四轮冻结后）

「已实现页面」中首页第 1 条的旧描述「地点 / 日期 / 场景输入」已不成立——第 4 屏的条件匹配表单已删除，改为单一邀约入口。AI 筛作品页当前仍走静态演示数据；AI 服务接入后会在此更新。
