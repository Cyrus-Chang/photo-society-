"""以图搜图接口的进程内自检（不需要起 HTTP 服务）。

三件事：
1. ``WorkIndex.search_vector`` 的排序正确性：拿索引里已有的作品向量当查询，
   排第一的必须就是它自己（同一条向量，相似度 1.0）。
2. ``rank_photographers`` 的聚合契约：每位摄影师最多 2 张代表作、重合度在
   0-100、按分排序。
3. ``scene_share`` 的统计口径：占比分母是作品数，不是标签出现次数。

用法（cwd 必须是 ai-classifier）：
    .\.venv\Scripts\python.exe tools\test_similar.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.retrieval import WorkIndex  # noqa: E402
from pipeline.similar import MATCH_SOURCE, rank_photographers, scene_share  # noqa: E402

INDEX_PATH = ROOT / "models" / "works.embed.npz"
MANIFEST_PATH = ROOT / "models" / "works.manifest.json"

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def main() -> int:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    works: dict[str, dict] = {}
    for key in ("works", "spiralWorks"):
        for item in manifest.get(key, []):
            works.setdefault(str(item["id"]), item)
    photographers = {str(item["id"]): item for item in manifest.get("photographers", [])}
    by_photographer: dict[str, list[dict]] = {}
    for item in works.values():
        by_photographer.setdefault(str(item.get("photographerId") or ""), []).append(item)

    index = WorkIndex(INDEX_PATH)
    archive = index._parts[0]["archive"]  # noqa: SLF001 - 自检脚本直接读产物
    ids = [str(item) for item in archive["ids"]]
    vecs = np.asarray(archive["vecs"], dtype=np.float32)
    check("索引非空", len(ids) >= 10, f"indexed={len(ids)}")

    # 1) 自我检索：同一条向量必须排第一
    for probe in (0, len(ids) // 2, len(ids) - 1):
        hits = index.search_vector(vecs[probe], k=5)
        top_id = hits[0]["id"] if hits else None
        check(f"search_vector 自我检索 #{probe}", top_id == ids[probe],
              f"expect={ids[probe]} got={top_id} score={hits[0]['score'] if hits else None}")

    # 2) 聚合契约：用一次真实检索命中喂给 rank_photographers
    hits = index.search_vector(vecs[0], k=24)
    matches = rank_photographers(hits, works, photographers, top_k=3, per_photographer=2)
    check("聚合成 1-3 位摄影师", 1 <= len(matches) <= 3, f"matches={len(matches)}")
    check("每位最多 2 张代表作", all(len(m["works"]) <= 2 for m in matches),
          f"works={[len(m['works']) for m in matches]}")
    check("重合度落在 0-100", all(0.0 <= m["matchPercent"] <= 100.0 for m in matches),
          f"percent=[{', '.join(str(m['matchPercent']) for m in matches)}]")
    check("按重合度降序", [m["matchPercent"] for m in matches] == sorted(
        [m["matchPercent"] for m in matches], reverse=True))
    check("重合度口径有出处", bool(MATCH_SOURCE and "0.65" in MATCH_SOURCE))
    first = matches[0] if matches else {}
    print("  首名样例:", json.dumps({
        "photographerId": first.get("photographerId"), "name": first.get("name"),
        "matchPercent": first.get("matchPercent"), "styleOverlap": first.get("styleOverlap"),
        "works": [w["id"] for w in first.get("works", [])],
    }, ensure_ascii=False))

    # 3) 场景统计口径
    pid = next((key for key, items in by_photographer.items() if key and len(items) >= 3), "")
    check("找到至少 3 件作品的摄影师", bool(pid), f"photographerId={pid}")
    if pid:
        stats = scene_share(by_photographer[pid])
        total = stats["totalWorks"]
        check("场景占比分母=作品数", total == len(by_photographer[pid]), f"totalWorks={total}")
        check("占比不超过 100", all(0.0 <= item["share"] <= 100.0 for item in stats["scenes"]))
        check("topSceneShare 与首位一致",
              (not stats["scenes"]) or stats["topSceneShare"] == stats["scenes"][0]["share"])
        print("  场景样例:", json.dumps(stats, ensure_ascii=False)[:320])

    index.close()
    print()
    if failures:
        print(f"RESULT: FAIL ({len(failures)} 项)", "; ".join(failures))
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
