"""以图搜图（样片向量比对）的纯函数层。

只做两件可单测的事，不碰 HTTP、不加载模型：

1. ``rank_photographers``：把检索命中聚合成「摄影师候选」，给出 0-100 的
   重合度。口径与 ``/v1/search`` 完全一致（CLIP 0.65 + 标签 0.20 + 色彩 0.15
   加权后的 score），所以两条链路的分数可比，不会出现两套数字。
2. ``scene_share``：按作品 styles 标签算场景覆盖，供摄影师主页展示。

HTTP 路由在 serve.py，图像编码复用 serve.build_inputs（同一套视觉塔与预处理），
不另起一套向量空间。
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

MATCH_SOURCE = (
    "CLIP 视觉相似度 0.65 + 标签重合 0.20 + color24 0.15 加权后 ×100"
    "（与 /v1/search 同一口径，不是另一个模型）"
)


def style_words(work: Mapping[str, Any]) -> list[str]:
    """作品标签可能是 "夜景 城市 低光" 这样的空格串，也可能是列表。"""
    raw = work.get("styles")
    if isinstance(raw, str):
        text = raw.replace("，", " ").replace("、", " ").replace("/", " ").replace("｜", " ")
        return [word for word in text.split() if word]
    if isinstance(raw, (list, tuple)):
        return [str(word) for word in raw if str(word).strip()]
    return []


def rank_photographers(
    hits: Sequence[Mapping[str, Any]],
    works_map: Mapping[str, Mapping[str, Any]],
    photographers: Mapping[str, Mapping[str, Any]],
    top_k: int = 3,
    per_photographer: int = 2,
    city: str = "",
) -> list[dict[str, Any]]:
    """命中 → 摄影师候选。

    - 每位摄影师最多收 ``per_photographer`` 张代表作；
    - ``matchPercent`` 取该摄影师最高分作品（同一口径），0-100 一位小数；
    - ``styleOverlap`` 保留原始 CLIP 余弦，便于解释「像在哪」；
    - 同城只影响排序（+0.02），不改数字，避免把城市写进「重合度」。
    """
    groups: dict[str, dict[str, Any]] = {}
    for hit in hits:
        work = works_map.get(str(hit.get("id", "")))
        if not work:
            continue
        pid = str(work.get("photographerId") or "")
        if not pid:
            continue
        entry = groups.setdefault(pid, {"score": 0.0, "hits": [], "tags": set()})
        if len(entry["hits"]) >= per_photographer:
            continue
        entry["hits"].append(hit)
        entry["score"] = max(entry["score"], float(hit.get("score") or 0.0))
        entry["tags"].update(str(tag) for tag in (hit.get("tagOverlap") or []))

    ranked: list[tuple[str, dict[str, Any], float]] = []
    for pid, entry in groups.items():
        profile = photographers.get(pid) or {}
        work_cities = {str((works_map.get(str(hit.get("id", ""))) or {}).get("city") or "")
                       for hit in entry["hits"]}
        profile_city = str(profile.get("city") or "")
        same_city = bool(city) and (profile_city == city or city in work_cities)
        rank_score = entry["score"] + (0.02 if same_city else 0.0)
        ranked.append((pid, entry, rank_score))
    ranked.sort(key=lambda item: (-item[2], item[0]))

    matches: list[dict[str, Any]] = []
    for pid, entry, _rank in ranked[: max(1, int(top_k))]:
        profile = photographers.get(pid) or {}
        best = max(float(hit.get("score") or 0.0) for hit in entry["hits"])
        best_vec = max(float(hit.get("vectorSimilarity") or 0.0) for hit in entry["hits"])
        work_cities = {str((works_map.get(str(hit.get("id", ""))) or {}).get("city") or "")
                       for hit in entry["hits"]}
        matches.append({
            "photographerId": pid,
            "name": str(profile.get("name") or pid),
            "city": str(profile.get("city") or ""),
            "sameCity": bool(city) and (str(profile.get("city") or "") == city or city in work_cities),
            "matchPercent": round(min(1.0, max(0.0, best)) * 100, 1),
            "styleOverlap": round(best_vec, 4),
            "tags": sorted(entry["tags"]),
            "works": [
                {
                    "id": str(hit.get("id")),
                    "title": str((works_map.get(str(hit.get("id", ""))) or {}).get("title") or ""),
                    "imageUrl": str((works_map.get(str(hit.get("id", ""))) or {}).get("imageUrl") or ""),
                    "city": str((works_map.get(str(hit.get("id", ""))) or {}).get("city") or ""),
                    "score": round(float(hit.get("score") or 0.0) * 100, 1),
                    "vectorSimilarity": round(float(hit.get("vectorSimilarity") or 0.0), 4),
                }
                for hit in entry["hits"]
            ],
        })
    return matches


def scene_share(works: Sequence[Mapping[str, Any]], top_n: int = 5) -> dict[str, Any]:
    """按作品 styles 算场景覆盖。

    分母是**作品数**（不是标签出现次数）：占总作品数的比例，避免一张作品打
    三个同义标签就把占比抬到 300%。
    """
    total = len(works)
    counts: dict[str, int] = {}
    for work in works:
        for word in style_words(work):
            counts[word] = counts.get(word, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[: max(1, int(top_n))]
    scenes = [
        {"scene": word, "count": count, "share": round(count / total * 100, 1) if total else 0.0}
        for word, count in ordered
    ]
    top_share = scenes[0]["share"] if scenes else 0.0
    return {
        "totalWorks": total,
        "scenes": scenes,
        "topSceneShare": top_share,
        "narrowCoverage": bool(total >= 3 and top_share > 60.0),
        "method": "按作品 styles 标签词频统计；分母=该摄影师作品数，同一作品多个标签分别计数",
    }
