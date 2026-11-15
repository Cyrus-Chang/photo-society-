"""统计 parquet 里 text（抓取用的搜索词）的分布——如果 query 有分类，它就能直接当题材标签。"""
import sys
from collections import Counter

import pyarrow.parquet as pq

from pipeline.console import ensure_utf8

PATH = r"E:\通用型摄影师接单平台\ai-classifier\external\datasets\pexels.parquet"


def main() -> int:
    ensure_utf8()
    pf = pq.ParquetFile(PATH)
    cnt: Counter[str] = Counter()
    dims: Counter[str] = Counter()
    n = 0
    for i in range(pf.metadata.num_row_groups):
        t = pf.read_row_group(i, columns=["text"]).column("text").to_pylist()
        cnt.update(t)
        n += len(t)
    print(f"总行数 {n}，text 去重后 {len(cnt)} 种")
    for k, v in cnt.most_common(40):
        print(f"   {v:6d}  {k}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, r"E:\通用型摄影师接单平台\ai-classifier")
    raise SystemExit(main())
