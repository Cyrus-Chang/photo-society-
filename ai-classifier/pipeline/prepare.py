"""把「目录约定」转成 labels.csv，并做标注完整性检查。

为什么要这个脚本：手工维护 csv 时 90% 的时间花在"贴路径"上，且极易拼错类别码。
按目录归类，一次转换，出错会当场报出来。

目录约定（两级：摄影师 → 类别目录）：

    data/
      p001/                          ← 摄影师 id（分组划分用，必填目录层）
        PORTRAIT__BLUE_TONE/         ← 题材__风格
          IMG_0001.jpg
        PORTRAIT+CONVENTION__INS/    ← 多题材用 + 连接
          IMG_0002.jpg
      ds_unsplash/                   ← 公开数据集：photographer_id 写成 ds_<来源>
        ARCHITECTURE__DARK_MOOD/
          u_001.jpg

规则：
    - 叶子目录名 = "<题材>[+题材...]__<风格>"，两个下划线是分隔符。
    - 题材、风格必须是 labels/dictionary.json 里已有的 code，否则报错。
    - 图片扩展名：jpg/jpeg/png/webp（大小写不限）。
    - 每个叶子目录建议 ≥20 张；<5 张会警告（训不出东西）。

用法：
    python -m pipeline.prepare --data data --out labels.csv
    python -m pipeline.prepare --data data --out labels.csv --strict   # 有任何错误就退出
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

from .console import ensure_utf8

EXTS = {".jpg", ".jpeg", ".png", ".webp"}
SEP = "__"
MULTI = "+"


def load_codes(dict_path: Path) -> tuple[dict[str, bool], dict[str, bool]]:
    """返回 {code: enabled}。enabled=false 的类定义还留着，但不许拿来训练。"""
    data = json.loads(dict_path.read_text(encoding="utf-8"))
    subj = {g["code"]: bool(g.get("enabled", True)) for g in data.get("SUBJECT", [])}
    style = {g["code"]: bool(g.get("enabled", True)) for g in data.get("STYLE", [])}
    return subj, style


def main() -> None:
    ensure_utf8()
    ap = argparse.ArgumentParser(description="目录 → labels.csv")
    ap.add_argument("--data", default="data", help="数据根目录")
    ap.add_argument("--out", default="labels.csv", help="输出 csv 路径")
    ap.add_argument("--dict", default="labels/dictionary.json")
    ap.add_argument("--strict", action="store_true", help="有错误直接退出（不写 csv）")
    args = ap.parse_args()

    root = Path(args.data)
    if not root.is_dir():
        raise SystemExit(f"数据目录不存在: {root}")
    subj_map, style_map = load_codes(Path(args.dict))

    rows: list[dict[str, str]] = []
    errors: list[str] = []
    warnings: list[str] = []
    per_leaf: Counter[str] = Counter()

    for photo_dir in sorted(p for p in root.iterdir() if p.is_dir()):
        photographer = photo_dir.name
        leaves = [p for p in photo_dir.iterdir() if p.is_dir()]
        if not leaves:
            warnings.append(f"{photographer}: 没有子目录，跳过")
            continue
        for leaf in sorted(leaves):
            name = leaf.name
            if SEP not in name:
                errors.append(f"{leaf}: 目录名缺分隔符 '{SEP}'，应为 题材__风格")
                continue
            left, _, right = name.partition(SEP)
            subjects = [c.strip() for c in left.split(MULTI) if c.strip()]
            styles = [c.strip() for c in right.split(MULTI) if c.strip()]
            if not subjects or not styles:
                errors.append(f"{leaf}: 题材或风格为空")
                continue
            ok = True
            for c in subjects:
                if c not in subj_map:
                    errors.append(f"{leaf}: 未知题材 code '{c}'（合法值见 dictionary.json 的 SUBJECT）")
                    ok = False
                elif not subj_map[c]:
                    errors.append(f"{leaf}: 题材 '{c}' 本期不训练（enabled=false）")
                    ok = False
            for c in styles:
                if c not in style_map:
                    errors.append(f"{leaf}: 未知风格 code '{c}'（合法值见 dictionary.json 的 STYLE）")
                    ok = False
                elif not style_map[c]:
                    errors.append(f"{leaf}: 风格 '{c}' 本期不训练（enabled=false）")
                    ok = False
            if not ok:
                continue

            files = sorted(p for p in leaf.iterdir() if p.suffix.lower() in EXTS and p.is_file())
            if not files:
                warnings.append(f"{leaf}: 没有图片")
                continue
            if len(files) < 5:
                warnings.append(f"{leaf}: 只有 {len(files)} 张，少于 5 张基本训不出这类")
            per_leaf[f"{MULTI.join(subjects)}{SEP}{MULTI.join(styles)}"] += len(files)
            for f in files:
                rows.append({
                    "path": str(f.resolve()),
                    "subject": ",".join(subjects),
                    "style": ",".join(styles),
                    "photographer_id": photographer,
                })

    if warnings:
        print("── 警告 ──", file=sys.stderr)
        for w in warnings:
            print(f"  {w}", file=sys.stderr)
    if errors:
        print("── 错误 ──", file=sys.stderr)
        for e in errors:
            print(f"  {e}", file=sys.stderr)
        if args.strict:
            raise SystemExit(f"共 {len(errors)} 个错误，--strict 下不写文件")

    if not rows:
        raise SystemExit("没有可用样本")

    out = Path(args.out)
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["path", "subject", "style", "photographer_id"])
        writer.writeheader()
        writer.writerows(rows)

    # ── 完整性报告：这是决定"现在能不能训"的唯一依据 ──
    print(f"\n已写入 {out}，共 {len(rows)} 张，{len({r['photographer_id'] for r in rows})} 个摄影师/来源")
    subj_cnt: Counter[str] = Counter()
    style_cnt: Counter[str] = Counter()
    for r in rows:
        for c in r["subject"].split(","):
            subj_cnt[c] += 1
        for c in r["style"].split(","):   # 风格是多标签，必须拆开计，否则分布报告会把 "A+B" 当成新类
            style_cnt[c] += 1

    print("\n题材分布（训练时多标签）：")
    for c, n in subj_cnt.most_common():
        flag = "  ⚠ 偏少" if n < 30 else ""
        print(f"  {c:16s} {n:4d}{flag}")
    print("\n风格分布（多标签，总和会大于图片数，属正常）：")
    for c, n in style_cnt.most_common():
        flag = "  ⚠ 偏少" if n < 30 else ""
        print(f"  {c:16s} {n:4d}{flag}")

    ph = Counter(r["photographer_id"] for r in rows)
    print("\n来源分布（决定分组划分是否可行）：")
    for p, n in ph.most_common():
        print(f"  {p:16s} {n:4d}")
    if len(ph) < 3:
        print("\n⚠ 摄影师/来源少于 3 个，分组划分会退化成随机划分，指标不可信。"
              "\n  公开数据集请按来源分目录（ds_unsplash / ds_coco / p001 / p002 ...）。")

    thin = [c for c, n in list(subj_cnt.items()) + list(style_cnt.items()) if n < 30]
    if thin:
        print(f"\n提示：{len(thin)} 个类别不足 30 张，训出来的指标会很难看；"
              f"先补到 ≥30，能到 60 最好。")


if __name__ == "__main__":
    main()
