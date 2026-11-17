"""运行安全红队与 benign 评估，比较纯规则和规则+CLIP 语义闸门。

用法（cwd=ai-classifier）：
  .venv\\Scripts\\python.exe tools\\run_safety_redteam.py
  .venv\\Scripts\\python.exe tools\\run_safety_redteam.py --no-clip
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parent
sys.path.insert(0, str(PKG))

from pipeline.safety import check_input, rule_version  # noqa: E402


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _semantic_state(disabled: bool) -> tuple[dict[str, Any] | None, str]:
    if disabled:
        return None, "disabled"
    try:
        # Reuse the exact CLIP model/processor already used by the service.
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        from pipeline import serve

        if serve._state.get("clip_ok") or serve._load_clip():
            serve._state["clip_ok"] = True
            return serve._state, "available"
    except Exception as exc:  # noqa: BLE001
        return None, f"unavailable:{type(exc).__name__}"
    return None, "unavailable"


def _run_case(case: dict[str, Any], semantic_state: dict[str, Any] | None, *, semantic: bool, dangerous: bool) -> dict[str, Any]:
    turns = case.get("turns") or [case.get("text", "")]
    context: list[str] = []
    first_escalation: int | None = None
    final: dict[str, Any] = {}
    for turn_no, turn in enumerate(turns, 1):
        context.append(str(turn))
        final = check_input(
            str(turn),
            semantic_state=semantic_state if semantic else None,
            context=context,
            enable_semantic=semantic,
        )
        if first_escalation is None and final.get("action") != "pass":
            first_escalation = turn_no
    return {
        "id": case["id"],
        "category": case.get("category", "benign"),
        "text": " / ".join(turns),
        "expected": case.get("expected_action", "pass"),
        "dangerous": dangerous,
        "action": final.get("action", "pass"),
        "ok": final.get("action") == case.get("expected_action", "pass")
        if case.get("expected_action")
        else final.get("action") == "pass",
        "miss": bool(case.get("expected_action") and final.get("action") == "pass"),
        "flags": final.get("flags", []),
        "semantic": final.get("semantic", {}),
        "firstEscalationTurn": first_escalation,
        "ruleVersion": final.get("ruleVersion", rule_version()),
    }


def _metrics(rows: list[dict[str, Any]], *, dangerous: bool) -> dict[str, Any]:
    subset = [row for row in rows if row.get("dangerous") is dangerous]
    if dangerous:
        misses = sum(bool(row.get("miss")) for row in subset)
        return {
            "total": len(subset),
            "misses": misses,
            "missRate": round(misses / len(subset), 4) if subset else 0.0,
            "passThroughRate": round(misses / len(subset), 4) if subset else 0.0,
            "actionCounts": {action: sum(row.get("action") == action for row in subset) for action in ("pass", "review", "block")},
        }
    false_positives = sum(row.get("action") != "pass" for row in subset)
    return {
        "total": len(subset),
        "falsePositives": false_positives,
        "falsePositiveRate": round(false_positives / len(subset), 4) if subset else 0.0,
        "actionCounts": {action: sum(row.get("action") == action for row in subset) for action in ("pass", "review", "block")},
    }


def _by_category(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        buckets[row["category"]].append(row)
    return {category: _metrics(items, dangerous=True) for category, items in sorted(buckets.items())}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-clip", action="store_true", help="只跑规则，便于复现纯词表基线")
    args = parser.parse_args()
    dangerous = _load_jsonl(Path(__file__).with_name("safety_redteam_cases.jsonl"))
    benign = _load_jsonl(Path(__file__).with_name("safety_benign_cases.jsonl"))
    state, semantic_status = _semantic_state(args.no_clip)
    modes = {
        "pure_rules": (None, False),
        "rules_plus_semantic": (state, not args.no_clip),
    }
    report: dict[str, Any] = {
        "ruleVersion": rule_version(),
        "semanticStatus": semantic_status,
        "cases": {"redteam": len(dangerous), "benign": len(benign)},
        "modes": {},
    }
    all_rows: list[dict[str, Any]] = []
    for mode, (mode_state, enabled) in modes.items():
        red_rows = [_run_case(case, mode_state, semantic=enabled, dangerous=True) for case in dangerous]
        benign_rows = [_run_case(case, mode_state, semantic=enabled, dangerous=False) for case in benign]
        for row in red_rows + benign_rows:
            row["mode"] = mode
        all_rows.extend(red_rows + benign_rows)
        report["modes"][mode] = {
            "redteam": _metrics(red_rows, dangerous=True),
            "benign": _metrics(benign_rows, dangerous=False),
            "byCategory": _by_category(red_rows),
            "misses": [row for row in red_rows if row["miss"]],
        }
    out_dir = REPO / ".review-tmp"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "redteam_summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "redteam_misses.json").write_text(json.dumps({mode: data["misses"] for mode, data in report["modes"].items()}, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out_dir / "redteam_results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["mode", "id", "category", "text", "expected", "dangerous", "action", "ok", "miss", "firstEscalationTurn", "flags", "semantic", "ruleVersion"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in all_rows:
            writer.writerow({**row, "flags": json.dumps(row["flags"], ensure_ascii=False), "semantic": json.dumps(row["semantic"], ensure_ascii=False)})
    for mode, data in report["modes"].items():
        red = data["redteam"]
        benign_metric = data["benign"]
        print(f"[{mode}] 漏检率={red['missRate']:.2%} 通过率={red['passThroughRate']:.2%} 误杀率={benign_metric['falsePositiveRate']:.2%}")
        if data["misses"]:
            print("  漏检：" + ", ".join(row["id"] for row in data["misses"]))
    print(f"[ok] semantic={semantic_status} -> {out_dir / 'redteam_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
