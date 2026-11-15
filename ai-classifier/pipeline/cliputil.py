"""CLIP 取特征的兼容层。

transformers 4.x：

    feats = model.get_image_features(**inputs)        # -> Tensor (N, 512)

transformers 5.x（装了 >=5 的机器上就会踩到）：

    get_image_features 被 @can_return_tuple 包了一层，返回
    BaseModelOutputWithPooling，投影后的向量挂在 .pooler_output 上。
    直接 normalize() 会报 `'BaseModelOutputWithPooling' object has no attribute 'norm'`。

两个版本的数值完全一致（都是 visual_projection(pooler_output)），所以这里只做解包，
不改变计算路径——训练和推理必须走同一份预处理，这条铁律不能因为版本差异被破坏。
"""

from __future__ import annotations

from typing import Any


def unwrap(out: Any) -> Any:
    """把 ModelOutput 解成 Tensor；本来就是 Tensor 时原样返回。"""
    pooled = getattr(out, "pooler_output", None)
    return pooled if pooled is not None else out


def image_features(model: Any, inputs: dict) -> Any:
    return unwrap(model.get_image_features(**inputs))


def text_features(model: Any, inputs: dict) -> Any:
    return unwrap(model.get_text_features(**inputs))
