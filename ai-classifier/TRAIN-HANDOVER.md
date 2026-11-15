# 训练交接文档 · 图片题材/风格分类器（v3.0）

> **这份文档是自包含的。执行者（人或 AI）只需要这一份 + 本目录的代码，不需要看任何其他设计文档。**
>
> **v3.0 变更（重要）**
> 1. **风格从 8 类扩到 13 类**（新增 韩系 / 欧美 / 电影感 / 清新，启用 复古）。
> 2. **风格头从单标签 softmax 改成多标签 sigmoid** —— 这是 13 类能训得出来的前提。
>    13 个风格里有三组天然共存（日系↔清新、胶片↔复古、港风↔胶片），
>    强制互斥会让模型在本可共存的类之间做选择，越加越乱。改成每类独立判断后互不干扰。
> 3. 题材仍为 8 类多标签（人像 5 子类 + 非人像 3 大类），TONE 9 个仍由规则算。
>
> 版本：v3.0 · 2026-11-13 · 对应 `ai-classifier/` 骨架 · 字典 `labels/dictionary.json` v5

---

## 0. 一句话任务与交付物

**任务**：用约 500 张照片（同一批图各标一次题材、1~3 个风格），训练两个多标签分类头，导出 ONNX。

| 维度 | 类别 | 标签形态 | 训练？ |
|---|---|---|---|
| **题材 SUBJECT** | 8 类（棚拍/外景/场照/街拍人像/室内人像 + 建筑/风光/静物美食） | **多标签** sigmoid | ✅ |
| **主风格 STYLE** | **13 类**（蓝调/ins/日系/韩系/欧美/胶片/复古/电影感/清新/暗调/黑白/港风/赛博） | **多标签** sigmoid | ✅ |
| **影调属性 TONE** | 9 个（暖/冷/高饱/低饱/高对比/柔和/高调/低调/黑位抬升） | 规则输出 | ❌ 已实现 |

`models/` 下交付 **10 个文件**：`style.onnx` / `style.labels.json` / `style.threshold.json` / `style.metrics.json`、`subject.onnx` / `subject.labels.json` / `subject.threshold.json` / `subject.metrics.json`、`metrics_report.txt`、`TRAIN_LOG.md`。

**时间**：**1.5 天**（标注 5~6 小时/人，或三人分工 2 小时；训练联调半天）。

---

## 1. 十二条铁律

1. **风格是多标签，不许强行选一个。** 一张"日系咖啡馆人像"完全可以同时标 `JAPANESE` + `FRESH`。标注时标所有成立的，不要纠结"最像哪个"——那个纠结过程才是标注一致率低的根源。
2. **但互斥的不能同时标。** `MONO` 不能和任何彩色风格同时标；`CYBER`（青+品红）和 `CINEMATIC`（青+橙）不同时标。见 §5.5。
3. **三个维度不许混。** 题材 = 拍什么场景；风格 = 调成什么样；TONE = 亮暗冷暖饱和。"低饱和"是 TONE 不是风格，"棚拍"是题材不是风格。
4. **人像细分按场景，不按风格。** "日系棚拍"和"日系外景"是同一风格的两个题材。
5. **不微调 CLIP。** 冻结主干、只训线性头。
6. **不随机划分训练/验证集。** 必须按 `photographer_id` 分组（脚本已实现，会打印 `[fix]` 自动修复）。
7. **风格任务禁止颜色增强。** 风格信息就在颜色分布里。最多水平翻转。
8. **训练图和推理图走同一份预处理**（`serve.py:build_inputs()`）。
9. **不要用 OpenCV 读图**（中文路径静默返回 `None`）。
10. **训练图片不进仓库、进交付物、进展示。**
11. **不用 AI 生成的图当训练数据。**
12. **不为了让指标好看而删难样本、改测试集、或把 macro-F1 换成 accuracy 报。**

---

## 2. 环境准备

### 2.1 要求

- **CPU 即可**。500 张图特征抽取约 1~2 分钟，训练 < 15 秒。
- 内存 ≥ 4GB（峰值约 2GB），磁盘 ≥ 3GB。
- Python **3.10 / 3.11**（不要 3.13）。

### 2.2 安装（Windows PowerShell）

```powershell
cd E:\通用型摄影师接单平台\ai-classifier

py -3.11 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

$env:HF_ENDPOINT = "https://hf-mirror.com"                     # 国内必须

python -m pip install -U pip
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

bash 把激活换成 `source .venv/bin/activate`。

### 2.3 装完立刻验证（30 秒，必须过）

```powershell
python -c "import torch, transformers, sklearn, onnx, onnxruntime, fastapi, PIL, pandas; print('deps ok', torch.__version__, transformers.__version__, onnxruntime.__version__)"

python -c "from transformers import CLIPModel, CLIPProcessor; CLIPModel.from_pretrained('openai/clip-vit-base-patch32'); CLIPProcessor.from_pretrained('openai/clip-vit-base-patch32'); print('clip ok')"

