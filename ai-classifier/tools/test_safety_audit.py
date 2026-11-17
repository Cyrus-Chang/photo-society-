"""审计日志回归检查，使用临时日志路径，不污染工作区日志。"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["SAFETY_AUDIT_LOG"] = str(Path(tmp) / "safety.jsonl")
        from pipeline.safety import check_input, query_audit

        result = check_input("私下转账，微信 wx_private123", enable_semantic=False)
        assert result["action"] == "block"
        rows = query_audit()
        assert rows and rows[-1]["action"] == "block"
        snippet = rows[-1]["snippet"]
        assert "wx_private123" not in snippet
        assert "reasonCodes" in rows[-1]
    print("[ok] audit redaction")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
