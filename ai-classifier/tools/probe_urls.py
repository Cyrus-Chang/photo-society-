"""探测候选数据集直链（大小/可用性），不整包下载。"""
import sys
import urllib.request

from pipeline.console import ensure_utf8

URLS = [
    "http://data.vision.ee.ethz.ch/ihnatova/camera_scene_detection_train.zip",
    "https://data.vision.ee.ethz.ch/ihnatova/camera_scene_detection_train.zip",
    "https://data.vision.ee.ethz.ch/ihnatova/camera_scene_detection_validation.zip",
    "https://hf-mirror.com/api/models/OFA-Sys/chinese-clip-vit-base-patch16",
]


def probe(url: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            head = r.read(512)
            size = r.headers.get("Content-Length")
            kind = "ZIP" if head[:2] == b"PK" else repr(head[:30])
            mb = f"{int(size) / 1024 / 1024:.1f} MB" if size and size.isdigit() else "?"
            print(f"{r.status}  {mb:>10s}  {kind[:40]:42s} {url}")
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {type(exc).__name__}: {str(exc)[:60]:62s} {url}")


def main() -> int:
    ensure_utf8()
    for u in URLS:
        probe(u)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, r"E:\通用型摄影师接单平台\ai-classifier")
    raise SystemExit(main())
