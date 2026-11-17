"""Evaluate the works retriever against a human-labelled query set.

This script deliberately refuses to turn model output into labels.  The labels
file must contain at least 40 rows written by a person, with one expected work
ID per query.  Until that file exists, the script writes an explicit
``evaluated: false`` report instead of fabricating recall numbers.

Run from ``ai-classifier`` while the FastAPI service is running::

    .\\.venv\\Scripts\\python.exe tools\\eval_retrieval.py

The endpoint is queried three times per case so that vector-only, balanced,
and metadata-heavy weight settings can be compared.  No new package is
introduced; the service's existing NumPy runtime is used to read index IDs
from the NPZ artifact for validation.
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable


PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parent
DEFAULT_LABELS = PKG / "data" / "retrieval_labels.json"
DEFAULT_INDEX = PKG / "models" / "works.embed.npz"
DEFAULT_REPORT = REPO / ".review-tmp" / "retrieval-eval.json"

# The names are part of the report contract.  Keep the three combinations
# intentionally distinct so a reviewer can see whether metadata is helping or
# merely overwhelming the CLIP signal.
WEIGHT_SETS: dict[str, dict[str, float]] = {
    "vector_only": {"vector": 1.0, "tags": 0.0, "color": 0.0},
    "balanced": {"vector": 0.55, "tags": 0.30, "color": 0.15},
    "metadata_heavy": {"vector": 0.35, "tags": 0.45, "color": 0.20},
}


def _json_load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_ids(path: Path) -> set[str]:
    """Read only the ids array from the current index artifact.

    ``np.load`` is imported lazily so a missing optional runtime does not hide
    the more useful labels-file validation error.  Accessing only ``ids`` also
    avoids touching the vector matrix during evaluation setup.
    """

    if not path.exists():
        return set()
    try:
        import numpy as np  # type: ignore

        paths = [path]
        meta_path = path.with_name("works.index.json")
        if meta_path.exists():
            meta = _json_load(meta_path)
            paths.extend(path.parent / str(item) for item in meta.get("shards", []))
        ids: set[str] = set()
        for candidate in paths:
            if not candidate.exists():
                continue
            with np.load(candidate, allow_pickle=False) as data:
                ids.update(str(item) for item in data["ids"].tolist())
        return ids
    except Exception as exc:  # noqa: BLE001 - report a clear validation error
        raise ValueError(f"无法读取索引 IDs：{path}（{exc}）") from exc


def _rows_from_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("items", payload.get("rows", payload.get("labels", [])))
    else:
        rows = []
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def validate_labels(path: Path, index_ids: set[str]) -> tuple[list[dict[str, str]], list[str]]:
    """Validate the human annotation contract without making assumptions.

    Accepted row shape::

        {"query": "想拍…", "expected_id": "w-001",
         "annotator": "name-or-id", "source": "human", "notes": "…"}

    ``source`` is mandatory and must literally be ``human``.  This prevents a
    zero-shot prediction or an imported title from being presented as manual
    ground truth.  Unknown IDs are rejected when an index is available.
    """

    errors: list[str] = []
    if not path.exists():
        return [], [f"缺少标注文件：{path}"]
    try:
        payload = _json_load(path)
    except Exception as exc:  # noqa: BLE001
        return [], [f"标注文件不是有效 JSON：{exc}"]

    rows = _rows_from_payload(payload)
    valid: list[dict[str, str]] = []
    seen_queries: set[str] = set()
    for number, row in enumerate(rows, 1):
        query = str(row.get("query", "")).strip()
        expected_id = str(row.get("expected_id", row.get("expectedWorkId", ""))).strip()
        source = str(row.get("source", "")).strip().lower()
        annotator = str(row.get("annotator", "")).strip()
        if not query:
            errors.append(f"第 {number} 条缺 query")
            continue
        if not expected_id:
            errors.append(f"第 {number} 条缺 expected_id")
            continue
        if source != "human":
            errors.append(f"第 {number} 条 source 必须为 human（当前：{source or '空'}）")
            continue
        if not annotator:
            errors.append(f"第 {number} 条缺 annotator")
            continue
        if query in seen_queries:
            errors.append(f"第 {number} 条 query 重复：{query}")
            continue
        if index_ids and expected_id not in index_ids:
            errors.append(f"第 {number} 条 expected_id 不在索引：{expected_id}")
            continue
        seen_queries.add(query)
        valid.append({
            "query": query,
            "expected_id": expected_id,
            "annotator": annotator,
            "source": source,
            "notes": str(row.get("notes", "")).strip(),
        })

    if len(valid) < 40:
        errors.append(f"有效人工标注仅 {len(valid)} 条，至少需要 40 条；不计算指标")
    return valid, errors


def _post_json(url: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"请求 {url} 失败：{exc}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"请求 {url} 返回不是 JSON 对象")
    if payload.get("ok") is False:
        raise RuntimeError(str(payload.get("error") or "search 返回 ok=false"))
    return payload


def _hits(payload: dict[str, Any]) -> list[dict[str, Any]]:
    hits = payload.get("hits", payload.get("results", []))
    return [row for row in hits if isinstance(row, dict)] if isinstance(hits, list) else []


def _hit_id(hit: dict[str, Any]) -> str:
    return str(hit.get("id", hit.get("workId", hit.get("work_id", ""))))


def _metrics(rows: Iterable[dict[str, Any]]) -> dict[str, float | int]:
    rows = list(rows)
    if not rows:
        return {"cases": 0, "recall@1": 0.0, "recall@5": 0.0, "MRR": 0.0}
    r1 = 0
    r5 = 0
    reciprocal = 0.0
    for row in rows:
        expected = row["expected_id"]
        ranked = row.get("ranked_ids", [])
        try:
            rank = ranked.index(expected) + 1
        except ValueError:
            rank = 0
        r1 += int(rank == 1)
        r5 += int(0 < rank <= 5)
        reciprocal += (1.0 / rank) if rank else 0.0
    total = len(rows)
    return {
        "cases": total,
        "recall@1": round(r1 / total, 4),
        "recall@5": round(r5 / total, 4),
        "MRR": round(reciprocal / total, 4),
    }


def evaluate(base_url: str, labels: list[dict[str, str]], timeout: float) -> dict[str, Any]:
    endpoint = base_url.rstrip("/") + "/v1/search"
    result: dict[str, Any] = {
        "endpoint": endpoint,
        "weights": {},
        "errors": [],
    }
    for name, weights in WEIGHT_SETS.items():
        evaluated_rows: list[dict[str, Any]] = []
        for label in labels:
            try:
                payload = _post_json(endpoint, {
                    "text": label["query"],
                    "k": 5,
                    "weights": weights,
                }, timeout)
                hits = _hits(payload)
                ranked_ids = [_hit_id(hit) for hit in hits]
                applied = payload.get("weights") if isinstance(payload.get("weights"), dict) else None
                if hits:
                    context = (hits[0].get("explanation") or {}).get("queryContext") or {}
                    if isinstance(context, dict):
                        applied = applied or context.get("weights")
                evaluated_rows.append({
                    "query": label["query"],
                    "expected_id": label["expected_id"],
                    "ranked_ids": ranked_ids,
                    "weightsApplied": applied,
                    "hit_details": hits,
                })
            except RuntimeError as exc:
                result["errors"].append({
                    "weightSet": name,
                    "query": label["query"],
                    "error": str(exc),
                })
        result["weights"][name] = {
            "config": weights,
            "metrics": _metrics(evaluated_rows),
            "rows": evaluated_rows,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="评测作品混合检索（仅接受真实人工标注）")
    parser.add_argument("--base-url", default="http://127.0.0.1:8100", help="FastAPI 地址")
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS, help="人工标注 JSON")
    parser.add_argument("--index", type=Path, default=DEFAULT_INDEX, help="作品索引 NPZ")
    parser.add_argument("--out", type=Path, default=DEFAULT_REPORT, help="评测报告 JSON")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--allow-missing", action="store_true", help="标注不足时返回 0 退出码（仍不计算指标）")
    args = parser.parse_args()

    try:
        index_ids = _load_ids(args.index)
    except ValueError as exc:
        index_ids = set()
        index_error = str(exc)
    else:
        index_error = ""
    labels, validation_errors = validate_labels(args.labels, index_ids)
    # A missing optional runtime should not obscure the primary, actionable
    # message when no annotation set has been supplied yet.  Once >=40 human
    # rows exist, the index-read error remains fatal and is reported below.
    if len(labels) < 40 and index_error:
        index_error = ""

    report: dict[str, Any] = {
        "evaluated": False,
        "labelFile": str(args.labels),
        "indexFile": str(args.index),
        "labelCount": len(labels),
        "requiredLabelCount": 40,
        "validationErrors": validation_errors + ([index_error] if index_error else []),
        "weights": {},
        "limitation": "缺少至少 40 条 source=human 的查询→作品 ID 标注；未计算 recall/MRR。",
    }
    if len(labels) >= 40 and not index_error and not validation_errors:
        result = evaluate(args.base_url, labels, args.timeout)
        report.update(result)
        report["evaluated"] = not bool(result.get("errors"))
        if result.get("errors"):
            report["limitation"] = "服务请求存在错误；仅报告成功请求的分母，详见 errors。"

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "evaluated": report["evaluated"],
        "labelCount": report["labelCount"],
        "validationErrors": report["validationErrors"],
        "report": str(args.out),
    }, ensure_ascii=False))
    if report["evaluated"]:
        for name, block in report.get("weights", {}).items():
            print(name, json.dumps(block["metrics"], ensure_ascii=False))
    return 0 if report["evaluated"] or args.allow_missing else 2


if __name__ == "__main__":
    raise SystemExit(main())

