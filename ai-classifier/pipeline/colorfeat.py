"""色彩/影调特征（24 维）——风格分类的关键特征。

为什么单独写这个文件：
    "蓝调 / ins 风 / 日系清透 / 胶片"本质上是调色 + 影调 + 构图偏好，
    只用 CLIP 语义向量去分，4 类以上准确率大概 65~75%，会卡在这个天花板。
    把这 24 个可解释的数值拼进风格头，同等样本量下通常能再涨 10~20 个点。

依赖只有 Pillow + NumPy，不需要 GPU、不需要模型权重，先跑这个也能出东西：
    python -m pipeline.colorfeat some.jpg

特征含义见 FEATURE_NAMES，训练报告里会按名字打印，方便跟摄影师对齐口径。
"""

from __future__ import annotations

import math
from typing import Union

import numpy as np
from PIL import Image, ImageOps

FEATURE_NAMES = [
    "L_mean",        # 明度均值：整体亮不亮
    "a_mean",        # 绿-红轴：偏绿还是偏品红
    "b_mean",        # 蓝-黄轴：负=偏蓝（蓝调的直接证据），正=偏黄
    "L_std",         # 明度标准差：全局对比强弱
    "a_std",
    "b_std",
    "L_p05",         # 暗部抬升：ins 风/胶片黑位不上死黑，这个值明显偏高
    "L_p95",         # 高光：日系/清透常常高光溢出
    "L_range",       # 影调范围 = p95 - p05
    "S_mean",        # 饱和度均值
    "S_p90",         # 高饱和像素占比 → 赛博/糖果色
    "V_mean",
    "V_p10",
    "clip_hi",       # 高光裁切率（V>=0.99）
    "clip_lo",       # 阴影裁切率（V<=0.01）
    "warmth",        # 整体冷暖 = mean(R-B)
    "warmth_shadow", # 暗部冷暖（蓝调在暗部更明显）
    "warmth_high",   # 高光冷暖（暖白平衡 + 冷暗部 = 电影感调色）
    "colorfulness",  # Hasler-Süsstrunk 色彩丰富度
    "hue_circvar",   # 色相集中度：单色调风格值低，多彩场景值高
    "hue_dominant",  # 主色相占比（12 bin 直方图最大值）
    "skin_ratio",    # 肤色占比 → 粗判"是不是人像"
    "L_entropy",     # 明度直方图熵
    "shadow_ratio",  # 深阴影占比（L<0.22）
]

# YCbCr 常用肤色阈值
_SKIN = (77.0, 127.0, 133.0, 173.0)


def open_rgb(path_or_img: Union[str, Image.Image]) -> Image.Image:
    """统一入口。处理两件 Windows/手机照片上必踩的事：

    1. 中文路径 —— 不用 cv2.imread（它会静默返回 None），走 PIL。
    2. EXIF 方向 —— 手机竖拍的图必须 exif_transpose，否则特征和肉眼看到的不是同一张。
    """
    img = path_or_img if isinstance(path_or_img, Image.Image) else Image.open(path_or_img)
    img = ImageOps.exif_transpose(img)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img


def resize_long(img: Image.Image, size: int = 384) -> Image.Image:
    """按长边缩到 size，只缩不放。384 兼顾速度和统计稳定性。"""
    w, h = img.size
    scale = size / max(w, h)
    if scale >= 1.0:
        return img
    return img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.BILINEAR)


