"""撮合 Agent：一句话需求 → 解析 → 调工具（向量检索 / 查档期）→ 候选摄影师 + 理由 + 开场话术。

设计取舍（也都是答辩要讲的）：
1. **真调工具**，不是「让模型编一段推荐」。每个工具都返回可核对的数据，toolTrace 原样回传。
2. 检索走 CLIP 跨模态：文本查询 → 作品图向量。中文必须先翻成英文提示词，
   因为底座是 ViT-B/32（英文语料），中文 query 会退化成噪声。
3. **不编造价格**：mock 数据里没有每位摄影师的报价字段，所以 Agent 明确说「未标注报价，
   建议开场直接问」，而不是猜一个区间（C2 不杜撰）。
4. LLM 只负责把结构化结果润成一句开场话术；没配 key 就退回模板，功能不降级成「不可用」。
"""
from __future__ import annotations

import json
import os
import re
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .safety import check_input, sanitize_output

MODEL_DIR = Path(os.environ.get("MODEL_DIR", "models"))
INDEX_PATH = MODEL_DIR / "works.embed.npz"
MANIFEST_PATH = MODEL_DIR / "works.manifest.json"

CITY_NAMES = ["西安", "成都", "青岛", "北京", "上海", "南京", "杭州", "广州", "深圳", "重庆", "武汉"]

# 中文风格词 → CLIP 英文提示词。表里没有的词不会假装认识，只按原样拼进去。
STYLE_PROMPTS: dict[str, str] = {
    "港风": "Hong Kong retro street photography, neon signs, cinematic",
    "复古": "vintage retro film photography, faded warm colors",
    "胶片": "35mm film grain, analog photography",
    "日系": "Japanese style airy portrait, soft daylight, low contrast",
    "韩系": "Korean style clean portrait, neutral soft tone",
    "ins风": "Instagram aesthetic minimal photography",
    "清新": "fresh clean bright photography",
    "电影感": "cinematic still frame, dramatic lighting",
    "暗调": "dark moody low key photography",
    "黑白": "black and white monochrome photography",
    "蓝调": "blue hour, cool blue tones",
    "赛博": "cyberpunk neon night city",
    "欧美": "western editorial portrait",
    "夜景": "night scene, city lights, lanterns",
    "古风": "traditional Chinese costume portrait, ancient architecture",
    "汉服": "hanfu traditional Chinese dress portrait",
    "街拍": "street photography, candid moment",
    "人像": "portrait of a person, shallow depth of field",
    "建筑": "architecture photography, geometric lines",
    "旅行": "travel photography, scenic landscape",
    "海边": "seaside beach photography, sea breeze",
    "秋色": "autumn foliage, warm golden leaves",
    "纪实": "documentary photography, candid reality",
    "群像": "group of people, event photography",
    "低饱和": "desaturated muted colors",
    "暖调": "warm tone, golden light",
    "王家卫感": "Wong Kar-wai inspired Hong Kong cinematic street photography, saturated color, motion blur",
    "情侣": "couple portrait photography, natural interaction",
    "毕业照": "graduation portrait photography, candid campus story",
    "婚礼": "wedding documentary photography, emotional candid moments",
    "旅拍": "travel portrait photography, location story",
}

# 口语化表达 → 规范化标签。原句仍保存在 slots.raw，避免把推断伪装成原始数据。
STYLE_ALIASES: dict[str, tuple[str, ...]] = {
    "王家卫": ("王家卫感", "港风", "电影感"),
    "王家卫那种": ("王家卫感", "港风", "电影感"),
    "港片感": ("港风", "电影感"),
    "港片": ("港风",),
    "电影感": ("电影感",),
    "像电影": ("电影感",),
    "胶片感": ("胶片",),
    "复古感": ("复古",),
    "氛围感": ("电影感",),
    "清冷": ("蓝调", "低饱和"),
    "松弛感": ("日系",),
    "大片感": ("电影感",),
    "旅拍": ("旅行",),
}

THEME_KEYWORDS = (
    "团队形象照", "团建合影", "朋友合照", "情侣写真", "个人写真", "婚纱照", "毕业照", "毕业", "婚礼", "求婚", "情侣", "约会", "闺蜜", "旅拍", "旅行", "汉服",
    "亲子", "宠物", "活动", "产品", "美食", "生日", "写真", "肖像", "街拍",
)

