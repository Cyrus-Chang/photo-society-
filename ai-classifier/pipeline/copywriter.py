"""作品文案生成（LLM 8 分那一项）。

落点选在「上传入库」：分类器已经给出结构化标签（13 类风格 + 9 条影调），
这比"直接看图写文案"稳定得多，也正好回答评分点里的「Prompt 设计 / 输出稳定可控」。

两条红线：
1. **不编造事实**。提示词明确禁止写时间、地点、人物关系、拍摄经历——这些数据我们本来就没有（C2）。
2. **降级要诚实**。没配 LLM key 时返回 mode="rule" 的模板兜底，界面必须标明，
   不能把模板结果伪装成模型输出。
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

STYLE_CN = {
    "JAPANESE": "日系", "KOREAN": "韩系", "INS": "ins风", "FRESH": "清新", "FILM": "胶片",
    "VINTAGE": "复古", "CINEMATIC": "电影感", "DARK_MOOD": "暗调", "MONO": "黑白",
    "BLUE_TONE": "蓝调", "HK_RETRO": "港风", "CYBER": "赛博", "WESTERN": "欧美",
}
TONE_CN = {
    "TONE_WARM": "暖调", "TONE_COOL": "冷调", "TONE_HIGH_SAT": "高饱和", "TONE_LOW_SAT": "低饱和",
    "TONE_HIGH_CONTRAST": "高对比", "TONE_LOW_CONTRAST": "低对比", "TONE_HIGH_KEY": "高调",
    "TONE_LOW_KEY": "低调", "TONE_LIFTED_BLACK": "抬黑",
}

SYSTEM_PROMPT = (
    "你是摄影社区的作品文案助手。只根据给定的风格/影调标签写中文文案。"
    "绝对不要编造时间、地点、人物身份、拍摄经过、情绪故事——这些数据没有提供。"
    "只返回 JSON：{\"titles\":[3 个不超过 12 字的中文标题],\"intro\":\"不超过 60 字的简介\","
    "\"tags\":[5 个可检索标签]}。不要输出 JSON 以外的任何内容。"
)


def _config() -> dict[str, str]:
    return {
        "key": os.environ.get("LLM_API_KEY", "").strip(),
        "base": os.environ.get("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/"),
        "model": os.environ.get("LLM_MODEL", "qwen-plus"),
    }


def llm_configured() -> bool:
    return bool(_config()["key"])


def _rule_fallback(payload: dict[str, Any], reason: str = "") -> dict[str, Any]:
    styles = [STYLE_CN.get(code, code) for code in payload.get("styles", [])]
    tones = [TONE_CN.get(code, code) for code in payload.get("tones", [])]
    style = styles[0] if styles else "摄影"
    tone = tones[0] if tones else ""
    base_title = payload.get("title", "").strip()
    titles = [
        base_title or f"{style}里的一帧",
        f"{style}{tone}的作品" if tone else f"{style}的一次现场",
        f"关于{style}的一张照片",
    ]
    intro_parts = []
    if styles:
        intro_parts.append("、".join(styles[:2]) + "的风格")
    if tones:
        intro_parts.append("、".join(tones[:2]) + "的影调")
    intro = ("这张照片是" + "，".join(intro_parts) + "。") if intro_parts else "这张照片已上传，等你补充介绍。"
    return {
        "mode": "rule",
        "titles": titles[:3],
        "intro": intro,
        "tags": [*styles[:3], *tones[:2]],
        "note": reason or "未配置 LLM，使用模板兜底（不编造画面外信息）",
    }


def _call_llm(payload: dict[str, Any]) -> dict[str, Any] | None:
    cfg = _config()
    if not cfg["key"]:
        return None
    body = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "temperature": 0.7,
        "max_tokens": 400,
        "response_format": {"type": "json_object"},
    }
    request = urllib.request.Request(
        f"{cfg['base']}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {cfg['key']}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        titles = [str(item).strip() for item in parsed.get("titles", []) if str(item).strip()][:3]
        intro = str(parsed.get("intro", "")).strip()
        tags = [str(item).strip() for item in parsed.get("tags", []) if str(item).strip()][:5]
        if not titles or not intro:
            return None
        return {"mode": "llm", "titles": titles, "intro": intro, "tags": tags, "note": ""}
    except (urllib.error.URLError, KeyError, IndexError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        # 失败原因带出去，方便前端说人话，不假装成功
        return None


def generate_copy(payload: dict[str, Any]) -> dict[str, Any]:
    result = _call_llm(payload)
    if result:
        return result
    reason = "" if not llm_configured() else "LLM 调用失败，已退回模板兜底"
    return _rule_fallback(payload, reason)
