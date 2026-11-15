"""留一法评估：原型分类器到底能不能分这 13 类。

为什么要做：CLIP 向量在这批「全是人像/旅拍」的图上余弦本来就高（0.8 起步），
只看余弦会被内容主导。风格信息主要在 24 维色彩特征里（交接文档也是这么说的）。
所以这里比三种打分方式，看色彩到底贡献多少：

  clip  : 只用 CLIP 余弦
  color : 只用 24 维色彩的标准化欧氏距离
  both  : 两者加权

留一法（LOO）：每张图拿"去掉它自己"的原型来判，避免自证。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from pipeline.anchors import CODES, preferred_dirname, scan
from pipeline.console import ensure_utf8

ROOT = Path(__file__).resolve().parents[1]
ANCHORS = ROOT / "data" / "incoming" / "anchors"
CACHE = ROOT / "cache" / "anchors_feat.npz"


def load_features():
    sys.path.insert(0, str(ROOT))
    from pipeline import train

    found = scan(ANCHORS)
    labels, paths = [], []
    for code in CODES:
        for p in found.get(code, []):
            labels.append(code)
            paths.append(str(p))

    if CACHE.exists():
        z = np.load(CACHE, allow_pickle=True)
        if list(z["paths"]) == paths:
            print(f"命中特征缓存 {CACHE.name}")
            return z["clip"], z["color"], np.array(labels), paths

    print(f"抽特征 {len(paths)} 张（约 1 张/秒）…")
    clip = train.extract_clip(paths)
    color = train.extract_color(paths)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(CACHE, paths=np.array(paths), clip=clip, color=color)
    return clip, color, np.array(labels), paths


def loo(clip: np.ndarray, color: np.ndarray, labels: np.ndarray):
    codes = [c for c in CODES if (labels == c).any()]
    idx = {c: np.where(labels == c)[0] for c in codes}

    # 色彩按全体的 std 标准化，避免某几维数值大就压过别的
    mu, sd = color.mean(axis=0), color.std(axis=0) + 1e-6
    cz = (color - mu) / sd

    results = {}
    for mode in ("clip", "color", "both"):
        hits = 0
        preds = []
        for i in range(len(clip)):
            scores = []
            for c in codes:
                members = idx[c][idx[c] != i]
                if len(members) == 0:
                    scores.append(-1e9)
                    continue
                pv = clip[members].mean(axis=0)
                pv /= max(1e-9, np.linalg.norm(pv))
                cos = float(clip[i] @ pv)
                dist = float(np.linalg.norm(cz[i] - cz[members].mean(axis=0)))
                if mode == "clip":
                    s = cos
                elif mode == "color":
                    s = -dist
                else:
                    s = cos - 0.35 * dist      # 经验权重：色彩距离折算到余弦量级
                scores.append(s)
            p = codes[int(np.argmax(scores))]
            preds.append(p)
            hits += int(p == labels[i])
        acc = hits / len(clip)
        results[mode] = (acc, preds)
        per_class = []
        for c in codes:
            m = labels == c
            rec = float((np.array(preds)[m] == c).mean())
            per_class.append((preferred_dirname(c), int(m.sum()), rec))
        print(f"\n[{mode:5s}] 准确率 {acc:.3f}")
        for zh, n, rec in per_class:
            flag = "  ⚠" if rec < 0.7 else ""
            print(f"   {zh:6s} n={n:2d} 召回 {rec:.2f}{flag}")
    return results


def main() -> int:
    ensure_utf8()
    clip, color, labels, paths = load_features()
    print(f"共 {len(labels)} 张，{len({c for c in CODES if (labels == c).any()})} 类")
    res = loo(clip, color, labels)
    best = max(res.items(), key=lambda kv: kv[1][0])
    print(f"\n最好的打分方式：{best[0]}（{best[1][0]:.3f}）")
    base = 1 / len([c for c in CODES if (labels == c).any()])
    print(f"随机基线 {base:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
