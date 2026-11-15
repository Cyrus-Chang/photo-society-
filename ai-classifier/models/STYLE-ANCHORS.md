# 风格锚图模型（原型匹配）

- 锚图 136 张 / 13 类，来源 `data/incoming/anchors/`
- 留一法准确率 **0.706**（随机基线 0.077，同批图零样本 0.331）
- 打分：`cos(CLIP) + 0.02 * cos(色彩-均值)`，置信度按间隔分档插值

| 风格 | 目录 | n | 召回 | 紧致度 |
|---|---|---|---|---|
| JAPANESE | 日系 | 7 | 0.43 ⚠ | 0.879 |
| KOREAN | 韩系 | 9 | 0.67 | 0.821 |
| INS | ins风 | 6 | 0.33 ⚠ | 0.829 |
| FRESH | 清新 | 11 | 0.73 | 0.837 |
| FILM | 胶片 | 17 | 0.88 | 0.836 |
| VINTAGE | 复古 | 11 | 0.27 ⚠ | 0.808 |
| CINEMATIC | 电影感 | 16 | 0.75 | 0.845 |
| DARK_MOOD | 暗调 | 12 | 0.58 ⚠ | 0.832 |
| MONO | 黑白 | 10 | 1.00 | 0.886 |
| BLUE_TONE | 蓝调 | 8 | 0.88 | 0.840 |
| HK_RETRO | 港风 | 10 | 0.90 | 0.823 |
| CYBER | 赛博 | 7 | 0.86 | 0.873 |
| WESTERN | 欧美 | 12 | 0.67 | 0.838 |

## 最容易混的类对（留一法）

| 真 → 判成 | 次数 |
|---|---|
| 复古 → 胶片 | 3 |
| 复古 → 韩系 | 3 |
| 暗调 → 黑白 | 3 |
| 电影感 → 日系 | 2 |
| 欧美 → 电影感 | 2 |
| 日系 → 暗调 | 1 |
| 日系 → 电影感 | 1 |
| 日系 → 蓝调 | 1 |

## 建议补图的类

- **复古**（VINTAGE）：召回 0.27，现有 11 张，建议再补 3~5 张更典型的
- **ins风**（INS）：召回 0.33，现有 6 张，建议再补 3~5 张更典型的
- **日系**（JAPANESE）：召回 0.43，现有 7 张，建议再补 3~5 张更典型的
- **暗调**（DARK_MOOD）：召回 0.58，现有 12 张，建议再补 3~5 张更典型的

## 复跑

```powershell
.\.venv\Scripts\python.exe tools\check_anchors.py      # 检查张数/分辨率/重复
.\.venv\Scripts\python.exe tools\build_anchors.py      # 原型 + 类内自检
.\.venv\Scripts\python.exe tools\eval_style.py         # 留一法（三种打分对比）
.\.venv\Scripts\python.exe tools\finalize_style.py     # 固化 models/style.anchors.npz
.\.venv\Scripts\python.exe tools\calibrate_style_temp.py  # 置信度分档
.\.venv\Scripts\python.exe tools\style_report.py       # 本报告
```