python -m pipeline.colorfeat --help
```

第二条会下载约 600MB 权重（镜像 2~5 分钟）。**必须先单独跑通。**

---

## 3. 要拉取哪些东西

| # | 什么 | 为什么 | 体积 |
|---|---|---|---|
| 1 | `torch`（CPU 版） | 跑 CLIP 视觉塔 | ~200MB |
| 2 | `openai/clip-vit-base-patch32` | **唯一特征主干**，服务端 `transformers` 与前端 `transformers.js` 共用同一套权重 | ~600MB |
| 3 | 图片数据 | 见 §4，队友成片为主 | 已有 |
| 4 | `scikit-learn` / `onnx` / `onnxruntime` | 训头、导出、推理 | 90MB |

**不需要拉**：`ultralytics`/YOLO/mediapipe（人像判定不在训练范围）、`timm`、`open_clip_torch`、Places365 权重、任何"现成风格分类权重"（**不存在**）。

---

## 4. 数据准备

### 4.1 目录约定

```
data/
├─ p001/                                  ← 摄影师 id（分组划分用，必须有 ≥3 个来源）
│  ├─ STUDIO__INS/                        ← 题材__风格
│  ├─ OUTDOOR__JAPANESE+FRESH/            ← 风格可多标，用 + 连接
│  ├─ CONVENTION__BLUE_TONE/
│  ├─ STREET_PORTRAIT__DARK_MOOD/
│  └─ INTERIOR_PORTRAIT__KOREAN/
├─ p002/
│  ├─ STUDIO__KOREAN+INS/
│  └─ OUTDOOR__FILM+VINTAGE/
└─ ds_unsplash/                           ← 公开图，主要补非人像 3 类
   ├─ ARCHITECTURE__MONO/
   ├─ LANDSCAPE__CINEMATIC/
   └─ STILL_FOOD__INS/
```

规则：

- 分隔符**两个下划线** `__`，左题材右风格。
- 题材（8 个）：`STUDIO` `OUTDOOR` `CONVENTION` `STREET_PORTRAIT` `INTERIOR_PORTRAIT` `ARCHITECTURE` `LANDSCAPE` `STILL_FOOD`
- 风格（13 个）：`BLUE_TONE` `INS` `JAPANESE` `KOREAN` `WESTERN` `FILM` `VINTAGE` `CINEMATIC` `FRESH` `DARK_MOOD` `MONO` `HK_RETRO` `CYBER`
- 多个风格用 `+`：`JAPANESE+FRESH`、`FILM+VINTAGE`、`HK_RETRO+FILM`
- 题材也可用 `+`：`STUDIO+CONVENTION__INS`（少见）
- **用停用类会被 `prepare.py` 拒绝**（`PET` `EVENT` `OTHER` `PORTRAIT` `LOW_SAT`）
- **一级目录至少 3 个**，否则分组划分退化，指标不可信

### 4.2 数据预算

同一批图，各标一次题材 + 1~3 个风格。风格多标签的好处：**不需要为 13 类准备 13 倍图片**——一张图能贡献 2~3 个风格正样本。

| 维度 | 类数 | 目标正样本/类 | 说明 |
|---|---|---|---|
| 题材 | 8 | 50 | 人像 5 类各 60+，非人像 3 类各 40~50 |
| 风格 | 13 | 40 | 平均每张图标 1.8 个风格 → 500 张图产出约 900 个正样本 |

**结论：约 450~500 张图。** 标注 5~6 小时/人，三人分工约 2 小时。

> 时间只有半天时：先按 §4.6 第 1 批（5 题材 + 6 风格）跑通，约 300 张图。

### 4.3 标注流程（三道工序）

**第一遍 · 挑锚图（20 分钟）**
13 个风格各挑 2~3 张最典型的放到 `data/_anchor/<STYLE>/`。挑不出来说明该类定义不清，回去看字典的 `definition` 和 `negative_hint`。

**第二遍 · 一级分桶 + 打标签（3~4 小时 / 500 张）**
按风格组合建目录，一张图拖进它**主风格**所在的组合目录。常见组合只有 10 种左右，不会爆：

| 常见组合 | 什么时候用 |
|---|---|
| `JAPANESE` / `JAPANESE+FRESH` | 青绿、柔光、空气感 |
| `FRESH` | 更亮更白、低饱和、干净 |
| `KOREAN` / `KOREAN+INS` | 粉白奶油感、锐而干净 |
| `INS` | 留白、几何、锐利 |
| `CINEMATIC` | 青橙对冲 |
| `WESTERN` | 高反差硬光、妆造强烈 |
| `FILM` / `FILM+VINTAGE` | 颗粒 + 黑位抬升（+黄褐褪色） |
| `VINTAGE` | 只有褪色黄褐、没有明显颗粒 |
| `BLUE_TONE` / `BLUE_TONE+DARK_MOOD` | 冷蓝偏移 |
| `DARK_MOOD` | 大面积暗部、单光源 |
| `MONO` | 完全去色（**只能单选，不能带任何彩色风格**） |
| `HK_RETRO` / `HK_RETRO+FILM` | 绿青中间调 + 暖肤色 |
| `CYBER` | 青品霓虹 |

规则：
- 主风格必填；次要风格只在**明显也成立**时加，别为了凑数
- 拿不准的拖进 `data/_unlabeled/`，**不要硬塞**（13 类里错标一类的代价比漏标高）
- `MONO` 可以把彩色图转灰度补齐（真实成像过程）。转灰度副本要放在**同一摄影师目录**下，避免泄漏
- 一批同次拍摄、同种调色的图，往往整批同一组合，可以整批拖

**第三遍 · 补分布（30 分钟）**
跑 `prepare.py` 看分布，哪类正样本不足 40 就专门找。通常 `HK_RETRO` `CYBER` `WESTERN` `VINTAGE` 会偏少。

### 4.4 生成 labels.csv 并检查

```powershell
python -m pipeline.prepare --data data --out labels.csv
```

输出（示例）：

```
已写入 labels.csv，共 486 张，4 个摄影师/来源

