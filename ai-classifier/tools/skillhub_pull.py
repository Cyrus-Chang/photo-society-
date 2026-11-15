"""从 skillhub.cn 拉取技能包到本地暂存目录（校验 sha256）。"""
import hashlib
import json
import os
import urllib.parse
import urllib.request

STAGE = r"E:\通用型摄影师接单平台\.skillstage"
MANIFEST = r"E:\通用型摄影师接单平台\.skillfiles.json"
UA = "@montersy123/dsh-skill-market/0.1"


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main() -> int:
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    for slug, m in manifest.items():
        ns = (m.get("namespace") or {}).get("handle")
        ver = m.get("version")
        for f in m.get("files", []):
            path = f["path"]
            query = urllib.parse.urlencode({"path": path, "namespace": ns, "version": ver})
            url = f"https://api.skillhub.cn/api/v1/skills/{urllib.parse.quote(slug)}/file?{query}"
            data = get(url)
            digest = hashlib.sha256(data).hexdigest()
            ok = "OK" if digest == f["sha256"] else "MISMATCH"
            dst = os.path.join(STAGE, slug, *path.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as fh:
                fh.write(data)
            print(f"{slug:45s} {path:22s} {len(data):7d}B sha256={ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