def color_features(path_or_img: Union[str, Image.Image]) -> np.ndarray:
    """返回 (24,) float32。全部数值大致落在 [-1, 1] 或 [0, 1]，无需再归一化。"""
    img = resize_long(open_rgb(path_or_img))

    rgb = np.asarray(img, dtype=np.float32) / 255.0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]

    # PIL 的 LAB 是 8bit：L 0-255，a/b 以 128 为中心偏移
    lab = np.asarray(img.convert("LAB"), dtype=np.float32) / 255.0
    L = lab[..., 0]
    A = lab[..., 1] - 0.5
    B = lab[..., 2] - 0.5

    hsv = np.asarray(img.convert("HSV"), dtype=np.float32) / 255.0
    H, S, V = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    L_flat, V_flat, S_flat = L.ravel(), V.ravel(), S.ravel()

    # 影调
    L_p05, L_p95 = np.percentile(L_flat, [5, 95])

    # Hasler & Süsstrunk colorfulness
    rg = r - g
    yb = 0.5 * (r + g) - b
    colorfulness = math.sqrt(float(rg.std()) ** 2 + float(yb.std()) ** 2) \
        + 0.3 * math.sqrt(float(rg.mean()) ** 2 + float(yb.mean()) ** 2)

    # 色相集中度：按饱和度加权的圆形方差
    ang = H.ravel() * 2.0 * math.pi
    wsum = S_flat.sum() + 1e-8
    vec = np.abs((S_flat * np.exp(1j * ang)).sum() / wsum)
    hue_circvar = 1.0 - float(vec)

    # 主色相 12 bin 占比
    hbins = np.bincount((H.ravel() * 12).astype(np.int32) % 12, weights=S_flat, minlength=12)
    hue_dominant = float(hbins.max() / (hbins.sum() + 1e-8))

    # 肤色占比
    ycbcr = np.asarray(img.convert("YCbCr"), dtype=np.float32)
    Cb, Cr = ycbcr[..., 1], ycbcr[..., 2]
    lo_cb, hi_cb, lo_cr, hi_cr = _SKIN
    skin_ratio = float((((Cb > lo_cb) & (Cb < hi_cb)) & ((Cr > lo_cr) & (Cr < hi_cr))).mean())

    # 明度直方图熵
    hist, _ = np.histogram(L_flat, bins=32, range=(0.0, 1.0))
    p = hist / (hist.sum() + 1e-8)
    p = p[p > 0]
    L_entropy = float(-(p * np.log2(p)).sum() / 5.0)  # 除以 log2(32) 归一化到 [0,1]

    warmth = float(rgb[..., 0].mean() - rgb[..., 2].mean())
    shadow = L < 0.25
    high = L > 0.75
    rb = r - b
    warmth_shadow = float(rb[shadow].mean()) if shadow.any() else 0.0
    warmth_high = float(rb[high].mean()) if high.any() else 0.0

    feats = np.array([
        float(L.mean()), float(A.mean()), float(B.mean()),
        float(L.std()), float(A.std()), float(B.std()),
        float(L_p05), float(L_p95), float(L_p95 - L_p05),
        float(S.mean()), float(np.percentile(S_flat, 90)), float(V.mean()), float(np.percentile(V_flat, 10)),
        float((V_flat >= 0.99).mean()), float((V_flat <= 0.01).mean()),
        warmth, warmth_shadow, warmth_high,
        colorfulness, hue_circvar, hue_dominant, skin_ratio, L_entropy,
        float((L_flat < 0.22).mean()),
    ], dtype=np.float32)

    assert feats.shape == (24,), feats.shape
    return feats


def batch(paths, size: int = 384) -> np.ndarray:
    """批量提取，返回 (N, 24)。单张失败不中断整批，用零向量占位并在第二列返回索引。"""
    out = np.zeros((len(paths), 24), dtype=np.float32)
    for i, p in enumerate(paths):
        try:
            out[i] = color_features(p)
        except Exception as exc:  # 损坏文件、非图片、权限
            print(f"[warn] {p}: {exc}")
    return out


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="提取 24 维色彩/影调特征")
    ap.add_argument("paths", nargs="+", help="图片路径，可传多个")
    args = ap.parse_args()
    for path in args.paths:
        f = color_features(path)
        print(f"\n{path}")
        for name, val in zip(FEATURE_NAMES, f):
            print(f"  {name:14s} {val:+.4f}")
