"""构建作品混合检索索引。

用法（cwd 为 ``ai-classifier``）：
    .\\.venv\\Scripts\\python.exe tools\\build_works_index.py

输出 ``models/works.embed.npz``，包含 CLIP 512 维向量、已有 color24、
manifest 标签和色彩标准化统计。增量作品写入 ``models/works.shards``，
不会覆盖基索引；见 ``tools/update_work_index.py``。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[2]
PKG = Path(__file__).resolve().parents[1]
MODEL_DIR = PKG / "models"
MANIFEST = MODEL_DIR / "works.manifest.json"

if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))


def resolve_local(image_url: str, item: dict[str, Any] | None = None) -> Path | None:
    """把 manifest URL 落回磁盘路径，支持下载后的 ``/works`` 外链副本。"""
    candidates: list[Path] = []
    if item:
        for key in ("localPath", "localFile", "cachedPath"):
            value = item.get(key)
            if value:
                candidates.append(Path(str(value)))
    if image_url.startswith("/src/assets/"):
        candidates.append(REPO / image_url.lstrip("/"))
    elif image_url.startswith("/works/"):
        candidates.append(REPO / "public" / image_url.lstrip("/"))
    for path in candidates:
        if not path.is_absolute():
            path = REPO / path
        if path.exists():
            return path
    return None


def _entries(data: dict[str, Any]) -> tuple[list[tuple[str, Path, dict[str, Any]]], int]:
    entries: list[tuple[str, Path, dict[str, Any]]] = []
    seen: set[str] = set()
    remote = 0
    for key in ("works", "spiralWorks"):
        for item in data.get(key, []):
            work_id = item.get("id")
            if not work_id or work_id in seen:
                continue
            seen.add(work_id)
            path = resolve_local(str(item.get("imageUrl", "")), item)
            if path is None:
                remote += 1
                continue
            entries.append((str(work_id), path, item))
    return entries, remote


def _write_index(ids: list[str], files: list[str], vecs: list[np.ndarray], colors: list[np.ndarray],
                 tags: list[list[str]], output: Path) -> tuple[np.ndarray, np.ndarray]:
    mat = np.vstack(vecs).astype(np.float32)
    color_mat = np.vstack(colors).astype(np.float32)
    color_mu = color_mat.mean(axis=0).astype(np.float32)
    color_sigma = color_mat.std(axis=0).astype(np.float32)
    color_sigma[color_sigma < 1e-4] = 1.0
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        ids=np.array(ids), files=np.array(files), vecs=mat,
        color24=color_mat,
        tags_json=np.array([json.dumps(item, ensure_ascii=False) for item in tags]),
        color_mu=color_mu, color_sigma=color_sigma,
    )
    return color_mu, color_sigma


def main() -> int:
    if not MANIFEST.exists():
        print(f"[x] 缺 {MANIFEST}，先导出真实 manifest")
        return 1
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries, remote = _entries(data)
    unique = len({item.get("id") for key in ("works", "spiralWorks") for item in data.get(key, []) if item.get("id")})
    print(f"[i] 唯一作品 {unique}，本地可索引 {len(entries)}，远程跳过 {remote}")

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    from PIL import Image
    from pipeline.colorfeat import FEATURE_NAMES, color_features, open_rgb
    from pipeline.serve import _startup, _state, build_inputs

    _startup()
    if not _state.get("clip_ok"):
        print("[x] CLIP 未加载，无法建索引")
        return 2

    ids: list[str] = []
    files: list[str] = []
    vecs: list[np.ndarray] = []
    colors: list[np.ndarray] = []
    tags: list[list[str]] = []
    for index, (work_id, path, item) in enumerate(entries, 1):
        try:
            image = open_rgb(Image.open(path))
            vec = build_inputs(image)[:512]
            ids.append(work_id)
            try:
                files.append(str(path.resolve().relative_to(REPO)).replace("\\", "/"))
            except ValueError:
                files.append(path.name)
            vecs.append(vec)
            colors.append(color_features(image))
            tags.append([str(tag) for tag in (item.get("styles") or []) + (item.get("types") or [])])
            print(f"  [{index:02d}/{len(entries)}] {work_id:<12} {path.name}")
        except Exception as exc:  # noqa: BLE001
            print(f"  [skip] {work_id}: {exc}")

    if not ids:
        print("[x] 没有任何可用向量")
        return 3
    output = MODEL_DIR / "works.embed.npz"
    color_mu, color_sigma = _write_index(ids, files, vecs, colors, tags, output)
    # Rebuilding the base starts a clean shard set; stale shards would duplicate ids.
    shard_dir = MODEL_DIR / "works.shards"
    if shard_dir.exists():
        for shard in shard_dir.glob("*.npz"):
            shard.unlink()
    meta = {
        "format": 2, "count": len(ids), "dim": int(np.vstack(vecs).shape[1]), "colorDim": 24,
        "clipModel": os.environ.get("CLIP_MODEL", "openai/clip-vit-base-patch32"),
        "source": "models/works.manifest.json", "base": output.name, "shards": [],
        "weights": {"vector": 0.65, "tags": 0.20, "color": 0.15},
        "colorFeatureNames": FEATURE_NAMES,
        "colorMu": [round(float(x), 7) for x in color_mu],
        "colorSigma": [round(float(x), 7) for x in color_sigma],
    }
    (MODEL_DIR / "works.index.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[ok] 索引 {len(ids)} 条 {np.vstack(vecs).shape} -> {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