# 未知词不会被当成已知标签吞掉。这里只过滤结构词；用户真正描述的
# 题材/风格词会原样进入 slots.unknownTerms，前端和检索解释都能看到。
_QUERY_STOPWORDS = {
    "我", "想", "要", "想要", "想拍", "请", "帮我", "帮忙", "找", "拍", "拍摄", "摄影",
    "照片", "图片", "一张", "一组", "风格", "感觉", "那种", "适合", "附近", "附近的",
    "在", "去", "来", "和", "与", "以及", "的", "人", "位", "个", "预算", "元", "块",
    "以内", "以下", "不超过", "左右", "上下", "出头", "周末", "本周末", "这周末",
}

_PLANNER_METRICS: dict[str, dict[str, Any]] = {
    "llm": {"calls": 0, "successes": 0, "latencies": []},
    "rule": {"calls": 0, "successes": 0, "latencies": []},
}

_RUNTIME: dict[str, Any] = {"manifest": None, "index": None, "error": ""}


def get_runtime() -> dict[str, Any]:
    if _RUNTIME["manifest"] is not None or _RUNTIME["error"]:
        return _RUNTIME
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        works: dict[str, dict] = {}
        for key in ("works", "spiralWorks"):
            for item in data.get(key, []):
                works.setdefault(item["id"], item)
        by_photographer: dict[str, list[dict]] = {}
        for item in works.values():
            by_photographer.setdefault(item.get("photographerId", ""), []).append(item)
        photographers = {item["id"]: item for item in data.get("photographers", [])}
        _RUNTIME["manifest"] = {
            "works": works,
            "byPhotographer": by_photographer,
            "photographers": photographers,
        }
        if INDEX_PATH.exists():
            from .retrieval import WorkIndex

            _RUNTIME["index"] = WorkIndex(INDEX_PATH)
        else:
            _RUNTIME["error"] = f"缺索引 {INDEX_PATH.name}，先跑 tools/build_works_index.py"
    except Exception as exc:  # noqa: BLE001  加载失败要把原因带出去，不能静默
        _RUNTIME["error"] = f"{type(exc).__name__}: {exc}"
    return _RUNTIME


def _unknown_query_terms(text: str, styles: list[str], theme: str, city: str, when: str) -> list[str]:
    """从原句提取未被映射表覆盖的描述，绝不静默丢词。"""
    known = set(STYLE_PROMPTS) | set(STYLE_ALIASES) | set(THEME_KEYWORDS) | set(CITY_NAMES)
    known.update({when} if when else set())
    # Longest first prevents replacing「个人写真」后又留下「写真」碎片。
    tail = text
    for phrase in sorted((item for item in known if item), key=len, reverse=True):
        tail = tail.replace(phrase, " ")
    tail = re.sub(r"预算?\s*[0-9]{2,5}", " ", tail)
    tail = re.sub(r"[0-9]{2,5}\s*(?:元|块|以内|以下|不超过|左右|上下|出头)?", " ", tail)
    tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z][A-Za-z0-9_-]{1,}", tail)
    out: list[str] = []
    for token in tokens:
        for stopword in sorted(_QUERY_STOPWORDS, key=len, reverse=True):
            token = token.replace(stopword, "")
        if len(token) < 2:
            continue
        if token in _QUERY_STOPWORDS or token in out:
            continue
        out.append(token)
    return out


