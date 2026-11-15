"""从 hf-mirror 拉一个 HF 数据集文件（可续传），并打印进度。"""
import os
import sys
import time

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from huggingface_hub import hf_hub_download  # noqa: E402

REPO = "RayyanAhmed9477/pexels-advertisement-photography"
FILE = "data/train-00000-of-00001.parquet"
DEST = r"E:\通用型摄影师接单平台\ai-classifier\external\datasets"


def main() -> int:
    t0 = time.time()
    path = hf_hub_download(
        repo_id=REPO,
        filename=FILE,
        repo_type="dataset",
        local_dir=DEST,
        local_dir_use_symlinks=False,
    )
    size = os.path.getsize(path) / 1024 / 1024
    print(f"OK  {path}  {size:.1f} MB  {time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
