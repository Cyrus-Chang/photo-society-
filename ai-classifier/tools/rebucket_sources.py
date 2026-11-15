"""把三个公开来源各切成 4 个批次，凑够 12 个「摄影师/来源」分组。

为什么必须这么干：grouped_split 是按顶层目录整组划分的。现在每个来源只装一个题材类，
3 组划分后验证集/测试集里必然整类缺席，train.py 会把它们全部搬回训练集，最后 train=全部、metrics=None。
切成 12 组后每组 40~60 张，三类的样本在每个划分里都能出现，指标才有意义。

顺带把 cache/feat.npz 的 key 改写成新路径（文件用 os.rename 移动，size/mtime 不变，
所以不必重新抽 8 分钟的特征）。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

from pipeline.console import ensure_utf8

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "feat.npz"
BUCKETS = 4


def restructure() -> None:
    for src in sorted(p for p in DATA.iterdir() if p.is_dir() and p.name.startswith("ds_")):
        if "_b" in src.name:          # 已经切过
            continue
        for combo in src.iterdir():
            if not combo.is_dir():
                continue
            files = sorted(combo.glob("*.jpg"))
            for i, f in enumerate(files):
                bucket = src.with_name(f"{src.name}_b{i % BUCKETS + 1}") / combo.name
                bucket.mkdir(parents=True, exist_ok=True)
                os.rename(f, bucket / f.name)
            combo.rmdir()
        src.rmdir()


def rewrite_cache() -> None:
    if not CACHE.exists():
        print("没有 cache，跳过 key 重写（后面 extract 会重建）")
        return
    old = np.load(CACHE, allow_pickle=True)
    by_sig = {}
    for p in DATA.rglob("*.jpg"):
        st = p.stat()
        by_sig[(p.name, os.path.getsize(p), os.stat(p).st_mtime_ns)] = str(p)

    new_keys = []
    miss = 0
    for key in old["key"]:
        path, size, mtime = key.rsplit("|", 2)
        name = Path(path).name
        hit = by_sig.get((name, int(size), int(mtime)))
        if hit is None:
            miss += 1
            new_keys.append(key)
        else:
            new_keys.append(f"{hit}|{size}|{mtime}")
    np.savez_compressed(CACHE, key=np.array(new_keys), clip=old["clip"], color=old["color"])
    print(f"cache key 重写完成：{len(new_keys)} 条，未命中 {miss} 条")


def main() -> int:
    ensure_utf8()
    restructure()
    rewrite_cache()
    dirs = sorted(p.name for p in DATA.iterdir() if p.is_dir() and p.name.startswith("ds_"))
    print(f"现在的来源分组（{len(dirs)} 个）：{', '.join(dirs)}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
