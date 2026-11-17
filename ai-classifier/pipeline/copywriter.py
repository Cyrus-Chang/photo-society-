"""作品文案生成。

这个模块只依赖 Python 标准库，负责把分类器给出的结构化标签交给
OpenAI 兼容接口，并在输出落库前做三层保护：JSON schema、画面外事实校验、
安全文本过滤。没有 key、超时或模型不合规时，统一降级到可解释的模板结果。
"""
from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from typing import Any

logger = logging.getLogger("paishe.copywriter")

from .prompts import COPYWRITER_PROMPT_VERSION, COPYWRITER_SYSTEM_PROMPT

PROMPT_VERSION = COPYWRITER_PROMPT_VERSION
SYSTEM_PROMPT = COPYWRITER_SYSTEM_PROMPT

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

# 事实校验词表是保守的：命中才拦截，不命中不代表模型获得了事实授权。
KNOWN_LOCATIONS = (
    "北京", "上海", "广州", "深圳", "杭州", "成都", "重庆", "西安", "南京", "苏州", "武汉", "厦门",
    "青岛", "大连", "长沙", "昆明", "东京", "京都", "巴黎", "伦敦", "纽约", "香港", "澳门", "台北",
    "外滩", "故宫", "西湖", "天安门", "长城", "陆家嘴", "迪士尼", "海边", "街角", "公园",
)
KNOWN_PEOPLE = (
    "张三", "李四", "王五", "赵六", "小明", "小红", "阿明", "阿华", "林徽因", "鲁迅", "周杰伦",
)
KNOWN_EQUIPMENT = (
    "徕卡", "佳能", "尼康", "索尼", "富士", "哈苏", "理光", "宾得", "奥林巴斯", "无反", "单反",
    "相机", "镜头", "闪光灯", "三脚架", "胶片机", "35mm", "50mm", "85mm", "广角镜",
)
_DATE_RE = re.compile(r"(?:\d{4}\s*[年./-]\s*\d{1,2}(?:\s*[月./-]\s*\d{1,2}\s*日?)?|\d{1,2}\s*月\s*\d{1,2}\s*日?)")
_LOCATION_RE = re.compile(r"(?:在|于|来自|地点(?:是|为)?)[\s:：]*([\u4e00-\u9fff]{2,12}(?:市|区|县|镇|村|路|街|公园|山|海|湖|岛))")
_PERSON_RE = re.compile(r"(?:摄影师|作者|人物|主角)[\s:：]*([\u4e00-\u9fff]{2,4})")
_PERSON_RELATION_RE = re.compile(r"(?:与|和|同|陪)[\s:：]*([A-Za-z][A-Za-z -]{1,24}|[\u4e00-\u9fff]{2,4})(?=\s*(?:一起|同行|合影|出镜|拍摄|同框))")
_EQUIPMENT_RE = re.compile(
    r"(?:用|使用|搭配|配合)[\s:：]*("
    r"(?:徕卡|佳能|尼康|索尼|富士|哈苏|理光|宾得|奥林巴斯|无反|单反|相机|镜头|闪光灯|三脚架|胶片机|"
    r"35mm|50mm|85mm|广角镜|Leica|Canon|Nikon|Sony|Fujifilm|Hasselblad)"
    r")",
    re.IGNORECASE,
)
_NON_PERSON_TOKENS = {"光影", "画面", "风景", "自然", "阳光", "城市", "镜头", "色彩"}

_METRICS: list[dict[str, Any]] = []
_METRICS_LOCK = threading.Lock()
_MAX_METRICS = 1000


class LLMCallFailure(RuntimeError):
    """携带可展示/可记录的模型失败原因。"""

    def __init__(self, code: str, message: str, status: int | None = None):
        super().__init__(message)
        self.code = code
        self.status = status


def _config() -> dict[str, Any]:
    try:
        timeout = max(1.0, float(os.environ.get("LLM_TIMEOUT_SEC", "20")))
    except ValueError:
        timeout = 20.0
    try:
        retries = max(0, min(5, int(os.environ.get("LLM_RETRIES", "2"))))
    except ValueError:
        retries = 2
    return {
        "key": os.environ.get("LLM_API_KEY", "").strip(),
        "base": os.environ.get("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/"),
        "model": os.environ.get("LLM_MODEL", "qwen-plus"),
        "timeout": timeout,
        "retries": retries,
    }