题材分布（多标签）：
  STUDIO             96
  OUTDOOR            82
  CONVENTION         74
  ARCHITECTURE       50
  STREET_PORTRAIT    48
  INTERIOR_PORTRAIT  46
  LANDSCAPE          30   ⚠ 偏少
  STILL_FOOD         20   ⚠ 偏少

风格分布（多标签）：
  INS                88
  JAPANESE           76
  FRESH              72
  BLUE_TONE          56
  FILM               54
  DARK_MOOD          52
  MONO               50
  KOREAN             48
  VINTAGE            44
  CINEMATIC          42
  HK_RETRO           38   ⚠ 偏少
  WESTERN            34   ⚠ 偏少
  CYBER              30   ⚠ 偏少

来源分布（决定分组划分是否可行）：
  p001              300
  p002              144
  ds_unsplash        42
```

**注意：风格分布的总和会大于图片数**（因为多标签），这是正常的。判读看每类的正样本数，< 30 会标 `⚠ 偏少`。

### 4.5 模型作用域（必须写进技术文档）

- 训练集里人像约占 60%（`ds_unsplash` 补的是非人像）。风格头学到的"蓝调"主要是**人像的蓝调**
- 判人像准；判建筑/美食风格会偏
- 这是**模型作用域**，主动写是加分项，被问出来是减分项

### 4.6 分批上线（推荐）

| 批次 | 题材 | 风格 | 图数 | 目的 |
|---|---|---|---|---|
| 第 1 批 | `STUDIO` `OUTDOOR` `CONVENTION` `ARCHITECTURE` `LANDSCAPE` | `INS` `JAPANESE` `FRESH` `BLUE_TONE` `DARK_MOOD` `MONO` | ~300 | 跑通链路 + 第一版指标 |
| 第 2 批 | 补 `STREET_PORTRAIT` `INTERIOR_PORTRAIT` `STILL_FOOD` | 补 `KOREAN` `WESTERN` `FILM` `VINTAGE` `CINEMATIC` `HK_RETRO` `CYBER` | +200 | 扩到 8+13，重训 |

扩类不需要改架构——**改字典 + 重训**就行。

---

## 5. 标注规范

### 5.1 风格判定顺序（13 类，多标签，按序走过每一档）

```
① 去色了吗？        S_mean < 0.04                      → MONO（到此为止，不再标别的彩色风格）
② 色相整体偏移？    b* 显著为负 + 暗部冷                → BLUE_TONE
                    暗部青 + 高光橙（双色对冲）          → CINEMATIC
                    中间调绿青 + 暖肤色                  → HK_RETRO
                    青 + 品红霓虹                        → CYBER
③ 地域审美？        粉白奶油感 + 锐 + 干净              → KOREAN
                    高反差 + 硬光 + 妆造强烈             → WESTERN
                    青绿 + 柔光 + 空气感 + 灰雾          → JAPANESE
                    留白 + 几何秩序 + 锐利               → INS
④ 影调？            每一条独立判，可同时成立：
                    高明度 + 低饱和 + 通透白亮           → FRESH
                    大面积暗部 + 单光源                  → DARK_MOOD
⑤ 质感？            颗粒 + 黑位抬升 + 青影暖高光        → FILM
                    褪色 + 黄褐偏移 + 低饱和             → VINTAGE
