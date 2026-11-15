"""把 .skillprobe3.json 压成一行一条的可读清单。"""
import json

SRC = r"E:\通用型摄影师接单平台\.skillprobe3.json"
DST = r"E:\通用型摄影师接单平台\.probe3.txt"
NOISE = ("WPS", "金山", "腾讯", "PPT", "公文", "网文", "股票", "招投标", "教师", "论文", "法律", "合同", "中标")


def main() -> int:
    data = json.load(open(SRC, encoding="utf-8"))
    lines = []
    for kw, v in data.items():
        if "items" not in v:
            lines.append(f"== {kw}  ERR {v.get('err')}")
            continue
        lines.append(f"== {kw}  (total {v['total']})")
        for it in v["items"]:
            name = it["name"]
            if any(n in name for n in NOISE):
                continue
            price = f" ￥{it['price']}" if it.get("price") else ""
            lines.append(
                f"   dl={it['dl'] or 0:<7} inst={it['inst'] or 0:<5} {it['ns']}{price}"
                f"  | {name} | {it['desc'][:70]}"
            )
    open(DST, "w", encoding="utf-8").write("\n".join(lines))
    print("ok", len(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
