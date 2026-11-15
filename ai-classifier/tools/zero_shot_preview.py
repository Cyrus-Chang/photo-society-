"""零样本预览：用字典里的 prompt_en 直接给一批图打分（不训练、不需要标注）。

训练前唯一能做的"视觉能力体检"：如果 13 个风格的 prompt 在你自己这批图上都分不开，
那再训线性头也是白搭——先改字典，再标数据。

用法：
    .\.venv\Scripts\python.exe tools\zero_shot_preview.py [图片目录] [--out 输出.csv]
默认扫 ../public/works，结果写 reports/zero_shot_preview.csv。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default=str(ROOT.parent / "public" / "works"))
    ap.add_argument("--out", default=str(ROOT / "reports" / "zero_shot_preview.csv"))
    args = ap.parse_args()

    from PIL import Image, ImageOps

    import pipeline.serve as serve

    src = Path(args.src)
    imgs = sorted(p for p in src.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    if not imgs:
        print(f"没有图片：{src}")
        return 2

    serve._state["clip_ok"] = serve._load_clip()
    serve._state["dict"] = json.loads((ROOT / "labels" / "dictionary.json").read_text(encoding="utf-8"))
    if not serve._state["clip_ok"]:
        print("CLIP 没加载起来，先跑 tools/fetch_clip.py")
        return 3

    rows = []
    for p in imgs:
        img = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
        vec = serve.build_inputs(img)
        zs = serve.classify_zero_shot(vec)
        tone = [t["code"] for t in serve.derive_tone(
            {n: float(v) for n, v in zip(serve.FEATURE_NAMES, vec[512:])})]
        subj = zs.get("subject", [])
        style = zs.get("style", [])
        rows.append({
            "file": p.name,
            "subject_top3": " | ".join(f"{d['code']}:{d['confidence']:.2f}" for d in subj),
            "style_top3": " | ".join(f"{d['code']}:{d['confidence']:.2f}" for d in style),
            "tone": ",".join(tone),
        })

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["file", "subject_top3", "style_top3", "tone"])
        w.writeheader()
        w.writerows(rows)

    print(f"\n{'file':44s} {'subject top1':28s} {'style top1':28s} tone")
    for r in rows:
        s1 = r["subject_top3"].split(" | ")[0]
        t1 = r["style_top3"].split(" | ")[0]
        print(f"{r['file'][:42]:44s} {s1:28s} {t1:28s} {r['tone']}")
    print(f"\n已写入 {out}（{len(rows)} 张；零样本结果只用于判断 prompt 质量，不是训练指标）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
