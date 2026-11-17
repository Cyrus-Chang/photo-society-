"""拍社「约拍对话框」：摄影师口吻的回复生成。

2026-11-16 用户拍板（第七轮交接 §四 P0）：
- 形态：约拍/接拍页上的入口 + AI 智能回复，**要接近人类真实口吻**；
- 模型：复用 8100 这套服务；
- 目录：新增本文件 + 在 serve.py 的 BFF 别名表里加一行。

**这条线故意做成可降级**：
1. `CHAT_MODEL_DIR` 指向的本地学生模型存在且 transformers 装好 → 用模型生成（mode="model"）；
2. 否则用「人设模板 + 槽位」兜底（mode="fallback"），保证演示不断线。

用户在 2026-11-16 已确认：AI 身份是「平台助手帮你想怎么开口」，
**不冒充真人摄影师**（所以前端要标注这是 AI）。
"""
from __future__ import annotations

import os
import random
import re
import time
from typing import Any, Dict, List, Optional

PROMPT_VERSION = "chat-v1"

#: 三组人设。key 与前端约定一致。
PERSONAS: Dict[str, Dict[str, Any]] = {
    "zhaoye": {
        "label": "话少、专业、不推销",
        "voice": "句子短，先给结论再说理由；不夸人，不用感叹号；不会的直说不会。",
        "max_sentences": 3,
    },
    "zhoumo": {
        "label": "话多、爱聊、有点自来熟",
        "voice": "先聊两句废话再进正题；有语气词（嘛/呗/哈哈）；容易跑题但会拉回来。",
        "max_sentences": 4,
    },
    "linchuhe": {
        "label": "谨慎、先问清楚、不急着成交",
        "voice": "先问用途和场景再报价；不确定先说「我看看」；给建议带条件；不追单。",
        "max_sentences": 3,
    },
}

DEFAULT_PERSONA = "zhaoye"

#: 反 AI 味硬规则（同时用于 prompt 和验收）
STYLE_RULES = [
    "不许用「您好！很高兴为您服务」这类客服腔。",
    "最多一个 emoji，且只在轻松语境。",
    "不夸客户（「您的想法很有创意」一律不要）。",
    "允许迟疑：我看看档期 / 应该是可以 / 我记一下。",
    "允许不完整句：先说半句再补一句。",
    "数字给具体值，不说「大约」「若干」。",
    "一次不超过三句，除非在解释复杂的事。",
    "不知道的就说「这个我得确认下」，绝对不编档期和价格。",
]

_INTENT_RULES = [
    ("price", ("多少钱", "价格", "报价", "预算", "收费", "几块", "费用", "¥", "元")),
    ("schedule", ("档期", "有空", "什么时候", "哪天", "几号", "周六", "周日", "周几", "时间", "排期")),
    ("style", ("风格", "感觉", "色调", "胶片", "日系", "复古", "怎么拍", "效果", "参考图", "像谁")),
    ("place", ("在哪", "地点", "位置", "哪里拍", "场地", "小寨", "大雁塔", "市内")),
    ("hello", ("你好", "在吗", "您好", "哈喽", "hi", "hello", "想问下", "想约")),
    ("thanks", ("谢谢", "好的", "可以", "行", "ok", "收到", "麻烦了")),
]


def _detect_intent(text: str) -> str:
    t = text or ""
    for name, keys in _INTENT_RULES:
        if any(k in t for k in keys):
            return name
    return "other"


def _ctx(context: Optional[Dict[str, Any]], key: str, default: str = "") -> str:
    if not context:
        return default
    value = context.get(key)
    if value is None:
        return default
    return str(value)


