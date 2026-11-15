# ai-classifier · 图片类型/风格分类器骨架

配合根目录 `AI-3_图片分类打标签工作流.md` 使用。**这里只有模型侧**（特征、训练、推理服务）；
入库链路、标签表、Spring Boot 集成在设计文档里。

## 它解决什么

给摄影师上传的照片自动打两类标签：

| 维度 | 例子 | 谁产出的 |
|---|---|---|
| 题材 SUBJECT（8 类） | 人像细分：棚拍 / 外景 / 漫展场照 / 街拍人像 / 室内环境人像；非人像：建筑 / 风光 / 静物美食 | 分类器（多标签） |
| 主风格 STYLE（13 类） | 蓝调 / ins风 / 日系 / 韩系 / 欧美 / 胶片 / 复古 / 电影感 / 清新 / 暗调 / 黑白 / 港风 / 赛博 | 分类器（**多标签**，可共存） |
| 影调属性 TONE（9 个） | 暖调 / 冷调 / 高饱和 / 低饱和 / 高对比 / 柔和 / 高调 / 低调 / 黑位抬升 | **规则算**，不训练 |
| 光线 LIGHT、服装 OUTFIT | 逆光 / 汉服 | 多模态大模型，或摄影师手填 |

## 5 分钟跑通（先验证环境，再谈效果）

```bash
cd ai-classifier
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt

# 1) 只看色彩特征，不依赖任何模型权重，先确认路径/EXIF 没问题
python -m pipeline.colorfeat D:\data\test.jpg

# 2) 抽特征（第一次会下载 CLIP，约 600MB；国内先设镜像：）
set HF_ENDPOINT=https://hf-mirror.com
python -m pipeline.train extract --csv labels.csv --cache cache/feat.npz

# 3) 训练两个头 + 导出 onnx（秒级）
python -m pipeline.train fit --csv labels.csv --cache cache/feat.npz --out models

# 4) 起服务
uvicorn pipeline.serve:app --host 127.0.0.1 --port 8100
curl -F "file=@D:\data\test.jpg" http://127.0.0.1:8100/v1/classify
```

`labels.csv` 只有四列，没有它什么都跑不了：

```csv
path,subject,style,photographer_id
D:\data\001.jpg,STUDIO,BLUE_TONE,p001
D:\data\002.jpg,"STUDIO,CONVENTION","JAPANESE,FRESH",p001
D:\data\003.jpg,ARCHITECTURE,DARK_MOOD,p002
```

- `photographer_id` **必填**。训练按它分组划分，否则同一摄影师的同质片子会同时进训练和验证集，指标虚高 15~25 个点，上线即崩。
- `subject` 和 `style` **都是多标签**（逗号分隔；字段里含逗号必须加引号）。平均每张图标 1.8 个风格。
- 类别码必须来自 `labels/dictionary.json` 且 `enabled=true`（当前：题材 8 类、风格 13 类），写错或用了停用类会在 `prepare.py` 直接报错。

## 目录

> **训练外包给别人/别的模型跑？先读 [`TRAIN-HANDOVER.md`](TRAIN-HANDOVER.md)。**
> 那份文档是自包含的：环境、拉什么、下什么数据、标注规范、每一步命令、产物契约、验收清单、故障排查全在里面，
> 执行者不需要看本文件，也不需要看根目录的设计文档。

