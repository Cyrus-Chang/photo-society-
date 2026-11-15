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

from .cliputil import image_features, text_features
from .colorfeat import FEATURE_NAMES, color_features, open_rgb

MODEL_DIR = Path(os.environ.get("MODEL_DIR", "models"))
DICT_PATH = Path(os.environ.get("DICT_PATH", "labels/dictionary.json"))
CLIP_MODEL = os.environ.get("CLIP_MODEL", "openai/clip-vit-base-patch32")
FEATURE_DIM = 512 + 24

# 业务用的置信度下限：低于它直接不返回，宁可空着让人工补
MIN_CONF = float(os.environ.get("MIN_CONF", "0.30"))

app = FastAPI(title="Photo Classifier", version="1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_state: Dict[str, Any] = {"clip": None, "proc": None, "torch": None,
                           "heads": {}, "booted_at": time.time()}


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
    return [{"code": a["codes"][int(i)], "confidence": round(float(p[i]), 4)} for i in order]


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
    return [{"code": code, "source": "RULE"} for code, hit in rules if hit]


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
                          "aboveThreshold": bool(p >= head["thresholds"].get(code, 0.5))})
        items.sort(key=lambda d: -d["confidence"])
        out[task] = items[:5]
    return out


def classify_zero_shot(vec: np.ndarray) -> Dict[str, List[Dict[str, Any]]]:
    """训练样本还不够时的兜底：用字典里的 prompt_en 直接算相似度。

    精度大概只有线性头的七八成，但它 0 样本可用，让整条链路明天就能联调。
    """
    if not _state.get("clip_ok"):
        return {}
    torch = _state["torch"]
    proc = _state["proc"]
    out: Dict[str, List[Dict[str, Any]]] = {}
    # ★ 只取前 512 维：后 24 维色彩特征没有文本对应物，拼进去维度就对不上了
    vision = torch.from_numpy(vec[:512])
    for tag_type, groups in (_state.get("dict") or {}).items():
        if tag_type not in ("SUBJECT", "STYLE"):
            continue
        # 只考虑本期启用的类（enabled=false 的定义还留在字典里，但不许出现在结果中）
        usable = [g for g in groups if g.get("prompt_en") and g.get("enabled", True)]
        prompts = [g["prompt_en"] for g in usable]
        codes = [g["code"] for g in usable]
        with torch.no_grad():
            t = proc(text=prompts, return_tensors="pt", padding=True)
            tf = text_features(_state["clip"], t)
            tf = torch.nn.functional.normalize(tf, dim=-1)
        cos = (tf @ vision).cpu().numpy()   # 单位向量点积，落在 [-1, 1]
        probs = _softmax(cos * 100.0)       # CLIP 的 logit scale 约为 100
        out[tag_type.lower()] = [
            {"code": c, "confidence": round(float(p), 4)}
            for c, p in sorted(zip(codes, probs), key=lambda kv: -kv[1])[:3]
        ]
    return out


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

    return {
        "subject": result.get("subject", []),
        "style": result.get("style", []),
        "tone": derive_tone(color),
        "color": color,
        "modelVersion": {k: v["version"] for k, v in _state["heads"].items()},
        "fallback": fallback,
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


class CopyRequest(BaseModel):
    title: str = ""
    styles: List[str] = []
    tones: List[str] = []


@app.post("/v1/copywrite")
def copywrite(body: CopyRequest) -> Dict[str, Any]:
    """根据分类标签生成作品标题/简介/标签。没配 LLM 时返回 mode=rule 的模板兜底。"""
    from .copywriter import generate_copy

    return generate_copy({"title": body.title, "styles": body.styles, "tones": body.tones})


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
]
for _path, _endpoint, _methods in _BFF_ALIASES:
    app.add_api_route(_path, _endpoint, methods=_methods, include_in_schema=False)
