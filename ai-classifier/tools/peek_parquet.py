"""看一眼 parquet 的字段与样本（不整表加载）。"""
import sys

import pyarrow.parquet as pq

from pipeline.console import ensure_utf8

PATH = r"E:\通用型摄影师接单平台\ai-classifier\external\datasets\pexels.parquet"


def main() -> int:
    ensure_utf8()
    pf = pq.ParquetFile(PATH)
    print(f"rows={pf.metadata.num_rows}  row_groups={pf.metadata.num_row_groups}")
    print("schema:")
    for f in pf.schema_arrow:
        print(f"   {f.name:24s} {f.type}")

    cols = [n for n in pf.schema_arrow.names]
    small = [c for c in cols if "image" not in c.lower() and "photo" not in c.lower() and "bytes" not in c.lower()]
    table = pf.read_row_group(0, columns=small)
    print(f"\n非图片列 {small}，前 3 行：")
    for row in table.slice(0, 3).to_pylist():
        for k, v in row.items():
            s = str(v)
            print(f"   {k:20s} {s[:160]}")
        print("   ---")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, r"E:\通用型摄影师接单平台\ai-classifier")
    raise SystemExit(main())
