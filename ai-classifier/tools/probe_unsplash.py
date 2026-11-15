"""探测 Unsplash Lite（官方 25k 数据集）与几个 HF 镜像是否可下载。"""
import json
import sys
import urllib.request

from pipeline.console import ensure_utf8

TARGETS = [
    ("unsplash lite", "https://unsplash.com/data/lite/latest"),
    ("hf unsplash-25k", "https://hf-mirror.com/api/datasets/jamescalam/unsplash-25k-photos"),
    ("hf unsplash-25k2", "https://hf-mirror.com/api/datasets/Data-Science-in-Practice/unsplash-lite-dataset"),
    ("hf koivuneva", "https://hf-mirror.com/api/datasets/koivuneva/unsplash"),
]
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def probe(label: str, url: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            size = r.headers.get("Content-Length")
            mb = f"{int(size)/1024/1024:.0f} MB" if size and size.isdigit() else "?"
            head = r.read(200)
            is_zip = head[:2] == b"PK"
            print(f"{label:16s} {r.status} {mb:>10s} zip={is_zip}  {url}")
            if not is_zip and head[:1] == b"{":
                d = json.loads(head if len(head) < 200 else b"{}")
                print(f"                 keys={list(d)[:8]}")
    except Exception as exc:  # noqa: BLE001
        print(f"{label:16s} FAIL {type(exc).__name__}: {str(exc)[:60]}  {url}")


def main() -> int:
    ensure_utf8()
    for label, url in TARGETS:
        probe(label, url)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, r"E:\通用型摄影师接单平台\ai-classifier")
    raise SystemExit(main())
