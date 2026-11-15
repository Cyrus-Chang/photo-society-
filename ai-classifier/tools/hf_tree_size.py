"""看两个候选 parquet 数据集的大小与字段；小的话直接抽样看标签分布。"""
import io
import json
import sys
import urllib.request

from pipeline.console import ensure_utf8

UA = "Mozilla/5.0 (compatible; dsh)"
DS = [
    "Falah/unsplash_photography_prompts",
    "RayyanAhmed9477/pexels-advertisement-photography",
]


def api(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())


def main() -> int:
    ensure_utf8()
    for ds in DS:
        try:
            tree = api(f"https://hf-mirror.com/api/datasets/{ds}/tree/main/data")
        except Exception as exc:  # noqa: BLE001
            print(f"{ds}: FAIL {exc}")
            continue
        for f in tree:
            size_mb = (f.get("size") or 0) / 1024 / 1024
            print(f"{ds:46s} {f['path']:44s} {size_mb:8.1f} MB")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, r"E:\通用型摄影师接单平台\ai-classifier")
    raise SystemExit(main())
