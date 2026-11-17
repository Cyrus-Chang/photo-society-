"""作品查重（/v1/works/audit）的端到端自检，走 ASGI，不绑端口。

验证四件事：
1. 库内作品自己查自己 → 汉明距离 0、风险 100、high；
2. 库外图片 → 风险明显更低（不是所有图都报 high）；
3. GET ?workId= 契约（前端旧调用形态）可用；
4. BFF 别名 /api/v1/ai/works/audit 的 GET/POST 都通。

用法（cwd 必须是 ai-classifier）：
    .\.venv\Scripts\python.exe tools\test_audit.py
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

REPO = ROOT.parent
SELF_IMAGE = REPO / "public" / "works" / "unsplash" / "w-001.jpg"
OTHER_IMAGE = REPO / "src" / "assets" / "works" / "ts-01.webp"

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def main() -> int:
    check("素材存在", SELF_IMAGE.exists() and OTHER_IMAGE.exists())
    with TestClient(serve.app) as client:
        with SELF_IMAGE.open("rb") as handle:
            resp = client.post("/v1/works/audit", files={"file": (SELF_IMAGE.name, handle, "image/jpeg")})
        check("POST 库内图 200", resp.status_code == 200, f"status={resp.status_code}")
        body = resp.json() if resp.status_code == 200 else {}
        nearest = body.get("nearest") or []
        check("命中自己（汉明距离 0）", bool(nearest) and nearest[0]["hamming"] == 0,
              json.dumps(nearest[0] if nearest else {}, ensure_ascii=False))
        check("库内自比风险=high", body.get("riskLevel") == "high", str(body.get("riskLevel")))
        check("响应写死公式可复算", "dHash" in str(body.get("method")),
              str(body.get("method"))[:80])

        with OTHER_IMAGE.open("rb") as handle:
            other = client.post("/v1/works/audit", files={"file": (OTHER_IMAGE.name, handle, "image/webp")})
        obody = other.json() if other.status_code == 200 else {}
        onearest = (obody.get("nearest") or [{}])[0]
        check("库外图风险更低", float(obody.get("duplicateRisk", 100)) < float(body.get("duplicateRisk", 0)),
              f"库内={body.get('duplicateRisk')} 库外={obody.get('duplicateRisk')} hamming={onearest.get('hamming')}")
        print("  库外首名:", json.dumps(onearest, ensure_ascii=False)[:200])

        by_id = client.get("/v1/works/audit", params={"workId": "w-001"})
        check("GET ?workId= 200", by_id.status_code == 200, f"status={by_id.status_code}")
        idbody = by_id.json() if by_id.status_code == 200 else {}
        check("按 id 查重同样命中自己",
              bool(idbody.get("nearest")) and idbody["nearest"][0]["workId"] == "w-001")

        alias = client.get("/api/v1/ai/works/audit", params={"workId": "w-002"})
        check("BFF 别名 GET 可用", alias.status_code == 200, f"status={alias.status_code}")

        with SELF_IMAGE.open("rb") as handle:
            alias_post = client.post("/api/v1/ai/works/audit",
                                     files={"file": (SELF_IMAGE.name, handle, "image/jpeg")})
        check("BFF 别名 POST 可用", alias_post.status_code == 200, f"status={alias_post.status_code}")

        missing = client.get("/v1/works/audit", params={"workId": "not-exist"})
        check("不存在的 workId 明确报错而不是 500", missing.status_code == 200 and not missing.json().get("ok"),
              str(missing.json().get("error"))[:60])

    print()
    if failures:
        print(f"RESULT: FAIL ({len(failures)} 项)", "; ".join(failures))
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