def llm_configured() -> bool:
    return bool(_config()["key"])


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _clip(value: Any, limit: int) -> str:
    return _text(value)[:limit]


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """接受旧前端的 code 字符串和分类器的 {code: ...} 两种形态。"""
    out = dict(payload or {})
    for key in ("styles", "tones"):
        values = out.get(key) or []
        out[key] = [
            _text(item.get("code", "")) if isinstance(item, dict) else _text(item)
            for item in values
        ]
    out["title"] = _text(out.get("title", ""))
    return out


def _split_labels(payload: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    """把 styles / tones 拆成中文标签，并单独交出无法映射的原始 code。

    之前的实现是 ``STYLE_CN.get(code, code)``：调用方误把影调 code 传进 styles
    时，原始英文 code 会直接进标题（``关于TONE_HIGH_``），既不可读也像 bug。
    现在：已知 code → 中文；影调 code 误传进 styles → 自动归位到 tones；剩余
    无法识别的 code 只记录不外露（响应里用 unmappedCodes 如实报出，不静默丢）。
    """
    styles: list[str] = []
    tones: list[str] = []
    unmapped: list[str] = []
    for code in payload.get("styles", []):
        text = _text(code)
        if not text:
            continue
        if text in STYLE_CN:
            styles.append(STYLE_CN[text])
        elif text in TONE_CN:
            tones.append(TONE_CN[text])
        elif text.isascii() and text.replace("_", "").isalnum() and text.upper() == text:
            unmapped.append(text)
        elif text not in styles:
            styles.append(text)
    for code in payload.get("tones", []):
        text = _text(code)
        if not text:
            continue
        if text in TONE_CN:
            tones.append(TONE_CN[text])
        elif text in STYLE_CN:
            styles.append(STYLE_CN[text])
        elif text.isascii() and text.replace("_", "").isalnum() and text.upper() == text:
            unmapped.append(text)
        elif text not in tones:
            tones.append(text)
    return styles, tones, unmapped


def _rule_fallback(payload: dict[str, Any], reason: str = "") -> dict[str, Any]:
    payload = _normalize_payload(payload)
    styles, tones, unmapped = _split_labels(payload)
    style = styles[0] if styles else "摄影"
    tone = tones[0] if tones else ""
    base_title = _clip(payload.get("title", ""), 12)
    titles = [
        base_title or f"{style}里的一帧",
        _clip(f"{style}{tone}的作品" if tone else f"{style}的一次现场", 12),
        _clip(f"关于{style}的一张照片", 12),
    ]
    intro_parts = []
    if styles:
        intro_parts.append("、".join(styles[:2]) + "的风格")
    if tones:
        intro_parts.append("、".join(tones[:2]) + "的影调")
    intro = ("这张照片是" + "，".join(intro_parts) + "。") if intro_parts else "这张照片已上传，等你补充介绍。"
    tags: list[str] = []
    for item in [*styles, *tones, "摄影", "作品", "光影", "氛围", "画面"]:
        if item and item not in tags:
            tags.append(item)
    return {
        "mode": "rule", "titles": titles[:3], "intro": _clip(intro, 60), "tags": tags[:5],
        "note": reason or "未配置 LLM，使用模板兜底（不编造画面外信息）",
        "promptVersion": PROMPT_VERSION,
        "unmappedCodes": unmapped,
        "labelSource": "styles/tones code → 中文词典（STYLE_CN / TONE_CN）",
    }


def _source_text(payload: dict[str, Any]) -> str:
    """只把用户/分类器传入的字段当作事实来源。"""
    keys = ("title", "description", "sourceText", "facts", "dates", "locations", "people", "equipment", "styles", "tones")
    bits: list[str] = []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, (list, tuple, set)):
            bits.extend(_text(item.get("code", "")) if isinstance(item, dict) else _text(item) for item in value)
        elif isinstance(value, dict):
            bits.extend(_text(item) for item in value.values())
        elif value is not None:
            bits.append(_text(value))
    return " ".join(bits).lower()


