"""作品查重（老师建议里的「样片溯源排查」最小可用版）。

两路信号，都不引入新模型：

1. **dHash 感知哈希**（64 bit，纯 PIL + numpy）：对缩放、轻微调色不敏感，
   用来抓「同一张图被重复上传 / 搬运后重传」。
2. **CLIP 余弦**（复用 /v1/embed 的视觉塔）：抓「同一组图改色/裁切后重传」。

两者都只是**信号**，不是判决：响应里给距离、余弦、风险档，并写清公式，
让人能复核。平台不做「判定搬运」这种法律结论，只提示「需要人工复核」。
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from PIL import Image

METHOD = (
    "dHash 64bit（汉明距离越小越像）+ CLIP 视觉余弦；"
    "duplicateRisk = max(0, 100 - hamming/24*100)（无关照片的汉明距离通常在 20-32，"
    "所以以 24 为归零点，避免把不相关图片报成中风险）；"
    "riskLevel=high 当 h<=8 或 (cos>=0.98 且 h<=14)。仅与平台作品库比对，不构成侵权判定。"
)


def dhash(img: Image.Image, size: int = 8) -> int:
    """差值哈希：转灰度 → 缩到 (size+1, size) → 相邻像素比较 → 64 bit 整数。"""
    small = img.convert("L").resize((size + 1, size), Image.Resampling.LANCZOS)
    px = np.asarray(small, dtype=np.int16)
    diff = px[:, 1:] > px[:, :-1]
    bits = 0
    for value in diff.flatten():
        bits = (bits << 1) | int(bool(value))
    return bits


def hamming(a: int, b: int) -> int:
    return int(bin(int(a) ^ int(b)).count("1"))


def build_table(entries: Iterable[Mapping[str, Any]], size: int = 8) -> dict[str, Any]:
    return {
        "version": f"phash-{size}x{size}-1",
        "size": size,
        "count": len(list(entries)) if not isinstance(entries, list) else len(entries),
        "entries": list(entries),
    }


def audit(
    query_hash: int,
    table: Mapping[str, Any],
    query_vector: Sequence[float] | None = None,
    index=None,
    top_n: int = 5,
) -> dict[str, Any]:
    """对一次上传做查重。

    ``index`` 可选：给了就用它算 CLIP 余弦（search_vector 的 vectorSimilarity），
    不给就只报哈希信号，并在 warnings 里写明少了一路证据。
    """
    warnings: list[str] = []
    entries = list(table.get("entries") or [])
    cosines: dict[str, float] = {}
    if index is not None and query_vector is not None:
        try:
            hits = index.search_vector(np.asarray(query_vector, dtype=np.float32), k=min(12, len(entries) or 12))
            cosines = {str(hit["id"]): float(hit.get("vectorSimilarity") or 0.0) for hit in hits}
        except Exception as exc:  # noqa: BLE001  查重不该因为索引问题 500
            warnings.append(f"CLIP 余弦不可用：{type(exc).__name__}: {exc}")
    else:
        warnings.append("未提供向量/索引：本次只报 dHash 信号")

    scored: list[dict[str, Any]] = []
    for entry in entries:
        try:
            dist = hamming(query_hash, int(entry["phash"]))
        except (KeyError, TypeError, ValueError):
            continue
        risk = round(max(0.0, 100.0 - dist / 24.0 * 100.0), 1)
        cosine = cosines.get(str(entry.get("id")))
        scored.append({
            "workId": str(entry.get("id")),
            "file": str(entry.get("file") or ""),
            "hamming": dist,
            "clipCosine": round(cosine, 4) if cosine is not None else None,
            "duplicateRisk": risk,
        })

    scored.sort(key=lambda item: (item["hamming"], -(item["clipCosine"] or 0.0), item["workId"]))
    nearest = scored[: max(1, int(top_n))]
    best_distance = nearest[0]["hamming"] if nearest else None
    best_cos = nearest[0]["clipCosine"] if nearest else None
    high = bool(nearest) and (best_distance <= 8 or (best_cos is not None and best_cos >= 0.98 and best_distance <= 14))
    duplicate_risk = nearest[0]["duplicateRisk"] if nearest else 0.0
    return {
        "ok": True,
        "duplicateRisk": duplicate_risk,
        "riskLevel": "high" if high else ("medium" if duplicate_risk >= 60.0 else "low"),
        "nearest": nearest,
        "comparedWorks": len(scored),
        "method": METHOD,
        "warnings": warnings,
        "note": "仅与平台作品库比对，提示人工复核；平台不据此做侵权判定。",
    }