# 兜底话术：按人设 × 意图。刻意写得不整齐，避免「模板味」。
_FALLBACK: Dict[str, Dict[str, List[str]]] = {
    "zhaoye": {
        "hello": [
            "在的。你说。",
            "在。你想拍什么？",
        ],
        "price": [
            "{price}。含 {count} 张精修，超出的按张加。",
            "一般是 {price}。你要是时间短一点，可以再谈。",
        ],
        "schedule": [
            "{slot}有空。你定哪天，我这边提前一天跟你确认。",
            "这周{slot}可以。具体点几点，我看看光线。",
        ],
        "style": [
            "得看你想要哪种。有参考图发我两张，我照着调。",
            "我偏自然光那一路。硬打光的不太拍。",
        ],
        "place": [
            "{city}这几个点我熟。你说个大概范围，我给你挑位置。",
            "地点你定或者我定都行。我建议避开人多的时候。",
        ],
        "thanks": ["嗯。有变化提前说。", "行。"],
        "other": [
            "这个我得确认下再回你。",
            "你说的我想一下。先问你，几个人拍？",
        ],
    },
    "zhoumo": {
        "hello": [
            "在在在！你说~",
            "在的，刚好在看片。你说吧",
        ],
        "price": [
            "{price}，我一般拍两小时。你要是想多拍会儿也行，反正我都到那儿了，不会另外收哈哈",
            "价格是{price}。含 {count} 张精修，要更多可以加，但别一次太多，挑不完",
        ],
        "schedule": [
            "{slot}我有空！你定哪天，我提前一天跟你对一下天气",
            "这周{slot}可以，下雨的话我们改期，不耽误你",
        ],
        "style": [
            "你喜欢什么感觉呀？我最近拍胶片色比较多，发你两张看看对不对味",
            "看你想要哪种，我这边日系和胶片都拍，不过说实话胶片色我更有把握哈哈",
        ],
        "place": [
            "{city}我最熟的就是那几个老地方，你说范围我给你挑，走两步就有好光",
            "地点你定就行，我早点过去踩一下",
        ],
        "thanks": ["不客气！有啥随时问我", "行~ 那就这么说定了"],
        "other": [
            "诶这个问题问得好，我得想一下再答你哈哈",
            "你说得对，我先确认下档期再回你",
        ],
    },
    "linchuhe": {
        "hello": [
            "在的。可以先说下你想拍什么用途吗？",
            "在。这组照片你打算用在哪？我按用途给不同建议。",
        ],
        "price": [
            "{price}，含 {count} 张精修。不过先问一句，你是自己留着还是发社交媒体？两种我给的方案不太一样。",
            "报价是{price}。如果要更多张可以加，但我不建议一次超过 15 张，挑不完的。",
        ],
        "schedule": [
            "{slot}还有档期。不过我得先知道你大概想拍多久，时间不一样我安排也不一样。",
            "这周{slot}可以。我先记一下，你确定了我再锁档期。",
        ],
        "style": [
            "用途不一样，我给的构图和数量会不太一样。你偏哪种？我这边自然光比硬光稳。",
            "我一般不建议在中午拍，光太硬。如果是傍晚，我可以给你看几张相近的。",
        ],
        "place": [
            "{city}我常去几个地方，但要看你想拍哪种光。你先把想法说一下。",
            "地点我建议避开周末人流，拍照的时候人一多就没法拍。",
        ],
        "thanks": ["好，你考虑完再定也来得及。", "行。有变动提前一天跟我说。"],
        "other": [
            "这个我得看一下再回你，不想给你不确定的答案。",
            "我先问清楚一件事：你几个人拍？这个影响我给的方案。",
        ],
    },
}


# 接拍页专用：用户是「想接这条需求的摄影师」，AI 起草的是回复话题材，
# 不是回答「多少钱」——所以这套模板把预算当成对方的出价来接，而不是报自己的价。
_DRAFT: Dict[str, List[str]] = {
    "zhaoye": [
        "这条我接了。你写的是 {slot}，我这边能到。具体拍多细你定，两小时我按常规节奏排。",
        "可以。{city}这几个点我熟，你说的方向我这周就能拍。先确认一下你几个人、要不要服化？",
    ],
    "zhoumo": [
        "诶这条看着挺合适的！{slot}我应该能到，{city}那边我常去，走两步就有好光。",
        "我接！你这个感觉我最近拍得挺多，要不要我先发两张相近的给你看看对不对味？",
    ],
    "linchuhe": [
        "可以先聊聊。{slot}我还有档期，但想先确认一下：这组你打算拍多久、要不要精修？",
        "这条我感兴趣。不过我不建议一次拍太久，{city}那个点光线窗口不长，两小时比较合适。",
    ],
}


