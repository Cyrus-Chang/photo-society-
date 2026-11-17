"""模型服务：FastAPI + ONNX Runtime。只做三件事，不碰数据库、不碰业务状态。

    POST /v1/classify   图片 → 类型标签 + 风格标签
    POST /v1/embed      图片 → 512 维向量（复用给 AI-2 的相似作品召回）
    GET  /v1/health     存活与模型版本
    GET  /v1/models     已加载模型的指标与阈值

启动：
    uvicorn pipeline.serve:app --host 0.0.0.0 --port 8100
    # 首次启动会加载 CLIP 视觉塔（约 1~2 秒），并把 models/*.onnx 读进内存。

为什么独立成一个服务，而不是塞进 Spring Boot：
    1) 训练和推理共用同一份 Python 预处理，能彻底避免"训练用 resize+center-crop、
       上线用 letterbox"这种静默的预处理偏移 —— 这是这类项目上线翻车的头号原因。
    2) 换 backbone、重训、灰度都只重启这一个容器，不影响业务主进程。
    3) 代价只是多一个 300MB 的 Python 镜像，对比赛部署完全可接受。
    如果坚持不多一个进程，见 AI-3 文档「6.2 方案 B」：onnxruntime-java + 手写预处理，
    但预处理参数必须严格照抄本文件的 build_inputs()。
"""

from __future__ import annotations

import base64
import io
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

from .cliputil import image_features, text_features
from .colorfeat import FEATURE_NAMES, color_features, open_rgb
from .labels import (
    PERSON_SUBJECT_CODES,
    PUBLIC_SUBJECT_CODES,
    metadata as label_metadata,
    prompt_entries,
)

MODEL_DIR = Path(os.environ.get("MODEL_DIR", "models"))
DICT_PATH = Path(os.environ.get("DICT_PATH", "labels/dictionary.json"))
CLIP_MODEL = os.environ.get("CLIP_MODEL", "openai/clip-vit-base-patch32")
FEATURE_DIM = 512 + 24

# 业务用的置信度下限：低于它直接不返回，宁可空着让人工补
MIN_CONF = float(os.environ.get("MIN_CONF", "0.30"))
# A model probability is useful for ranking, but it should not silently become
# a user-facing assertion.  The review threshold is deliberately independent
# from MIN_CONF (which only controls result truncation).
REVIEW_CONF = float(os.environ.get("REVIEW_CONF", "0.55"))
# Subject output is additionally gated by CLIP evidence that the image is not
# a portrait.  This is a calibration gate, not a new model.
SUBJECT_GATE_CONF = float(os.environ.get("SUBJECT_GATE_CONF", "0.78"))
SUBJECT_PERSON_MASS_MAX = float(os.environ.get("SUBJECT_PERSON_MASS_MAX", "0.45"))

app = FastAPI(title="Photo Classifier", version="1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_state: Dict[str, Any] = {"clip": None, "proc": None, "torch": None,
                           "heads": {}, "booted_at": time.time()}

STYLE_CONFIDENCE_SOURCE = "style_anchor_loo_margin_quartiles"
SUBJECT_CONFIDENCE_SOURCE = "subject_head_probability_plus_person_gate"
TONE_CONFIDENCE_SOURCE = "tone_color_rule_thresholds"


# ---------------------------------------------------------------------------
# 模型加载
# ---------------------------------------------------------------------------
def _load_clip() -> bool:
    try:
        import torch
        from transformers import CLIPModel, CLIPProcessor

        _state["clip"] = CLIPModel.from_pretrained(CLIP_MODEL).eval()
        _state["proc"] = CLIPProcessor.from_pretrained(CLIP_MODEL)
        _state["torch"] = torch
        return True
    except Exception as exc:  # 权重没下、离线环境、torch 没装
        print(f"[warn] CLIP 加载失败，将只提供色彩规则结果: {exc}")
        return False


def _load_anchors() -> None:
    """加载「锚图原型」风格模型（models/style.anchors.npz）。

    和线性头的区别：没有训练权重，13 类各存一个原型向量，推理时算余弦取最近。
    好处是加一张锚图立刻生效、能解释「它跟哪几张参考图最像」；坏处是精度上限低于有标注训练。
    """
    path = MODEL_DIR / "style.anchors.npz"
    if not path.exists():
        return
    z = np.load(path, allow_pickle=True)
    _state["anchors"] = {
        "codes": [str(c) for c in z["codes"]],
        "clip": z["clip"].astype(np.float32),
        "color": z["color"].astype(np.float32),
        "color_mu": z["color_mu"].astype(np.float32),
        "weight": float(z["weight"]),
        "bin_centers": z["bin_centers"].astype(np.float32),
        "bin_accs": z["bin_accs"].astype(np.float32),
    }
    meta_path = MODEL_DIR / "style.anchors.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    _state["anchors_meta"] = meta
    print(f"[ok] style: {len(_state['anchors']['codes'])} 类原型锚图"
          f"（留一法 {meta.get('loo_accuracy', '?')}）")


