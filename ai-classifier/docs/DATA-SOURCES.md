# 公开数据源核查台账（2026-11-13）

目的：给「8 题材 / 13 风格」分类器找**许可可查、能真下载**的训练图。结论先行：
**没有一个公开数据集能覆盖 13 类风格**——日系 / 韩系 / 港风 / 蓝调 / 赛博这些是中文摄影市场的运营叫法，
公开学术数据集按「场景 / 美学分 / 景深」分层，不按这个分层。

## 一、已经死掉或不可用的

| 源 | 预期内容 | 实测结论 |
|---|---|---|
| CamSDD（Image-Scene-Classification） | 30 类相机场景、9897 张 576×384 | `data.vision.ee.ethz.ch/ihnatova/camera_scene_detection_*.zip` 全部 **404**；GitHub 搜 `CamSDD` **0 结果**，无镜像。 |
| DoF（photography-style-analysis） | 景深/审美属性 | 数据在 Google Drive，需人工授权抓取；标签是景深/审美，不是业务风格。 |
| DSD（DSD-finetune-blip-llava） | 10610 张 GuruShots 人工排序图 | 仓库**只有代码和模型**，图片来自 GuruShots 商业目录，不随仓库分发。 |
| photo_classification（Alex/Kelly） | 485 条人工特征 | 有 `features.csv`，但**没有图片**；只能做特征层基线，不能训练图像模型。 |

## 二、huggingface 镜像（hf-mirror.com）实测

- `huggingface.co` 直连不可达；`hf-mirror.com` 的 `/api/datasets/{id}`、`/api/models/{id}` **可用**。
- 但 `/api/datasets?search=`、`/raw/`、`/resolve/` 连续返回 **503**（限流/封锁），只能按已知 id 精确取。
- 能按 id 取到的两个摄影集：

| 数据集 | 规模 | 许可 | 可用性判断 |
|---|---|---|---|
| `devoppro/Nature-Cinematic-Photography` | 8050 张 jpg（全为 `nature_*.jpg`，**无类别标签**） | 未标注 | 只能当"风光"单类；无标签、无许可声明，**不进生产模型** |
| `RayyanAhmed9477/pexels-advertisement-photography` | 1 个 parquet，2270 MB，10K~100K 张 | `other`（Pexels License：可免费商用、可修改、无需署名） | 真实摄影作品、可商用；字段待下载后确认 |

## 三、边界（沿用 TRAIN-HANDOVER 铁律）

- 不使用**未确认授权**的图片训练生产模型。
- 公开数据训出来的东西只作为「公开数据基线」，写进报告时必须标清来源，不能冒充业务模型。
- 真正的生产 `models/` 仍然只能由**真实客片 + 人工标注**生成。

## 四、最终实际用上的数据（2026-11-13 训练）

| 来源目录 | 数据集 | 许可 | 张数 | → 题材 |
|---|---|---|---|---|
| `ds_nature` | HF `devoppro/Nature-Cinematic-Photography` | 未声明 | 232 | LANDSCAPE |
| `ds_pexels_food` | HF `RayyanAhmed9477/pexels-advertisement-photography` | Pexels License | 220 | STILL_FOOD |
| `ds_pexels_property` | 同上（另一组抓取词） | Pexels License | 220 | ARCHITECTURE |

- 题材标签取自 parquet 的 `text` 列（抓取搜索词），不是模型猜的。
- 原始 parquet 2.27 GB 存在 `external/datasets/pexels.parquet`（可删，重下载约 2 分钟）。
- 图片统一缩到长边 640 / JPEG q88，672 张共 41 MB。
- 训练结果与四条前提：见 `models/TRAIN_LOG.md`。

## 五、复跑方式

```powershell
cd E:\通用型摄影师接单平台\ai-classifier
$env:PYTHONPATH="E:\通用型摄影师接单平台\ai-classifier"
.\.venv\Scripts\python.exe tools\find_camsdd.py        # 复验 CamSDD 是否复活
.\.venv\Scripts\python.exe tools\hf_probe_datasets.py  # 复验候选 HF 数据集
.\.venv\Scripts\python.exe tools\build_public_dataset.py 220   # 建公开数据集
.\.venv\Scripts\python.exe tools\rebucket_mixed.py     # 8 个混合分组（关键：别按来源整组切）
```