```

**关键**：② 和 ③ 之间可以同时成立（比如"蓝调 + 日系"），⑤ 的两项也常同时成立。到了 ④ ⑤ 就每条独立判。

### 5.2 题材判定（先判有没有人，再判子类）

```
有没有明确的人像主体？
├─ 没有 → 结构/线条/空间 → ARCHITECTURE
│         自然景观       → LANDSCAPE
│         独立物件/食物  → STILL_FOOD
└─ 有 → 纯色/布景纸背景 + 人工布光 → STUDIO
        展馆 + 摊位/人群/展板       → CONVENTION
        城市街道 + 店面/招牌/通勤人 → STREET_PORTRAIT
        真实室内空间（咖啡馆/家居） → INTERIOR_PORTRAIT
        自然环境（公园/海边/山野）  → OUTDOOR
```

### 5.3 最容易混的五对

| 混淆对 | 区分点 |
|---|---|
| `JAPANESE` ↔ `FRESH` | 日系有**青绿调 + 灰雾 + 柔光**；清新**更亮更白、更干净**。**两者常常同时成立，允许一起标** |
| `JAPANESE` ↔ `KOREAN` | 日系偏**青绿**、有空气感；韩系偏**粉白**、皮肤通透、更锐更干净 |
| `FILM` ↔ `VINTAGE` | 胶片的核心是**颗粒 + 黑位抬升**；复古的核心是**黄褐褪色**。可以同时成立 |
| `WESTERN` ↔ `CINEMATIC` | 欧美是**高反差硬光**（没有固定调色）；电影感有明确的**青橙双色对冲** |
| `WESTERN` ↔ `DARK_MOOD` | 欧美是明暗都足的高反差；暗调是大面积暗部、单光源 |
| `STUDIO` ↔ `INTERIOR_PORTRAIT` | 棚拍背景是**纯色或布景纸**；室内环境人像背景是**真实可生活空间**（家具、窗、挂画） |
| `OUTDOOR` ↔ `STREET_PORTRAIT` | 外景是**自然元素**；街拍是**城市人文元素** |

### 5.4 一致性自检（10 分钟，必做）

标完 60 张后隔一小时不看，重标其中 20 张（风格部分）。

- 一致率 ≥ 88% → 继续
- 78~88% → 回 §5.1 对齐，重点看 §5.3
- < 78% → 停。判定标准不清，改字典的 `definition`，**不要硬标**

多标签的一致率天然比单标签低一点（因为标的多），所以及格线从 90% 下调到 88%。

### 5.5 哪些风格不能同时标（后处理也用这张表）

| 互斥 | 原因 |
|---|---|
| `MONO` ↔ 任何彩色风格 | 去色了就谈不上蓝调/亲橙调 |
| `CYBER` ↔ `CINEMATIC` | 青+品红 vs 青+橙，调色逻辑相反 |
| `INS` ↔ `DARK_MOOD` | 高亮留白 vs 大面积暗部（弱互斥，极端情况下可共存，但很少） |

其余组合几乎都允许共存。这张表也可以直接写进业务侧的后处理：**如果 `MONO` 命中，就丢掉其他风格标签**。

---

## 6. 执行步骤

### Step 0 · 冒烟（每类 5 张，15 分钟）

```powershell
python -m pipeline.colorfeat data\p001\STUDIO__INS\IMG_0001.jpg
```

预期：打印 24 行特征 + 数值，**不该全是 0.0000**。

```powershell
python -m pipeline.prepare --data data --out labels.csv
python -m pipeline.train extract --csv labels.csv --cache cache/feat.npz
python -m pipeline.train fit --csv labels.csv --cache cache/feat.npz --out models
```

- `extract` 预期：`clip=(30, 512) color=(30, 24)`
- `fit` 若打印 `[skip] ... 训练集只有 N 张` —— 正常，样本太少

### Step 1 · 补到 40~50 正样本/类

只堆数据，不改代码。

### Step 2 · 抽特征

```powershell
python -m pipeline.train extract --csv labels.csv --cache cache/feat.npz
```

预期：`缓存命中 0/486，需补算 486 张` → 1~2 分钟 → `clip=(486, 512) color=(486, 24)`

**只做一次**，以后调参从缓存走。

### Step 3 · 训练 + 评测 + 导出

```powershell
python -m pipeline.train fit --csv labels.csv --cache cache/feat.npz --out models
```

预期输出（末尾）：

```
[subject] classes=8 train=342 val=72 test=72 val_macroF1=0.80 test_macroF1=0.78
  test: macroF1=0.78 acc=0.43 n=72
    STUDIO           P=0.89 R=0.86 F1=0.87 n=14
    ...
[style] classes=13 train=340 val=73 test=73 val_macroF1=0.74 test_macroF1=0.71
  test: macroF1=0.71 acc=0.31 n=73
    INS              P=0.82 R=0.79 F1=0.80 n=14
    JAPANESE         P=0.78 R=0.75 F1=0.76 n=12
    ...