def classify_anchors(vec: np.ndarray) -> List[Dict[str, Any]]:
    """原型匹配出风格。置信度是「间隔 → 判对概率」的逻辑回归校准，不是 softmax。"""
    a = _state.get("anchors")
    if not a:
        return []
    clip = vec[:512].astype(np.float32)
    color = vec[512:].astype(np.float32)
    cc = color - a["color_mu"]
    n = float(np.linalg.norm(cc)) or 1.0
    score = a["clip"] @ clip + a["weight"] * (a["color"] @ (cc / n))
    order = np.argsort(-score)[:3]
    top = int(order[0])
    # 第一名的置信度：领先亚军的间隔 → 留一法实测分档插值（不是 softmax，也不是逻辑回归）
    margin = float(score[top] - np.delete(score, top).max())
    p_top = float(np.interp(margin, a["bin_centers"], a["bin_accs"]))
    # 二三名：按同一温度归一，保证"第一名 = 校准值"且整体单调递减。
    z = score - score[top]
    target = 1.0 / max(p_top, 1e-6)
    lo, hi = 1e-5, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if float(np.exp(z / mid).sum()) > target:   # 温度太大 → 和过大 → 往小收
            hi = mid
        else:
            lo = mid
    p = np.exp(z / ((lo + hi) / 2))
    p /= p.sum()
    return [
        {
            "code": a["codes"][int(i)],
            "confidence": round(float(p[i]), 4),
            "confidenceSource": STYLE_CONFIDENCE_SOURCE,
            "needsReview": bool(float(p[i]) < REVIEW_CONF),
        }
        for i in order
    ]


def _load_heads() -> None:
    import onnxruntime as ort

    for task in ("subject", "style"):
        onnx_path = MODEL_DIR / f"{task}.onnx"
        if not onnx_path.exists():
            print(f"[warn] 缺 {onnx_path}，{task} 走零样本兜底")
            continue
        sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
        labels: List[str] = []
        multi = task == "subject"   # 默认值；最终以 labels.json 的 multi 为准
        lp = MODEL_DIR / f"{task}.labels.json"
        if lp.exists():
            meta = json.loads(lp.read_text(encoding="utf-8"))
            labels = meta["classes"]
            multi = bool(meta.get("multi", multi))
        thr: Dict[str, float] = {}
        tp = MODEL_DIR / f"{task}.threshold.json"
        if tp.exists():
            thr = json.loads(tp.read_text(encoding="utf-8"))
        metrics_path = MODEL_DIR / f"{task}.metrics.json"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.exists() else {}
        _state["heads"][task] = {
            "session": sess, "labels": labels, "thresholds": thr,
            "version": os.environ.get(f"{task.upper()}_VERSION", metrics.get("version", "local")),
            "metrics": metrics, "multi": multi,
        }
        print(f"[ok] {task}: {len(labels)} 类，输入 {FEATURE_DIM} 维")


@app.on_event("startup")
def _startup() -> None:
    _state["clip_ok"] = _load_clip()
    _state["dict"] = json.loads(DICT_PATH.read_text(encoding="utf-8")) if DICT_PATH.exists() else {}
    try:
        _load_heads()
    except ImportError:
        print("[warn] 未安装 onnxruntime，分类头不可用")
    try:
        _load_anchors()
    except Exception as exc:  # noqa: BLE001  锚图模型坏了不该拖垮整个服务
        print(f"[warn] 风格锚图加载失败，风格走零样本: {exc}")


# ---------------------------------------------------------------------------
# 预处理（与 train.py 严格一致：exif 纠正 → RGB → CLIPProcessor 224 center-crop）
# ---------------------------------------------------------------------------
def build_inputs(img) -> np.ndarray:
    """返回 (536,) float32：前 512 是 L2 归一化的 CLIP 视觉向量，后 24 是色彩特征。"""
    torch = _state["torch"]
    proc = _state["proc"]
    with torch.no_grad():
        inputs = proc(images=[img], return_tensors="pt")
        feat = image_features(_state["clip"], inputs)
        feat = torch.nn.functional.normalize(feat, dim=-1).cpu().numpy()[0]
    color = color_features(img)  # 复用同一张已纠正方向的图，避免二次解码
    vec = np.concatenate([feat, color]).astype(np.float32)
    assert vec.shape == (FEATURE_DIM,), vec.shape
    return vec


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


