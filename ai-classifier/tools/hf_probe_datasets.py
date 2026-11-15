"""逐个探测候选 HF 数据集（不用 search 接口，避免触发限流）。"""
import json
import sys
import time
import urllib.request

from pipeline.console import ensure_utf8

IDS = [
    "keremberke/intel-image-classification",
    "dima806/food_image_classification",
    "Falah/unsplash_photography_prompts",
    "devoppro/Nature-Cinematic-Photography",
    "RayyanAhmed9477/pexels-advertisement-photography",
    "Shuai1995/TAD66K_for_Image_Aesthetics_Assessment",
]
UA = "Mozilla/5.0 (compatible; dsh)"


def get(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main() -> int:
    ensure_utf8()
    for ds in IDS:
        try:
            info = get(f"https://hf-mirror.com/api/datasets/{ds}")
        except Exception as exc:  # noqa: BLE001
            print(f"{ds:56s} FAIL {type(exc).__name__}: {str(exc)[:40]}")
            time.sleep(3)
            continue
        tags = info.get("tags") or []
        lic = next((x.split(":", 1)[1] for x in tags if x.startswith("license:")), "?")
        size = next((x.split(":", 1)[1] for x in tags if x.startswith("size_categories:")), "")
        sibs = info.get("siblings") or []
        parq = [s["rfilename"] for s in sibs if s["rfilename"].endswith(".parquet")]
        img = [s["rfilename"] for s in sibs if s["rfilename"].lower().endswith((".jpg", ".png", ".jpeg"))]
        print(f"{ds:56s} lic={lic:12s} {size:14s} parquet={len(parq):3d} img_files={len(img):4d}")
        if parq:
            print(f"      e.g. {parq[0]}  ({len(parq)} shards)")
        time.sleep(2)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, r"E:\通用型摄影师接单平台\ai-classifier")
    raise SystemExit(main())
