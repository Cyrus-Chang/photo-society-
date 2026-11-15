"""最后一次确认：hf-mirror 的 dataset resolve 到底返回什么（只取 1 字节）。"""
import sys
import urllib.request

from pipeline.console import ensure_utf8

TARGETS = [
    ("dataset file", "https://hf-mirror.com/datasets/devoppro/Nature-Cinematic-Photography/resolve/main/data/nature_0000.jpg"),
    ("dataset file2", "https://hf-mirror.com/datasets/RayyanAhmed9477/pexels-advertisement-photography/resolve/main/data/train-00000-of-00001.parquet"),
    ("model file", "https://hf-mirror.com/openai/clip-vit-base-patch32/resolve/main/config.json"),
]


def main() -> int:
    ensure_utf8()
    for label, url in TARGETS:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Range": "bytes=0-0"})
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                print(f"{label:14s} {r.status}  len={r.headers.get('Content-Length')}  {url[:96]}")
        except Exception as exc:  # noqa: BLE001
            print(f"{label:14s} FAIL {type(exc).__name__}: {str(exc)[:50]}  {url[:80]}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, r"E:\通用型摄影师接单平台\ai-classifier")
    raise SystemExit(main())