def derive_tone(color: Dict[str, float]) -> List[Dict[str, Any]]:
    """从 24 维色彩特征直接推「影调属性词」，不训练、零标注。

    为什么单独做这一层：摄影师嘴里说的「暖调/冷调/高饱和/柔和/高调」是**属性**，
    不是风格。把它们塞进风格 softmax 会让 13 个风格类互相打架（同一张图既可能"日系"
    又可能"低饱和"）。用阈值算，既准又能叠加，还不用标注。

    阈值是初始值，跑 50~100 张后按实际分布校准（改这里，不用重训）。
    """
    rules = [
        ("TONE_WARM", color.get("warmth", 0) > 0.035),
        ("TONE_COOL", color.get("warmth", 0) < -0.020),
        ("TONE_HIGH_SAT", color.get("S_mean", 0) > 0.45),
        ("TONE_LOW_SAT", color.get("S_mean", 1) < 0.22),
        ("TONE_HIGH_CONTRAST", color.get("L_range", 0) > 0.72),
        ("TONE_LOW_CONTRAST", color.get("L_range", 1) < 0.45),
        ("TONE_HIGH_KEY", color.get("L_mean", 0) > 0.62),
        ("TONE_LOW_KEY", color.get("L_mean", 1) < 0.28),
        ("TONE_LIFTED_BLACK", color.get("L_p05", 0) > 0.16),
    ]
    return [
        {
            "code": code,
            "source": "RULE",
            "confidenceSource": TONE_CONFIDENCE_SOURCE,
            # A deterministic rule is reviewable by design, but does not have
            # a calibrated probability.  Keep needsReview false here; the UI
            # can explain the source without inventing a percentage.
            "needsReview": False,
        }
        for code, hit in rules if hit
    ]


def _decorate_predictions(items: List[Dict[str, Any]], source: str) -> List[Dict[str, Any]]:
    """Add the same review contract to predictions from every backend path."""

    out: List[Dict[str, Any]] = []
    for item in items:
        row = dict(item)
        row.setdefault("confidenceSource", source)
        if "confidence" in row:
            row.setdefault("needsReview", bool(float(row["confidence"]) < REVIEW_CONF))
        else:
            row.setdefault("needsReview", False)
        out.append(row)
    return out


def classify_heads(vec: np.ndarray) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    x = vec[None, :]
    for task, head in _state["heads"].items():
        logits = head["session"].run(None, {"features": x})[0][0]
        probs = 1 / (1 + np.exp(-logits)) if head["multi"] else _softmax(logits)
        items = []
        for code, p in zip(head["labels"], probs):
            if p < MIN_CONF:
                continue
            items.append({"code": code, "confidence": round(float(p), 4),
                          "aboveThreshold": bool(p >= head["thresholds"].get(code, 0.5)),
                          "confidenceSource": SUBJECT_CONFIDENCE_SOURCE if task == "subject"
                          else "trained_head_probability",
                          "needsReview": bool(float(p) < REVIEW_CONF)})
        items.sort(key=lambda d: -d["confidence"])
        out[task] = items[:5]
    return out


def _zero_shot_ranked(vec: np.ndarray, tag_type: str) -> List[Dict[str, Any]]:
    """Return full zero-shot scores, caching text embeddings per process."""

    if not _state.get("clip_ok"):
        return []
    torch = _state["torch"]
    proc = _state["proc"]
    cache = _state.setdefault("text_cache", {})
    key = str(tag_type).upper()
    usable = list(prompt_entries(_state.get("dict", {}), key))
    if not usable:
        return []
    cached = cache.get(key)
    if cached is None:
        prompts = [g["prompt_en"] for g in usable]
        with torch.no_grad():
            t = proc(text=prompts, return_tensors="pt", padding=True)
            tf = text_features(_state["clip"], t)
            tf = torch.nn.functional.normalize(tf, dim=-1)
        cached = {str(g["code"]): tf[i] for i, g in enumerate(usable)}
        cache[key] = cached
    # ★ 只取前 512 维：后 24 维色彩特征没有文本对应物，拼进去维度就对不上了
    vision = torch.from_numpy(vec[:512])
    with torch.no_grad():
        tf = torch.stack([cached[str(g["code"])] for g in usable])
        cos = (tf @ vision).cpu().numpy()   # 单位向量点积，落在 [-1, 1]
    probs = _softmax(cos * 100.0)       # CLIP 的 logit scale 约为 100
    return [
        {
            "code": str(g["code"]),
            "confidence": round(float(p), 4),
            "confidenceSource": "zero_shot_text_similarity",
            "needsReview": bool(float(p) < REVIEW_CONF),
        }
        for g, p in sorted(zip(usable, probs), key=lambda kv: -kv[1])
    ]


