"""流式下载 hf-mirror 上的大文件（支持断点续传）。

huggingface_hub 的 hf_hub_download 在这台机器上会卡在 0 字节（它的 HEAD/锁流程被镜像挡），
但带 Range 的 GET 是通的（206），所以这里自己拼请求。
"""
import os
import sys
import time
import urllib.request


def download(url: str, dest: str, chunk: int = 4 * 1024 * 1024) -> str:
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    have = os.path.getsize(dest) if os.path.exists(dest) else 0
    headers = {"User-Agent": "Mozilla/5.0"}
    if have:
        headers["Range"] = f"bytes={have}-"
    req = urllib.request.Request(url, headers=headers)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=60) as r:
        total = r.headers.get("Content-Length")
        total = int(total) + have if total and total.isdigit() else None
        mode = "ab" if have and r.status == 206 else "wb"
        if mode == "wb":
            have = 0
        with open(dest, mode) as fh:
            while True:
                buf = r.read(chunk)
                if not buf:
                    break
                fh.write(buf)
                have += len(buf)
                if total:
                    pct = have / total * 100
                    speed = have / 1024 / 1024 / max(1e-6, time.time() - t0)
                    print(f"\r  {have/1024/1024:8.1f}/{total/1024/1024:.1f} MB  {pct:5.1f}%  {speed:5.1f} MB/s",
                          end="", file=sys.stderr)
    print("", file=sys.stderr)
    return dest


if __name__ == "__main__":
    url, dest = sys.argv[1], sys.argv[2]
    path = download(url, dest)
    print(f"OK {path} {os.path.getsize(path)/1024/1024:.1f} MB")
