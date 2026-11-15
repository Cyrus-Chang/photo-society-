"""在 hf-mirror 上搜数据集（huggingface.co 直连不可达，镜像的 /api 可用）。"""
import json
import sys
import urllib.parse
import urllib.request

from pipeline.console import ensure_utf8

BASE = "https://hf-mirror.com/api/datasets"
UA = "Mozilla/5.0 (compatible; dsh)"


def get(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main() -> int:
    ensure_utf8()
    terms = ["photo style", "photography", "image aesthetics", "scene classification",
             "photo classification", "camera scene", "image style"]
    for t in terms:
        url = f"{BASE}?search={urllib.parse.quote(t)}&limit=8&sort=downloads&direction=-1"
        try:
            data = get(url)
        except Exception as exc:  # noqa: BLE001
            print(f"== {t}: FAIL {exc}")
            continue
        print(f"== {t}  ({len(data)} hits)")
        for d in data[:8]:
            tags = d.get("tags") or []
            lic = next((x.split(":", 1)[1] for x in tags if x.startswith("license:")), "?")
            size = next((x.split(":", 1)[1] for x in tags if x.startswith("size_categories:")), "")
            print(f"   {d.get('downloads', 0):>7} dl  {d['id'][:52]:54s} lic={lic:12s} {size}")
        print()
    return 0


if __name__ == "__main__":
    sys.path.insert(0, r"E:\通用型摄影师接单平台\ai-classifier")
    raise SystemExit(main())