def classify_zero_shot(vec: np.ndarray) -> Dict[str, List[Dict[str, Any]]]:
    """训练样本还不够时的兜底：用字典里的 prompt_en 直接算相似度。"""

    out: Dict[str, List[Dict[str, Any]]] = {}
    for key in ("SUBJECT", "STYLE"):
        rows = _zero_shot_ranked(vec, key)
        if rows:
            out[key.lower()] = rows[:3]
    return out


def gate_subject(vec: np.ndarray, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Suppress subject output when the existing CLIP evidence suggests a person."""

    public = [row for row in candidates if row.get("code") in PUBLIC_SUBJECT_CODES]
    ranked = _zero_shot_ranked(vec, "SUBJECT")
    if not public:
        return {"items": [], "passed": False, "needsReview": True,
                "reason": "no_non_person_candidate", "personProbability": None}
    if not ranked:
        return {"items": [], "passed": False, "needsReview": True,
                "reason": "person_evidence_unavailable", "personProbability": None}
    by_code = {row["code"]: float(row.get("confidence", 0.0)) for row in ranked}
    person_mass = sum(by_code.get(code, 0.0) for code in PERSON_SUBJECT_CODES)
    non_person_mass = sum(by_code.get(code, 0.0) for code in PUBLIC_SUBJECT_CODES)
    top_conf = float(public[0].get("confidence", 0.0))
    passed = (top_conf >= SUBJECT_GATE_CONF
              and person_mass <= SUBJECT_PERSON_MASS_MAX
              and non_person_mass >= person_mass)
    if not passed:
        return {"items": [], "passed": False, "needsReview": True,
                "reason": "person_evidence_or_confidence_below_gate",
                "personProbability": round(person_mass, 4),
                "nonPersonProbability": round(non_person_mass, 4)}
    return {"items": _decorate_predictions(public[:3], SUBJECT_CONFIDENCE_SOURCE),
            "passed": True,
            "needsReview": any(row.get("needsReview") for row in public[:3]),
            "reason": "passed",
            "personProbability": round(person_mass, 4),
            "nonPersonProbability": round(non_person_mass, 4)}


# ---------------------------------------------------------------------------
# 接口
# ---------------------------------------------------------------------------
class B64Request(BaseModel):
    imageBase64: str
    returnColor: bool = True


def _run(img) -> Dict[str, Any]:
    t0 = time.perf_counter()
    vec = build_inputs(img)
    color = {n: round(float(v), 4) for n, v in zip(FEATURE_NAMES, vec[512:])}
    fallback = ""
    result = classify_heads(vec) or {}

    # 风格：优先用锚图原型（比零样本准一倍），没有才走零样本
    style = classify_anchors(vec)
    if style:
        result["style"] = style
    elif not result.get("style"):
        zs = classify_zero_shot(vec)
        result["style"] = zs.get("style", [])
        result.setdefault("subject", zs.get("subject", []))
        fallback = "ZERO_SHOT"
    elif not result.get("subject"):
        zs = classify_zero_shot(vec)
        result["subject"] = zs.get("subject", [])

    style = result.get("style", [])
    subject_raw = list(result.get("subject", []))
    subject_gate = gate_subject(vec, subject_raw)
    result["subject"] = subject_gate["items"]
    anchors = _state.get("anchors") or {}
    bin_centers = anchors.get("bin_centers")
    bin_accs = anchors.get("bin_accs")
    review_reasons: List[str] = []
    if subject_gate.get("needsReview"):
        review_reasons.append(f"subject:{subject_gate.get('reason', 'gate')}")
    if not style:
        review_reasons.append("style:no_calibrated_anchor")
    if any(item.get("needsReview") for item in style):
        review_reasons.append("style:low_confidence")

    return {
        "subject": result.get("subject", []),
        "subjectVisible": result.get("subject", []),
        # Keep the raw model output available for audit/debugging while the
        # public subject list stays safely gated.  The UI should render only
        # `subject` and use `subjectGate` to explain an empty result.
        "subjectRaw": subject_raw,
        "style": result.get("style", []),
        "tone": derive_tone(color),
        "color": color,
        "modelVersion": {k: v["version"] for k, v in _state["heads"].items()},
        "fallback": fallback,
        "confidenceSource": {
            "style": STYLE_CONFIDENCE_SOURCE if style else "zero_shot_text_similarity",
            "subject": SUBJECT_CONFIDENCE_SOURCE,
            "tone": TONE_CONFIDENCE_SOURCE,
        },
        "confidenceCalibration": {
            "style": {
                "method": "leave-one-out margin quartile bins",
                "binCenters": [round(float(v), 6) for v in (bin_centers.tolist() if bin_centers is not None else [])],
                "binAccuracies": [round(float(v), 6) for v in (bin_accs.tolist() if bin_accs is not None else [])],
                "looAccuracy": (_state.get("anchors_meta") or {}).get("loo_accuracy"),
                "reviewThreshold": REVIEW_CONF,
            },
            "subject": {
                "method": "trained head probability plus CLIP portrait mass gate",
                "reviewThreshold": REVIEW_CONF,
                "gateConfidence": SUBJECT_GATE_CONF,
                "maxPortraitProbability": SUBJECT_PERSON_MASS_MAX,
            },
        },
        "needsReview": bool(review_reasons),
        "confidenceThreshold": REVIEW_CONF,
        "reviewReasons": review_reasons,
        "subjectGate": subject_gate,
        "labelDictionary": {
            "schema": (_state.get("dict") or {}).get("_meta", {}).get("schema", "unknown"),
            "layers": label_metadata(_state.get("dict", {})),
        },
        "latencyMs": round((time.perf_counter() - t0) * 1000, 1),
    }


@app.post("/v1/classify")
async def classify(file: Optional[UploadFile] = File(None),
                   imageBase64: Optional[str] = Form(None)) -> Dict[str, Any]:
    if file is not None:
        raw = await file.read()
    elif imageBase64:
        raw = base64.b64decode(imageBase64.split(",")[-1])
    else:
        raise HTTPException(400, "need file or imageBase64")
    if len(raw) > 24 * 1024 * 1024:
        raise HTTPException(413, "image too large")
    try:
        from PIL import Image

        img = open_rgb(Image.open(io.BytesIO(raw)))
    except Exception as exc:
        raise HTTPException(415, f"not a decodable image: {exc}")
    return _run(img)


@app.post("/v1/classify-base64")
def classify_b64(body: B64Request) -> Dict[str, Any]:
    raw = base64.b64decode(body.imageBase64.split(",")[-1])
    from PIL import Image

    return _run(open_rgb(Image.open(io.BytesIO(raw))))


@app.post("/v1/embed")
async def embed(file: UploadFile = File(...)) -> Dict[str, Any]:
    from PIL import Image

    img = open_rgb(Image.open(io.BytesIO(await file.read())))
    vec = build_inputs(img)
    return {"dim": 512, "vector": [round(float(v), 6) for v in vec[:512]]}


@app.get("/v1/health")
def health() -> Dict[str, Any]:
    anchors = _state.get("anchors") or {}
    meta = _state.get("anchors_meta") or {}
    return {
        "status": "ok" if _state.get("clip_ok") else "degraded",
        "clip": _state.get("clip_ok", False),
        "heads": {k: {"classes": len(v["labels"]), "version": v["version"]}
                  for k, v in _state["heads"].items()},
        "styleAnchors": {
            "classes": len(anchors.get("codes", [])),
            "looAccuracy": meta.get("loo_accuracy"),
            "zeroshotSameSet": meta.get("zeroshot_same_set"),
        } if anchors else None,
        "uptimeSec": round(time.time() - _state["booted_at"], 1),
    }


@app.get("/v1/models")
def models() -> Dict[str, Any]:
    return {k: {"version": v["version"], "labels": v["labels"],
                "thresholds": v["thresholds"],
                "macroF1": v["metrics"].get("test", {}).get("macro_f1")}
            for k, v in _state["heads"].items()}


class TextRequest(BaseModel):
    text: str
    k: int = 5
    weights: Optional[Dict[str, float]] = None
    tags: Optional[List[str]] = None
    city: str = ""


@app.post("/v1/search")
def search(body: TextRequest) -> Dict[str, Any]:
    """纯检索：文本 → 作品向量 top-k（RAG 的检索端，单独暴露便于 MCP/评测复用）。"""
    from .agent import get_runtime

    runtime = get_runtime()
    if runtime.get("error"):
        return {"ok": False, "error": runtime["error"]}
    index = runtime.get("index")
    if index is None:
        return {"ok": False, "error": "索引未建立，先跑 tools/build_works_index.py"}
    hits = index.search_text(
        body.text,
        _state,
        k=max(1, min(body.k, 20)),
        weights=body.weights,
        query_tags=body.tags,
    )
    query_context = hits[0].get("explanation", {}).get("queryContext", {}) if hits else {}
    return {
        "ok": True,
        "count": len(hits),
        "indexed": len(index),
        "weights": query_context.get("weights", body.weights or {}),
        "query": query_context,
        "hits": hits,
    }


@app.post("/v1/similar")
async def similar(file: UploadFile = File(...), topK: int = 3) -> Dict[str, Any]:
    """以图搜图：上传一张样片 → 风格 + 最接近的摄影师（样片向量比对）。

    与 /v1/search 共用同一套打分口径（CLIP 0.65 + 标签 0.20 + 色彩 0.15），
    所以 matchPercent 与文本检索的分数可比；图像编码复用 build_inputs，不另起
    一套向量空间，也就不会出现"搜图和搜词各说各话"。
    """
    from PIL import Image

    from .agent import get_runtime
    from .similar import MATCH_SOURCE, rank_photographers

    t0 = time.perf_counter()
    if not _state.get("clip_ok"):
        raise HTTPException(status_code=503, detail="视觉模型未加载（CLIP），以图搜图暂不可用")
    runtime = get_runtime()
    if runtime.get("error"):
        return {"ok": False, "error": runtime["error"], "matches": [], "warnings": ["作品索引不可用"]}
    index = runtime.get("index")
    if index is None:
        return {"ok": False, "error": "索引未建立", "matches": [],
                "warnings": ["先跑 tools/build_works_index.py"]}
    img = open_rgb(Image.open(io.BytesIO(await file.read())))
    vec = build_inputs(img)
    k_top = max(1, min(int(topK), 8))
    hits = index.search_vector(vec[:512], k=max(12, min(k_top * 8, 48)))
    styles = classify_anchors(vec)[:1]
    matches = rank_photographers(
        hits, runtime["manifest"]["works"], runtime["manifest"]["photographers"],
        top_k=k_top, per_photographer=2, city="",
    )
    warnings: List[str] = []
    if not hits:
        warnings.append("索引为空：先跑 tools/build_works_index.py")
    if not styles:
        warnings.append("风格锚图未加载，styleMatch 为空")
    return {
        "ok": True,
        "mode": "vector",
        "styleMatch": styles[0] if styles else None,
        "indexed": len(index),
        "matchPercentSource": MATCH_SOURCE,
        "matches": matches,
        "warnings": warnings,
        "latencyMs": round((time.perf_counter() - t0) * 1000, 1),
    }


@app.get("/v1/photographer/{photographer_id}/scene-share")
def photographer_scene_share(photographer_id: str) -> Dict[str, Any]:
    """某位摄影师的场景覆盖（作品 styles 标签词频，不训练新模型）。"""
    from .agent import get_runtime
    from .similar import scene_share

    runtime = get_runtime()
    if runtime.get("error"):
        return {"ok": False, "error": runtime["error"], "scenes": []}
    works = runtime["manifest"]["byPhotographer"].get(photographer_id) or []
    if not works:
        return {"ok": False, "photographerId": photographer_id,
                "error": f"没有摄影师 {photographer_id} 的作品", "scenes": [], "totalWorks": 0}
    stats = scene_share(works)
    return {"ok": True, "photographerId": photographer_id,
            "source": "works.manifest.json 的 styles 标签词频", **stats}


def _phash_table() -> Dict[str, Any]:
    """运行时构建作品 dHash 表并缓存（50 张图约 0.3s），不落盘、不依赖构建脚本。

    受限沙箱里子进程写不了工作区文件，因此这里刻意选择「启动后首次调用时在内存
    里算一次」，既避免产物文件与索引不同步，也省掉一个需要 gitignore 的中间物。
    """
    cached = _state.get("phash")
    if cached is not None:
        return cached
    from PIL import Image

    from .agent import get_runtime
    from .audit import build_table, dhash

    entries: List[Dict[str, Any]] = []
    root = Path(__file__).resolve().parents[2]
    runtime = get_runtime()
    index = runtime.get("index")
    if index is not None:
        for work_id, file_str in zip(index.ids, index.files):
            path = root / str(file_str)
            if not path.exists():
                continue
            try:
                with Image.open(path) as img:
                    entries.append({"id": str(work_id), "file": str(file_str), "phash": dhash(img)})
            except Exception:  # noqa: BLE001  单张坏图不该拖垮查重
                continue
    _state["phash"] = build_table(entries)
    return _state["phash"]


def _audit_image(img, top_n: int) -> Dict[str, Any]:
    from .agent import get_runtime
    from .audit import audit, dhash

    runtime = get_runtime()
    index = runtime.get("index") if not runtime.get("error") else None
    query_hash = dhash(img)
    vector = build_inputs(img)[:512] if _state.get("clip_ok") else None
    return audit(query_hash, _phash_table(), vector, index if vector is not None else None,
                 top_n=max(1, min(int(top_n), 10)))


@app.post("/v1/works/audit")
async def works_audit(file: UploadFile = File(...), topN: int = 5) -> Dict[str, Any]:
    """上传一张作品 → 与平台作品库比对（dHash + CLIP 余弦），供发布前自检。

    只给信号与风险档，不做侵权判定；响应里的 method 写死了公式，评审可复算。
    """
    from PIL import Image

    img = open_rgb(Image.open(io.BytesIO(await file.read())))
    t0 = time.perf_counter()
    result = _audit_image(img, topN)
    result["latencyMs"] = round((time.perf_counter() - t0) * 1000, 1)
    return result


@app.get("/v1/works/audit")
def works_audit_by_id(workId: str = "", topN: int = 5) -> Dict[str, Any]:
    """按作品 id 查重（库里已有作品的自检；前端旧契约走的就是这条）。"""
    from PIL import Image

    from .agent import get_runtime

    runtime = get_runtime()
    if runtime.get("error"):
        return {"ok": False, "error": runtime["error"], "nearest": [], "warnings": ["作品索引不可用"]}
    index = runtime.get("index")
    if index is None or not workId:
        return {"ok": False, "error": "缺少 workId 或索引未建立", "nearest": [], "warnings": []}
    try:
        position = index.ids.index(str(workId))
    except ValueError:
        return {"ok": False, "error": f"作品库里没有 {workId}", "nearest": [], "warnings": []}
    path = Path(__file__).resolve().parents[2] / str(index.files[position])
    if not path.exists():
        return {"ok": False, "error": f"作品图片缺失：{index.files[position]}", "nearest": [], "warnings": []}
    t0 = time.perf_counter()
    with Image.open(path) as img:
        result = _audit_image(open_rgb(img), topN)
    result["latencyMs"] = round((time.perf_counter() - t0) * 1000, 1)
    result["workId"] = str(workId)
    return result


class SafetyRequest(BaseModel):
    text: str
    confidence: Optional[float] = None


@app.post("/v1/safety/check")
def safety_check(body: SafetyRequest) -> Dict[str, Any]:
    from .safety import check_input

    return check_input(body.text, body.confidence, semantic_state=_state)


@app.get("/v1/safety/audit")
def safety_audit(limit: int = 100) -> Dict[str, Any]:
    from .safety import query_audit, rule_version

    return {"ok": True, "ruleVersion": rule_version(), "records": query_audit(limit)}


class CopyRequest(BaseModel):
    title: str = ""
    styles: List[str] = []
    tones: List[str] = []
    # 可选事实来源：上传弹窗可把用户已写的简介传入，事实校验会将其视为允许事实。
    description: str = ""
    sourceText: str = ""
    facts: Optional[Dict[str, Any]] = None


def _copy_payload(body: CopyRequest) -> Dict[str, Any]:
    return {
        "title": body.title,
        "styles": body.styles,
        "tones": body.tones,
        "description": body.description,
        "sourceText": body.sourceText,
        "facts": body.facts or {},
    }


@app.post("/v1/copywrite")
def copywrite(body: CopyRequest) -> Dict[str, Any]:
    """根据分类标签生成作品标题/简介/标签。没配 LLM 时返回 mode=rule 的模板兜底。"""
    from .copywriter import generate_copy

    return generate_copy(_copy_payload(body))


@app.post("/v1/copywrite/stream")
def copywrite_stream(body: CopyRequest) -> StreamingResponse:
    """SSE 流式文案：meta → delta* → result → done。"""
    from .copywriter import stream_copy

    return StreamingResponse(
        stream_copy(_copy_payload(body)),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.get("/v1/copywrite/metrics")
def copywrite_metrics() -> Dict[str, Any]:
    """返回本进程文案调用的 P50/P95、模式与最近一次调用指标。"""
    from .copywriter import copywriter_metrics as get_copywriter_metrics

    return get_copywriter_metrics()


class ChatTurn(BaseModel):
    role: str = "user"
    content: str = ""


class ChatRequest(BaseModel):
    message: str
    persona: str = "zhaoye"
    mode: str = "chat"
    context: Optional[Dict[str, Any]] = None
    history: Optional[List[ChatTurn]] = None


@app.post("/v1/chat/reply")
def chat_reply_endpoint(body: ChatRequest) -> Dict[str, Any]:
    """约拍对话框：摄影师口吻回复。

    2026-11-16 新增（第七轮 P0）。本地学生模型就绪时走模型（mode=model），
    否则落「人设模板 + 槽位」兜底（mode=fallback），演示不会断线。
    """
    from .chat import chat_reply

    history = [turn.model_dump() for turn in (body.history or [])]
    return chat_reply(body.message, persona=body.persona, context=body.context,
                      history=history, mode=body.mode)


class AgentRequest(BaseModel):
    text: str
    topN: int = 3


@app.post("/v1/agent/match")
def agent_match(body: AgentRequest) -> Dict[str, Any]:
    """一句话撮合：解析 → 向量检索 → 查档期 → 候选摄影师 + 理由 + 开场话术。"""
    from .agent import run_agent

    return run_agent(body.text, top_n=max(1, min(body.topN, 6)), state=_state)


@app.get("/v1/agent/status")
def agent_status() -> Dict[str, Any]:
    from .agent import get_runtime

    runtime = get_runtime()
    index = runtime.get("index")
    return {
        "ok": not bool(runtime.get("error")),
        "error": runtime.get("error", ""),
        "indexedWorks": len(index) if index is not None else 0,
        "llmConfigured": bool(os.environ.get("LLM_API_KEY")),
        "llmModel": os.environ.get("LLM_MODEL", "qwen-plus"),
        "llmBase": os.environ.get("LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    }


# ---------------------------------------------------------------------------
# BFF 别名层（2026-11-15）
#
# 方案 B：前端只认 /api/v1/*（这是它原本就写死的业务前缀），vite dev 把 /api
# 代理到本进程 8100；生产环境反过来由网关转发。这样做的三个理由：
#   1) 不新增第二个服务进程（Node BFF / Spring Boot 都要多一个东西要维护）；
#   2) 前端 src/services/api.ts 的路径一个字都不用改，冻结的代码面最小；
#   3) 答辩时能讲「业务接口前缀 + 模型服务解耦」，而不是「页面直连模型端口」。
#
# 这里用 add_api_route 复用同一批 handler，不复制逻辑 —— /v1/* 仍是内部契约
# （tools/check_serve_model.py 等脚本照旧），/api/v1/ai/* 是给前端看的门面。
# ---------------------------------------------------------------------------
_BFF_ALIASES = [
    ("/api/v1/ai/classify", classify, ["POST"]),
    ("/api/v1/ai/classify-base64", classify_b64, ["POST"]),
    ("/api/v1/ai/embed", embed, ["POST"]),
    ("/api/v1/ai/health", health, ["GET"]),
    ("/api/v1/ai/models", models, ["GET"]),
    ("/api/v1/ai/agent/match", agent_match, ["POST"]),
    ("/api/v1/ai/agent/status", agent_status, ["GET"]),
    ("/api/v1/ai/copywrite", copywrite, ["POST"]),
    ("/api/v1/ai/copywrite/stream", copywrite_stream, ["POST"]),
    ("/api/v1/ai/copywrite/metrics", copywrite_metrics, ["GET"]),
    ("/api/v1/ai/chat/reply", chat_reply_endpoint, ["POST"]),
    ("/api/v1/ai/search", search, ["POST"]),
    ("/api/v1/ai/similar", similar, ["POST"]),
    ("/api/v1/ai/photographer/{photographer_id}/scene-share", photographer_scene_share, ["GET"]),
    ("/api/v1/ai/works/audit", works_audit, ["POST"]),
    ("/api/v1/ai/works/audit", works_audit_by_id, ["GET"]),
    ("/api/v1/ai/safety/check", safety_check, ["POST"]),
    ("/api/v1/ai/safety/audit", safety_audit, ["GET"]),
]
for _path, _endpoint, _methods in _BFF_ALIASES:
    app.add_api_route(_path, _endpoint, methods=_methods, include_in_schema=False)
