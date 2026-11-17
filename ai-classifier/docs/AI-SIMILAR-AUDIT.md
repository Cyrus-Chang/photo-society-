# 以图搜图 / 场景覆盖 / 作品查重（2026-11-16）

三件事都**没有引入新模型、没有新增依赖**，全部复用已有 CLIP ViT-B/32 与 50 条作品索引。

## 1. `POST /v1/similar` 以图搜图

上传一张样片 → 风格标签 + 最接近的摄影师（每位最多 2 张代表作）。

| 字段 | 含义 |
|---|---|
| `styleMatch` | 复用 13 类风格锚图，置信度来自留一法间隔分档（`needsReview` 表示建议人工确认） |
| `matches[].matchPercent` | **与 `/v1/search` 完全相同的加权分 ×100**（CLIP 0.65 + 标签 0.20 + color24 0.15），不是第二个模型 |
| `matches[].styleOverlap` | 原始 CLIP 余弦，用于解释「像在哪」 |
| `matchPercentSource` | 响应里写死口径字符串，防止对外说法漂移 |

实现：`pipeline/retrieval.py: WorkIndex.search_vector()`（打分公式与 `search_text` 一字不差）
+ `pipeline/similar.py: rank_photographers()`（聚合，同城只影响排序不加分）。

自检：

```powershell
cd E:\通用型摄影师接单平台\ai-classifier
.\.venv\Scripts\python.exe tools\test_similar.py      # 14 项：自检索排第一、聚合契约
.\.venv\Scripts\python.exe tools\smoke_similar_live.py # 10 项：ASGI 真打接口
```

实测：`ts-01.webp` → `JAPANESE 0.5 (needsReview)`，三位摄影师 89.0 / 87.7 / 80.8。

## 2. `GET /v1/photographer/{id}/scene-share` 场景覆盖

按作品 `styles` 标签词频统计，**分母是作品数**（同一作品多个标签分别计数），
不是标签出现次数，避免一张图三个同义标签把占比抬到 300%。

返回 `totalWorks`、`scenes[{scene,count,share}]`、`topSceneShare`、`narrowCoverage`（>60% 视为偏窄）、`method`（口径原文）。

## 3. `/v1/works/audit` 作品查重（样片溯源的最小可用版）

- `POST`（multipart `file`）：发布前对**待上传图片**查重。
- `GET ?workId=w-001`：对**库内已有作品**查重（前端旧契约）。

两路信号：dHash 64bit（汉明距离）+ CLIP 视觉余弦。

```
duplicateRisk = max(0, 100 - hamming/24*100)
riskLevel: high 当 h<=8 或 (cos>=0.98 且 h<=14)；medium 当 risk>=60；其余 low
```

**以 24 为归零点**是因为无关照片的汉明距离通常就在 20–32；用 64 做分母会把不相关图
报成中风险（初版实测 70.3，改后 20.8）。

实现：`pipeline/audit.py`（纯函数）+ `serve.py: _phash_table()`（**运行时在内存里算 50 张图的哈希并缓存，不落盘**）。
不落盘的原因：受限沙箱里子进程写不了工作区文件，且产物文件容易与索引不同步。

自检：

```powershell
.\.venv\Scripts\python.exe tools\test_audit.py   # 11 项：库内自比 h=0/100、库外更低、GET/POST/BFF
```

平台**只给信号与风险档，不做侵权判定**；响应 `note` 里写死了这句。

## 4. 前端对接注意

`WorkAuditPanel.vue` 目前调的是 `GET /api/v1/ai/works/audit?workId=`，但**发布前还没有 workId**。
发布前应改成 `POST /api/v1/ai/works/audit`（multipart `file`），返回结构相同（多了 `latencyMs`）。
两条路由都保留了，改前端不会破坏库内自检。

## 5. 上线前置

`uvicorn` 无 `--reload`，以上路由需要**重启 8100** 才生效。
