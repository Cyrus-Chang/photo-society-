"""同一划分下比「零样本」和「训练出来的线性头」——判断训练到底带来了多少增益。

只有 3 个类时很容易出现 0.98~1.0 的漂亮数字，因为风光/美食/建筑类间差异极大，
零样本本来也能分开。不做这个对照，就会把「任务简单」误读成「模型好」。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from pipeline import train  # noqa: E402
from pipeline.console import ensure_utf8  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ensure_utf8()
    df = pd.read_csv(ROOT / "labels.csv", dtype=str, encoding="utf-8-sig").fillna("")
    cache = np.load(ROOT / "cache" / "feat.npz", allow_pickle=True)
    key_map = {k: i for i, k in enumerate(cache["key"])}
    idx = [key_map[f"{p}|{os.path.getsize(p)}|{os.stat(p).st_mtime_ns}"] for p in df["path"]]
    clip = cache["clip"][idx]

    dicts = json.loads((ROOT / "labels" / "dictionary.json").read_text(encoding="utf-8"))
    classes = sorted({c for row in df["subject"] for c in row.split(",")})
    prompts = {}
    for g in dicts["SUBJECT"]:
        if g["code"] in classes and g.get("prompt_en"):
            prompts[g["code"]] = g["prompt_en"]
    order = [c for c in classes if c in prompts]
    print("参与对比的类：", order)

    import torch
    from transformers import CLIPModel, CLIPProcessor

    model = CLIPModel.from_pretrained(train.CLIP_MODEL).eval()
    proc = CLIPProcessor.from_pretrained(train.CLIP_MODEL)
    with torch.no_grad():
        tok = proc(text=[prompts[c] for c in order], return_tensors="pt", padding=True)
        from pipeline.cliputil import text_features
        tf = text_features(model, tok)
        tf = torch.nn.functional.normalize(tf, dim=-1).cpu().numpy()

    cos = clip @ tf.T                    # (N, C)
    pred_zs = [order[i] for i in cos.argmax(axis=1)]

    split = train.grouped_split(df, "subject", seed=42)
    truth = [row.split(",")[0] for row in df["subject"]]
    head = json.loads((ROOT / "models" / "subject.metrics.json").read_text(encoding="utf-8"))

    for name, mask in (("val", (split == "VAL").to_numpy()), ("test", (split == "TEST").to_numpy())):
        if not mask.any():
            continue
        y = np.array(truth)[mask]
        pz = np.array(pred_zs)[mask]
        acc_zs = float((y == pz).mean())
        f1s = []
        for c in order:
            tp = int(((pz == c) & (y == c)).sum())
            fp = int(((pz == c) & (y != c)).sum())
            fn = int(((pz != c) & (y == c)).sum())
            prec = tp / (tp + fp) if tp + fp else 0.0
            rec = tp / (tp + fn) if tp + fn else 0.0
            f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
        print(f"{name:5s} n={mask.sum():3d}  零样本 acc={acc_zs:.4f} macroF1={np.mean(f1s):.4f}"
              f"   |   训练后 acc={head[name]['accuracy']:.4f} macroF1={head[name]['macro_f1']:.4f}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
