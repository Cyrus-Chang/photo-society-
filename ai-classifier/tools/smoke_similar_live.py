"""以图搜图与场景统计的端到端自检（走 ASGI，不绑定端口，因此不受沙箱限制）。

用 FastAPI TestClient 触发 startup（加载 CLIP），然后真按 HTTP 形态打：
  1. POST /v1/similar（multipart 上传真实照片）
  2. GET  /v1/photographer/{id}/scene-share
  3. 同名 BFF 别名 /api/v1/ai/*（前端走的就是这条）

用法（cwd 必须是 ai-classifier）：
    .\.venv\Scripts\python.exe tools\smoke_similar_live.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from pipeline import serve  # noqa: E402

IMAGE = ROOT.parent / "src" / "assets" / "works" / "ts-01.webp"
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def main() -> int:
    with TestClient(serve.app) as client:
        check("startup 里 CLIP 加载成功", bool(serve._state.get("clip_ok")))

        with IMAGE.open("rb") as handle:
            resp = client.post("/v1/similar", params={"topK": 3},
                               files={"file": (IMAGE.name, handle, "image/webp")})
        check("POST /v1/similar 200", resp.status_code == 200, f"status={resp.status_code}")
        body = resp.json() if resp.status_code == 200 else {}
        matches = body.get("matches") or []
        check("返回 1-3 位摄影师", 1 <= len(matches) <= 3, f"matches={len(matches)}")
        check("带 styleMatch", bool(body.get("styleMatch")),
              json.dumps(body.get("styleMatch"), ensure_ascii=False)[:120])
        check("重合度 0-100", all(0.0 <= m.get("matchPercent", -1) <= 100.0 for m in matches),
              str([m.get("matchPercent") for m in matches]))
        check("每位最多 2 张代表作", all(len(m.get("works") or []) <= 2 for m in matches))
        print("  首名:", json.dumps({
            "photographerId": matches[0].get("photographerId") if matches else None,
            "name": matches[0].get("name") if matches else None,
            "matchPercent": matches[0].get("matchPercent") if matches else None,
            "works": [w["id"] for w in (matches[0].get("works") or [])] if matches else [],
        }, ensure_ascii=False))

        pid = (matches[0].get("photographerId") if matches else "") or "p-001"
        share = client.get(f"/v1/photographer/{pid}/scene-share")
        check("GET /v1/photographer/{id}/scene-share 200", share.status_code == 200,
              f"status={share.status_code}")
        sbody = share.json() if share.status_code == 200 else {}
        check("场景统计有数据", bool(sbody.get("scenes")), f"totalWorks={sbody.get('totalWorks')}")
        check("占比 ≤100", all(0.0 <= item.get("share", -1) <= 100.0
                              for item in (sbody.get("scenes") or [])))
        print("  场景:", json.dumps({
            "photographerId": sbody.get("photographerId"),
            "totalWorks": sbody.get("totalWorks"),
            "top3": (sbody.get("scenes") or [])[:3],
            "narrowCoverage": sbody.get("narrowCoverage"),
        }, ensure_ascii=False))

        alias = client.get(f"/api/v1/ai/photographer/{pid}/scene-share")
        check("BFF 别名 /api/v1/ai/photographer 可用", alias.status_code == 200,
              f"status={alias.status_code}")

    print()
    if failures:
        print(f"RESULT: FAIL ({len(failures)} 项)", "; ".join(failures))
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
