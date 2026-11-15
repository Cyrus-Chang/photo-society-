"""置信度校准：用留一法的实测分档，把「第一名领先亚军的间隔」映射成「判对的概率」。

为什么不用 softmax：13 类原型余弦差得极小（常常 0.005），softmax 无论怎么调温度都摊平在 8%~13%。
为什么不用逻辑回归：拟合出来在间隔≈0 处给 0.70，而实测那一档只有 0.50——口径对不上。
这里直接按间隔的四分位分 4 档，每档存"实测正确率"，推理时线性插值。
好处是每个数字都能在留一法报告里对上，答辩时可直接复核。

产物写回 models/style.anchors.npz（bin_edges / bin_accs）与 .json。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from pipeline.anchors import CODES, preferred_dirname, scan
from pipeline.console import ensure_utf8

ROOT = Path(__file__).resolve().parents[1]
NPZ = ROOT / "models" / "style.anchors.npz"
JSONF = ROOT / "models" / "style.anchors.json"


def main() -> int:
    ensure_utf8()
    z = np.load(ROOT / "cache" / "anchors_feat.npz", allow_pickle=True)
    clip, color = z["clip"], z["color"]
    found = scan(ROOT / "data" / "incoming" / "anchors")
    dir2code = {f.parent.name: code for code, files in found.items() for f in files}
    y = np.array([dir2code[Path(p).parent.name] for p in z["paths"]])

    art = np.load(NPZ, allow_pickle=True)
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

    order = np.argsort(-scores, axis=1)
    pred = np.array(codes)[order[:, 0]]
    correct = (pred == y).astype(float)
    margin = scores[np.arange(len(pred)), order[:, 0]] - scores[np.arange(len(pred)), order[:, 1]]
    acc = float(correct.mean())

    edges = np.quantile(margin, [0, 0.25, 0.5, 0.75, 1.0])
    edges[0], edges[-1] = -1.0, margin.max() * 2 + 1.0     # 两端放开，插值不越界
    centers, accs = [], []
    print(f"留一法准确率 {acc:.3f}，间隔 {margin.min():.4f}~{margin.max():.4f}\n")
    print(f"{'档':>2s} {'间隔区间':>20s} {'n':>4s} {'实测正确率':>10s}")
    for k in range(4):
        lo, hi = edges[k], edges[k + 1]
        m = (margin >= lo) & (margin <= hi)
        if not m.any():
            continue
        a = float(correct[m].mean())
        centers.append(float(margin[m].mean()))
        accs.append(a)
        print(f"{k+1:>2d} {lo:>9.4f}~{hi:<9.4f} {int(m.sum()):>4d} {a:>10.2f}")
    # 保序（防止小样本抖动导致不单调）
    for i in range(1, len(accs)):
        accs[i] = max(accs[i], accs[i - 1])

    np.savez_compressed(NPZ, codes=art["codes"], clip=P, color=CP, color_mu=mu,
                        weight=art["weight"],
                        bin_centers=np.array(centers, dtype=np.float32),
                        bin_accs=np.array(accs, dtype=np.float32))
    meta = json.loads(JSONF.read_text(encoding="utf-8"))
    meta.pop("confidence", None)
    meta["confidence"] = {
        "rule": "按留一法间隔分档的实测正确率，线性插值",
        "bin_centers": [round(c, 5) for c in centers],
        "bin_accs": [round(a, 3) for a in accs],
        "loo_accuracy": round(acc, 4),
    }
    JSONF.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n已更新 models/style.anchors.npz 与 .json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
