# TRAIN_LOG · 公开数据基线（题材头 v0）

**一句话**：用公开摄影数据把「非人像 3 类」题材头训出来了（macro-F1 val 0.988 / test 1.000，
同一划分下零样本只有 0.773 / 0.750）。**这还不是业务模型**：缺人像 5 类，风格头未训练。

- 日期：2026-11-13
- 运行者：DSH（AI）
- 主干：`openai/clip-vit-base-patch32`（冻结）+ 24 维色彩特征 → 线性头（ONNX）
- 特征维度：536（512 CLIP + 24 color）

## 1. 数据来源与许可

| 来源目录 | 数据集 | 许可 | 张数 | 映射到的题材 |
|---|---|---|---|---|
| `ds_nature` | HF `devoppro/Nature-Cinematic-Photography` | **未声明**（仅在公开仓库分发） | 232 | `LANDSCAPE` |
| `ds_pexels_food` | HF `RayyanAhmed9477/pexels-advertisement-photography` | Pexels License（可商用、可改、免署名） | 220 | `STILL_FOOD` |
| `ds_pexels_property` | 同上（不同抓取词桶） | 同上 | 220 | `ARCHITECTURE` |

题材标签来自数据集的抓取搜索词（`text` 列），不是模型猜的：
- `food photography commercial` / `chocolate dessert food photography` / `coffee cup latte art` / `food advertisement menu` → `STILL_FOOD`
- `real estate advertisement property` / `furniture modern interior design` / `retail store advertisement display` → `ARCHITECTURE`
- nature 数据集全为 `nature_*.jpg` → `LANDSCAPE`

**风格列全部填 `INS` 占位**，因此 `--tasks subject` 只训题材头；风格头留空，`serve.py` 会走零样本兜底。

图片已统一缩到长边 640、JPEG q88（原图 1024~2000px），672 张共 41 MB。

## 2. 划分

按顶层目录分组（`photographer_id`），8 个混合批次 `mx_01..mx_08`，每批都含 3 个类，
避免"某类整批落进验证集"导致 macro-F1 无意义（第一版按来源切就踩了这个坑：val 只有 LANDSCAPE、
test 只有 STILL_FOOD，macro-F1 0.33）。

划分结果：train 504 / val 85 / test 83。

## 3. 结果

| 划分 | 零样本 acc | 零样本 macro-F1 | 训练后 acc | 训练后 macro-F1 |
|---|---|---|---|---|
| val (n=85) | 0.7765 | 0.7732 | **0.9882** | **0.9881** |
| test (n=83) | 0.7590 | 0.7496 | **1.0000** | **1.0000** |

按类（test）：ARCHITECTURE P/R/F1 = 1.000/1.000/1.000（n=27）、LANDSCAPE 1.000/1.000/1.000（n=29）、
STILL_FOOD 1.000/1.000/1.000（n=27）。val 上只有 ARCHITECTURE 掉到 R=0.964。

## 4. 必须说清的四个前提（别拿这组数字去答辩）

1. **只有 3 个类**，是 8 类题材里的非人像三类。人像 5 类（棚拍/外景/场展/街拍/室内人像）一张都没有。
2. **test=1.0 偏乐观**。分组是按"每类第 i 张"机械切的，同一抓取词的近邻图会跨训练/测试集；
   真实业务里按摄影师整人划分不会有这么漂亮。这组数字只能当**上限**看。
3. **风格头根本没训**。13 类风格是中文摄影市场的运营叫法，公开数据集没有对应标签；这批数据风格列是 `INS` 占位。
4. **风光来源许可未声明**。如果这个模型要进交付物，`ds_nature` 那 232 张必须换成许可明确的图，
   或者整体重训（数据换掉只需重跑 extract + fit，约 10 分钟）。

## 5. 产物与复跑

```
models/subject.onnx / .onnx.data      线性头（输入 536 维，输出 3 类 sigmoid）
models/subject.labels.json            classes / multi=true / feature_layout
models/subject.threshold.json         按验证集推的每类阈值
models/subject.metrics.json           完整指标
models/metrics_report.txt             上面的表
```

```powershell
cd E:\通用型摄影师接单平台\ai-classifier
$env:HF_HUB_OFFLINE="1"; $env:TRANSFORMERS_OFFLINE="1"
.\.venv\Scripts\python.exe tools\build_public_dataset.py 220      # 拉公开图（约 76 秒）
.\.venv\Scripts\python.exe tools\rebucket_mixed.py                # 8 个混合分组
.\.venv\Scripts\python.exe -m pipeline.prepare --data data --out labels.csv
.\.venv\Scripts\python.exe -m pipeline.train extract --csv labels.csv --cache cache\feat.npz
.\.venv\Scripts\python.exe -m pipeline.train fit --csv labels.csv --cache cache\feat.npz --out models --tasks subject
.\.venv\Scripts\python.exe tools\compare_zeroshot.py               # 零样本 vs 训练 对照
```

## 6. 下一步

- 真实客片到位后：`prelabel.py scan → 人工过 CSV → apply`，删掉 `data/mx_*` 与 `labels.csv`，从 `prepare` 重跑。
- 风格头要等真实标注；风格是这套系统真正的差异化，公开数据帮不上。
- `serve.py` 现在会：题材走 ONNX（只认这 3 类），风格与其余题材走零样本兜底。