def parse_request(text: str) -> dict[str, Any]:
    """把中文一句话拆成槽位。规则明确可核对，不用模型也能跑。"""
    city = next((c for c in CITY_NAMES if c in text), "")
    # 预算支持单值、区间、上下限和口语化「左右」。budget 保留单值兼容字段，
    # 精确区间放在 budgetRange，避免把范围压成一个伪精确报价。
    budget_range: dict[str, Any] = {}
    budget = 0
    budget_provided = False
    range_match = re.search(
        r"(?:预算\s*)?(\d{2,5})\s*(?:-|—|~|～|到|至)\s*(\d{2,5})\s*(?:元|块)?",
        text,
    )
    if range_match:
        low, high = sorted((int(range_match.group(1)), int(range_match.group(2))))
        budget = low
        budget_provided = True
        budget_range = {"min": low, "max": high, "label": f"预算 {low}–{high} 元", "source": "用户输入"}
    else:
        within = re.search(r"(?:预算\s*)?(\d{2,5})\s*(?:元|块)?\s*(?:以内|以下|不超过)", text)
        approx = re.search(r"(?:预算\s*)?(\d{2,5})\s*(?:元|块)?\s*(?:左右|上下|出头)", text)
        single = (
            re.search(r"预算\s*(\d{2,5})", text)
            or re.search(r"(\d{2,5})\s*(?:元|块)", text)
            # 口语里常省略“预算/元”（例如“北京周末 900，2 人”）；
            # 只在数字后紧跟标点或句末时接受，避免把人数/年份误当预算。
            or re.search(r"(?<![\d])([1-9]\d{2,4})(?=\s*(?:，|,|；|;|$))", text)
        )
        if within:
            high = int(within.group(1))
            budget = high
            budget_provided = True
            budget_range = {"min": 0, "max": high, "label": f"预算 {high} 元以内", "source": "用户输入"}
        elif approx:
            center = int(approx.group(1))
            low, high = round(center * 0.8), round(center * 1.2)
            budget = center
            budget_provided = True
            budget_range = {"min": low, "max": high, "label": f"预算约 {center} 元（参考 {low}–{high}）", "source": "用户输入口语化范围"}
        elif single:
            budget = int(single.group(1))
            budget_provided = True
            budget_range = {"min": budget, "max": budget, "label": f"预算 {budget} 元", "source": "用户输入"}

    when = ""
    time_aliases = (
        ("下个礼拜天", "下周日"), ("下个星期天", "下周日"),
        ("下周六", "下周六"), ("下星期六", "下周六"), ("下礼拜六", "下周六"),
        ("下周日", "下周日"),
        ("下周末", "下周末"), ("这周末", "这周末"), ("本周末", "本周末"),
        ("月底", "月底"), ("月末", "月底"), ("国庆", "国庆"), ("周末", "周末"),
        ("周六", "周六"), ("星期六", "周六"), ("礼拜六", "周六"),
        ("周日", "周日"), ("星期天", "周日"), ("星期日", "周日"), ("礼拜天", "周日"),
        ("明天", "明天"), ("后天", "后天"), ("下周", "下周"),
    )
    for token, normalized in time_aliases:
        if token in text:
            when = normalized
            break

    styles: list[str] = []
    for style in STYLE_PROMPTS:
        if style in text and style not in styles:
            styles.append(style)
    for phrase, aliases in sorted(STYLE_ALIASES.items(), key=lambda item: -len(item[0])):
        if phrase in text:
            for style in aliases:
                if style not in styles:
                    styles.append(style)

    people = 0
    people_match = re.search(r"(?<!\d)(\d{1,2})\s*(?:人|位|个(?:人)?)", text)
    if people_match:
        people = int(people_match.group(1))
    else:
        chinese_people = {
            "一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5,
            "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
        }
        chinese_match = re.search(r"([一两二三四五六七八九十])\s*(?:人|位|个(?:人)?)", text)
        if chinese_match:
            people = chinese_people[chinese_match.group(1)]
    if people == 0 and "情侣" in text:
        people = 2
    elif people == 0 and ("一家" in text or "全家" in text):
        people = 3

    theme = next((keyword for keyword in sorted(THEME_KEYWORDS, key=len, reverse=True) if keyword in text), "")
    unknown_terms = _unknown_query_terms(text, styles, theme, city, when)
    return {
        "city": city,
        "budget": budget,
        "budgetRange": budget_range,
        "budgetProvided": budget_provided,
        "when": when,
        "styles": styles,
        "unknownTerms": unknown_terms,
        "people": people,
        "theme": theme,
        "raw": text,
    }