已写入 models
```

注意风格行的 `acc=0.31` —— 这是**子集准确率**（一张图的 2 个风格全判对才算对），31% 在 13 类多标签下是**正常值**，不要慌。看 macro-F1 和 per-class F1。

看到 `[fix] 类别 X 在训练集缺席 → 把分组 Y 搬回训练集` 是**正常自动修复**。

### Step 4 · 对齐自检（★ 必做，1 分钟）

```powershell
python -c "
import numpy as np, onnxruntime as ort
c = np.load('cache/feat.npz', allow_pickle=True)
X = np.concatenate([c['clip'][:5], c['color'][:5]], axis=1).astype(np.float32)
for task in ('style', 'subject'):
    h = np.load(f'models/{task}.head.npz', allow_pickle=True)
    ref = ((X - h['mean']) / h['std']) @ h['W'].T + h['b']
    sess = ort.InferenceSession(f'models/{task}.onnx', providers=['CPUExecutionProvider'])
    got = sess.run(None, {'features': X})[0]
    print(task, 'max abs diff =', float(np.abs(ref - got).max()), '(必须 < 1e-3)')
"
```

### Step 5 · 起服务，肉眼验六张

```powershell
uvicorn pipeline.serve:app --host 127.0.0.1 --port 8100
```

```powershell
curl.exe -F "file=@data\p001\OUTDOOR__JAPANESE+FRESH\IMG_0001.jpg" http://127.0.0.1:8100/v1/classify
```

预期：

```json
{"subject":[{"code":"OUTDOOR","confidence":0.88,"aboveThreshold":true}],
 "style":[{"code":"JAPANESE","confidence":0.79,"aboveThreshold":true},
          {"code":"FRESH","confidence":0.68,"aboveThreshold":false},
          {"code":"INS","confidence":0.22,"aboveThreshold":false}],
 "tone":[{"code":"TONE_HIGH_KEY","source":"RULE"},{"code":"TONE_LOW_SAT","source":"RULE"}],
 "color":{"L_mean":0.66,"S_mean":0.19,"..."},
 "modelVersion":{"subject":"local","style":"local"},"fallback":"","latencyMs":201}
```

业务侧展示规则：**取 `confidence` 最高且 `aboveThreshold=true` 的作为主风格**，其余作为附加标签。

**人工验六张**：明确黑白 / 明确日系 / 明确韩系 / 明确电影感 / 明确复古 / 明确建筑。

### Step 6 · 交回项目

见 §10。

---

## 7. 产物契约

### 7.1 特征布局（顺序不可变）

```
features[0:512]   = CLIP ViT-B/32 图像向量，L2 归一化后
features[512:536] = 24 维色彩影调特征，顺序严格等于 pipeline/colorfeat.FEATURE_NAMES
```

| 项 | 要求 |
|---|---|
| 主干权重 | `openai/clip-vit-base-patch32`（**不能换版本**） |
| 取哪一层 | `CLIPModel.get_image_features()` 后 `F.normalize(dim=-1)` |
| 预处理 | `CLIPProcessor` 默认（短边 resize 224 → center-crop 224 → 官方 mean/std） |
| 读图 | PIL + `ImageOps.exif_transpose` |

24 维顺序：

```
1 L_mean          7 L_p05           13 V_p10          19 colorfulness
2 a_mean          8 L_p95           14 clip_hi        20 hue_circvar
3 b_mean          9 L_range         15 clip_lo        21 hue_dominant
4 L_std          10 S_mean          16 warmth         22 skin_ratio
5 a_std          11 S_p90           17 warmth_shadow  23 L_entropy
6 b_std          12 V_mean          18 warmth_high    24 shadow_ratio
```

> 直接 `from pipeline.colorfeat import color_features`，不要重写。

### 7.2 ONNX 文件

| 项 | 要求 |
|---|---|
| 文件 | `models/style.onnx`、`models/subject.onnx` |
| 输入名 | `features`（**必须对**） |
| 输入形状 | `(batch, 536)` `float32` C-contiguous |
| 输出名 | `logits` |
| 输出形状 | `(batch, C)` |
| 输出语义 | **未过 sigmoid / softmax 的 logits**（两个头都是多标签，服务端做 sigmoid） |
| 标准化 | **mean/std 折叠进权重** |
| opset | ≥ 13（推荐 17） |

### 7.3 labels.json（★ `multi` 两个头都是 true）

```json
{
  "task": "style",
  "classes": ["BLUE_TONE","INS","JAPANESE","KOREAN","WESTERN","FILM","VINTAGE","CINEMATIC","FRESH","DARK_MOOD","MONO","HK_RETRO","CYBER"],
  "multi": true,
  "feature_layout": ["clip512", "color24"],
  "clip_model": "openai/clip-vit-base-patch32"
}
```

- `classes` 的**下标必须与 onnx 输出列一一对应**。错一位 = 整体错位且不报错。**最容易犯的错。**
- `multi: true` 决定服务端用 sigmoid 还是 softmax。**写错了整个输出就变了语义。**

### 7.4 threshold.json

13 个风格各一个阈值，键是 code：

```json
{"BLUE_TONE":0.62,"INS":0.58,"JAPANESE":0.60,"KOREAN":0.58,"WESTERN":0.60,
 "FILM":0.58,"VINTAGE":0.60,"CINEMATIC":0.62,"FRESH":0.56,"DARK_MOOD":0.58,
 "MONO":0.72,"HK_RETRO":0.62,"CYBER":0.64}
