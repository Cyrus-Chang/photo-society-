"""生成风格锚图模型的最终报告（每类召回、混淆对、错投清单），写 models/STYLE-ANCHORS.md。"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np

from pipeline.anchors import CODES, preferred_dirname, scan
from pipeline.console import ensure_utf8

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "models" / "STYLE-ANCHORS.md"


def main() -> int:
    ensure_utf8()
    z = np.load(ROOT / "cache" / "anchors_feat.npz", allow_pickle=True)
    clip, color = z["clip"], z["color"]
    found = scan(ROOT / "data" / "incoming" / "anchors")
    dir2code = {f.parent.name: code for code, files in found.items() for f in files}
    dir_of = {code: files for code, files in found.items()}
    y = np.array([dir2code[Path(p).parent.name] for p in z["paths"]])
    paths = [str(p) for p in z["paths"]]

    art = np.load(ROOT / "models" / "style.anchors.npz", allow_pickle=True)
    codes = list(art["codes"])
    P, CP, mu, w = art["clip"], art["color"], art["color_mu"], float(art["weight"])
    idx = {c: np.where(y == c)[0] for c in codes}
    cc = color - mu
    cc /= (np.linalg.norm(cc, axis=1, keepdims=True) + 1e-9)

    scores = np.zeros((len(clip), len(codes)))
    for i in range(len(clip)):
        for j, c in enumerate(codes):
            mem = idx[c][idx[c] != i]
            pv = clip[mem].mean(0); pv /= (np.linalg.norm(pv) + 1e-9)
            cv = cc[mem].mean(0); cv /= (np.linalg.norm(cv) + 1e-9)
            scores[i, j] = float(clip[i] @ pv) + w * float(cc[i] @ cv)

    pred = np.array(codes)[scores.argmax(1)]
    acc = float((pred == y).mean())
    conf = Counter((t, p) for t, p in zip(y, pred) if t != p)

    lines = [f"# 风格锚图模型（原型匹配）", "",
             f"- 锚图 {len(y)} 张 / {len(codes)} 类，来源 `data/incoming/anchors/`",
             f"- 留一法准确率 **{acc:.3f}**（随机基线 {1/len(codes):.3f}，同批图零样本 0.331）",
             f"- 打分：`cos(CLIP) + {w:.2f} * cos(色彩-均值)`，置信度按间隔分档插值", "",
             "| 风格 | 目录 | n | 召回 | 紧致度 |", "|---|---|---|---|---|"]
    for j, c in enumerate(codes):
        m = idx[c]
        rec = float((pred[m] == c).mean())
        coh = float((clip[m] @ P[j]).mean())
        flag = " ⚠" if rec < 0.6 else ""
        lines.append(f"| {c} | {preferred_dirname(c)} | {len(m)} | {rec:.2f}{flag} | {coh:.3f} |")

    if conf:
        lines += ["", "## 最容易混的类对（留一法）", ""]
        lines.append("| 真 → 判成 | 次数 |")
        lines.append("|---|---|")
        for (t, p), n in conf.most_common(8):
            lines.append(f"| {preferred_dirname(t)} → {preferred_dirname(p)} | {n} |")

    mis = [(y[i], pred[i], Path(paths[i]).name) for i in range(len(y))
           if scores[i].argmax() != codes.index(y[i])]
    weak = [(c, float((pred[idx[c]] == c).mean())) for c in codes
            if float((pred[idx[c]] == c).mean()) < 0.6]
    if weak:
        lines += ["", "## 建议补图的类", ""]
        for c, rec in sorted(weak, key=lambda kv: kv[1]):
            lines.append(f"- **{preferred_dirname(c)}**（{c}）：召回 {rec:.2f}，"
                         f"现有 {len(idx[c])} 张，建议再补 3~5 张更典型的")

    lines += ["", "## 复跑", "", "```powershell",
              r".\.venv\Scripts\python.exe tools\check_anchors.py      # 检查张数/分辨率/重复",
              r".\.venv\Scripts\python.exe tools\build_anchors.py      # 原型 + 类内自检",
              r".\.venv\Scripts\python.exe tools\eval_style.py         # 留一法（三种打分对比）",
              r".\.venv\Scripts\python.exe tools\finalize_style.py     # 固化 models/style.anchors.npz",
              r".\.venv\Scripts\python.exe tools\calibrate_style_temp.py  # 置信度分档",
              r".\.venv\Scripts\python.exe tools\style_report.py       # 本报告", "```"]

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:24]))
    print(f"\n已写入 {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