```
ai-classifier/
├─ TRAIN-HANDOVER.md       ★ 训练交接文档（外包执行者只读这一份）
├─ pipeline/prepare.py     目录约定 → labels.csv，并做标注完整性检查
├─ pipeline/colorfeat.py   24 维色彩影调特征（风格分类的关键，纯 numpy/PIL）
├─ pipeline/train.py       抽特征 / 分组划分 / 训练线性头 / 评测 / 导出 onnx
├─ pipeline/cliputil.py    CLIP 取特征兼容层（transformers 4.x / 5.x 返回值不一样）
├─ pipeline/console.py     Windows GBK 控制台编码兜底
├─ pipeline/serve.py       FastAPI + ONNX Runtime 推理服务
├─ labels/dictionary.json  标签字典（类别空间唯一真源）
├─ sql/ai_classify.sql     4 张新表 DDL + 字典种子 + work_tag 增量迁移
├─ tools/fetch_clip.py     拉 CLIP 权重（镜像 + 跳过 flax/tf）
├─ tools/smoke_vision.py   视觉链路冒烟（CLIP 512 维 + 色彩 24 维）
├─ tools/smoke_pipeline.py 全链路冒烟（prepare→extract→fit→ONNX，标签是假的，别当结果）
├─ tools/zero_shot_preview.py 零样本预览：不给标注也能看 8 题材 / 13 风格 prompt 分不分得开
├─ tools/prelabel.py        标注加速：零样本预填 CSV → 人工确认 → 直接生成 data/ 目录
├─ data/                    训练图（按摄影师/题材__风格 分目录；见 data/README.md）
├─ reports/                零样本预览等体检产物（不是训练指标）
├─ models/                 训练产物（onnx / labels / threshold / metrics）
└─ cache/                  特征缓存 npz（可删，重跑会重建）
```

## 视觉主干就绪状态（2026-11-13 实测）

- **CLIP ViT-B/32 权重已落盘**（580.7 MB，走 hf-mirror，76 秒）：
  `C:\Users\discr\.cache\huggingface\hub\models--openai--clip-vit-base-patch32\snapshots\3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268`
  拉取命令：`python tools/fetch_clip.py`（只下 `pytorch_model.bin` + 文本/预处理配置，flax/ tf 权重不拉）。
- **依赖已验证**：torch 2.15.0+cpu / transformers 5.22.2 / onnxruntime 1.31.1 / onnxscript 0.7.2 全部可 import，
  `tools/smoke_vision.py` 与 `tools/smoke_pipeline.py` 均 PASS（后者导出的 ONNX 输入 `(batch, 536)`、输出 `(1, N)`）。
- **两个已经踩过的版本坑（代码里已修，别回退）**：
  1. transformers ≥5 的 `get_image_features()` 返回 `BaseModelOutputWithPooling` 而不是 Tensor，直接
     `normalize()` 会报 `'BaseModelOutputWithPooling' object has no attribute 'norm'`。统一走 `pipeline/cliputil.py`。
  2. `prepare.py` 报告里的 `⚠` 在中文 Windows（cp936）控制台会 `UnicodeEncodeError` 崩在最后一段输出。
     入口已调用 `ensure_utf8()`。
- **torch ≥2.15 必须装 `onnxscript`**，否则 `torch.onnx.export` 走 dynamo 导出器时 ModuleNotFoundError（已写进 requirements.txt）。
- **仍未就绪的只有一样**：`data/` 里的真实标注图。没有它就没有 `labels.csv`、没有 `cache/`、没有 `models/`。
- **零样本体检可以现在做**：`python tools/zero_shot_preview.py` 把 `public/works` 的 26 张样片
  按字典 `prompt_en` 直接打分 → `reports/zero_shot_preview.csv`。实测题材 top1 置信度多在 0.7~0.99，
  风格 top1 多在 0.3~0.9（风格本来就是分布外概念，这正是要训线性头、且风格头必须拼 24 维色彩特征的原因）。

## 配套的视觉技能包（skillhub.cn，2026-11-13 装）

