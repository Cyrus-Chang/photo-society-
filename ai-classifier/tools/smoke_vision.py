"""冒烟测试：验证 CLIP 视觉主干 + 色彩特征在真实图片上跑通（CPU）。

用法：
    .\.venv\Scripts\python.exe tools\smoke_vision.py [图片目录]
不传目录时用 public/works 里的样片。
"""
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "public" / "works"
    imgs = [str(p) for p in sorted(src.rglob("*")) if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}][:6]
    if not imgs:
        print(f"[smoke] no images under {src}")
        return 2

    sys.path.insert(0, str(ROOT))
    from pipeline import colorfeat, train  # noqa: E402

    t0 = time.time()
    clip = train.extract_clip(imgs)
    print(f"[smoke] clip {clip.shape} dtype={clip.dtype} 均值={clip.mean():.4f} "
          f"（{time.time() - t0:.1f}s，{(time.time() - t0) / len(imgs):.2f}s/张）")

    t1 = time.time()
    color = train.extract_color(imgs)
    print(f"[smoke] color {color.shape} dtype={color.dtype} （{time.time() - t1:.1f}s）")

    # 归一化后自相似度应接近 1，不同图之间明显小于 1
    import numpy as np
    sim = clip @ clip.T
    off = sim[~np.eye(len(sim), dtype=bool)]
    print(f"[smoke] clip 自相似 min={off.min():.3f} max={off.max():.3f}（同图=1.0）")

    c = colorfeat.color_features(imgs[0])
    print(f"[smoke] colorfeat 单图 {c.shape}")
    print("[smoke] PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
