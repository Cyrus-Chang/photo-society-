"""扫色彩权重：在留一法下找 clip 余弦与 24 维色彩距离的最佳配比。"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from pipeline.anchors import CODES, preferred_dirname, scan
from pipeline.console import ensure_utf8

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cache" / "anchors_feat.npz"


def main() -> int:
    ensure_utf8()
    z = np.load(CACHE, allow_pickle=True)
    clip, color = z["clip"], z["color"]
    found = scan(ROOT / "data" / "incoming" / "anchors")
    dir2code = {f.parent.name: code for code, files in found.items() for f in files}
    y = np.array([dir2code[Path(p).parent.name] for p in z["paths"]])
    codes = [c for c in CODES if (y == c).any()]
    idx = {c: np.where(y == c)[0] for c in codes}

    mu, sd = color.mean(0), color.std(0) + 1e-6
    cz = (color - mu) / sd

    def loo(w: float, color_mode: str) -> float:
        hits = 0
        for i in range(len(clip)):
            best, best_p = -1e9, None
            for c in codes:
                mem = idx[c][idx[c] != i]
                if not len(mem):
                    continue
                pv = clip[mem].mean(0)
                pv /= max(1e-9, np.linalg.norm(pv))
                cos = float(clip[i] @ pv)
                if color_mode == "dist":
                    s = cos - w * float(np.linalg.norm(cz[i] - cz[mem].mean(0)))
                else:  # cos：色彩先减全局均值再算余弦
                    cc = color - mu
                    ccc = cc / (np.linalg.norm(cc, axis=1, keepdims=True) + 1e-9)
                    cv = ccc[mem].mean(0)
                    cv /= max(1e-9, np.linalg.norm(cv))
                    s = cos + w * float(ccc[i] @ cv)
                if s > best:
                    best, best_p = s, c
            hits += int(best_p == y[i])
        return hits / len(clip)

    print(f"{'模式':6s} {'w':>6s}  准确率")
    rows = []
    for mode in ("dist", "cos"):
        for w in (0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.5):
            acc = loo(w, mode)
            rows.append((acc, mode, w))
            print(f"{mode:6s} {w:>6.2f}  {acc:.3f}")
    best = max(rows)
    print(f"\n最佳：{best[1]} w={best[2]:.2f} → {best[0]:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
