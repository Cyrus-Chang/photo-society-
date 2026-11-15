"""验证 serve.py 能加载新模型并对真实图片出结果（不走 HTTP，直接调内部函数）。"""
from __future__ import annotations

import glob
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from PIL import Image, ImageOps  # noqa: E402

import pipeline.serve as serve  # noqa: E402
from pipeline.console import ensure_utf8  # noqa: E402


def main() -> int:
    ensure_utf8()
    serve._state["clip_ok"] = serve._load_clip()
    serve._state["dict"] = json.loads((Path("labels") / "dictionary.json").read_text(encoding="utf-8"))
    serve._load_heads()
    try:
        serve._load_anchors()
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] 锚图模型没加载起来: {exc}")
    heads = serve._state["heads"]
    print("已加载的头：", {k: len(v["labels"]) for k, v in heads.items()} or "无")
    anchors = serve._state.get("anchors")
    print("风格锚图：", len(anchors["codes"]) if anchors else "未加载（走零样本）")

    imgs = sorted(glob.glob(r"..\public\works\*.jpg"))[:3]
    imgs += sorted(glob.glob(r"data\mx_01\*\*.jpg"))[:3]
    for p in imgs:
        img = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
        out = serve._run(img)
        subj = [(d["code"], d["confidence"]) for d in out.get("subject", [])[:3]]
        style = [(d["code"], d["confidence"]) for d in out.get("style", [])[:2]]
        print(f"{Path(p).name[:34]:36s} subject={subj}  style={style}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    raise SystemExit(main())
