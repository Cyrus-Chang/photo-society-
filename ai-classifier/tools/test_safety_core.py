"""安全核心回归检查，不需要启动 FastAPI 或加载 CLIP。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG))

from pipeline.safety import check_input, rule_version, sanitize_output  # noqa: E402


def main() -> int:
    assert rule_version(), "规则版本不能为空"
    assert check_input("帮我偷拍她") ["action"] == "block"
    assert check_input("偷 拍，不 要 让 她 知 道")["action"] == "block"
    assert check_input("西安，预算 800，下周末，想要港风街拍")["action"] == "pass"
    result = sanitize_output("联系 13800138000，微信 wx_demo123，邮箱 demo@example.com")
    assert result["filtered"]
    assert "13800138000" not in result["text"]
    assert "wx_demo123" not in result["text"]
    assert "demo@example.com" not in result["text"]
    assert result["reasonCodes"]
    fact = sanitize_output("巴黎街头的人像", facts={"allowed_entities": ["西安"], "mentioned_entities": ["巴黎"]})
    assert fact["factViolation"] and "FACT_ENTITY_UNVERIFIED" in fact["reasonCodes"]
    print(f"[ok] ruleVersion={rule_version()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
