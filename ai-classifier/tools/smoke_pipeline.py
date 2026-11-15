"""流水线端到端冒烟：prepare -> extract -> fit -> ONNX 推理。

目的只有一个：**证明代码能跑通**（尤其是 transformers 5.x 的 API 变化、
ONNX 导出的输入维度、多标签头的输出形状）。
它用 public/works 里的 26 张样片随便贴了标签，**产出的指标没有任何意义**，
全部写进 .smoke/ 目录，跑完即删，绝不进 models/。

用法：
    .\.venv\Scripts\python.exe tools\smoke_pipeline.py
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / ".smoke"
SRC = ROOT.parent / "public" / "works"

# 4 个组合够触发多标签 + 分组划分，又不至于每类只剩 1 张
COMBOS = [
    ("STUDIO", "INS"),
    ("OUTDOOR", "JAPANESE"),
    ("ARCHITECTURE", "MONO"),
    ("LANDSCAPE", "CINEMATIC"),
]


def build_data() -> int:
    if SMOKE.exists():
        shutil.rmtree(SMOKE)
    data = SMOKE / "data"
    imgs = sorted(p for p in SRC.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"})
    for i, img in enumerate(imgs):
        subject, style = COMBOS[i % len(COMBOS)]
        person = f"p00{i % 5 + 1}"
        dst = data / person / f"{subject}__{style}"
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(img, dst / f"{i:03d}{img.suffix.lower()}")
    return len(imgs)


def run(cmd: list[str]) -> None:
    print(f"\n$ {' '.join(cmd[1:])}", flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    n = build_data()
    print(f"[smoke] {n} 张样片已铺进 {SMOKE / 'data'}（标签是假的，只验通路）")
    py = sys.executable
    run([py, "-m", "pipeline.prepare", "--data", str(SMOKE / "data"), "--out", str(SMOKE / "labels.csv")])
    run([py, "-m", "pipeline.train", "extract", "--csv", str(SMOKE / "labels.csv"),
         "--cache", str(SMOKE / "cache" / "feat.npz")])
    run([py, "-m", "pipeline.train", "fit", "--csv", str(SMOKE / "labels.csv"),
         "--cache", str(SMOKE / "cache" / "feat.npz"), "--out", str(SMOKE / "models")])

    # 导出物自检：维度、标签数、能不能被 onnxruntime 直接跑
    import numpy as np
    import onnxruntime as ort

    cache = np.load(SMOKE / "cache" / "feat.npz", allow_pickle=True)
    vec = np.concatenate([cache["clip"][0], cache["color"][0]]).astype(np.float32)[None, :]
    for task in ("subject", "style"):
        onnx_path = SMOKE / "models" / f"{task}.onnx"
        meta = json.loads((SMOKE / "models" / f"{task}.labels.json").read_text(encoding="utf-8"))
        sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        out = sess.run(None, {sess.get_inputs()[0].name: vec})[0]
        print(f"[smoke] {task}: in={sess.get_inputs()[0].shape} out={out.shape} "
              f"classes={len(meta['classes'])} multi={meta['multi']} 首行={np.round(out[0], 3)[:4]}")
        assert out.shape == (1, len(meta["classes"])), (task, out.shape)
    print("\n[smoke] PASS —— prepare/extract/fit/ONNX 全链路可跑")
    return 0


if __name__ == "__main__":
    sys.exit(main())
