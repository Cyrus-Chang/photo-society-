"""用公开数据搭出「非人像 3 类」训练集（风光 / 建筑 / 静物美食）。

来源与许可：
  · 风光：HF `devoppro/Nature-Cinematic-Photography`（8050 张 nature_*.jpg，许可未声明 → 只做公开数据基线）
  · 美食 / 建筑：HF `RayyanAhmed9477/pexels-advertisement-photography`（Pexels License，可商用），
    按 parquet 里的 `text`（抓取搜索词）分桶。

输出到 data/，每个来源一个顶层目录（满足 prepare.py 的「≥3 个摄影师/来源」分组划分要求）：
  data/ds_nature/LANDSCAPE__INS/
  data/ds_pexels_food/STILL_FOOD__INS/
  data/ds_pexels_property/ARCHITECTURE__INS/

风格统一填 INS 占位：本批只训「题材头」，风格头等真实客片标注后再训（train.py --tasks subject）。
"""
from __future__ import annotations

import io
import os
import sys
import time
import urllib.request
from pathlib import Path

from PIL import Image

from pipeline.console import ensure_utf8

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PARQUET = ROOT / "external" / "datasets" / "pexels.parquet"
NATURE_REPO = "devoppro/Nature-Cinematic-Photography"
MIRROR = "https://hf-mirror.com"

FOOD_QUERIES = {"food photography commercial", "chocolate dessert food photography",
                "coffee cup latte art", "food advertisement menu"}
ARCH_QUERIES = {"real estate advertisement property", "furniture modern interior design",
                "retail store advertisement display"}

MAX_SIDE = 640          # 原图多为 1024~2000px，统一到 640 长边；CLIP 只吃 224
JPEG_Q = 88


def save_scaled(raw: bytes, dst: Path) -> bool:
    try:
        img = Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception:  # noqa: BLE001
        return False
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    dst.parent.mkdir(parents=True, exist_ok=True)
    img.save(dst, "JPEG", quality=JPEG_Q, optimize=True)
    return True


def _one(url: str, dst: Path) -> bool:
    if dst.exists():
        return True
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
                                    timeout=45) as r:
            raw = r.read()
    except Exception as exc:  # noqa: BLE001
        print(f"  [warn] {dst.name}: {str(exc)[:50]}")
        return False
    return save_scaled(raw, dst)


def build_nature(n: int) -> int:
    """从 HF 数据集按文件名并发下载风光图。"""
    import json
    from concurrent.futures import ThreadPoolExecutor

    req = urllib.request.Request(f"{MIRROR}/api/datasets/{NATURE_REPO}", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=40) as r:
        info = json.loads(r.read())
    files = [s["rfilename"] for s in (info.get("siblings") or []) if s["rfilename"].endswith(".jpg")]
    files.sort()
    out = DATA / "ds_nature" / "LANDSCAPE__INS"
    out.mkdir(parents=True, exist_ok=True)
    todo = [(f"{MIRROR}/datasets/{NATURE_REPO}/resolve/main/{f}", out / Path(f).name)
            for f in files[: n * 2]]
    t0 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=12) as pool:
        for ok in pool.map(lambda a: _one(*a), todo):
            done += 1
            if ok:
                pass
            if done % 50 == 0:
                have = len(list(out.glob("*.jpg")))
                print(f"  nature {have}/{n}  ({done} 请求, {time.time()-t0:.0f}s)", file=sys.stderr)
            if len(list(out.glob("*.jpg"))) >= n:
                break
    return len(list(out.glob("*.jpg")))



def build_pexels(n_food: int, n_arch: int) -> tuple[int, int]:
    import pyarrow.parquet as pq

    pf = pq.ParquetFile(PARQUET)
    out_food = DATA / "ds_pexels_food" / "STILL_FOOD__INS"
    out_arch = DATA / "ds_pexels_property" / "ARCHITECTURE__INS"
    food = arch = 0
    seen = 0
    for gi in range(pf.metadata.num_row_groups):
        if food >= n_food and arch >= n_arch:
            break
        tbl = pf.read_row_group(gi, columns=["image", "text"])
        imgs = tbl.column("image").to_pylist()
        texts = tbl.column("text").to_pylist()
        for raw, q in zip(imgs, texts):
            seen += 1
            if q in FOOD_QUERIES and food < n_food:
                if save_scaled(raw, out_food / f"food_{food:04d}.jpg"):
                    food += 1
            elif q in ARCH_QUERIES and arch < n_arch:
                if save_scaled(raw, out_arch / f"arch_{arch:04d}.jpg"):
                    arch += 1
        print(f"  row_group {gi+1}/{pf.metadata.num_row_groups} 读 {seen} 行 → food={food} arch={arch}",
              file=sys.stderr)
    return food, arch


def main() -> int:
    ensure_utf8()
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 220
    print(f"目标：风光 {n} / 美食 {n} / 建筑 {n}")
    if not PARQUET.exists():
        print(f"缺少 {PARQUET}，先跑 tools/hf_stream_download.py")
        return 2
    t0 = time.time()
    a = build_nature(n)
    b, c = build_pexels(n, n)
    print(f"\n完成：风光 {a} / 美食 {b} / 建筑 {c}，用时 {time.time()-t0:.0f}s")
    print(f"目录：{DATA}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
