# 作品检索质量报告

## 数据与许可

`models/works.manifest.json` 的 6 个 Unsplash 外链已下载到
`public/works/unsplash/w-001.jpg` 至 `w-006.jpg`，并改为 `/works/unsplash/...`
本地路径。来源 URL、下载日期、SHA256 和许可判断见
[`WORKS-SOURCES.md`](WORKS-SOURCES.md)。Unsplash License 通常允许商业使用，
但其禁止把图片编成可替代 Unsplash 的图集；当前用途标为
`development-index-only / review-required`，生产发布前应取得单独授权或替换为
明确允许数据库展示的 CC0/公有领域素材。

重跑 `tools/build_works_index.py` 后索引包含 50 个唯一作品（原基线为 44 个）。
索引仍使用 `openai/clip-vit-base-patch32`，没有更换底座。

## 混合打分

每个命中同时返回 CLIP 余弦、标签重合和 color24 三路分数；最终 `score` 按请求
权重归一化。评测脚本默认比较：

| 组别 | vector | tags | color |
|---|---:|---:|---:|
| vector_only | 1.00 | 0.00 | 0.00 |
| balanced | 0.55 | 0.30 | 0.15 |
| metadata_heavy | 0.35 | 0.45 | 0.20 |

命中解释位于 `hits[].explanation`，包含 `matchedTags`、`colorFeatures`、
`queryContext.mapping` 和 `queryContext.unknownTerms`。未知中文词不会被静默丢弃。

## 标注评测状态

当前仓库没有现成的「查询 → 期望作品 ID」人工标注。已有的 Agent 槽位评测和
`prelabel_works.csv` 都不含检索 ground truth，后者还是模型预标，不能冒充人工标注。
因此 `data/retrieval_labels.json` 保持空模板，不能报告虚构的 recall/MRR。

补齐至少 40 条人工标注后，在服务运行于 8100 时执行：

```powershell
.\.venv\Scripts\python.exe tools\eval_retrieval.py
```

脚本会校验 `source=human`、唯一 query、expected ID 在索引中，并写入
`.review-tmp/retrieval-eval.json`；标注不足时只写 `evaluated=false` 和限制说明。

当前三组指标均为“未评估”：

| 组别 | Recall@1 | Recall@5 | MRR |
|---|---:|---:|---:|
| vector_only | 未评估 | 未评估 | 未评估 |
| balanced | 未评估 | 未评估 | 未评估 |
| metadata_heavy | 未评估 | 未评估 | 未评估 |

## 分数取舍

现有基线的 CLIP 相似度绝对值约为 0.20–0.29，因此不能把绝对值当作“匹配概率”。
本实现只用它做排序，并保留原始余弦与三路归一化分数供核对；标签和彩色特征用于
可解释的增量信号。最终权重应以真实人工标注集的 Recall@1、Recall@5 和 MRR 选择，
不能以单次主观示例替代评测。

## 持久化与增量

基索引写入 `models/works.embed.npz`，新增作品由
`tools/update_work_index.py` 写入 `models/works.shards/*.npz` 并更新
`models/works.index.json`。服务启动只读取分片元数据；向量在首次查询按分片加载。
本机对 50 条基索引的 `WorkIndex` 初始化约 **39 ms**，初始化时 `vecs_loaded=False`；
首次查询才载入向量矩阵。
新增一张作品只计算该图片的 CLIP/color24 并追加一个分片，不触发 50 张基索引重建。
本机实测（CPU、同一份 ViT-B/32 权重）：全量 50 张重建墙钟约 **63,781 ms**；
对临时新增 1 张的单分片 upsert，在模型已加载后提取与写盘约 **579.6 ms**，随后已回滚临时行和分片。
两者都包含脚本/文件 IO，差异来自只计算 1 张而不是 50 张；首次 CLIP 冷启动约 32 s，属于服务启动成本，
不随单张增量重复支付。真实新增作品运行同一脚本会打印 `elapsedMs`，不会触发全量重建。
