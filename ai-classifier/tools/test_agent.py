"""Agent 冒烟测试：进程内跑三条真实需求，把结果写成 UTF-8 JSON 供人/模型核对。

用法（cwd 必须是 ai-classifier）：
    .\\.venv\\Scripts\\python.exe tools\\test_agent.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parent
sys.path.insert(0, str(PKG))
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from pipeline.agent import run_agent  # noqa: E402
from pipeline.serve import _startup, _state  # noqa: E402

QUERIES = [
    "西安，预算 800，下周末，想要港风街拍",
    "成都周末想拍日系清新，预算 600",
    "北京想拍古风汉服，预算 1200，周六",
]


def main() -> int:
    _startup()
    if not _state.get("clip_ok"):
        print("[x] CLIP 未加载")
        return 2
    results = []
    for query in QUERIES:
        result = run_agent(query, top_n=3, state=_state)
        results.append({
            "query": query,
            "ok": result["ok"],
            "mode": result["mode"],
            "slots": result["slots"],
            "latencyMs": result["latencyMs"],
            "reply": result["reply"],
            "warnings": result.get("warnings", []),
            "tools": [step["tool"] for step in result["toolTrace"]],
            "candidates": [
                {
                    "name": item["name"],
                    "city": item["city"],
                    "crossCity": item.get("crossCity", False),
                    "score": item["score"],
                    "works": [
                        {"title": work["title"], "score": work["score"], "reason": work["reason"]}
                        for work in item["works"]
                    ],
                }
                for item in result["candidates"]
            ],
        })
        print(f'  [{query[:14]}…] slots={result["slots"]["city"]}/{result["slots"]["when"]}/'
              f'budget={result["slots"]["budget"]}/styles={result["slots"]["styles"]} '
              f'-> {len(result["candidates"])} 位 {result["latencyMs"]}ms')

    out = REPO / ".review-tmp" / "agent-smoke.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[ok] -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