```

没给默认 0.5（不建议）。`MONO` 阈值给得最高，因为它是硬规则能判的类，宁可漏。

### 7.5 metrics.json

```json
{"task":"style","classes":[...],"n_train":340,"n_val":73,"n_test":73,
 "train_domain":"human portrait ~60%, non-portrait from public datasets",
 "test":{"macro_f1":0.71,"accuracy":0.31,"n_eval":73,
         "per_class":[{"code":"INS","precision":0.82,"recall":0.79,"f1":0.80,"support":14}],
         "confusion":null}}
```

多标签下 `confusion` 为 `null`（不适用），看 `per_class`。

**`train_domain` 必须写**。

---

## 8. 指标解读

### 8.1 看什么数字

1. `test.macro_f1` —— 主指标。13 类等权。
2. `test.per_class[].f1` —— **逐类看**。多标签下某一类很差会被 macro 平均稀释，必须逐类扫一遍。
3. `test.accuracy` —— **子集准确率**（一张图的全部标签都判对才算对）。13 类多标签下 0.3 左右是正常的，**不要拿它当目标**。

### 8.2 目标值

| 维度 | 及格 | 目标 | 说明 |
|---|---|---|---|
| **风格（13 类多标签）** | macro-F1 ≥ 0.65 | **0.72** | 且至少 **10/13 类**的 per-class F1 > 0.60 |
| **题材（8 类多标签）** | macro-F1 ≥ 0.70 | **0.78** | 人像 5 子类会明显高于整体 |

**题材看两个数**：
- 整体 macro-F1（被非人像小类拖累）
- **人像 5 子类平均 F1**（业务主力指标，应该显著更高）

两个都写进 `TRAIN_LOG.md`。只报整体会让你误判"人像分得不好"。

### 8.3 什么时候该合并类

13 类里必然有几个分不清，这正常。看 `metrics_report.txt` 的 per-class 和 `confusion_*_test.csv`（题材才有混淆矩阵）：

- 若 A↔B 互相误判 **超过该类 25%**，且合并后 macro-F1 提升 **≥ 4 点** → 合并
- 合并方式：**改标签，不改模型输出**。`labels.csv` 里 `B` 全替换成 `A`，同步改字典，重训
- 合并后必须写进 `TRAIN_LOG.md`

**按优先级考虑合并/拆掉的三个**：

| 候选 | 判断 |
|---|---|
| `WESTERN` | 定义最宽（本质是"地域集合"不是风格）。若 F1 < 0.55 且与其他类大量混淆 → **拆掉它**，比硬留强 |
| `JAPANESE` + `FRESH` | 若两者互相误判 > 30%，说明标注员没分出来 → 合并成 `JAPANESE` 并注明含清新 |
| `FILM` + `VINTAGE` | 若互相误判 > 30% → 合并成 `FILM` |

**"拆掉一个类"不是失败**，是诚实的工程决策。技术文档写"我们基于 486 张实测，把 13 类收敛到 11 类，macro-F1 从 0.61 提到 0.71"，比硬凑 13 类可信得多。

### 8.4 题材头什么时候该放弃

`macro-F1 < 0.70` 时看 per_class：

- `STILL_FOOD`/`LANDSCAPE` 拖后腿 → 补样本，或合并成 `STILL_LANDSCAPE`
- 5 个人像子类互相混（`STUDIO`↔`INTERIOR_PORTRAIT`、`OUTDOOR`↔`STREET_PORTRAIT`）→ 合并到 3 类：把字典里停用的 `PORTRAIT` 与 `OTHER` 改回 `enabled: true`，5 人像子类统一成 `PORTRAIT`、`CONVENTION` 保留、非人像 3 类统一成 `OTHER`，`labels.csv` 做替换后重训
- 合并后仍 < 0.70 → **不交 subject 头**，题材改用「人脸检测 + 几何 + VLM」

**放弃题材头不影响风格头。**

---

## 9. 验收清单

- [ ] `python -m pipeline.train fit` 无异常退出
- [ ] `models/` 下有 10 个必交文件
- [ ] §6 Step 4 两个头都打印 `max abs diff < 1e-3`
- [ ] 风格 test **macro-F1 ≥ 0.65**，且 **≥10/13 类** per-class F1 > 0.60
- [ ] 题材 test macro-F1 ≥ 0.70
- [ ] `style.labels.json` 与 `subject.labels.json` 的 `multi` 都是 **true**
- [ ] `curl /v1/models` 能看到 13 个风格类、8 个题材类
- [ ] `metrics.json` 里有 `train_domain`
- [ ] `TRAIN_LOG.md` 里同时记了**整体题材 macro-F1**和**人像 5 子类平均 F1**
- [ ] 六张肉眼验证：黑白 / 日系 / 韩系 / 电影感 / 复古 / 建筑
- [ ] `tone` 字段在返回里，`source` 为 `RULE`
- [ ] `data/`、`cache/` 没进交付物；训练图片不在仓库任何位置

---

## 10. 交付方式

### 10.1 拷回去

```
ai-classifier/
├─ models/          ← 整个目录（< 1MB）
├─ labels.csv       ← 只含路径和标签，不含图片
└─ TRAIN_LOG.md     ← 手写
```

不要拷 `data/`、`cache/`、`.venv/`。

### 10.2 TRAIN_LOG.md 模板

```markdown
# 训练日志 · v3.0（题材 8 类 + 风格 13 类，均多标签）

