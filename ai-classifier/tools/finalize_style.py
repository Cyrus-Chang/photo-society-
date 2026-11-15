"""把锚图固化成可直接推理的风格模型（原型匹配版）。

产物：
  models/style.anchors.npz   codes / 每类 CLIP 原型 / 每类色彩原型 / 全局色彩均值 / 权重 / 温度
  models/style.anchors.json  人读的指标（类内紧致度、留一法准确率、温度）

打分：score = cos(clip) + w * cos(color - 全局均值)，再 softmax(score / T)。
w 与 T 都是在留一法上定的，不是拍脑袋：w=0.02 最优（0.706），T 用极大似然拟到概率上。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from pipeline.anchors import CODES, preferred_dirname, scan
from pipeline.console import ensure_utf8

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cache" / "anchors_feat.npz"
OUT = ROOT / "models"
W_COLOR = 0.02


def softmax(z):
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


def main() -> int:
    ensure_utf8()
    z = np.load(CACHE, allow_pickle=True)
    clip, color = z["clip"], z["color"]
    found = scan(ROOT / "data" / "incoming" / "anchors")
    dir2code = {f.parent.name: code for code, files in found.items() for f in files}
    y = np.array([dir2code[Path(p).parent.name] for p in z["paths"]])
    codes = [c for c in CODES if (y == c).any()]
    idx = {c: np.where(y == c)[0] for c in codes}

    mu = color.mean(0)
    cc = color - mu
    cc /= (np.linalg.norm(cc, axis=1, keepdims=True) + 1e-9)

    clip_p, col_p = [], []
    for c in codes:
        pv = clip[idx[c]].mean(0)
        clip_p.append(pv / (np.linalg.norm(pv) + 1e-9))
        cv = cc[idx[c]].mean(0)
        col_p.append(cv / (np.linalg.norm(cv) + 1e-9))
    P, CP = np.stack(clip_p), np.stack(col_p)

    # 留一法分数（用于温度标定与准确率汇报）
    loo_scores = np.zeros((len(clip), len(codes)))
    for i in range(len(clip)):
        for j, c in enumerate(codes):
            mem = idx[c][idx[c] != i]
            pv = clip[mem].mean(0)
            pv /= (np.linalg.norm(pv) + 1e-9)
            cv = cc[mem].mean(0)
            cv /= (np.linalg.norm(cv) + 1e-9)
            loo_scores[i, j] = float(clip[i] @ pv) + W_COLOR * float(cc[i] @ cv)

    acc = float((np.array(codes)[loo_scores.argmax(1)] == y).mean())

    # 温度：网格搜索最小化 NLL
    truth = np.array([codes.index(c) for c in y])
    best_t, best_nll = None, 1e18
    for t in np.arange(4, 41, 1.0):
        p = softmax(loo_scores / t)
        nll = -np.log(np.clip(p[np.arange(len(y)), truth], 1e-9, 1)).mean()
        if nll < best_nll:
            best_nll, best_t = nll, float(t)

    p = softmax(loo_scores / best_t)
    print(f"留一法准确率 {acc:.3f}   温度 T={best_t:.0f}   NLL={best_nll:.3f}")
    print(f"{'风格':8s} {'n':>3s} {'紧致度':>7s}")
    metas = []
    for j, c in enumerate(codes):
        m = idx[c]
        coh = float((clip[m] @ P[j]).mean())
        metas.append({"code": c, "dir": preferred_dirname(c), "n": int(len(m)), "cohesion": round(coh, 4)})
        print(f"{preferred_dirname(c):8s} {len(m):>3d} {coh:>7.3f}")

    OUT.mkdir(exist_ok=True)
    np.savez_compressed(OUT / "style.anchors.npz",
                        codes=np.array(codes), clip=P.astype(np.float32),
                        color=CP.astype(np.float32), color_mu=mu.astype(np.float32),
                        weight=np.float32(W_COLOR), temperature=np.float32(best_t))
    (OUT / "style.anchors.json").write_text(json.dumps({
        "kind": "prototype-anchors",
        "clip_model": "openai/clip-vit-base-patch32",
        "feature_layout": ["clip512_l2norm", "color24_minus_mean_l2norm"],
        "weight_color": W_COLOR,
        "temperature": best_t,
        "loo_accuracy": round(acc, 4),
        "loo_nll": round(float(best_nll), 4),
        "random_baseline": round(1 / len(codes), 4),
        "zeroshot_same_set": 0.331,
        "classes": metas,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n已写入 {OUT / 'style.anchors.npz'} 与 .json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