装在 `C:\Users\discr\.dsh\skills\`（用户级技能根目录，DSH 启动时扫描；**装完要新开一个会话**才进技能表）：

| 技能 | 目录 | 在本项目里的用途 | 备注 |
|---|---|---|---|
| `image-utils` | `clawhub_galbria--image-utils` | 纯 Pillow 的批处理：512 长边缩放、转 webp、去 EXIF、灰度副本（补 `MONO`）、批量重命名 | MIT，无第三方服务；`references/code-examples/image_utils.py` 是可直接 import 的库 |
| `image-cropper` | `clawhub_mingo-318--image-cropper` | 按 COCO/YOLO/VOC/LabelMe 标注框批量裁物体，用来从公开数据集里抽题材样本 | 纯 Pillow；**上游 SKILL.md 漏了 frontmatter，本地已补 name/description**，重装后要再补 |
| `image-search`（包名 tobemsk-image-search） | `clawhub_tobemsk--tobemsk-image-search` | CLIP + FAISS 的本地图片语义检索脚手架，对应 `/v1/embed` 与「作品智能入库」 | 默认模型是 `OFA-Sys/chinese-clip-vit-base-patch16`、默认全盘扫描。**用前必须改 `scripts/config.py` 两行**：`MODEL_NAME` 换成 `openai/clip-vit-base-patch32`（否则向量空间和 `serve.py` 不通用）、`SCAN_ROOTS` 指向作品目录（别让它扫 C/D/E/F 全盘）；`faiss-cpu` 尚未在本机验证 |

拉取/检索脚本留在 `tools/skillhub_*.py`（走 `api.skillhub.cn`，逐个文件校验 sha256；要装别的技能改 `CANDS` 即可）。
**没有装**的几类及原因：`yolo-vision-tools`（交接文档 §3 明确不需要 YOLO）、`computer-vision-expert`（只有人设没工具）、
`image-resizer`（依赖 sharp + npm，本机 npm 装包受限，且与本目录「一律走 PIL」的约定冲突）、
`exiftool-*`（只有文档桩，不带 exiftool 本体）、所有需要 API Key / 付费的技能。



## 风格头：锚图原型匹配（2026-11-15，已接入 serve.py）

没有客片，改用**每类 6~17 张典型参考图**做原型匹配（不训练权重）：13 类 × 136 张锚图，
每类存一个 CLIP 原型 + 一个色彩原型，推理时算 cos(CLIP) + 0.02 x cos(色彩) 取最近。

| 指标 | 数值 |
|---|---|
| 留一法准确率 | **0.706** |
| 同批图的零样本 | 0.331 |
| 随机基线 | 0.077 |

**零样本的两倍多**，这是本轮最关键的结论：风格确实是分布外概念，光靠 prompt 不行。

产物：`models/style.anchors.npz`（原型向量 + 置信度分档）、`models/STYLE-ANCHORS.md`（每类召回、易混类对、建议补图的类）。

三个已知短板：

- **复古 0.27 / ins风 0.33 / 日系 0.43** 召回偏低，主因是每类只有 6~11 张且互相抢样本
- 最常混：复古→胶片、复古→韩系、暗调→黑白
- 置信度只落在 0.5~0.9（按间隔分档），**它不是概率，是"这一档间隔的历史正确率"**

锚图留在 `data/incoming/anchors/`，删不删都不影响推理（`models/style.anchors.npz` 自包含）；
**进交付物前建议删掉**。
## 公开数据基线：题材头 v0 已训出（2026-11-13）

用公开摄影数据把 **8 类题材里的非人像 3 类**（建筑 / 风光 / 静物美食）训出来了，672 张、8 个混合分组：

| 划分 | 零样本 acc / macro-F1 | 训练后 acc / macro-F1 |
|---|---|---|
| val (n=85) | 0.7765 / 0.7732 | **0.9882 / 0.9881** |
| test (n=83) | 0.7590 / 0.7496 | **1.0000 / 1.0000** |

产物在 `models/`（subject.onnx + labels/threshold/metrics + metrics_report.txt + `TRAIN_LOG.md`），
数据来源与许可、复跑命令、**四条必须写进答辩的前提**都在 [models/TRAIN_LOG.md](models/TRAIN_LOG.md)，
数据源核查台账在 [docs/DATA-SOURCES.md](docs/DATA-SOURCES.md)。

三条最要紧的：

1. **只有 3 类**，人像 5 类一张没有；**风格头没训**（这批数据风格列是占位值，`--tasks subject` 只训题材）。
2. **test=1.0 是上限不是水平**：分组是"每类第 i 张"机械切的，同抓取词的近邻图会跨训练/测试集。
3. **这个 3 类头不能直接上生产**：它只认识 3 个类，遇到人像会硬塞进这 3 类。
   实测 `public/works/2d877e35…jpg`（藏区经幡前的背影人像）被它判成 `STILL_FOOD 0.998`。
   给人像和风格用的仍然是 `serve.py` 的零样本兜底。

## 现在离训练还有多远（2026-11-13 收口）

除 `data/` 之外全部就绪。已把**最贵的标注环节**做成半自动：

```powershell
# ① 照片全扔 data/incoming/（可分子目录，一个子目录 = 一次拍摄）
.\.venv\Scripts\python.exe tools\prelabel.py scan data\incoming --person-from-dir --out labels_proposed.csv
# ② Excel 过一遍：decision=skip 弃图，改错的 subject_1 / style_1，photographer_id 按批次填
.\.venv\Scripts\python.exe tools\prelabel.py apply labels_proposed.csv --data data
# ③ prepare → extract → fit
```

26 张样片实测：预填 26 张约 40 秒，`apply` 建出 16 个 `题材__风格` 目录，
`prepare` 正常报告分布（ARCHITECTURE 7 / STREET_PORTRAIT 7 / BLUE_TONE 10 ……全部 `⚠ 偏少`）。
**分布这一关必须靠真图补**：26 张、1 个来源离底线（300 张 / ≥3 来源 / 每类 ≥30）还差一整个数量级。

## 为什么是"冻结 CLIP + 线性头"，不是"微调 CLIP"

每类 50~200 张的量级上，微调整网会灾难性遗忘 + 过拟合，验证集 macro-F1 通常比
linear probe 低 10 个点以上，而且每次迭代要 GPU 几十分钟。冻结后特征只提一次存 npz，
之后调参是秒级——两个人、五天工期，这是唯一能反复试错的做法。

真到需要更高精度，升级顺序是：
TTA 翻转平均 → LoRA/Adapter（训 1~2M 参数）→ 最后才解冻顶层小学习率微调。
**不要从零训 CNN。**

## 为什么风格头要多拼 24 维色彩特征

"蓝调/ins风/日系"是**分布外概念**，CLIP 文本塔本来就分不清；而且 CLIP 训练时用了强颜色
增广，对全局色调不敏感。同一张图换个调色层，内容不变，风格判定的信息几乎全在
LAB 均值、饱和度分位、黑点位置、冷暖差这些低层统计量里。
类型头（语义）用 512 维 CLIP 就够，风格头必须拼这 24 维。

`pipeline/colorfeat.py` 里的 `FEATURE_NAMES` 每一项都对着一个摄影师的直觉说法，
标注员和算法才能对齐口径。

## 常见坑

| 现象 | 原因 | 处理 |
|---|---|---|
| `colorfeat` 读不到图 | 中文路径 + cv2.imread 静默返回 None | 本目录一律走 PIL，不要换 cv2 |
| 竖拍图特征不对 | 未做 EXIF 方向纠正 | `open_rgb()` 已 `exif_transpose`，别绕开它 |
| CLIP 下载卡住 | huggingface.co 直连不通 | `set HF_ENDPOINT=https://hf-mirror.com` |
| 验证集 F1 高得离谱（>0.98） | 随机划分导致同摄影师泄漏 | 检查 `photographer_id` 是否有值 |
| 某类 F1 恒为 0 | 该类样本 < 5 张，或 category code 拼错 | 看 `models/metrics_report.txt` 的 support 列 |
| 风格全判成同一类 | 训练集本身风格不均衡（比如 80% 都是 ins 风） | 加样本，或先合并近义类 |
| onnx 导出报 opset | torch 版本过老 | `--opset 17` 或升级 torch ≥ 2.0 |
| 服务启动 `clip 加载失败` | 权重没下 / torch 没装 | 会降级成色彩规则 + 零样本，接口仍可用 |

## 与训练集有关的红线

- 训练图只放你**有授权**的：队友的作品、公开可商用数据集（Open Images / COCO）、
  自己拍的。**不要爬小红书/微博的图**，比赛交付物要过版权审查。
- 用户原图不要直接进训练池：先转 512 长边 webp，清 EXIF，单独存 `classify_sample`。
- 人脸图不需要做身份相关的任何事，只做题材/风格分类。
