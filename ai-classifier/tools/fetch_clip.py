"""拉取训练所需的视觉主干权重：openai/clip-vit-base-patch32（CLIP ViT-B/32）。

本机 huggingface.co 直连不可达，必须走 hf-mirror.com 镜像。
用法：
    .\.venv\Scripts\python.exe tools\fetch_clip.py
"""
import os
import sys
import time

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")

from huggingface_hub import snapshot_download  # noqa: E402

REPO = "openai/clip-vit-base-patch32"

# 只取推理/特征抽取需要的文件，跳过 flax/tf 权重（各 ~600MB，纯浪费）
ALLOW = [
    "*.json",
    "*.txt",
    "pytorch_model.bin",
    "merges.txt",
    "vocab.json",
    "preprocessor_config.json",
    "tokenizer.json",
]


def main() -> int:
    t0 = time.time()
    print(f"[fetch] repo={REPO} endpoint={os.environ['HF_ENDPOINT']}", flush=True)
    path = snapshot_download(
        repo_id=REPO,
        allow_patterns=ALLOW,
        resume_download=True,
        max_workers=2,
    )
    size = sum(
        os.path.getsize(os.path.join(root, f))
        for root, _dirs, files in os.walk(path)
        for f in files
    )
    print(f"[fetch] ok -> {path}", flush=True)
    print(f"[fetch] bytes={size} ({size / 1024 / 1024:.1f} MB) elapsed={time.time() - t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
