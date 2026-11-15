"""按 slug+namespace 拉取候选技能的全部文件到暂存目录（校验 sha256）。"""
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request

STAGE = r"E:\通用型摄影师接单平台\.skillstage"
UA = "@montersy123/dsh-skill-market/0.1"
CANDS = [
    ("tobemsk-image-search", "@clawhub_tobemsk"),
    ("image-utils", "@clawhub_galbria"),
    ("image-cropper", "@clawhub_mingo-318"),
]


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main() -> int:
    summary = []
    for slug, ns in CANDS:
        manifest = json.loads(get(
            f"https://api.skillhub.cn/api/v1/skills/{urllib.parse.quote(slug)}/files"
            f"?namespace={urllib.parse.quote(ns)}"
        ))
        total = 0
        for f in manifest.get("files", []):
            path = f["path"]
            query = urllib.parse.urlencode({"path": path, "namespace": ns, "version": manifest["version"]})
            data = get(f"https://api.skillhub.cn/api/v1/skills/{urllib.parse.quote(slug)}/file?{query}")
            ok = hashlib.sha256(data).hexdigest() == f["sha256"]
            dst = os.path.join(STAGE, slug, *path.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as fh:
                fh.write(data)
            total += len(data)
            print(f"{slug:28s} {path:34s} {len(data):7d}B {'OK' if ok else 'MISMATCH'}")
        summary.append((slug, ns, manifest["version"], len(manifest.get("files", [])), total))
    print("\n".join(f"{s:28s} {n:28s} v{v} files={c} bytes={b}" for s, n, v, c, b in summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