def _fact_candidates(text: str) -> dict[str, set[str]]:
    lower = text.lower()
    dates = {re.sub(r"\s+", "", item) for item in _DATE_RE.findall(lower)}
    locations = {item for item in KNOWN_LOCATIONS if item.lower() in lower}
    locations.update(item.lower() for item in _LOCATION_RE.findall(text))
    people = {item for item in KNOWN_PEOPLE if item.lower() in lower}
    people.update(item.lower() for item in _PERSON_RE.findall(text) if item.lower() not in {"照片", "作品", "拍摄"})
    people.update(
        item.strip().lower() for item in _PERSON_RELATION_RE.findall(text)
        if item.strip().lower() not in _NON_PERSON_TOKENS
    )
    equipment = {item.lower() for item in KNOWN_EQUIPMENT if item.lower() in lower}
    equipment.update(item.lower() for item in _EQUIPMENT_RE.findall(text))
    return {"dates": dates, "locations": locations, "people": people, "equipment": equipment}


def validate_facts(result: dict[str, Any], payload: dict[str, Any]) -> tuple[bool, str]:
    """检查结果中的日期、地点、人名和器材是否在输入事实中出现。"""
    source = _fact_candidates(_source_text(_normalize_payload(payload)))
    generated_text = " ".join([_text(result.get("intro", "")), *[_text(x) for x in result.get("titles", [])], *[_text(x) for x in result.get("tags", [])]])
    generated = _fact_candidates(generated_text)
    for category in ("dates", "locations", "people", "equipment"):
        unknown = sorted(generated[category] - source[category])
        if unknown:
            return False, f"事实校验拒稿：{category} 未在输入中出现（{', '.join(unknown[:3])}）"
    return True, ""


def _validate_schema(result: Any) -> tuple[bool, str]:
    if not isinstance(result, dict):
        return False, "结果不是 JSON 对象"
    titles = result.get("titles")
    intro = result.get("intro")
    tags = result.get("tags")
    if not isinstance(titles, list) or len(titles) != 3 or any(not isinstance(x, str) or not x.strip() or len(x.strip()) > 12 for x in titles):
        return False, "titles 必须正好 3 条且每条不超过 12 字"
    if not isinstance(intro, str) or not intro.strip() or len(intro.strip()) > 60:
        return False, "intro 必须是非空字符串且不超过 60 字"
    if not isinstance(tags, list) or len(tags) != 5 or any(not isinstance(x, str) or not x.strip() for x in tags):
        return False, "tags 必须正好 5 条非空标签"
    return True, ""


def _sanitize_result(result: dict[str, Any]) -> dict[str, Any]:
    """输出侧安全：标题、简介和标签统一过滤联系方式/外链。"""
    from .safety import sanitize_output

    intro = sanitize_output(_text(result.get("intro", "")))
    result["intro"] = intro["text"]
    title_results = [sanitize_output(_text(item)) for item in result.get("titles", [])]
    tag_results = [sanitize_output(_text(item)) for item in result.get("tags", [])]
    result["titles"] = [item["text"] for item in title_results]
    result["tags"] = [item["text"] for item in tag_results]
    if intro["filtered"] or any(item["filtered"] for item in [*title_results, *tag_results]):
        result["note"] = (result.get("note") or "") + "（输出已过滤联系方式）"
    return result


def _parse_content(content: Any) -> dict[str, Any]:
    if isinstance(content, list):
        content = "".join(_text(part.get("text", "") if isinstance(part, dict) else part) for part in content)
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        raise LLMCallFailure("invalid_content", "模型 content 不是字符串")
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMCallFailure("invalid_json", f"模型输出不是合法 JSON：{exc.msg}") from exc
    if not isinstance(parsed, dict):
        raise LLMCallFailure("invalid_json", "模型输出不是 JSON 对象")
    return parsed