## 数据
- 总样本：486 张，来源：p001(300) / p002(144) / ds_unsplash(42)
- 人像占比：约 62%
- 题材各类：STUDIO 96 / OUTDOOR 82 / CONVENTION 74 / ARCHITECTURE 50 / STREET_PORTRAIT 48 / INTERIOR_PORTRAIT 46 / LANDSCAPE 30 / STILL_FOOD 20
- 风格各类：INS 88 / JAPANESE 76 / FRESH 72 / BLUE_TONE 56 / FILM 54 / DARK_MOOD 52 / MONO 50 / KOREAN 48 / VINTAGE 44 / CINEMATIC 42 / HK_RETRO 38 / WESTERN 34 / CYBER 30
- 平均每张图标风格数：1.8
- 数据授权：队友成片（已获授权）/ Unsplash License
- 一致性自检：20 张重标，一致 18/20 = 90%

## 训练
- 主干：openai/clip-vit-base-patch32（冻结）
- 特征：clip512 + color24 = 536 维
- 头：题材 OneVsRest LR(balanced) / 风格 OneVsRest LR(balanced)，均 sigmoid
- 划分：按 photographer_id 分组 70/15/15，seed=42

## 指标
| 维度 | train | val | test | macro-F1 | 备注 |
|---|---|---|---|---|---|
| 题材（8类整体） | 342 | 72 | 72 | 0.78 | |
| 题材（人像5子类均值） | — | — | — | 0.85 | 业务主力指标 |
| 风格（13类） | 340 | 73 | 73 | 0.71 | 10/13 类 F1>0.6 |

## 决策
- 拆掉/合并的类：WESTERN F1 仅 0.51 且与 CINEMATIC 混淆 28% → 拆掉，收敛到 12 类，macro-F1 0.68→0.72
- 是否交付题材头：是