def _fill(template: str, context: Optional[Dict[str, Any]]) -> str:
    price = _ctx(context, "price", "面议")
    slot = _ctx(context, "nextSlot", "这周")
    count = _ctx(context, "count", "8")
    city = _ctx(context, "city", "西安")
    return (
        template.replace("{price}", price)
        .replace("{slot}", slot)
        .replace("{count}", count)
        .replace("{city}", city)
    )


# --- 数字守卫 -------------------------------------------------------------
# 小样本（90/360 条）训出来的学生模型会**编价格和档期**：
# 实测把 ¥280、「下午茶 380、晚餐 480」安到赵野头上，而 context 里根本没有这些数。
# 项目宪法 C2 不许杜撰数字，所以这里做硬拦截：回复里的「¥数字 / 数字+元|块|起|张|人|小时|天|号|点」
# 只要在 context 里找不到出处，整条丢弃，改用模板兜底，并把 mode 标成 "guard"（前端照实标）。
_NUM_UNIT_RE = re.compile(
    r"(¥\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:元|块|起|张|人|小时|天))"
)
_BARE_PRICE_RE = re.compile(r"(?<![\d.])(\d{3,4})(?![\d.])")


def _context_digits(context: Optional[Dict[str, Any]]) -> set:
    digits = set()
    for value in (context or {}).values():
        if value is None:
            continue
        for found in re.findall(r"\d+(?:\.\d+)?", str(value)):
            digits.add(found.lstrip("0") or "0")
    return digits


def _ungrounded_numbers(reply: str, context: Optional[Dict[str, Any]]) -> List[str]:
    allowed = _context_digits(context)
    bad: List[str] = []

    def check(num: str, raw: str) -> None:
        if not num:
            return
        if (num.lstrip("0") or "0") in allowed:
            return
        if raw not in bad:
            bad.append(raw)

    spans = []
    for match in _NUM_UNIT_RE.finditer(reply or ""):
        spans.append(match.span())
        check(match.group(2) or match.group(3) or "", match.group(0).strip())
    # 裸数字：模型也会写成「下午茶 380、晚餐 480」这种不带单位的价格。
    # 只抓 3-4 位（价格量级），四位里的 19xx/20xx 当成年份放过；已被上面带单位命中过的跳过。
    for match in _BARE_PRICE_RE.finditer(reply or ""):
        if any(start <= match.start() and match.end() <= end for start, end in spans):
            continue
        num = match.group(1)
        if len(num) == 4 and num.startswith(("19", "20")):
            continue
        check(num, num)
    return bad


def compose_fallback(message: str, persona: str, context: Optional[Dict[str, Any]],
                     mode: str = "chat") -> str:
    """无人设模型时的兜底：人设 × 意图 的模板，按消息哈希挑一条，同一句话结果稳定。"""
    key = persona if persona in _FALLBACK else DEFAULT_PERSONA
    if mode == "draft":
        pool = _DRAFT.get(key) or _DRAFT[DEFAULT_PERSONA]
        pick = pool[abs(hash(message + key)) % len(pool)]
        return _fill(pick, context)
    intent = _detect_intent(message)
    pool = _FALLBACK[key].get(intent) or _FALLBACK[key]["other"]
    if not message.strip():
        pool = _FALLBACK[key]["hello"]
    pick = pool[abs(hash(message + key + intent)) % len(pool)]
    # 没有价格上下文时，模板里的「{price}」会渲染成「面议」，读起来像机器
    if "{price}" in pick and not _ctx(context, "price", ""):
        return "价格我得确认下再回你。你先把时间和人数说一下。"
    return _fill(pick, context)


# ---------------------------------------------------------------------------
# 模型路径（可选）：本地学生模型 + transformers
# ---------------------------------------------------------------------------
_MODEL_CACHE: Dict[str, Any] = {"pipe": None, "error": "", "tried": False}


