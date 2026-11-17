"""把新增作品追加为一个 NPZ 分片，不重建基索引。

用法（cwd 为 ``ai-classifier``）：
    .\\.venv\\Scripts\\python.exe tools\\update_work_index.py
    .\\.venv\\Scripts\\python.exe tools\\update_work_index.py --id w-new

脚本按 manifest 中的 id 与现有 base/shards 去重，只对缺少的图片运行一次
CLIP + color24。分片与基索引共用 color_mu/color_sigma，WorkIndex 会自动发现。
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

PKG = Path(__file__).resolve().parents[1]
MODEL_DIR = PKG / "models"
MANIFEST = MODEL_DIR / "works.manifest.json"
if str(PKG) not in sys.path:
    sys.path.insert(0, str(PKG))


def _manifest_entries(data: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    from tools.build_works_index import resolve_local

    for key in ("works", "spiralWorks"):
        for item in data.get(key, []):
            work_id = str(item.get("id", ""))
            if not work_id or work_id in seen:
                continue
            seen.add(work_id)
            path = resolve_local(str(item.get("imageUrl", "")), item)
            if path is not None:
                out.append({"id": work_id, "path": path, "item": item})
    return out


def _existing_ids(base: Path, meta: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    paths = [base]
    paths.extend(MODEL_DIR / str(item) for item in meta.get("shards", []))
    for path in paths:
        if not path.exists():
            continue
        with np.load(path, allow_pickle=False) as data:
            ids.update(str(item) for item in data["ids"])
    return ids


def main() -> int:
    ap = argparse.ArgumentParser(description="append missing works as an NPZ shard")
    ap.add_argument("--id", action="append", dest="ids", help="只追加指定作品 id，可重复传入")
    args = ap.parse_args()
    if not MANIFEST.exists():
        print(f"[x] 缺 {MANIFEST}")
        return 1
    base = MODEL_DIR / "works.embed.npz"
    meta_path = MODEL_DIR / "works.index.json"
    if not base.exists() or not meta_path.exists():
        print("[x] 缺少基索引，请先运行 tools/build_works_index.py")
        return 1
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    existing = _existing_ids(base, meta)
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    wanted = set(args.ids or [])
    entries = [e for e in _manifest_entries(data) if e["id"] not in existing and (not wanted or e["id"] in wanted)]
    if not entries:
        print(f"[ok] 无需追加（已有 {len(existing)} 条）")
        return 0

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    from PIL import Image
    from pipeline.colorfeat import color_features, open_rgb
    from pipeline.serve import _startup, _state, build_inputs

    _startup()
    if not _state.get("clip_ok"):
        print("[x] CLIP 未加载，无法增量建索引")
        return 2
    ids: list[str] = []
    files: list[str] = []
    vecs: list[np.ndarray] = []
    colors: list[np.ndarray] = []
    tags: list[list[str]] = []
    started = time.perf_counter()
    for entry in entries:
        try:
            image = open_rgb(Image.open(entry["path"]))
            ids.append(entry["id"])
            try:
                files.append(str(entry["path"].resolve().relative_to(PKG.parent)).replace("\\", "/"))
            except ValueError:
                files.append(entry["path"].name)
            vecs.append(build_inputs(image)[:512])
            colors.append(color_features(image))
            item = entry["item"]
            tags.append([str(tag) for tag in (item.get("styles") or []) + (item.get("types") or [])])
            print(f"  [ok] {entry['id']:<12} {entry['path'].name}")
        except Exception as exc:  # noqa: BLE001
            print(f"  [skip] {entry['id']}: {exc}")
    if not ids:
        print("[x] 没有新增可用图片")
        return 3

    with np.load(base, allow_pickle=False) as old:
        mu = np.asarray(old["color_mu"], dtype=np.float32) if "color_mu" in old else np.zeros(24, dtype=np.float32)
        sigma = np.asarray(old["color_sigma"], dtype=np.float32) if "color_sigma" in old else np.ones(24, dtype=np.float32)
    shard_dir = MODEL_DIR / "works.shards"
    shard_dir.mkdir(parents=True, exist_ok=True)
    shard_name = f"shard-{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 1000000:06d}.npz"
    shard_path = shard_dir / shard_name
    np.savez_compressed(
        shard_path, ids=np.array(ids), files=np.array(files), vecs=np.vstack(vecs).astype(np.float32),
        color24=np.vstack(colors).astype(np.float32),
        tags_json=np.array([json.dumps(item, ensure_ascii=False) for item in tags]),
        color_mu=mu, color_sigma=sigma,
    )
    shards = [str(item) for item in meta.get("shards", [])]
    rel = str(shard_path.relative_to(MODEL_DIR)).replace("\\", "/")
    if rel not in shards:
        shards.append(rel)
    meta["shards"] = shards
    meta["count"] = len(existing) + len(ids)
    meta["lastIncrement"] = {"count": len(ids), "shard": rel, "elapsedMs": round((time.perf_counter() - started) * 1000, 1)}
    tmp_meta = meta_path.with_suffix(meta_path.suffix + ".tmp")
    tmp_meta.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp_meta, meta_path)
    print(f"[ok] 增量 {len(ids)} 条 -> {shard_path}，耗时 {meta['lastIncrement']['elapsedMs']}ms；总数 {meta['count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

