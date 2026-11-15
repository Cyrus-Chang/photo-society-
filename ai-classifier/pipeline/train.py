"""特征 + 训练 + 导出 ONNX。

设计取舍（为什么这么做，别改成"端到端微调 CLIP"）：
    你的样本量在几百张量级。这个量级上，冻结 CLIP 主干 + 线性头，
    比微调整网稳定得多：微调 300 张、13 类，验证集大概率过拟合，
    macro-F1 反而比线性头低 10 个点以上，而且每次迭代要 GPU 几十分钟。
    冻结后特征只提一次（NPZ 缓存），之后调 C、调类别权重是秒级的事。

用法：
    1) 准备标注表 labels.csv，列固定：
         path,subject,style,photographer_id
         D:/data/a.jpg,PORTRAIT,BLUE_TONE,p001
         D:/data/b.jpg,"PORTRAIT,STREET",INS,p002     ← subject 可多标签，逗号分隔要加引号
    2) 先提特征（第一次会比较慢）：
         python -m pipeline.train extract --csv labels.csv --cache cache/feat.npz
    3) 训练 + 评测 + 导出：
         python -m pipeline.train fit     --csv labels.csv --cache cache/feat.npz --out models
    产物：
         models/subject.onnx / subject.labels.json / subject.metrics.json
         models/style.onnx   / style.labels.json   / style.metrics.json
         models/metrics_report.txt / confusion_*.csv

依赖：numpy pandas pillow scikit-learn transformers torch onnx onnxruntime
（只有 extract 那一步需要 transformers/torch；只调头的时候不需要）
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import pandas as pd

from . import cliputil
from .console import ensure_utf8

CLIP_MODEL = "openai/clip-vit-base-patch32"   # 与前端 transformers.js 用同一套权重，端云结果才一致
CLIP_DIM = 512
COLOR_DIM = 24


# ---------------------------------------------------------------------------
# 特征抽取
# ---------------------------------------------------------------------------
def _clip_backbone(device: str = "cpu"):
    import torch
    from transformers import CLIPModel, CLIPProcessor

    model = CLIPModel.from_pretrained(CLIP_MODEL).to(device).eval()
    proc = CLIPProcessor.from_pretrained(CLIP_MODEL)
    return model, proc, torch


def extract_clip(paths: Sequence[str], device: str = "cpu", batch_size: int = 16) -> np.ndarray:
    """返回 (N, 512) 的 L2 归一化图像向量。"""
    model, proc, torch = _clip_backbone(device)
    from PIL import Image, ImageOps

    out = np.zeros((len(paths), CLIP_DIM), dtype=np.float32)
    with torch.no_grad():
        for start in range(0, len(paths), batch_size):
            chunk = paths[start:start + batch_size]
            imgs = []
            for p in chunk:
                img = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
                imgs.append(img)
            inputs = proc(images=imgs, return_tensors="pt").to(device)
            feats = cliputil.image_features(model, inputs)
            feats = torch.nn.functional.normalize(feats, dim=-1)
            out[start:start + len(chunk)] = feats.cpu().numpy()
            print(f"\r  clip {start + len(chunk)}/{len(paths)}", end="", file=sys.stderr)
    print("", file=sys.stderr)
    return out


def extract_color(paths: Sequence[str]) -> np.ndarray:
    from .colorfeat import color_features

    out = np.zeros((len(paths), COLOR_DIM), dtype=np.float32)
    for i, p in enumerate(paths):
        try:
            out[i] = color_features(p)
        except Exception as exc:
            print(f"\n[warn] 色彩特征失败 {p}: {exc}", file=sys.stderr)
    return out


def cmd_extract(args) -> None:
    df = pd.read_csv(args.csv, dtype=str, encoding="utf-8-sig").fillna("")
    paths = df["path"].tolist()
    cache = Path(args.cache)
    cache.parent.mkdir(parents=True, exist_ok=True)

    # 简易增量缓存：以 (路径, 文件大小, 修改时间) 为键
    key = np.array([f"{p}|{os.path.getsize(p)}|{os.stat(p).st_mtime_ns}" for p in paths])
    clip = color = None
    if cache.exists():
        old = np.load(cache, allow_pickle=True)
        old_map = {k: i for i, k in enumerate(old["key"])}
        clip = np.zeros((len(paths), CLIP_DIM), dtype=np.float32)
        color = np.zeros((len(paths), COLOR_DIM), dtype=np.float32)
        todo = []
        for i, k in enumerate(key):
            j = old_map.get(k)
            if j is None:
                todo.append(i)
            else:
                clip[i] = old["clip"][j]
                color[i] = old["color"][j]
        print(f"缓存命中 {len(paths) - len(todo)}/{len(paths)}，需补算 {len(todo)} 张", file=sys.stderr)
        if todo:
            clip[todo] = extract_clip([paths[i] for i in todo], device=args.device)
            color[todo] = extract_color([paths[i] for i in todo])
    else:
        clip = extract_clip(paths, device=args.device)
        color = extract_color(paths)

    np.savez_compressed(cache, key=key, clip=clip, color=color)
    print(f"已写入 {cache}  clip={clip.shape} color={color.shape}")


# ---------------------------------------------------------------------------
# 训练
# ---------------------------------------------------------------------------
def grouped_split(df: pd.DataFrame, label_col: str, seed: int = 42) -> pd.Series:
    """按摄影师分组划分 70/15/15，然后把"训练集里缺席的类别"整组搬回来。

    两个必须处理的坑，缺一个今天下午就会失败：
    1. 随机划分 → 同一摄影师高度相似的片子横跨训练集和验证集，指标虚高 15~25 点。
    2. 单纯按人分组 → 某个类别只被一位摄影师拍过时，他若落到验证集，
       该类在训练集里彻底缺席，模型永远学不会，评估还会因为类别不在 classes 里崩掉。
       所以划分后要做修复：任何在训练集缺席的类别，把包含它的最小分组整体搬回训练集。
    """
    rng = np.random.default_rng(seed)
    split = pd.Series("TRAIN", index=df.index)

    has_ph = "photographer_id" in df.columns and not df["photographer_id"].eq("").all()
    if not has_ph:
        print("[warn] 缺 photographer_id，退化为随机划分，指标会偏乐观", file=sys.stderr)
        order = rng.permutation(len(df))
        n_val = max(1, int(len(df) * 0.15))
        split.iloc[order[:n_val]] = "VAL"
        split.iloc[order[n_val:2 * n_val]] = "TEST"
        return split

    groups = np.array(sorted(df["photographer_id"].unique()))
    rng.shuffle(groups)
    n_val = max(1, int(len(groups) * 0.15))
    split[df["photographer_id"].isin(set(groups[:n_val]))] = "VAL"
    split[df["photographer_id"].isin(set(groups[n_val:2 * n_val]))] = "TEST"

    codes = [[c.strip() for c in str(v).split(",") if c.strip()] for v in df[label_col]]
    labels_pos = split.to_numpy()
    for _ in range(5):
        train_codes = {c for cs, s in zip(codes, labels_pos) if s == "TRAIN" for c in cs}
        missing = {c for cs, s in zip(codes, labels_pos) if s != "TRAIN" for c in cs} - train_codes
        if not missing:
            break
        target = sorted(missing)[0]
        rows = [i for i, (cs, s) in enumerate(zip(codes, labels_pos))
                if s != "TRAIN" and target in cs]
        if not rows:
            break
        # 搬"含该类图片最少"的那个分组，改动面最小
        counts = df["photographer_id"].iloc[rows].value_counts()
        group = counts.index[-1]
        split[df["photographer_id"] == group] = "TRAIN"
        labels_pos = split.to_numpy()
        print(f"[fix] 类别 {target} 在训练集缺席 → 把分组 {group} 搬回训练集", file=sys.stderr)
    return split


def fit_head(X: np.ndarray, y: List, multi: bool):
    """返回 (W, b, classes)，形状 W=(C,D) b=(C,)。"""
    from sklearn.linear_model import LogisticRegression
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.preprocessing import MultiLabelBinarizer

    if multi:
        classes = sorted({c for row in y for c in row})
        mlb = MultiLabelBinarizer(classes=classes)
        Y = mlb.fit_transform(y)
        clf = OneVsRestClassifier(LogisticRegression(max_iter=3000, class_weight="balanced", C=1.0))
        clf.fit(X, Y)
        W = np.stack([e.coef_[0] for e in clf.estimators_])
        b = np.stack([e.intercept_[0] for e in clf.estimators_])
    else:
        clf = LogisticRegression(max_iter=3000, class_weight="balanced", C=1.0)
        clf.fit(X, y)
        classes = [str(c) for c in clf.classes_]
        W, b = clf.coef_, clf.intercept_
    return W.astype(np.float32), b.astype(np.float32), classes


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def predict_proba(raw: np.ndarray, W: np.ndarray, b: np.ndarray, mean: np.ndarray,
                  std: np.ndarray, multi: bool) -> np.ndarray:
    z = (raw - mean) / std
    logits = z @ W.T + b
    return 1.0 / (1.0 + np.exp(-logits)) if multi else _softmax(logits)


def export_onnx(path: Path, W: np.ndarray, b: np.ndarray, mean: np.ndarray, std: np.ndarray,
                dim: int, multi: bool) -> None:
    """把标准化折叠进权重，导出的 ONNX 直接吃原始特征，前端/Python 端都不用再算 mean/std。"""
    import torch

    Wf = W / std[None, :]
    bf = b - (W @ (mean / std))
    layer = torch.nn.Linear(dim, W.shape[0])
    with torch.no_grad():
        layer.weight.copy_(torch.from_numpy(Wf))
        layer.bias.copy_(torch.from_numpy(bf))

    class Head(torch.nn.Module):
        def __init__(self, inner, multi_: bool):
            super().__init__()
            self.inner = inner
            self.multi = multi_

        def forward(self, x):
            return self.inner(x)  # 输出 logits，softmax/sigmoid 留给调用方

    head = Head(layer, multi).eval()
    dummy = torch.zeros(1, dim, dtype=torch.float32)
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        head, dummy, str(path),
        input_names=["features"], output_names=["logits"],
        dynamic_axes={"features": {0: "batch"}, "logits": {0: "batch"}},
        opset_version=17,
    )


def evaluate(y_true, proba: np.ndarray, classes: Sequence[str], multi: bool) -> Dict:
    from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                                 precision_recall_fscore_support)

    if multi:
        from sklearn.preprocessing import MultiLabelBinarizer

        mlb = MultiLabelBinarizer(classes=list(classes))
        Yt = mlb.fit_transform(y_true)
        pred = (proba >= 0.5).astype(int)
        macro_f1 = float(f1_score(Yt, pred, average="macro", zero_division=0))
        acc = float(accuracy_score(Yt, pred))  # 子集准确率，偏严格，看趋势即可
        cm = None
    else:
        pred_idx = proba.argmax(axis=1)
        cls_idx = {c: i for i, c in enumerate(classes)}
        yt = np.array([cls_idx[v] for v in y_true])
        macro_f1 = float(f1_score(yt, pred_idx, average="macro", zero_division=0))
        acc = float(accuracy_score(yt, pred_idx))
        cm = confusion_matrix(yt, pred_idx, labels=list(range(len(classes)))).tolist()

    # 逐类指标：多标签与单标签统一走 one-vs-rest 口径
    if multi:
        p, r, f1, support = precision_recall_fscore_support(Yt, pred, average=None, zero_division=0)
    else:
        p, r, f1, support = precision_recall_fscore_support(
            yt, pred_idx, labels=list(range(len(classes))), average=None, zero_division=0)

    per_class = [
        {"code": c, "precision": round(float(p[i]), 4), "recall": round(float(r[i]), 4),
         "f1": round(float(f1[i]), 4), "support": int(support[i])}
        for i, c in enumerate(classes)
    ]
    return {"macro_f1": round(macro_f1, 4), "accuracy": round(acc, 4),
            "per_class": per_class, "confusion": cm, "n_eval": int(len(y_true))}


def derive_thresholds(proba: np.ndarray, y_true, classes: Sequence[str], multi: bool) -> Dict[str, float]:
    """按"精确率优先"给每类挑阈值：把该类预测的 P>=0.8 的最低阈值留下。

    风格标签在业务上宁缺毋滥（标错的风格会直接污染筛选），所以用精确率导向；
    类型标签可以放宽到 0.5，漏标比错标代价低。
    """
    out: Dict[str, float] = {}
    for i, code in enumerate(classes):
        best = 0.5
        if multi:
            truth = np.array([code in row for row in y_true])
        else:
            truth = np.array([row == code for row in y_true])
        if truth.sum() == 0:
            out[code] = 0.55
            continue
        for th in np.arange(0.30, 0.96, 0.05):
            pred = proba[:, i] >= th
            if pred.sum() == 0:
                continue
            prec = (pred & truth).sum() / pred.sum()
            if prec >= 0.8:
                best = round(float(th), 2)
                break
        out[code] = best
    return out


def _task_frame(df: pd.DataFrame, col: str, multi: bool) -> Tuple[pd.DataFrame, List]:
    if multi:
        rows, labels = [], []
        for _, r in df.iterrows():
            codes = [c.strip() for c in str(r[col]).split(",") if c.strip()]
            if codes:
                rows.append(r)
                labels.append(codes)
        return pd.DataFrame(rows), labels
    sub = df[df[col].astype(str).str.strip() != ""]
    return sub, [str(v).strip() for v in sub[col]]


def cmd_fit(args) -> None:
    df = pd.read_csv(args.csv, dtype=str, encoding="utf-8-sig").fillna("")
    cache = np.load(args.cache, allow_pickle=True)
    key_list = [str(k) for k in cache["key"]]
    key_map = {k: i for i, k in enumerate(key_list)}

    def rows_for(sub: pd.DataFrame) -> np.ndarray:
        idx = [key_map[f"{p}|{os.path.getsize(p)}|{os.stat(p).st_mtime_ns}"] for p in sub["path"]]
        return np.concatenate([cache["clip"][idx], cache["color"][idx]], axis=1).astype(np.float32)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_lines: List[str] = []
    dim = CLIP_DIM + COLOR_DIM

    # 题材和风格都是多标签：风格里「日系+清新」「胶片+复古」天然共存，
    # 强制互斥（softmax）会让重叠的类互相拉扯，13 类时尤其明显。
    # --tasks 允许只训其中一个头：用公开数据先把题材头训出来时，风格那列的标签还是占位值，
    # 训它等于给模型灌噪声，不如留着走 serve.py 的零样本兜底。
    wanted = [t.strip() for t in getattr(args, "tasks", "subject,style").split(",") if t.strip()]
    for task, col, multi in (("subject", "subject", True), ("style", "style", True)):
        if task not in wanted:
            print(f"[skip] {task}: 本次只训 {wanted}", file=sys.stderr)
            continue
        sub, labels = _task_frame(df, col, multi)
        if len(sub) == 0:
            print(f"[skip] {task}: 没有可用标注", file=sys.stderr)
            continue
        raw = rows_for(sub)
        split = grouped_split(sub, col, seed=args.seed)
        tr = (split == "TRAIN").to_numpy()
        va = (split == "VAL").to_numpy()
        te = (split == "TEST").to_numpy()
        if tr.sum() < 10:
            print(f"[skip] {task}: 训练集只有 {tr.sum()} 张，至少要 10 张", file=sys.stderr)
            continue

        # 训练、评估、导出的 ONNX 必须使用同一特征空间。先按训练集统计量
        # 标准化，再训练线性头；export_onnx() 会把这一步折叠回原始输入。
        mean = raw[tr].mean(axis=0)
        std = raw[tr].std(axis=0) + 1e-6
        train_x = (raw[tr] - mean) / std
        W, b, classes = fit_head(train_x, [labels[i] for i in np.where(tr)[0]], multi)

        # 评估集里可能出现在训练集完全没见过的类别（按摄影师分组划分时很常见，
        # 比如只有一位摄影师拍过漫展，而他恰好被分到验证集）。这类样本无法被评估，剔除。
        cls_set = set(classes)
        metrics: Dict[str, Dict] = {}
        for s, mask in (("val", va), ("test", te)):
            keep = [i for i in np.where(mask)[0]
                    if (all(c in cls_set for c in labels[i]) if multi else labels[i] in cls_set)]
            if not keep:
                continue
            dropped = int(mask.sum()) - len(keep)
            if dropped:
                print(f"[warn] {task}/{s}: {dropped} 张的类别未出现在训练集，已排除", file=sys.stderr)
            metrics[s] = evaluate([labels[i] for i in keep],
                                  predict_proba(raw[keep], W, b, mean, std, multi), classes, multi)

        # 阈值用验证集推，测试集只看不改，避免阈值也过拟合
        vm = va if va.sum() > 0 else te
        vidx = [i for i in np.where(vm)[0]
                if (all(c in cls_set for c in labels[i]) if multi else labels[i] in cls_set)]
        if vidx:
            thr = derive_thresholds(predict_proba(raw[vidx], W, b, mean, std, multi),
                                    [labels[i] for i in vidx], classes, multi)
        else:
            thr = {c: 0.5 for c in classes}

        stem = out_dir / task
        np.savez_compressed(f"{stem}.head.npz", W=W, b=b, mean=mean, std=std,
                            classes=np.array(classes), multi=np.array(multi))
        (Path(f"{stem}.labels.json")).write_text(
            json.dumps({"task": task, "classes": list(classes), "multi": multi,
                        "feature_layout": ["clip512", "color24"], "clip_model": CLIP_MODEL},
                       ensure_ascii=False, indent=2), encoding="utf-8")
        (Path(f"{stem}.threshold.json")).write_text(
            json.dumps(thr, ensure_ascii=False, indent=2), encoding="utf-8")
        subject_codes = {c for row in labels for c in (row if multi else [row])}
        portrait_codes = {"STUDIO", "OUTDOOR", "CONVENTION", "STREET_PORTRAIT", "INTERIOR_PORTRAIT"}
        portrait_share = round(
            sum(bool(set(row if multi else [row]) & portrait_codes) for row in labels) / max(1, len(labels)), 4
        ) if task == "subject" else None
        metrics_payload = {
            "task": task,
            "classes": list(classes),
            "n_train": int(tr.sum()),
            "n_val": int(va.sum()),
            "n_test": int(te.sum()),
            "train_domain": {
                "photographer_count": int(df["photographer_id"].replace("", np.nan).dropna().nunique())
                if "photographer_id" in df.columns else 0,
                "portrait_share": portrait_share,
                "subject_codes": sorted(subject_codes),
            },
            **metrics,
        }
        (Path(f"{stem}.metrics.json")).write_text(
            json.dumps(metrics_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        export_onnx(Path(f"{stem}.onnx"), W, b, mean, std, dim, multi)

        # 混淆矩阵落 CSV，答辩时直接贴
        for s, m in metrics.items():
            if m.get("confusion"):
                pd.DataFrame(m["confusion"], index=classes, columns=classes) \
                  .to_csv(out_dir / f"confusion_{task}_{s}.csv", encoding="utf-8-sig")

        report_lines.append(f"[{task}] classes={len(classes)} train={int(tr.sum())} "
                            f"val_macroF1={metrics.get('val', {}).get('macro_f1')} "
                            f"test_macroF1={metrics.get('test', {}).get('macro_f1')}")
        for m_name, m in metrics.items():
            report_lines.append(f"  {m_name}: macroF1={m['macro_f1']} acc={m['accuracy']} n={m['n_eval']}")
            for pc in m["per_class"]:
                report_lines.append(f"    {pc['code']:16s} P={pc['precision']:.3f} "
                                    f"R={pc['recall']:.3f} F1={pc['f1']:.3f} n={pc['support']}")
        print("\n".join(report_lines[-12:]))

    (out_dir / "metrics_report.txt").write_text("\n".join(report_lines), encoding="utf-8")
    print(f"\n已写入 {out_dir}")


def main() -> None:
    ensure_utf8()
    ap = argparse.ArgumentParser(description="图片类型/风格分类器：特征、训练、导出")
    ap.add_argument("cmd", choices=["extract", "fit"])
    ap.add_argument("--csv", required=True)
    ap.add_argument("--cache", default="cache/feat.npz")
    ap.add_argument("--out", default="models")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tasks", default="subject,style",
                    help="只训哪些头，逗号分隔：subject / style。公开数据先把题材头训出来时用 --tasks subject")
    args = ap.parse_args()
    cmd_extract(args) if args.cmd == "extract" else cmd_fit(args)


if __name__ == "__main__":
    main()
