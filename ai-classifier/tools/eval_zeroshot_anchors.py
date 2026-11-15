"""同一批 136 张锚图上比：零样本 vs 原型匹配。

锚图是"典型样本"，零样本在这种图上本来就占便宜——所以这个对比是给原型分类器设的**及格线**：
如果原型都打不过零样本，那这套东西就不该上线，直接用零样本 + 调 prompt 更省事。
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
CACHE = ROOT / "cache" / "anchors_feat.npz"


def main() -> int:
    ensure_utf8()
    sys.path.insert(0, str(ROOT))
    from pipeline.cliputil import text_features
    from pipeline.train import CLIP_MODEL

    z = np.load(CACHE, allow_pickle=True)
    clip, labels = z["clip"], np.array([Path(p).parent.name for p in z["paths"]])

    # 目录名 → code
    dir2code = {}
    found = scan(ANCHORS)
    for code, files in found.items():
        for f in files:
            dir2code[f.parent.name] = code
    y = np.array([dir2code[d] for d in labels])
    codes = [c for c in CODES if (y == c).any()]

    dicts = json.loads((ROOT / "labels" / "dictionary.json").read_text(encoding="utf-8"))
    prompt = {g["code"]: g["prompt_en"] for g in dicts["STYLE"]
              if g.get("enabled", True) and g.get("prompt_en")}
    codes = [c for c in codes if c in prompt]

    import torch
    from transformers import CLIPModel, CLIPProcessor

    model = CLIPModel.from_pretrained(CLIP_MODEL).eval()
    proc = CLIPProcessor.from_pretrained(CLIP_MODEL)
    with torch.no_grad():
        tok = proc(text=[prompt[c] for c in codes], return_tensors="pt", padding=True)
        tf = text_features(model, tok)
        tf = torch.nn.functional.normalize(tf, dim=-1).cpu().numpy()

    sim = clip @ tf.T
    pred = np.array([codes[i] for i in sim.argmax(axis=1)])
    acc = float((pred == y).mean())
    print(f"零样本准确率 {acc:.3f}  （{len(y)} 张 / {len(codes)} 类，随机基线 {1/len(codes):.3f}）")
    for c in codes:
        m = y == c
        rec = float((pred[m] == c).mean())
        flag = "  ⚠" if rec < 0.7 else ""
        print(f"   {preferred_dirname(c):6s} n={int(m.sum()):2d} 召回 {rec:.2f}{flag}")

    # 混淆最多的一对
    conf: dict[tuple[str, str], int] = {}
    for t, p in zip(y, pred):
        if t != p:
            conf[(t, p)] = conf.get((t, p), 0) + 1
    top = sorted(conf.items(), key=lambda kv: -kv[1])[:5]
    if top:
        print("\n最常搞混（真 → 判成）：")
        for (t, p), n in top:
            print(f"   {preferred_dirname(t)} → {preferred_dirname(p)}  {n} 次")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