def _load_pipe():
    if _MODEL_CACHE["tried"]:
        return _MODEL_CACHE["pipe"]
    _MODEL_CACHE["tried"] = True
    model_dir = os.environ.get("CHAT_MODEL_DIR", "").strip()
    if not model_dir:
        _MODEL_CACHE["error"] = "CHAT_MODEL_DIR 未配置"
        return None
    if not os.path.isdir(model_dir):
        _MODEL_CACHE["error"] = f"模型目录不存在: {model_dir}"
        return None
    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        device = os.environ.get("CHAT_DEVICE", "").strip()
        if not device:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device.startswith("cuda") else torch.float32
        model = AutoModelForCausalLM.from_pretrained(model_dir, dtype=dtype).to(device).eval()
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        _MODEL_CACHE["pipe"] = {"model": model, "tokenizer": tokenizer, "device": device}
        return _MODEL_CACHE["pipe"]
    except Exception as exc:  # noqa: BLE001 - 任何加载失败都要落回兜底
        _MODEL_CACHE["error"] = f"{type(exc).__name__}: {exc}"
        return None


def _system_prompt(persona: str) -> str:
    p = PERSONAS.get(persona) or PERSONAS[DEFAULT_PERSONA]
    rules = "\n".join(f"- {r}" for r in STYLE_RULES)
    return (
        "你是一位在西安/青岛接单的摄影师，正在跟潜在客户聊天。"
        f"\n说话方式：{p['voice']}"
        "\n必须遵守：\n" + rules
        + "\n另外：你是 AI 助手，用户知道这一点，但你要用摄影师的口吻说话，不要自称 AI。"
    )


def compose_model(message: str, persona: str, context: Optional[Dict[str, Any]],
                  history: Optional[List[Dict[str, str]]] = None) -> Optional[str]:
    pipe = _load_pipe()
    if not pipe:
        return None
    try:
        tokenizer = pipe["tokenizer"]
        model = pipe["model"]
        ctx = "、".join(
            f"{k}={v}" for k, v in (context or {}).items() if v
        )
        messages = [{"role": "system", "content": _system_prompt(persona)}]
        if ctx:
            messages.append({"role": "system", "content": f"已知信息：{ctx}"})
        for turn in (history or [])[-6:]:
            role = "assistant" if turn.get("role") == "assistant" else "user"
            content = str(turn.get("content") or "").strip()
            if content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": message})
        prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        ids = tokenizer(prompt, return_tensors="pt").to(pipe["device"])
        out = model.generate(
            **ids,
            max_new_tokens=int(os.environ.get("CHAT_MAX_NEW_TOKENS", "96")),
            do_sample=True,
            temperature=float(os.environ.get("CHAT_TEMPERATURE", "0.8")),
            top_p=0.9,
            repetition_penalty=1.05,
            pad_token_id=tokenizer.eos_token_id,
        )
        text = tokenizer.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        # 截断到最多 4 句，避免模型自说自话写小作文
        parts = [s for s in re.split(r"(?<=[。！？!?\n])", text) if s.strip()]
        text = "".join(parts[:4]).strip()
        return text or None
    except Exception as exc:  # noqa: BLE001
        _MODEL_CACHE["error"] = f"generate: {type(exc).__name__}: {exc}"
        return None


def chat_reply(message: str, persona: str = DEFAULT_PERSONA,
               context: Optional[Dict[str, Any]] = None,
               history: Optional[List[Dict[str, str]]] = None,
               mode: str = "chat") -> Dict[str, Any]:
    """给 serve.py 调用的入口（同步函数，路由层做成 def 即可）。"""
    started = time.perf_counter()
    reply = compose_model(message, persona, context, history)
    mode_out = "model"
    guarded: List[str] = []
    if reply:
        guarded = _ungrounded_numbers(reply, context)
        if guarded:
            reply = None  # 模型编了 context 里没有的数字：整条作废，走模板
    if not reply:
        reply = compose_fallback(message, persona, context, mode)
        mode_out = "guard" if guarded else "fallback"
    return {
        "reply": reply,
        "mode": mode_out,
        "guard": guarded,
        "persona": persona if persona in PERSONAS else DEFAULT_PERSONA,
        "intent": _detect_intent(message),
        "promptVersion": PROMPT_VERSION,
        "modelReady": _MODEL_CACHE["pipe"] is not None,
        "modelError": _MODEL_CACHE["error"],
        "latencyMs": round((time.perf_counter() - started) * 1000, 1),
    }
