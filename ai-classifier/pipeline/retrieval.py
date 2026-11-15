"""作品检索（RAG 的检索端）。

- 索引是 images 的 CLIP 视觉向量（models/works.embed.npz）
- 查询是 CLIP 文本向量，用余弦相似度做跨模态检索
- 注意：本项目 CLIP 底座是 ViT-B/32（英文语料），中文查询必须先翻成英文提示词，
  直接喂中文会退化成噪声。翻译表在 agent.py 的 STYLE_PROMPTS 里，不在这里硬编码。
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .cliputil import text_features


class WorkIndex:
    def __init__(self, path: Path) -> None:
        data = np.load(path, allow_pickle=False)
        self.ids = [str(item) for item in data["ids"]]
        self.files = [str(item) for item in data["files"]]
        vecs = data["vecs"].astype(np.float32)
        # 兜底归一化：即使索引构建时漏了 normalize，检索也不会被模长带偏
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        self.vecs = vecs / np.clip(norms, 1e-8, None)

    def __len__(self) -> int:
        return len(self.ids)

    def search_text(self, text: str, state: dict, k: int = 8) -> list[dict]:
        torch = state["torch"]
        proc = state["proc"]
        with torch.no_grad():
            inputs = proc(text=[text], return_tensors="pt", padding=True, truncation=True)
            feat = text_features(state["clip"], inputs)
            feat = torch.nn.functional.normalize(feat, dim=-1).cpu().numpy()[0]
        sims = self.vecs @ feat
        order = np.argsort(-sims)[: max(1, min(k, len(self.ids)))]
        return [
            {"id": self.ids[int(i)], "file": self.files[int(i)], "score": round(float(sims[int(i)]), 4)}
            for i in order
        ]
