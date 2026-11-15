"""把 13 类风格锚图压成「原型向量」，并当场做自检。

原型 = 该类所有锚图 CLIP 向量的均值（再 L2 归一化），另存一份 24 维色彩均值。
推理时算余弦相似度取最近的原型即可，**不训练权重**——50~130 张的规模上，
原型匹配比训线性头更稳，而且加一张锚图就能立刻生效。

自检三件事：
  1. 类内紧致度（成员到自身原型的平均余弦）：低于 0.75 说明这类内部不统一。
  2. 离群图：到自身原型最远的两张，人工复核是不是投错类。
  3. 跨类混淆：如果某张图离**别的**原型更近，基本就是投错类了，直接点名。

产物：
  models/style.prototype.npz   原型向量（clip 512 归一化 + color 24 标准化）
  models/style.prototype.json  类别、紧致度、离群与错投清单
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from pipeline.anchors import CODES, preferred_dirname, scan
from pipeline.console import ensure_utf8

ROOT = Path(__file__).resolve().parents[1]
ANCHORS = ROOT / "data" / "incoming" / "anchors"
OUT_DIR = ROOT / "models"
LOW_COHESION = 0.75
OUTLIER_COS = 0.70


def main() -> int:
    ensure_utf8()
    sys.path.insert(0, str(ROOT))
    from pipeline import train

    found = scan(ANCHORS)
    labels, paths = [], []
    for code in CODES:
        for p in found.get(code, []):
            labels.append(code)
            paths.append(str(p))
    if not paths:
        print("没有找到图，先确认 data/incoming/anchors/ 下的中文目录名没被改过")
        return 2

    print(f"共 {len(paths)} 张，开始抽特征（约 1 张/秒）…")
    clip = train.extract_clip(paths)
    color = train.extract_color(paths)
    labels_arr = np.array(labels)

    protos, colors, stats = {}, {}, {}
    for code in CODES:
        m = labels_arr == code
        if not m.any():
            continue
        v = clip[m].mean(axis=0)
        v /= max(1e-9, np.linalg.norm(v))
        protos[code] = v
        colors[code] = color[m].mean(axis=0)
        cos = clip[m] @ v
        stats[code] = {
            "n": int(m.sum()),
            "cohesion": float(cos.mean()),
            "worst_cos": float(cos.min()),
            "worst_file": Path(paths[int(np.where(m)[0][cos.argmin()])]).name,
            "dir": preferred_dirname(code),
        }

    codes = [c for c in CODES if c in protos]
    P = np.stack([protos[c] for c in codes])
    sim = clip @ P.T                      # (N, C)
    own = np.array([codes.index(c) for c in labels_arr])
    own_sim = sim[np.arange(len(clip)), own]
    sim_masked = sim.copy()
    sim_masked[np.arange(len(clip)), own] = -9
    other_best = sim_masked.argmax(axis=1)
    other_sim = sim_masked[np.arange(len(clip)), other_best]

    print(f"\n{'风格':10s} {'目录':8s} {'张数':>4s} {'紧致度':>7s} {'最差':>6s}")
    for c in codes:
        s = stats[c]
        flag = "  ⚠ 类内不统一" if s["cohesion"] < LOW_COHESION else ""
        print(f"{c:10s} {s['dir']:8s} {s['n']:>4d} {s['cohesion']:>7.3f} {s['worst_cos']:>6.3f}{flag}")

    # 1) 离群图
    outliers = []
    for i in range(len(clip)):
        if own_sim[i] < OUTLIER_COS:
            outliers.append((labels_arr[i], Path(paths[i]).name, float(own_sim[i])))

    # 2) 跨类错投
    mis = []
    for i in range(len(clip)):
        if other_sim[i] > own_sim[i] + 0.02:
            mis.append((labels_arr[i], codes[other_best[i]], Path(paths[i]).name,
                        float(own_sim[i]), float(other_sim[i])))

    if mis:
        print(f"\n⚠ 疑似投错类 {len(mis)} 张（离别的类更近）：")
        for own_c, oth_c, name, a, b in mis:
            print(f"   {preferred_dirname(own_c)}/{name}  自己 {a:.3f} < {preferred_dirname(oth_c)} {b:.3f}")
    if outliers:
        print(f"\n离群图 {len(outliers)} 张（到本类原型 <{OUTLIER_COS}）：")
        for c, name, v in outliers:
            print(f"   {preferred_dirname(c)}/{name}  {v:.3f}")

    # 3) 类间可分性：任意两类原型之间最大相似度
    G = P @ P.T
    np.fill_diagonal(G, -9)
    a, b = np.unravel_index(G.argmax(), G.shape)
    print(f"\n最像的两类：{preferred_dirname(codes[a])} ↔ {preferred_dirname(codes[b])}  原型余弦 {G[a, b]:.3f}")
    if G[a, b] > 0.92:
        print("  ⚠ 这两类在这批锚图上几乎分不开，考虑合并或补更典型的图")

    OUT_DIR.mkdir(exist_ok=True)
    np.savez_compressed(OUT_DIR / "style.prototype.npz",
                        codes=np.array(codes),
                        clip=P.astype(np.float32),
                        color=np.stack([colors[c] for c in codes]).astype(np.float32))
    (OUT_DIR / "style.prototype.json").write_text(json.dumps({
        "kind": "prototype",
        "feature_layout": ["clip512_l2norm", "color24"],
        "clip_model": train.CLIP_MODEL,
        "classes": [{"code": c, **stats[c]} for c in codes],
        "misplaced": [{"true": o, "closer_to": t, "file": n, "own": round(x, 4), "other": round(y, 4)}
                      for o, t, n, x, y in mis],
        "outliers": [{"code": c, "file": n, "cos": round(v, 4)} for c, n, v in outliers],
        "closest_pair": {"a": codes[a], "b": codes[b], "cos": round(float(G[a, b]), 4)},
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n已写入 {OUT_DIR / 'style.prototype.npz'} 和 .json")
    ok = not mis and all(stats[c]["cohesion"] >= LOW_COHESION for c in codes)
    print("结论：" + ("锚图质量可以，进入推理接入" if ok else "先处理上面的错投/离群，再进推理"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