def _extract_json_object(raw: str) -> dict[str, Any] | None:
    """Extract the first JSON object from a model response, including fenced JSON."""
    value = raw.strip()
    if value.startswith("```"):
        value = re.sub(r"^```(?:json)?\s*|\s*```$", "", value, flags=re.I | re.S).strip()
    try:
        data = json.loads(value)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", value, flags=re.S)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
            return data if isinstance(data, dict) else None
        except json.JSONDecodeError:
            return None


ALLOWED_PLAN_TOOLS = {"parse_request", "search_works", "check_slot", "estimate_price", "llm_open_line"}


def _rule_plan() -> dict[str, Any]:
    return {
        "steps": [
            {"tool": "parse_request", "args": {}},
            {"tool": "search_works", "args": {}},
            {"tool": "check_slot", "args": {}},
            {"tool": "estimate_price", "args": {}},
            {"tool": "llm_open_line", "args": {}},
        ],
        "source": "rule",
    }


def _llm_plan(text: str) -> tuple[dict[str, Any] | None, str | None, float]:
    """Ask an OpenAI-compatible endpoint for a JSON tool plan; never expose user text to LLM on safety failure."""
    key = os.environ.get("LLM_API_KEY", "").strip()
    if not key:
        return None, "LLM_API_KEY 未配置，LLM 规划器在无 key 时不可验证", 0.0
    started = time.perf_counter()
    base = os.environ.get("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "qwen-plus")
    system = (
        "你是撮合 Agent 的规划器。只输出 JSON，不要 markdown。格式："
        '{"steps":[{"tool":"parse_request|search_works|check_slot|estimate_price|llm_open_line","args":{}}]}. '
        "只能选择这些工具；不写推荐结论、不填价格、不编造档期。"
    )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
        ],
        "temperature": 0,
        "max_tokens": 300,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        plan = _extract_json_object(content if isinstance(content, str) else json.dumps(content, ensure_ascii=False))
        steps = plan.get("steps") if isinstance(plan, dict) else None
        if not isinstance(steps, list) or not steps:
            raise ValueError("planner steps 为空")
        clean_steps = []
        for item in steps:
            if not isinstance(item, dict) or item.get("tool") not in ALLOWED_PLAN_TOOLS:
                raise ValueError("planner 返回了未允许的工具")
            clean_steps.append({"tool": item["tool"], "args": item.get("args") if isinstance(item.get("args"), dict) else {}})
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        return {"steps": clean_steps, "source": "llm"}, None, elapsed
    except (urllib.error.URLError, KeyError, IndexError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        elapsed = round((time.perf_counter() - started) * 1000, 1)
        return None, f"LLM planner failed: {type(exc).__name__}", elapsed


def _record_planner(mode: str, success: bool | None, latency_ms: float) -> dict[str, Any]:
    stats = _PLANNER_METRICS[mode]
    stats["calls"] += 1
    if success:
        stats["successes"] += 1
    stats["latencies"].append(float(latency_ms))
    stats["latencies"] = stats["latencies"][-200:]
    return {
        "mode": mode,
        "latencyMs": round(latency_ms, 1),
        "success": success,
        "calls": stats["calls"],
        "successRate": round(stats["successes"] / stats["calls"] * 100, 1) if stats["calls"] else 0,
        "p50Ms": round(statistics.median(stats["latencies"]), 1) if stats["latencies"] else 0,
    }


def build_query(slots: dict[str, Any]) -> str:
    parts = [STYLE_PROMPTS[s] for s in slots["styles"] if s in STYLE_PROMPTS]
    if slots.get("theme") and slots["theme"] in STYLE_PROMPTS:
        parts.append(STYLE_PROMPTS[slots["theme"]])
    if not parts:
        # 没命中词表时也不把中文原句直接喂给英文 CLIP；未知词会在
        # slots.unknownTerms/queryContext 中原样保留，向量路退回中性的英文域提示。
        parts = ["photography, visual style matching"]
    if slots["city"]:
        parts.append(f"shot in {slots['city']}")
    return ". ".join(parts)


def _date_matches(shoot_date: str, when: str) -> bool:
    """Conservative date filter over the human-readable availability strings in the manifest."""
    if not when:
        return True
    value = shoot_date or ""
    if not value or value.startswith("作品集"):
        return False
    if when in {"周六", "周日"}:
        return when in value
    if when in {"下周日", "下周末", "下周"}:
        return "下周" in value or (when == "下周末" and "周末" in value)
    if when in {"这周末", "本周末", "周末"}:
        return "周末" in value or "本周" in value or "周六" in value or "周日" in value
    if when in {"明天", "后天", "月底", "国庆"}:
        # 公开作品数据没有可核对的具体日期，不能把模糊词硬映射到某个档期。
        return when in value
    return when in value


def _check_slot(
    candidates: list[dict[str, Any]],
    by_photographer: dict[str, list[dict[str, Any]]],
    when: str,
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for candidate in candidates:
        pid = candidate["photographerId"]
        rows = [
            work for work in by_photographer.get(pid, [])
            if work.get("canBook") and _date_matches(work.get("shootDate", ""), when)
        ]
        availability = [str(work.get("shootDate", "")) for work in rows if work.get("shootDate")]
        result.append({
            "photographerId": pid,
            "when": when,
            "available": bool(rows) if when else (True if any(work.get("canBook") for work in by_photographer.get(pid, [])) else None),
            "availability": availability,
            "source": "works.manifest.json",
        })
    return result


_MARKET_CACHE: list[dict[str, Any]] | None = None


def _load_public_market_budgets() -> list[dict[str, Any]]:
    """Read public market post budgets from the checked-in frontend fixture.

    This is reference data only. If the fixture is absent or has no parseable budget,
    estimate_price returns no numbers and asks the user to confirm with the photographer.
    """
    global _MARKET_CACHE
    if _MARKET_CACHE is not None:
        return _MARKET_CACHE
    path = Path(__file__).resolve().parents[2] / "src" / "data" / "mock.ts"
    rows: list[dict[str, Any]] = []
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        _MARKET_CACHE = rows
        return rows
    for match in re.finditer(r"\{\s*id:\s*'post-[^']+'(?P<body>.*?)\}\s*,?", source, flags=re.S):
        body = match.group("body")
        city_match = re.search(r"city:\s*'([^']+)'", body)
        budget_match = re.search(r"budget:\s*'([^']+)'", body)
        if not budget_match:
            continue
        numbers = [int(value) for value in re.findall(r"\d{2,5}", budget_match.group(1))]
        if not numbers:
            continue
        rows.append({"city": city_match.group(1) if city_match else "", "low": min(numbers), "high": max(numbers), "raw": budget_match.group(1)})
    _MARKET_CACHE = rows
    return rows


def estimate_price(slots: dict[str, Any]) -> dict[str, Any]:
    rows = _load_public_market_budgets()
    city = slots.get("city", "")
    city_rows = [row for row in rows if city and row["city"] == city]
    usable = city_rows or rows
    if not usable:
        return {
            "currency": "¥",
            "source": "集市公开需求",
            "note": "当前没有可用的公开预算样本；具体报价与档期需向摄影师确认。",
            "sampleCount": 0,
        }
    low = min(row["low"] for row in usable)
    high = max(row["high"] for row in usable)
    return {
        "low": low,
        "high": high,
        "currency": "¥",
        "source": f"集市公开需求（src/data/mock.ts，{len(usable)} 条{'·同城' if city_rows else ''}）",
        "sampleCount": len(usable),
        "note": "仅作公开需求预算参考，不代表任何摄影师报价；具体价格、服务内容与档期需向对方确认。",
    }


def _reason_for(work: dict[str, Any], hit_score: float, slots: dict[str, Any]) -> str:
    bits = [f"作品《{work.get('title', '')}》向量相似度 {hit_score:.2f}"]
    shared = [s for s in slots["styles"] if s in (work.get("styles") or [])]
    if shared:
        bits.append("标签重合：" + "、".join(shared))
    if slots["city"] and work.get("city") == slots["city"]:
        bits.append(f"同城（{work['city']}）")
    if work.get("canBook"):
        bits.append(f"可约：{work.get('shootDate', '')}")
    return "；".join(bits)


def _llm_open_line(payload: dict[str, Any]) -> str | None:
    """可选：把结构化结果润成开场话术。没配 key 或失败都返回 None，调用方走模板。"""
    key = os.environ.get("LLM_API_KEY", "").strip()
    if not key:
        return None
    base = os.environ.get("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "qwen-plus")
    system = (
        "你是摄影约拍平台的撮合助手。只根据给定数据写一段 60 字以内的开场沟通话术，"
        "语气自然、像人话；不许编造价格、档期、经历或作品信息；数据里没有的就说需要向对方确认。"
    )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        "temperature": 0.4,
        "max_tokens": 300,
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return (data["choices"][0]["message"]["content"] or "").strip() or None
    except (urllib.error.URLError, KeyError, IndexError, TimeoutError, json.JSONDecodeError):
        return None


def run_agent(text: str, top_n: int = 3, state: dict[str, Any] | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    trace: list[dict[str, Any]] = []
    # 安全门永远先于 LLM planner，避免把偷拍/注入内容发送到外部接口。
    guard = check_input(text, semantic_state=state)
    trace.append({"tool": "safety_check", "args": {"chars": len(text)}, "result": guard})
    if not guard["ok"]:
        return {
            "ok": False, "blocked": True, "action": guard["action"], "flags": guard["flags"],
            "error": guard["note"], "slots": None, "candidates": [], "reply": guard["note"],
            "summary": guard["note"], "warnings": [], "missingFields": [], "toolTrace": trace,
            "planner": "rule", "plannerSuccess": None,
            "plannerError": "安全闸门已拦截，未调用 LLM planner",
            "latencyMs": round((time.perf_counter() - started) * 1000, 1),
        }

    rt = get_runtime()
    if rt["error"]:
        return {"ok": False, "error": rt["error"], "toolTrace": trace, "safety": guard}

    planner_started = time.perf_counter()
    llm_plan, planner_error, llm_latency = _llm_plan(text)
    llm_configured = bool(os.environ.get("LLM_API_KEY", "").strip())
    # 记录 LLM 尝试本身，哪怕它失败后回退到规则；无 key 时不把“未尝试”算进分母。
    llm_attempt_stats = _record_planner("llm", bool(llm_plan), llm_latency) if llm_configured else None
    if llm_plan:
        planner = "llm"
        planner_success: bool | None = True
        plan = llm_plan
        planner_latency = llm_latency
    else:
        planner = "rule"
        # 规则计划自身成功完成；如果配置了 key，plannerError 另行说明 LLM 尝试失败。
        planner_success = True
        plan = _rule_plan()
        planner_latency = llm_latency if llm_configured else (time.perf_counter() - planner_started) * 1000
    planner_stats = llm_attempt_stats if planner == "llm" and llm_attempt_stats else _record_planner(planner, planner_success, planner_latency)
    trace.append({
        "tool": "planner",
        "args": {"configured": bool(os.environ.get("LLM_API_KEY"))},
        "result": {"planner": planner, "success": planner_success, "error": planner_error, "plan": plan},
    })

    slots = parse_request(text)
    trace.append({"tool": "parse_request", "args": {"text": text}, "result": slots})
    missing_fields = []
    if not slots.get("city"):
        missing_fields.append("city")
    if not slots.get("budgetProvided"):
        missing_fields.append("budget")

    if missing_fields:
        labels = {"city": "拍摄城市", "budget": "预算"}
        ask = "、".join(labels[field] for field in missing_fields)
        reply = f"为了帮你筛到合适的人，还想确认一下{ask}？补充后我再继续匹配。"
        return {
            "ok": True, "mode": planner, "planner": planner, "plannerLatencyMs": round(planner_latency, 1),
            "plannerSuccess": planner_success, "plannerError": planner_error, "plannerStats": planner_stats,
            "plannerMetrics": {"llm": _record_planner_snapshot("llm"), "rule": _record_planner_snapshot("rule")},
            "safety": guard, "slots": slots, "query": "", "candidates": [], "reply": reply,
            "openingLine": reply, "summary": reply, "warnings": [], "missingFields": missing_fields,
            "communicationPoints": ["先补充城市和预算，再核对日期与档期。"],
            "priceReference": estimate_price(slots), "toolTrace": trace,
            "latencyMs": round((time.perf_counter() - started) * 1000, 1),
        }

    query = build_query(slots)
    hits: list[dict[str, Any]] = []
    index = rt["index"]
    if state and state.get("clip_ok") and index is not None and len(index):
        hits = index.search_text(
            text,
            state,
            k=max(8, top_n * 4),
            query_tags=slots.get("styles", []),
            query_mapping={s: STYLE_PROMPTS[s] for s in slots.get("styles", []) if s in STYLE_PROMPTS},
        )
    trace.append({
        "tool": "search_works", "args": {"query": query, "k": max(8, top_n * 4)},
        "result": {"indexed": len(index) if index is not None else 0, "hitCount": len(hits), "top": hits[:5]},
    })

    works = rt["manifest"]["works"]
    by_photographer = rt["manifest"]["byPhotographer"]
    photographers = rt["manifest"]["photographers"]
    scores: dict[str, dict[str, Any]] = {}
    for hit in hits:
        work = works.get(hit["id"])
        if not work:
            continue
        pid = work.get("photographerId", "")
        entry = scores.setdefault(pid, {"score": 0.0, "vectorScore": 0.0, "works": [], "matchedTags": set()})
        if len(entry["works"]) < 2:
            overlap_tags = set(hit.get("tagOverlap") or [])
            adjusted = float(hit["score"])
            entry["works"].append((work, adjusted, hit))
            entry["score"] += adjusted
            entry["vectorScore"] = max(entry["vectorScore"], float(hit["score"]))
            entry["matchedTags"].update(overlap_tags)

    for pid, entry in scores.items():
        items = entry["works"]
        profile = photographers.get(pid, {})
        all_works = by_photographer.get(pid, [])
        city_hit = any(work.get("city") == slots["city"] for work in all_works) if slots["city"] else False
        if slots["city"] and (profile.get("city") == slots["city"] or city_hit):
            entry["score"] += 0.05
            entry["cityMatch"] = True
        if any(w.get("canBook") for w, _, _ in items):
            entry["score"] += 0.03
            entry["bookable"] = True

    ranked = sorted(scores.items(), key=lambda kv: -kv[1]["score"])
    if slots["city"]:
        ranked = [kv for kv in ranked if kv[1].get("cityMatch")] + [kv for kv in ranked if not kv[1].get("cityMatch")]
    ranked = ranked[:top_n]
    candidates: list[dict[str, Any]] = []
    for pid, entry in ranked:
        profile = photographers.get(pid, {})
        items = entry["works"]
        top_work, top_score, top_hit = items[0]
        candidates.append({
            "photographerId": pid,
            "name": profile.get("name") or top_work.get("photographerName", ""),
            "city": profile.get("city") or top_work.get("city", ""),
            "tags": profile.get("tags", []),
            "nextSlot": profile.get("nextSlot", ""),
            "responseTime": profile.get("responseTime", ""),
            "verified": bool(profile.get("verified")),
            "crossCity": bool(slots["city"]) and not entry.get("cityMatch"),
            "matchedCity": slots["city"] if entry.get("cityMatch") else "",
            "score": round(entry["score"], 4),
            "vectorScore": round(entry["vectorScore"], 4),
            "matchedTags": sorted(entry["matchedTags"]),
            "tagOverlap": len(entry["matchedTags"]),
            "works": [
                {
                    "id": w.get("id"), "title": w.get("title", ""), "imageUrl": w.get("imageUrl", ""),
                    "city": w.get("city", ""), "styles": w.get("styles", []), "shootDate": w.get("shootDate", ""),
                    "score": round(s, 4),
                    "reason": _reason_for(w, float(h.get("vectorSimilarity", s)) if isinstance(h, dict) else s, slots),
                    "components": (h.get("components") or {
                        "vectorSimilarity": h.get("vectorSimilarity"),
                        "vectorScore": h.get("vectorScore"),
                        "tagScore": h.get("tagScore"),
                        "colorScore": h.get("colorScore"),
                    }) if isinstance(h, dict) else {},
                    "explanation": h.get("explanation", {}) if isinstance(h, dict) else {},
                }
                for w, s, h in items
            ],
        })

    slot_rows = _check_slot(candidates, by_photographer, slots.get("when", ""))
    slot_by_id = {row["photographerId"]: row for row in slot_rows}
    for candidate in candidates:
        row = slot_by_id.get(candidate["photographerId"], {})
        candidate["availability"] = row.get("availability") or ([candidate["nextSlot"]] if candidate.get("nextSlot") else [])
        candidate["available"] = row.get("available")
    trace.append({"tool": "check_slot", "args": {"photographerIds": [c["photographerId"] for c in candidates], "when": slots.get("when", "")}, "result": slot_rows})
    # 兼容旧 trace 名称，前端/评测可同时核对新旧工具。
    trace.append({"tool": "check_availability", "args": {"photographerIds": [c["photographerId"] for c in candidates]}, "result": slot_rows})

    price_reference = estimate_price(slots)
    trace.append({"tool": "estimate_price", "args": {"city": slots.get("city", "")}, "result": price_reference})
    condition = " · ".join([x for x in [
        slots["city"] or "不限城市", slots["when"] or "时间待定",
        slots["budgetRange"].get("label") if slots.get("budgetRange") else "预算未说",
        "/".join(slots["styles"]) or "风格未指定", f"{slots['people']} 人" if slots.get("people") else "人数待定",
        slots.get("theme") or "主题待定",
    ]])
    rule_line = (
        f"按「{condition}」检索了 {len(index) if index is not None else 0} 张作品，找到 {len(candidates)} 位最接近的摄影师。"
        "报价与最终档期未在作品库中记录，需要向对方确认。"
        if candidates else f"按「{condition}」没有找到足够接近的作品，建议放宽风格或城市。"
    )
    llm_line = _llm_open_line({"condition": condition, "candidates": candidates, "priceReference": price_reference}) if candidates else None
    if llm_line:
        llm_line = sanitize_output(llm_line)["text"]
    trace.append({"tool": "llm_open_line", "args": {"configured": bool(os.environ.get("LLM_API_KEY"))}, "result": {"used": bool(llm_line)}})

    warnings: list[str] = []
    if slots["city"] and candidates and not any(item["matchedCity"] == slots["city"] for item in candidates):
        warnings.append(f"作品库里没有「{slots['city']}」的可检索作品，下面是风格最接近的异地摄影师（已标注 crossCity）")
    if slots["city"] and not candidates:
        warnings.append(f"没有匹配到任何作品，建议去掉「{slots['city']}」这个条件再试")
    if warnings and not llm_line:
        rule_line += "（注意：" + "；".join(warnings) + "）"
    communication_points = [
        "先确认具体日期、时段和拍摄地点；公开作品档期仅供参考。",
        "确认服务时长、成片数量、交付时间，以及是否包含服化/交通等增项。",
        "报价不在作品库中，需向摄影师本人确认，平台不会替任何人承诺价格。",
    ]
    if slots.get("people"):
        communication_points.insert(1, f"本次需求识别为 {slots['people']} 人，沟通时确认是否需要多人引导或分组拍摄。")
    if slots.get("theme"):
        communication_points.insert(1, f"主题识别为「{slots['theme']}」，可让对方先给出场景与参考图建议。")
    opening_line = llm_line or rule_line
    return {
        "ok": True, "mode": "llm+rule" if llm_line else planner, "planner": planner,
        "plannerLatencyMs": round(planner_latency, 1), "plannerSuccess": planner_success,
        "plannerError": planner_error, "plannerStats": planner_stats,
        "plannerMetrics": {"llm": _record_planner_snapshot("llm"), "rule": _record_planner_snapshot("rule")},
        "safety": guard, "slots": slots, "query": query, "candidates": candidates,
        "reply": opening_line, "openingLine": opening_line, "summary": rule_line,
        "warnings": warnings, "missingFields": [], "communicationPoints": communication_points,
        "priceReference": price_reference, "toolTrace": trace,
        "latencyMs": round((time.perf_counter() - started) * 1000, 1),
    }


def _record_planner_snapshot(mode: str) -> dict[str, Any]:
    stats = _PLANNER_METRICS[mode]
    latencies = stats["latencies"]
    return {
        "calls": stats["calls"],
        "successRate": round(stats["successes"] / stats["calls"] * 100, 1) if stats["calls"] else 0,
        "p50Ms": round(statistics.median(latencies), 1) if latencies else 0,
    }
