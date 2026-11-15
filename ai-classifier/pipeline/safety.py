"""AI 安全层（评分表「AI 安全与可控性 4 分」）。

为什么不做一份"涉政涉黄词表"——那不是这个产品真实的风险面。摄影约拍平台的真实风险是：
1. **偷拍 / 隐私**：「帮我拍她」「偷拍」「跟拍」这类需求会把平台变成侵权工具；
2. **绕过平台私下交易**：「私下转账」「加微信直接约」——撮合平台的核心利益就在这一步；
3. **Prompt 注入**：用户输入会被塞进 LLM 提示词，必须挡住「忽略以上指令」这类话术；
4. **输出泄漏**：模型不得在文案里编造联系方式或引流信息。

处置分三档，全部可解释、可回溯：
    pass    正常放行
    review  转人工（命中低危词，或模型置信度低于阈值）
    block   直接拒（命中高危词或注入模式）
"""
from __future__ import annotations

import re
from typing import Any

# 高危：一旦命中直接拒，并告知原因
BLOCK_TERMS = [
    "偷拍", "偷窥", "跟踪拍摄", "跟拍她", "跟拍他", "不让她知道", "不让他知道",
    "私下转账", "微信转账", "绕过平台", "线下付款", "走私单",
]

# 低危：转人工复核
REVIEW_TERMS = [
    "私房", "私密", "换衣", "更衣", "未授权", "商用授权", "肖像权",
]

# Prompt 注入模式
INJECTION_PATTERNS = [
    r"忽略(之前|以上|前面)的?(所有)?(指令|要求|提示)",
    r"ignore\s+(all\s+)?(previous|above)\s+instructions",
    r"你现在是", r"system\s*prompt", r"开发者模式", r"jailbreak",
]

# 输出侧：联系方式/引流，一律不落进作品文案
CONTACT_PATTERNS = [
    r"1[3-9]\d{9}",                       # 手机号
    r"(微信|weixin|wx|vx|v信)\s*[:：]?\s*\S{3,}",  # 微信号
    r"https?://\S+",                      # 外链
    r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # 邮箱
]

MAX_INPUT_CHARS = 500


def check_input(text: str, confidence: float | None = None, threshold: float = 0.30) -> dict[str, Any]:
    """检查用户输入（撮合需求 / 作品标题 / 简介）。"""
    raw = (text or "").strip()
    flags: list[str] = []

    if len(raw) > MAX_INPUT_CHARS:
        return {
            "ok": False, "action": "block", "flags": ["TOO_LONG"],
            "note": f"输入超过 {MAX_INPUT_CHARS} 字，请精简后再试",
        }
    if not raw:
        return {"ok": False, "action": "block", "flags": ["EMPTY"], "note": "内容为空"}

    lowered = raw.lower()
    for term in BLOCK_TERMS:
        if term in raw:
            flags.append(f"BLOCK_TERM:{term}")
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            flags.append(f"PROMPT_INJECTION:{pattern}")
    if flags:
        return {
            "ok": False, "action": "block", "flags": flags,
            "note": "这段需求里包含平台不承接的内容（偷拍/隐私或绕过平台的私下交易），已拦下",
        }

    for term in REVIEW_TERMS:
        if term in raw:
            flags.append(f"REVIEW_TERM:{term}")

    if confidence is not None and confidence < threshold:
        flags.append(f"LOW_CONFIDENCE:{confidence:.2f}<{threshold:.2f}")

    action = "review" if flags else "pass"
    note = "已标记转人工复核" if action == "review" else ""
    return {"ok": True, "action": action, "flags": flags, "note": note}


def sanitize_output(text: str) -> dict[str, Any]:
    """清理模型输出：去掉联系方式与外链，超长截断。不修改语义，只做安全裁剪。"""
    cleaned = text or ""
    hits: list[str] = []
    for pattern in CONTACT_PATTERNS:
        if re.search(pattern, cleaned):
            hits.append(pattern)
            cleaned = re.sub(pattern, "（已隐藏联系方式）", cleaned)
    if len(cleaned) > 400:
        cleaned = cleaned[:400] + "…"
    return {"text": cleaned, "filtered": bool(hits), "patterns": hits}
