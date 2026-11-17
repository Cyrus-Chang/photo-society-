"""文案生成冒烟与事实校验测试（不经过 HTTP）。

用法（cwd 必须是 ai-classifier）：
    .\\.venv\\Scripts\\python.exe tools\\test_copywriter.py

如果本地设置了 LLM_API_KEY，冒烟样例会真实调用兼容接口；脚本不会读取、打印或写入 key。
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
REPO = PKG.parent
sys.path.insert(0, str(PKG))

from pipeline.copywriter import (  # noqa: E402
    _sanitize_result,
    copywriter_metrics,
    generate_copy,
    llm_configured,
    stream_copy,
    validate_facts,
)

PAYLOADS = [
    {"title": "", "styles": [{"code": "JAPANESE"}], "tones": [{"code": "TONE_WARM"}]},
    {"title": "夜市里的红伞", "styles": [{"code": "HK_RETRO"}], "tones": [{"code": "TONE_HIGH_CONTRAST"}]},
    {"title": "", "styles": [], "tones": []},
]


def _valid_result(intro: str, title: str = "一帧光影") -> dict:
    return {"titles": [title, "光影留白", "安静一刻"], "intro": intro, "tags": ["摄影", "作品", "光影", "构图", "质感"]}


def _adversarial_cases() -> list[tuple[dict, dict, str]]:
    """20 条输入没有事实、输出却注入事实的对抗样例。"""
    cases: list[tuple[dict, dict, str]] = []
    payload = {"title": "一帧光影", "styles": ["JAPANESE"], "tones": ["TONE_WARM"]}
    for index, date in enumerate(("2024年1月1日", "2025年5月20日", "2026-11-15", "10月1日", "1999/12/31"), 1):
        cases.append((payload, _valid_result(f"记录于{date}的光影"), f"date-{index}"))
    for index, location in enumerate(("上海", "北京", "西湖", "东京", "外滩"), 1):
        cases.append((payload, _valid_result(f"在{location}留下的光影"), f"location-{index}"))
    for index, person in enumerate(("张三", "李四", "王五", "小明", "鲁迅"), 1):
        cases.append((payload, _valid_result(f"与{person}一起的光影"), f"person-{index}"))
    for index, equipment in enumerate(("徕卡", "佳能", "富士", "50mm", "三脚架"), 1):
        cases.append((payload, _valid_result(f"使用{equipment}拍摄的光影"), f"equipment-{index}"))
    return cases


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
        started = time.perf_counter()
        result = generate_copy(normalized)
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        results.append({"input": normalized, "output": result})
        usage = result.get("usage") or {}
        print(f'  [{result["mode"]}] model={result.get("model") or "rule"} latencyMs={result.get("latencyMs", elapsed)} '
              f'tokens={usage.get("total_tokens", 0)} degraded={result.get("degraded", False)} '
              f'errorCode={result.get("errorCode", "")} titles={result["titles"]}')

    filtered = _sanitize_result({
        "titles": ["正常标题", "wx_bad123", "第三个"],
        "intro": "画面介绍",
        "tags": ["微信 wx_bad123", "街拍", "光影"],
    })
    assert all("wx_bad123" not in value for value in [*filtered["titles"], *filtered["tags"]])
    accepted, reason = validate_facts(
        {"titles": ["巴黎街头", "街景", "作品"], "intro": "巴黎街头", "tags": ["巴黎", "街拍", "摄影", "作品", "光影"]},
        {"title": "西安街拍", "styles": [], "tones": []},
    )
    assert not accepted and "locations" in reason
    print("  [security] tags contact filtering + invented entity rejection OK")

    # The service route wraps this generator in StreamingResponse. Keep a
    # dependency-free contract check here so the SSE event order is replayable
    # even when the local sandbox cannot bind a TCP port.
    stream_chunks = list(stream_copy(PAYLOADS[0]))
    stream_events = [chunk.splitlines()[0].split(":", 1)[1].strip() for chunk in stream_chunks]
    assert stream_events[0] == "meta" and "delta" in stream_events and "result" in stream_events and stream_events[-1] == "done"
    print(f"[sse] events=meta,delta(x{stream_events.count('delta')}),result,done mode=rule")

    rejected = 0
    fact_report = []
    for payload, result, case_id in _adversarial_cases():
        accepted, reason = validate_facts(result, payload)
        if not accepted:
            rejected += 1
        fact_report.append({"id": case_id, "rejected": not accepted, "reason": reason})
    total = len(fact_report)
    reject_rate = round(rejected / total * 100, 1) if total else 0.0
    print(f"[facts] rejected={rejected}/{total} rejectRate={reject_rate}%")
    metrics = copywriter_metrics()
    print(f"[metrics] calls={metrics['count']} latencyP50={metrics['p50Ms']}ms latencyP95={metrics['p95Ms']}ms "
          f"tokenP50={metrics['p50Tokens']} tokenP95={metrics['p95Tokens']} totalTokens={metrics['totalTokens']}")

    out = REPO / ".review-tmp" / "copywriter-smoke.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"results": results, "facts": fact_report, "metrics": metrics}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[ok] -> {out}")
    return 0 if rejected == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
