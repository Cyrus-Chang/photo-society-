"""为作品库生成 dHash 表（作品查重的底座）。

产物：``models/works.phash.json``

    { "version": "phash-8x8-1", "size": 8, "generatedAt": "...",
      "count": 50, "entries": [{"id": "w-001", "file": "src/assets/...", "phash": 1234}, ...] }

只读索引里记录的文件路径，不重新编码图片、不训练模型。索引新增作品后重跑即可。

用法（cwd 必须是 ai-classifier）：
    .\.venv\Scripts\python.exe tools\build_audit_index.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

from pipeline.audit import dhash  # noqa: E402

INDEX_PATH = ROOT / "models" / "works.embed.npz"
OUT_PATH = ROOT / "models" / "works.phash.json"
REPO_ROOT = ROOT.parent


def main(argv: list[str] | None = None) -> int:
    import numpy as np

    argv = list(argv if argv is not None else sys.argv[1:])
    out_path = OUT_PATH
    if "--out" in argv:
        out_path = (ROOT / argv[argv.index("--out") + 1]).resolve()

    data = np.load(INDEX_PATH, allow_pickle=False)
    ids = [str(item) for item in data["ids"]]
    files = [str(item) for item in data["files"]]
    entries: list[dict] = []
    missing: list[str] = []
    for work_id, file_str in zip(ids, files):
        path = (REPO_ROOT / file_str).resolve()
        if not path.exists():
            missing.append(file_str)
            continue
        with Image.open(path) as img:
            entries.append({"id": work_id, "file": file_str, "phash": dhash(img)})
    payload = {
        "version": "phash-8x8-1",
        "size": 8,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "works.embed.npz 的 ids/files",
        "count": len(entries),
        "entries": entries,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if "--stdout" in argv:
        # 受限沙箱里子进程写不了工作区文件：把 JSON 打到 stdout，由调用方落盘。
        print(json.dumps(payload, ensure_ascii=True))
        return 0
    out_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"[ok] {out_path.name}: {len(entries)} 条哈希" + (f"，缺失图片 {len(missing)}" if missing else ""))
    if missing:
        print("[warn] 缺图:", ", ".join(missing[:5]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
