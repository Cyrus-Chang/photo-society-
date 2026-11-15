"""标注加速器：零样本预填 + 人工确认 → 直接生成 prepare.py 要的目录结构。

为什么需要它：交接文档 §4 说标注要 5~6 小时/500 张，这是整条线最贵的一步。
CLIP 零样本在题材上的 top1 置信度实测 0.5~0.99、风格 0.27~0.97，
把它当"初稿"、人只做确认和纠错，能把这一段压到 1~2 小时。

两步走（第二步必须有人的判断，不要在没人看的情况下直接 apply）：

  1) 预填：
     python tools/prelabel.py scan D:\\photos --out labels_proposed.csv
     —— 每张图一行，给出 subject_1 / style_1..3 及置信度，decision 留空。

  2) 人工过一遍 CSV（Excel 直接开，UTF-8 BOM）：
     - 认了：decision 留空，或写 ok
     - 改：直接把 subject_1 / style_1 改成正确类别码（逗号分隔可多标，最多 3 个）
     - 弃：decision 写 skip（模糊、重复、不是摄影作品）
     - photographer_id 列决定分组划分，一个人一个值；同一次拍摄请填同一个

  3) 落地：
     python tools/prelabel.py apply labels_proposed.csv --data data
     —— 按 data/<photographer_id>/<SUBJ>__<STYLE>/ 建目录（硬链接，不复制不占空间）

之后就是常规三步：prepare → extract → fit。

注意：预填只是省时间，不能替代判断。全盘接受零样本结果等于让模型学自己，
训练出来的东西不会有增益——这是交接文档铁律 12 的延伸。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path
from typing import Dict, List

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

EXTS = {".jpg", ".jpeg", ".png", ".webp"}
DICT_PATH = ROOT / "labels" / "dictionary.json"

COLUMNS = [
    "path", "photographer_id",
    "subject_1", "subject_1_conf", "subject_2", "subject_3",
    "style_1", "style_1_conf", "style_2", "style_3",
    "tone", "decision",
]

SKIP_WORDS = {"skip", "x", "no", "drop", "弃", "跳过"}


# ---------------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------------
def _load_dictionary() -> Dict[str, List[dict]]:
    data = json.loads(DICT_PATH.read_text(encoding="utf-8"))
    out: Dict[str, List[dict]] = {}
    for tag in ("SUBJECT", "STYLE"):
        out[tag] = [g for g in data.get(tag, []) if g.get("enabled", True) and g.get("prompt_en")]
    return out


def cmd_scan(args) -> int:
    import pipeline.serve as serve
    from PIL import Image, ImageOps

    src = Path(args.src)
    imgs = sorted(p for p in src.rglob("*") if p.suffix.lower() in EXTS)
    if args.person_from_dir:
        imgs = [p for p in imgs if p.parent != src or True]
    if not imgs:
        print(f"没有图片：{src}")
        return 2
    if args.limit:
        imgs = imgs[: args.limit]

    serve._state["clip_ok"] = serve._load_clip()
    serve._state["dict"] = json.loads(DICT_PATH.read_text(encoding="utf-8"))
    if not serve._state["clip_ok"]:
        print("CLIP 没加载起来，先跑 tools/fetch_clip.py")
        return 3

    rows = []
    for i, p in enumerate(imgs, 1):
        try:
            img = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
            vec = serve.build_inputs(img)
            zs = serve.classify_zero_shot(vec)
            tone = [t["code"] for t in serve.derive_tone(
                {n: float(v) for n, v in zip(serve.FEATURE_NAMES, vec[512:])})]
        except Exception as exc:  # noqa: BLE001  单张坏图不该打断整批
            print(f"[warn] {p.name}: {exc}")
            continue
        subj = zs.get("subject", [])
        style = zs.get("style", [])
        person = p.parent.name if args.person_from_dir else "p001"
        rows.append({
            "path": str(p),
            "photographer_id": person,
            "subject_1": subj[0]["code"] if subj else "",
            "subject_1_conf": f"{subj[0]['confidence']:.3f}" if subj else "",
            "subject_2": subj[1]["code"] if len(subj) > 1 else "",
            "subject_3": subj[2]["code"] if len(subj) > 2 else "",
            "style_1": style[0]["code"] if style else "",
            "style_1_conf": f"{style[0]['confidence']:.3f}" if style else "",
            "style_2": style[1]["code"] if len(style) > 1 else "",
            "style_3": style[2]["code"] if len(style) > 2 else "",
            "tone": ",".join(tone),
            "decision": "",
        })
        print(f"\r  预填 {i}/{len(imgs)}  {p.name[:40]:42s}", end="", file=sys.stderr)

    print("", file=sys.stderr)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print(f"已写入 {out}（{len(rows)} 张）。下一步：人工过一遍 decision/subject_1/style_1，再 apply。")
    return 0


# ---------------------------------------------------------------------------
# apply
# ---------------------------------------------------------------------------
def _split_multi(cell: str) -> List[str]:
    return [c.strip() for c in (cell or "").replace("+", ",").split(",") if c.strip()]


def cmd_apply(args) -> int:
    src_csv = Path(args.csv)
    data = Path(args.data)
    if not src_csv.exists():
        print(f"csv 不存在：{src_csv}")
        return 2

    dicts = _load_dictionary()
    subj_ok = {g["code"] for g in dicts["SUBJECT"]}
    style_ok = {g["code"] for g in dicts["STYLE"]}

    rows = list(csv.DictReader(src_csv.open(encoding="utf-8-sig")))
    made, skipped, bad, dup = 0, 0, 0, 0
    seen: Dict[str, str] = {}
    for row in rows:
        dec = (row.get("decision") or "").strip().lower()
        if dec in SKIP_WORDS:
            skipped += 1
            continue
        path = Path((row.get("path") or "").strip())
        if not path.exists():
            print(f"[warn] 找不到图：{path}")
            bad += 1
            continue
        subj = [c for c in _split_multi(row.get("subject_1", "")) if c in subj_ok]
        style = [c for c in _split_multi(row.get("style_1", "")) if c in style_ok]
        if not subj or not style:
            print(f"[warn] 标签不合法（subject={row.get('subject_1')!r} style={row.get('style_1')!r}）：{path.name}")
            bad += 1
            continue
        person = (row.get("photographer_id") or "").strip() or "p001"
        d = data / person / f"{'+'.join(subj)}__{'+'.join(style)}"
        d.mkdir(parents=True, exist_ok=True)
        dst = d / path.name
        if dst.exists():
            dup += 1
            continue
        seen[str(dst)] = str(path)
        if args.copy:
            import shutil
            shutil.copy2(path, dst)
        else:
            try:
                os.link(path, dst)          # 硬链接：同盘零拷贝
            except OSError:
                import shutil
                shutil.copy2(path, dst)     # 跨盘自动退回复制
        made += 1

    print(f"落地 {made} 张 → {data}（跳过 {skipped}，非法 {bad}，重名 {dup}）")
    if made:
        print("下一步：python -m pipeline.prepare --data data --out labels.csv")
    return 0


def main() -> None:
    from pipeline.console import ensure_utf8
    ensure_utf8()

    ap = argparse.ArgumentParser(description="零样本预填标注 + 生成 data/ 目录")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("scan", help="扫描目录，零样本预填 CSV")
    s.add_argument("src")
    s.add_argument("--out", default=str(ROOT / "labels_proposed.csv"))
    s.add_argument("--limit", type=int, default=0)
    s.add_argument("--person-from-dir", action="store_true",
                   help="用图片所在目录名当 photographer_id（按拍摄批次分组的常见做法）")
    s.set_defaults(func=cmd_scan)

    a = sub.add_parser("apply", help="按 CSV 建 data/<摄影师>/<题材>__<风格>/")
    a.add_argument("csv")
    a.add_argument("--data", default=str(ROOT / "data"))
    a.add_argument("--copy", action="store_true", help="复制而不是硬链接")
    a.set_defaults(func=cmd_apply)

    args = ap.parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
