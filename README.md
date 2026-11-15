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

冷启动约 45 秒（torch + CLIP）。接口：`POST /v1/classify`、`POST /v1/classify-base64`、`POST /v1/embed`、`GET /v1/health`、`GET /v1/models`。

## 模型指标的诚实口径

- **风格（13 类 · 锚图原型匹配）**：留一法准确率 **0.706**，同批图零样本 **0.331**，随机基线 0.077。风格属于分布外概念，文本 prompt 覆盖不到，必须靠参考图——这是本项目最可讲的一个数字。
- **题材（3 类 · 冻结 CLIP + 线性头）**：`val macro-F1 0.9881 / test 1.0000`，但**只有建筑 / 风景 / 美食三类**，且测试集存在同 query 近邻跨集，该数字是上限；对人像会误判，**不在界面暴露，标注「内测中」**。
- **影调（9 条色彩规则）**：无监督、零标注，不报准确率，只讲可解释。

## 现状口径（2026-11-15 第四轮冻结后）

「已实现页面」中首页第 1 条的旧描述「地点 / 日期 / 场景输入」已不成立——第 4 屏的条件匹配表单已删除，改为单一邀约入口。AI 筛作品页当前仍走静态演示数据；AI 服务接入后会在此更新。
