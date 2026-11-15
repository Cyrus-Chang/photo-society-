"""检查 13 类风格锚图放得对不对：张数、分辨率、重复、跨类错投。

目录名可以用中文（日系/韩系/ins风…），也可以用英文 code，脚本都认。

用法：
    .\\.venv\\Scripts\\python.exe tools\\check_anchors.py
    .\\.venv\\Scripts\\python.exe tools\\check_anchors.py --dir data\\incoming\\anchors
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image

from pipeline.anchors import CODES, preferred_dirname, scan, style_code
from pipeline.console import ensure_utf8

ROOT = Path(__file__).resolve().parents[1]
MIN_SIDE = 1000
MIN_PER_CLASS = 3


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def main() -> int:
    ensure_utf8()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(ROOT / "data" / "incoming" / "anchors"))
    args = ap.parse_args()
    base = Path(args.dir)

    if not base.exists():
        print(f"目录不存在：{base}")
        return 2

    found = scan(base)
    hashes: dict[str, list[str]] = defaultdict(list)
    problems: list[str] = []
    rows = []
    total = 0

    for code in CODES:
        files = found.get(code, [])
        total += len(files)
        smallest = None
        for p in files:
            try:
                with Image.open(p) as im:
                    w, h = im.size
            except Exception as exc:  # noqa: BLE001
                problems.append(f"{p.parent.name}/{p.name}: 打不开 ({type(exc).__name__})")
                continue
            long_side = max(w, h)
            smallest = long_side if smallest is None else min(smallest, long_side)
            if long_side < MIN_SIDE:
                problems.append(f"{p.parent.name}/{p.name}: 长边只有 {long_side}px（要求 ≥{MIN_SIDE}）")
            hashes[sha(p)].append(f"{p.parent.name}/{p.name}")
        flag = "" if len(files) >= MIN_PER_CLASS else "  ⚠ 不足 3 张"
        rows.append((code, preferred_dirname(code), len(files), smallest, flag))

    print(f"{'风格':10s} {'目录':8s} {'张数':>4s} {'最小长边':>8s}")
    for code, zh, n, smallest, flag in rows:
        print(f"{code:10s} {zh:8s} {n:>4d} {str(smallest) if smallest else '-':>8s}{flag}")

    dup = {k: v for k, v in hashes.items() if len(v) > 1}
    cross = {k: v for k, v in dup.items() if len({x.split('/')[0] for x in v}) > 1}

    ok_classes = sum(1 for _, _, n, _, _ in rows if n >= MIN_PER_CLASS)
    print(f"\n合计 {total} 张，{ok_classes}/13 类达标")

    # 认不出名字的目录单独提示（多半是打错字）
    for d in base.iterdir():
        if d.is_dir() and style_code(d.name) is None:
            print(f"注：目录「{d.name}」没被认出来（名字不对），图放进去也不会被统计")

    if dup:
        print("\n重复图（内容相同，只该出现一次）：")
        for k, v in dup.items():
            print(f"  {k}  {v}")
    if cross:
        print("\n⚠ 上面带跨类重复的，说明同一张图投了两类，必须删掉一个")
    if problems:
        print(f"\n问题 {len(problems)} 条：")
        for p in problems[:40]:
            print(f"  - {p}")

    ok = (not problems) and (not cross) and total >= 13 * MIN_PER_CLASS
    print("\n结论：" + ("可以进入下一步（生成原型向量）" if ok else "先把上面的问题处理掉"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    raise SystemExit(main())
