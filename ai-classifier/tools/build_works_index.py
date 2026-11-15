"""建「作品向量索引」——RAG 的检索端。

索引来源：models/works.manifest.json（由前端真实模块导出，不是我手写的假数据）
图片来源：src/assets/works/*.jpg、src/assets/spirals/*.webp（manifest 里的本地路径）
向量口径：直接复用 pipeline.serve.build_inputs，保证「训练 / 分类 / 检索」三处预处理完全一致——
         这是这类项目上线翻车的头号原因，不能在索引脚本里另写一份 resize。

用法（cwd 必须是 ai-classifier）：
    .\\.venv\\Scripts\\python.exe tools\\build_works_index.py
输出：
    models/works.embed.npz   ids / vecs / files
    models/works.index.json  条数与维度等元信息
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PKG = Path(__file__).resolve().parents[1]
MODEL_DIR = PKG / "models"
MANIFEST = MODEL_DIR / "works.manifest.json"

# 直接 `python tools/xxx.py` 时 sys.path[0] 是 tools/，包根不在里面
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))


def resolve_local(image_url: str) -> Path | None:
    """把 manifest 里的前端 URL 落回磁盘路径；远程图（unsplash）不索引。"""
    if image_url.startswith("/src/assets/"):
        path = REPO / image_url.lstrip("/")
        return path if path.exists() else None
    if image_url.startswith("/works/"):
        path = REPO / "public" / image_url.lstrip("/")
        return path if path.exists() else None
    return None


def main() -> int:
    if not MANIFEST.exists():
        print(f"[x] 缺 {MANIFEST}，先从运行中的前端导出（.review-tmp/works.json）")
        return 1

    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries: list[tuple[str, Path]] = []
    seen: set[str] = set()
    remote = 0
    for key in ("works", "spiralWorks"):
        for item in data.get(key, []):
            work_id = item.get("id")
            if not work_id or work_id in seen:
                continue
            seen.add(work_id)
            path = resolve_local(item.get("imageUrl", ""))
            if path is None:
                remote += 1
                continue
            entries.append((work_id, path))
    print(f"[i] 唯一作品 {len(seen)}，本地可索引 {len(entries)}，远程跳过 {remote}")

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

    from PIL import Image

    from pipeline.colorfeat import open_rgb
    from pipeline.serve import _startup, _state, build_inputs

    _startup()
    if not _state.get("clip_ok"):
        print("[x] CLIP 未加载，无法建索引")
        return 2

    ids: list[str] = []
    files: list[str] = []
    vecs: list[np.ndarray] = []
    for index, (work_id, path) in enumerate(entries, 1):
        try:
            image = open_rgb(Image.open(path))
            vec = build_inputs(image)[:512]
            ids.append(work_id)
            files.append(path.name)
            vecs.append(vec)
            print(f"  [{index:02d}/{len(entries)}] {work_id:<12} {path.name}")
        except Exception as exc:  # noqa: BLE001 单张坏图不该中断整批
            print(f"  [skip] {work_id}: {exc}")

    if not ids:
        print("[x] 没有任何可用向量")
        return 3

    mat = np.vstack(vecs).astype(np.float32)
    np.savez_compressed(MODEL_DIR / "works.embed.npz", ids=np.array(ids), vecs=mat, files=np.array(files))
    meta = {
        "count": len(ids),
        "dim": int(mat.shape[1]),
        "clipModel": os.environ.get("CLIP_MODEL", "openai/clip-vit-base-patch32"),
        "source": "models/works.manifest.json",
    }
    (MODEL_DIR / "works.index.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[ok] 索引 {len(ids)} 条 {mat.shape} -> models/works.embed.npz")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
