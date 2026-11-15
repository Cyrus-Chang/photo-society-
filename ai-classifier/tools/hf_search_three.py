"""定向搜三类（建筑/风光/美食）的公开图片数据集，只看许可干净的。"""
import json
import sys
import urllib.parse
import urllib.request

from pipeline.console import ensure_utf8

BASE = "https://hf-mirror.com/api/datasets"
OK_LIC = {"apache-2.0", "mit", "cc-by-4.0", "cc-by-sa-4.0", "cc0-1.0", "bsd-3-clause", "openrail"}


def get(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def show(term: str) -> None:
    url = f"{BASE}?search={urllib.parse.quote(term)}&limit=20&sort=downloads&direction=-1"
    try:
        data = get(url)
    except Exception as exc:  # noqa: BLE001
        print(f"== {term}: FAIL {exc}")
        return
    print(f"== {term}")
    for d in data:
        tags = d.get("tags") or []
        lic = next((x.split(":", 1)[1] for x in tags if x.startswith("license:")), "?")
        size = next((x.split(":", 1)[1] for x in tags if x.startswith("size_categories:")), "")
        if lic not in OK_LIC:
            continue
        print(f"   {d.get('downloads', 0):>7} dl  {d['id'][:56]:58s} lic={lic:12s} {size}")
    print()


def main() -> int:
    ensure_utf8()
    for t in ["landscape photo", "landscape photography", "architecture images", "building photos",
              "food photography", "food images", "portrait photography", "street photography"]:
        show(t)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, r"E:\通用型摄影师接单平台\ai-classifier")
    raise SystemExit(main())
