"""看某个 HF 数据集里到底有什么（文件名分布、目录结构、能否按类别取）。"""
import json
import sys
import urllib.request
from collections import Counter

from pipeline.console import ensure_utf8

IDS = ["devoppro/Nature-Cinematic-Photography", "Falah/unsplash_photography_prompts"]


def get(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())


def main() -> int:
    ensure_utf8()
    for ds in IDS:
        info = get(f"https://hf-mirror.com/api/datasets/{ds}")
        files = [s["rfilename"] for s in (info.get("siblings") or [])]
        dirs = Counter(f.rsplit("/", 1)[0] if "/" in f else "." for f in files)
        print(f"== {ds}  共 {len(files)} 个文件")
        for d, n in dirs.most_common(12):
            print(f"   {n:5d}  {d}")
        print("   样例:", files[:5])
        print()
    return 0


if __name__ == "__main__":
    sys.path.insert(0, r"E:\通用型摄影师接单平台\ai-classifier")
    raise SystemExit(main())