def _extract_response(data: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    try:
        choice = data["choices"][0]
        message = choice.get("message", {})
        content = message.get("content", "")
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMCallFailure("invalid_response", "模型响应缺少 choices[0].message.content") from exc
    parsed = _parse_content(content)
    usage_raw = data.get("usage") or {}
    usage = {key: int(usage_raw.get(key, 0) or 0) for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    return parsed, usage


def _build_request(payload: dict[str, Any], stream: bool) -> urllib.request.Request:
    cfg = _config()
    body: dict[str, Any] = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(_normalize_payload(payload), ensure_ascii=False)},
        ],
        "temperature": 0.7,
        "max_tokens": 400,
        "response_format": {"type": "json_object"},
    }
    if stream:
        body["stream"] = True
        body["stream_options"] = {"include_usage": True}
    return urllib.request.Request(
        f"{cfg['base']}/chat/completions", data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {cfg['key']}"}, method="POST",
    )


def _read_error(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="replace")[:500]
    except Exception:
        body = ""
    return body or str(exc.reason or "HTTP error")


def _request_once(payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    cfg = _config()
    try:
        with urllib.request.urlopen(_build_request(payload, stream=False), timeout=cfg["timeout"]) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise LLMCallFailure(f"http_{exc.code}", _read_error(exc), exc.code) from exc
    except urllib.error.URLError as exc:
        raise LLMCallFailure("network_error", str(exc.reason)) from exc
    except TimeoutError as exc:
        raise LLMCallFailure("timeout", "LLM 请求超时") from exc
    except json.JSONDecodeError as exc:
        raise LLMCallFailure("invalid_response", "LLM 响应不是 JSON") from exc
    return _extract_response(data)


def _validate_result(result: dict[str, Any], payload: dict[str, Any]) -> tuple[bool, str]:
    ok, reason = _validate_schema(result)
    if not ok:
        return ok, reason
    return validate_facts(result, payload)


def _record_metric(event: dict[str, Any]) -> None:
    with _METRICS_LOCK:
        _METRICS.append(dict(event))
        del _METRICS[:-_MAX_METRICS]
    logger.info("copywrite_call %s", json.dumps(event, ensure_ascii=False, sort_keys=True))


def copywriter_metrics() -> dict[str, Any]:
    with _METRICS_LOCK:
        values = list(_METRICS)
    latencies = sorted(float(item.get("latencyMs", 0)) for item in values)
    tokens = sorted(int((item.get("usage") or {}).get("total_tokens", 0) or 0) for item in values)

    def percentile(values: list[float], p: float) -> float:
        if not values:
            return 0.0
        index = min(len(values) - 1, max(0, int((len(values) - 1) * p)))
        return round(values[index], 1)

    return {
        "count": len(values), "p50Ms": percentile(latencies, 0.50), "p95Ms": percentile(latencies, 0.95),
        "p50Tokens": int(percentile([float(value) for value in tokens], 0.50)),
        "p95Tokens": int(percentile([float(value) for value in tokens], 0.95)),
        "totalTokens": sum(tokens),
        "llmCount": sum(item.get("mode") == "llm" for item in values),
        "ruleCount": sum(item.get("mode") == "rule" for item in values),
        "last": values[-1] if values else None,
    }


def _call_llm_detailed(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    cfg = _config()
    if not cfg["key"]:
        return None, {"errorCode": "missing_api_key", "attempts": 0, "usage": {}}
    last: LLMCallFailure | None = None
    for attempt in range(cfg["retries"] + 1):
        try:
            parsed, usage = _request_once(payload)
            ok, reason = _validate_result(parsed, payload)
            if not ok:
                raise LLMCallFailure("validation_failed", reason)
            result = {"mode": "llm", "titles": [x.strip() for x in parsed["titles"]], "intro": parsed["intro"].strip(),
                      "tags": [x.strip() for x in parsed["tags"]], "note": "", "promptVersion": PROMPT_VERSION}
            result = _sanitize_result(result)
            ok, reason = _validate_schema(result)
            if not ok:
                raise LLMCallFailure("validation_failed", reason)
            return result, {"attempts": attempt + 1, "usage": usage}
        except LLMCallFailure as exc:
            last = exc
            logger.warning("copywrite_attempt_failed attempt=%s/%s code=%s message=%s", attempt + 1, cfg["retries"] + 1, exc.code, exc)
    return None, {"errorCode": last.code if last else "unknown", "errorMessage": str(last) if last else "", "status": last.status if last else None, "attempts": cfg["retries"] + 1, "usage": {}}


def _call_llm(payload: dict[str, Any]) -> dict[str, Any] | None:
    """兼容旧调用方的单结果接口；失败返回 None。"""
    return _call_llm_detailed(payload)[0]


def generate_copy(payload: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    payload = _normalize_payload(payload)
    result, meta = _call_llm_detailed(payload)
    if result is None:
        reason = "未配置 LLM，使用模板兜底" if not llm_configured() else "LLM 调用失败，已退回模板兜底"
        if meta.get("errorCode") and meta["errorCode"] != "missing_api_key":
            reason += f"（{meta['errorCode']}）"
        result = _sanitize_result(_rule_fallback(payload, reason))
        mode = "rule"
    else:
        mode = "llm"
    latency = round((time.perf_counter() - started) * 1000, 1)
    usage = meta.get("usage") or {}
    result.update({"model": _config()["model"] if mode == "llm" else None, "latencyMs": latency,
                   "usage": usage, "tokenUsage": int(usage.get("total_tokens", 0) or 0),
                   "attempts": meta.get("attempts", 0), "promptVersion": PROMPT_VERSION,
                   "degraded": mode == "rule", "errorCode": meta.get("errorCode", "")})
    _record_metric({"mode": mode, "model": result.get("model"), "latencyMs": latency, "usage": usage,
                    "attempts": meta.get("attempts", 0), "errorCode": meta.get("errorCode", ""),
                    "promptVersion": PROMPT_VERSION})
    return result


def _iter_upstream_stream(payload: dict[str, Any]) -> tuple[Iterator[str], dict[str, Any]]:
    """返回上游 SSE 的增量迭代器和可写入的 usage 容器。"""
    cfg = _config()
    try:
        response = urllib.request.urlopen(_build_request(payload, stream=True), timeout=cfg["timeout"])
    except urllib.error.HTTPError as exc:
        raise LLMCallFailure(f"http_{exc.code}", _read_error(exc), exc.code) from exc
    except urllib.error.URLError as exc:
        raise LLMCallFailure("network_error", str(exc.reason)) from exc
    except TimeoutError as exc:
        raise LLMCallFailure("timeout", "LLM 请求超时") from exc
    usage: dict[str, Any] = {}

    def iterator() -> Iterator[str]:
        try:
            for raw in response:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                value = line[5:].strip()
                if value == "[DONE]":
                    continue
                try:
                    chunk = json.loads(value)
                except json.JSONDecodeError:
                    continue
                usage_raw = chunk.get("usage") or {}
                if usage_raw:
                    usage.update({key: int(usage_raw.get(key, 0) or 0) for key in ("prompt_tokens", "completion_tokens", "total_tokens")})
                for choice in chunk.get("choices", []):
                    delta = choice.get("delta") or {}
                    text = delta.get("content")
                    if text:
                        yield str(text)
        except urllib.error.URLError as exc:
            raise LLMCallFailure("network_error", str(exc.reason)) from exc
        except TimeoutError as exc:
            raise LLMCallFailure("timeout", "LLM 请求超时") from exc
        finally:
            response.close()
    return iterator(), usage


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _partial_intro(raw: str) -> str:
    """Extract the currently available intro from a streamed JSON object.

    The upstream model streams JSON tokens, so sending the raw object to the
    browser would make the user watch braces and field names.  This helper
    exposes only the intro characters that are already complete.  If the
    model has not reached ``intro`` yet, it returns an empty string.
    """
    match = re.search(r'"intro"\s*:\s*"((?:\\.|[^"\\])*)', raw, flags=re.DOTALL)
    if not match:
        return ""
    try:
        return json.loads('"' + match.group(1) + '"')
    except json.JSONDecodeError:
        return ""


def stream_copy(payload: dict[str, Any]) -> Iterator[str]:
    """生成前端可消费的 SSE：meta → delta* → result → done。"""
    payload = _normalize_payload(payload)
    started = time.perf_counter()
    cfg = _config()
    yield _sse("meta", {"mode": "llm" if cfg["key"] else "rule", "model": cfg["model"], "promptVersion": PROMPT_VERSION})
    if not cfg["key"]:
        result = _sanitize_result(_rule_fallback(payload))
        for index, char in enumerate(result["intro"]):
            yield _sse("delta", {"field": "intro", "text": char, "index": index})
        latency = round((time.perf_counter() - started) * 1000, 1)
        result.update({"latencyMs": latency, "model": None, "usage": {}, "tokenUsage": 0, "attempts": 0,
                       "promptVersion": PROMPT_VERSION, "degraded": True, "errorCode": "missing_api_key"})
        yield _sse("result", result)
        yield _sse("done", {"ok": True, "mode": "rule", "latencyMs": latency})
        _record_metric({"mode": "rule", "model": None, "latencyMs": latency, "usage": {}, "attempts": 0, "errorCode": "missing_api_key", "promptVersion": PROMPT_VERSION})
        return

    last: LLMCallFailure | None = None
    attempts = 0
    for attempt in range(cfg["retries"] + 1):
        attempts = attempt + 1
        try:
            chunks, usage = _iter_upstream_stream(payload)
            raw = ""
            streamed_intro = ""
            for chunk in chunks:
                raw += chunk
                current_intro = _partial_intro(raw)
                if len(current_intro) > len(streamed_intro):
                    delta = current_intro[len(streamed_intro):]
                    streamed_intro = current_intro
                    yield _sse("delta", {"field": "intro", "text": delta})
            parsed = _parse_content(raw)
            ok, reason = _validate_result(parsed, payload)
            if not ok:
                raise LLMCallFailure("validation_failed", reason)
            result = _sanitize_result({"mode": "llm", "titles": [x.strip() for x in parsed["titles"]], "intro": parsed["intro"].strip(),
                                       "tags": [x.strip() for x in parsed["tags"]], "note": "", "promptVersion": PROMPT_VERSION})
            ok, reason = _validate_schema(result)
            if not ok:
                raise LLMCallFailure("validation_failed", reason)
            latency = round((time.perf_counter() - started) * 1000, 1)
            result.update({"latencyMs": latency, "model": cfg["model"], "usage": usage,
                           "tokenUsage": int(usage.get("total_tokens", 0) or 0), "attempts": attempts,
                           "promptVersion": PROMPT_VERSION, "degraded": False, "errorCode": ""})
            yield _sse("result", result)
            yield _sse("done", {"ok": True, "mode": "llm", "latencyMs": latency})
            _record_metric({"mode": "llm", "model": cfg["model"], "latencyMs": latency, "usage": usage, "attempts": attempts, "errorCode": "", "promptVersion": PROMPT_VERSION})
            return
        except LLMCallFailure as exc:
            last = exc
            logger.warning("copywrite_stream_attempt_failed attempt=%s/%s code=%s message=%s", attempts, cfg["retries"] + 1, exc.code, exc)
            if attempt < cfg["retries"]:
                # The browser must discard the partial JSON/intro before the
                # next retry starts, otherwise a failed attempt is duplicated.
                yield _sse("reset", {"reason": exc.code, "attempt": attempts})

    reason = f"LLM 调用失败，已退回模板兜底（{last.code if last else 'unknown'}）"
    result = _sanitize_result(_rule_fallback(payload, reason))
    latency = round((time.perf_counter() - started) * 1000, 1)
    result.update({"latencyMs": latency, "model": cfg["model"], "usage": {}, "tokenUsage": 0, "attempts": attempts,
                   "promptVersion": PROMPT_VERSION, "degraded": True, "errorCode": last.code if last else "unknown"})
    yield _sse("fallback", {"reason": reason, "mode": "rule"})
    yield _sse("result", result)
    yield _sse("done", {"ok": True, "mode": "rule", "latencyMs": latency, "errorCode": last.code if last else "unknown"})
    _record_metric({"mode": "rule", "model": cfg["model"], "latencyMs": latency, "usage": {}, "attempts": attempts, "errorCode": last.code if last else "unknown", "promptVersion": PROMPT_VERSION})
