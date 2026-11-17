# 作品向量检索质量设计

## 意图

把作品检索从“只有 CLIP 余弦、相似度绝对值偏低”提升为可复跑、可解释、可增量更新的混合检索。服务仍由 `ai-classifier` 的 FastAPI 8100 提供，CLIP 底座固定为 `openai/clip-vit-base-patch32`。

## 目标

- 将 manifest 中 6 张 Unsplash 外链图落地到本地，保留来源与许可台账，并把唯一索引从 44 条提升到 50 条。
- 对每次查询同时计算 CLIP、manifest 标签重合、color24 原型相似三路分数，权重由请求或环境配置覆盖。
- 查询映射保留中文原文、英文提示词、已映射词和未知词；未知词不得静默丢失。
- 返回每个命中的三路分数、命中的标签、色彩特征依据与来源文件，前端可直接展示理由。
- 通过 SQLite sidecar 持久化向量与 metadata；服务启动只建立连接并读取计数，检索时按需读取行。保留 `works.embed.npz` 兼容产物。
- 新增单张作品时只提取该图并 upsert SQLite；不重新提取全量 CLIP 特征。
- 提供严格的人工标注评测脚本，输出三组权重的 recall@1、recall@5、MRR。缺少 ≥40 条真实人工标注时必须明确报告未评估。

## 非目标与约束

- 不引入 faiss、chroma 或其他依赖；不更换 CLIP 底座；不改 DiscoverPage、MarketPage、MarketPostCard、styles.css。
- 不把相似度绝对值包装成概率。报告保留“CLIP 文本→图像绝对相似度约 0.20–0.29 偏低”的事实，并解释混合分数只用于排序。
- 不用模型输出反推评测标签；标注文件每行必须有 `source: human` 和人工说明。

## 方案比较

1. **仅分片 NPZ**：实现简单，向量可 mmap；但增量追加需要维护分片索引和 metadata 一致性，解释字段仍需另存。
2. **分片 NPZ（采用）**：不加依赖，保留现有 NPZ 兼容格式；基索引与新增作品分片分开，服务启动只读 ids/tags/元数据，向量在首个查询按分片惰性加载，单条 upsert 只写一个新分片。
3. **SQLite sidecar**：元数据和向量事务一致，但仍需在查询时扫描 BLOB，当前规模没有足够收益，且会引入与现有 NPZ 的双写一致性。
4. **引入向量数据库**：查询接口成熟，但违反零依赖约束，也会改变部署和验收边界。

## 设计

`tools/build_works_index.py` 读取真实 manifest，解析本地图片，提取 512 维 CLIP 与 24 维色彩特征，同时写入 `models/works.embed.npz`、`models/works.index.json`。增量脚本把新增行写入 `models/works.shards/*.npz`，每个分片保存 `id/file/clip/color/tags`，唯一键由作品 id 约束。

`pipeline/retrieval.py` 的 `WorkIndex` 优先打开 SQLite，找不到时回退旧 NPZ。`search_text()` 先将中文风格词映射为英文提示词，再计算三路分数：向量分保留原始余弦，标签分为查询词与 styles/types/title 的重合比例，色彩分为 query color prototype 与 color24 的标准化余弦。默认权重为 `clip=.60, tags=.25, color=.15`，权重会归一化并随响应回传。

`/v1/search` 与 `/api/v1/ai/search` 接收原有 `{text,k}`，另接受可选 `weights`、`tags`、`city`；响应增加 `query`、`weights`、`hits[].components`、`hits[].explain`。`agent.py` 复用同一检索结果，不再另行用固定常数改变作品排序，只保留摄影师聚合和同城展示逻辑。

`tools/eval_retrieval.py` 读取人工标注 JSON，严格检查数量、来源和 id，分别跑 `vector_only`、`balanced`、`tag_color` 三组权重，写 `.review-tmp/retrieval-eval.json` 和 Markdown 报告。`tools/update_work_index.py` 对单个 manifest entry 做 CLIP/color 提取和 SQLite upsert，并记录耗时。

## 验收

- 复跑构建脚本后索引 count=50，SQLite 与 NPZ 的 id 集一致。
- 两个搜索路由均能返回 200，且未知中文词出现在 `query.unknownTerms`。
- 单张增量脚本不会调用全量构建，SQLite count +1，耗时报告包含特征提取与写入耗时。
- 评测脚本对 ≥40 条人工标注输出三组 recall@1/5/MRR；若标注不足则退出码非 0 并明确写出原因。