## 已知问题
- WESTERN 定义过宽，已拆
- FRESH 与 JAPANESE 在逆光场景互相误判
- 模型作用域：人像为主，判建筑/美食风格偏弱
```

---

## 11. 故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `clip ok` 卡住 | huggingface.co 被墙 | 确认 `$env:HF_ENDPOINT`，重开终端 |
| `prepare.py` 报「风格 X 本期不训练」 | 用了停用类 | 13 个启用风格之外的都不可用（`LOW_SAT` 已移入 TONE） |
| 风格分布总和 > 图片数 | 多标签正常现象 | 不需处理 |
| `colorfeat` 打印 24 个 0.0000 | 读图失败 | 用 `colorfeat.open_rgb`，不要 cv2 |
| `[skip] 训练集只有 8 张` | 样本太少 | 补到 40 正样本/类 |
| 风格 macro-F1 只有 0.4 | 标注一致性差 / 类太少样本 | 先查一致性自检，再补样本，最后才考虑合并类 |
| 风格 `accuracy` 只有 0.3 | 多标签的子集准确率，正常 | 看 macro-F1 与 per-class F1，忽略 accuracy |
| 某类 F1 恒为 0 | 正样本 < 5，或 code 拼错 | 看 `metrics_report.txt` 的 support 列 |
| 所有类都被判为 true | 阈值太低 / 类别不均衡 | `class_weight=balanced` 已在代码；检查 `threshold.json` 是否被写成 0 |
| `MONO` 和其他风格同时出现 | 多标签没有互斥约束 | 业务侧后处理：MONO 命中就丢掉其他风格（§5.5） |
| `STUDIO` 全被判成 `INTERIOR_PORTRAIT` | 两人定义没对齐 | 回 §5.3，重标 20 张 |
| `tone` 字段缺失 | 跑的是旧版 serve.py | 用最新代码 |
| `tone` 判定不对 | 阈值未校准 | 跑 50 张看 `color` 分布，改 `derive_tone` 阈值（不用重训） |
| `max abs diff` > 0.1 | 标准化没折叠 / 特征顺序不一致 | 用 `train.py:export_onnx()` |
| 服务返回 `fallback: "ZERO_SHOT"` | `models/*.onnx` 没找到 | 检查 `MODEL_DIR` 与 `models/` 路径 |
| `pip install torch` 下 2.5GB | 装成 CUDA | 用 `--index-url .../cpu` |

---

## 12. 不要做的事

1. ❌ 不要混维度（"低饱和"是 TONE、"棚拍"是题材）。
2. ❌ 不要让风格头回退成单标签 softmax。13 类互斥就是灾难。
3. ❌ 不要在标注时纠结"最像哪个"——多标签就标全部成立的。
4. ❌ 不要扩到 20 类以上。每加一类都要 40 个正样本和一次标注纪律对齐。
5. ❌ 不要微调 CLIP。
6. ❌ 不要随机划分。
7. ❌ 不要给风格加颜色增强。
8. ❌ 不要把阈值硬编码进 Java。
9. ❌ 不要改 `classes` 顺序却不更新 `labels.json`。
10. ❌ 不要把训练图片放进仓库/交付物/演示视频。
11. ❌ 不要用 AI 生成图训练。
12. ❌ 不要为了保住 13 类而容忍 WESTERN 的 F1 0.51。**拆掉一个类比留着一个坏类诚实。**

---

## 13. 本期不在训练范围的维度

| 维度 | 正确做法 | 为什么不用训练 |
|---|---|---|
| 是否人像 | 人脸检测 + `人脸框面积 / 画面面积 > 0.02` | 几乎确定性，检测比分类准 |
| 人数 | 人脸/人体框计数 | 几何问题 |
| 景别（特写/半身/全身） | 人脸框高 ÷ 画面高：>30% 特写、10~30% 半身、<10% 全身 | 同上 |
| **影调属性 TONE**（9 个） | **`serve.py:derive_tone()` 已实现**，从 24 维色彩特征按阈值输出 | 属性可叠加、可数值判；塞进风格 softmax 会互相拉扯 |
| 服装 / 地点 / 描述 | 多模态大模型（Qwen-VL 等） | 需要世界知识与文化常识 |

**执行者的边界：只训题材（8 类）+ 风格（13 类）两个多标签头，其余不要碰。**

---

## 附录 A · 应急：CLIP 拉不下来

只用 24 维色彩特征训风格头：

1. `cmd_extract` 跳过 `extract_clip`，让 `clip = np.zeros((len(paths), 0), np.float32)`
2. `cmd_fit` 的 `rows_for()` 去掉 `cache["clip"]` 拼接；`dim` 改 24
3. `serve.py` → `FEATURE_DIM = 24`，`build_inputs()` 只返回 `color_features(img)`；`labels.json` 的 `feature_layout` 写 `["color24"]`

**限制**：只能救风格。题材没有 CLIP 做不了——走「检测 + 几何 + VLM」。

---

## 附录 B · 在 GPT 沙箱里跑的注意事项

1. 沙箱常无外网或限速，600MB CLIP 可能下不动。先跑 §2.3 的 `clip ok`，不通走附录 A。
2. 会话结束文件就没了。训完立刻把 `models/` 打包下载。
3. 不要在同一会话里既装依赖又下权重又训练。
4. 不要相信沙箱指标能代表线上。

**更省事：GPT 写和改代码，本机跑。** 把这段连同本文档发给 GPT：

```
你在本项目里负责「图片题材/风格分类器」的训练实现。
先读 ai-classifier/TRAIN-HANDOVER.md（唯一规格来源）和 pipeline/ 下的
colorfeat.py、train.py、prepare.py、serve.py。

约束（违反视为错误）：
1. 训两个头，且都是多标签 sigmoid：题材 8 类 + 风格 13 类。
2. 类别只能取 labels/dictionary.json 里 enabled=true 的 code，不许新增。
3. 只训线性头，冻结 CLIP；不得改写特征抽取逻辑。
4. 特征布局固定 [clip512, color24]，顺序见 §7.1。
5. ONNX 契约见 §7.2：输入名 features、输出名 logits、float32、标准化已折叠进权重。
6. labels.json 的 multi 必须是 true（两个头都是）。
7. 不要训「是否人像 / 人数 / 景别 / TONE」（§13）。
8. 输出代码必须能直接 `python -m pipeline.train fit` 跑通，不要伪代码。

我需要你做的具体事情是：<在这里写这一轮要它做的事>
```

---

## 附录 C · 文档索引

| 想知道什么 | 看哪 |
|---|---|
| 每个标签的准确定义、易混对、判定顺序 | `labels/dictionary.json` 的 `definition` / `negative_hint` / `_meta` |
| 24 维特征各自的物理含义 | `pipeline/colorfeat.py` 的 `FEATURE_NAMES` 注释 |
| TONE 阈值在哪 | `pipeline/serve.py:derive_tone()` |
| 为什么这样选型（讲给评委听） | 根目录 `AI-3_图片分类打标签工作流.md` §4 |
| 不训练的维度怎么做 | 同文档 §4.5 |
| 标签表结构 | `sql/ai_classify.sql` |
| 日常跑通用法 | `README.md` |
