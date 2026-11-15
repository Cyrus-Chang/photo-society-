"""探测 skillhub 上与「摄影 / 图像 / 训练」相关的技能，汇总成一份可读清单。"""
import json
import urllib.parse
import urllib.request

API = "https://api.skillhub.cn/api/skills"
UA = "Mozilla/5.0 (compatible; dsh-probe)"
KEYWORDS = [
    "图像数据集", "标注工具", "主动学习", "特征提取", "向量检索", "embedding",
    "人像", "构图", "影调", "白平衡", "直方图", "图像质量评估", "审美评分",
    "图像去重", "相似图片", "以图搜图", "图像分类器", "迁移学习", "线性探测",
    "opencv", "pillow", "matplotlib", "faiss", "clip 模型",
]


def get(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def main() -> int:
    out = {}
    for kw in KEYWORDS:
        q = urllib.parse.quote(kw)
        try:
            d = get(f"{API}?page=1&pageSize=6&keyword={q}")
        except Exception as exc:  # noqa: BLE001
            out[kw] = {"err": f"{type(exc).__name__}: {exc}"}
            continue
        items = []
        for s in d["data"]["skills"]:
            price = (s.get("channelPricing") or {}).get("price")
            items.append({
                "name": s["name"],
                "ns": (s.get("namespace") or {}).get("canonicalName"),
                "dl": s.get("downloads"),
                "inst": s.get("installs"),
                "price": price,
                "verified": s.get("verified"),
                "desc": (s.get("description_zh") or s.get("description") or "")[:90],
            })
        out[kw] = {"total": d["data"]["total"], "items": items}
    with open(r"E:\通用型摄影师接单平台\.skillprobe3.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("ok", len(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
