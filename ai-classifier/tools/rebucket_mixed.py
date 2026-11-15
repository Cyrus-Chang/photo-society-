"""把图片重新分成 8 个「混合批次」，每批都含 3 个题材类。

上一版按来源切 → 每批只有一类 → 验证集/测试集整类缺席，macro-F1 毫无意义（0.33）。
正确做法：让每个分组横跨所有类别（真实业务里一个摄影师本来就会拍多种题材）。
按 组号 = 该类别内序号 % N_GROUPS 分配，三个类别等量落进每一组。
"""
from __future__ import annotations

import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from pipeline.console import ensure_utf8

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CACHE = ROOT / "cache" / "feat.npz"
N_GROUPS = 8


def collect() -> dict[str, list[Path]]:
    by_combo: dict[str, list[Path]] = defaultdict(list)
    for p in DATA.rglob("*.jpg"):
        if "incoming" in p.parts:
            continue
        by_combo[p.parent.name].append(p)
    for v in by_combo.values():
        v.sort()
    return by_combo


def regroup(by_combo: dict[str, list[Path]]) -> None:
    for combo, files in by_combo.items():
        for i, f in enumerate(files):
            g = f"mx_{i % N_GROUPS + 1:02d}"
            dst = DATA / g / combo
            dst.mkdir(parents=True, exist_ok=True)
            os.rename(f, dst / f.name)
    # 清掉空目录
    for d in sorted(DATA.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()


def rewrite_cache() -> None:
    if not CACHE.exists():
        return
    old = np.load(CACHE, allow_pickle=True)
    by_sig = {}
    for p in DATA.rglob("*.jpg"):
        st = p.stat()
        by_sig[(p.name, os.path.getsize(p), st.st_mtime_ns)] = str(p)
    new_keys, miss = [], 0
    for key in old["key"]:
        path, size, mtime = key.rsplit("|", 2)
        hit = by_sig.get((Path(path).name, int(size), int(mtime)))
        if hit is None:
            miss += 1
            new_keys.append(key)
        else:
            new_keys.append(f"{hit}|{size}|{mtime}")
    np.savez_compressed(CACHE, key=np.array(new_keys), clip=old["clip"], color=old["color"])
    print(f"cache key 重写：{len(new_keys)} 条，未命中 {miss}")


def main() -> int:
    ensure_utf8()
    by_combo = collect()
    for combo, files in sorted(by_combo.items()):
        print(f"  {combo:22s} {len(files)}")
    regroup(by_combo)
    rewrite_cache()
    groups = sorted(p.name for p in DATA.iterdir() if p.is_dir() and p.name.startswith("mx_"))
    print(f"混合分组 {len(groups)} 个：{', '.join(groups)}")
    sample = sorted((DATA / groups[0]).iterdir())
    counts = []
    for p in sample:
        counts.append("%s(%d)" % (p.name, len(list(p.glob("*.jpg")))))
    print("  抽查 %s：%s" % (groups[0], " ".join(counts)))
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
