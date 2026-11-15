"""文案生成冒烟测试（不经过 HTTP）。

用法（cwd 必须是 ai-classifier）：
    .\\.venv\\Scripts\\python.exe tools\\test_copywriter.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parent
sys.path.insert(0, str(PKG))

from pipeline.copywriter import generate_copy, llm_configured  # noqa: E402

PAYLOADS = [
    {"title": "", "styles": [{"code": "JAPANESE"}], "tones": [{"code": "TONE_WARM"}]},
    {"title": "夜市里的红伞", "styles": [{"code": "HK_RETRO"}], "tones": [{"code": "TONE_HIGH_CONTRAST"}]},
    {"title": "", "styles": [], "tones": []},
]


def normalize(payload: dict) -> dict:
    return {
        "title": payload.get("title", ""),
        "styles": [item["code"] if isinstance(item, dict) else item for item in payload.get("styles", [])],
        "tones": [item["code"] if isinstance(item, dict) else item for item in payload.get("tones", [])],
    }


def main() -> int:
    print(f"[i] LLM 已配置 = {llm_configured()}")
    results = []
    for payload in PAYLOADS:
        normalized = normalize(payload)
        result = generate_copy(normalized)
        results.append({"input": normalized, "output": result})
        print(f'  [{result["mode"]}] titles={result["titles"]}')
    out = REPO / ".review-tmp" / "copywriter-smoke.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[ok] -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
