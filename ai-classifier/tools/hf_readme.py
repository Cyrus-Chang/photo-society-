"""抓两个数据集的 README（urllib 会自动跟随 308 重定向）。"""
import sys
import urllib.request

from pipeline.console import ensure_utf8

URLS = [
    "https://hf-mirror.com/datasets/RayyanAhmed9477/pexels-advertisement-photography/raw/main/README.md",
    "https://hf-mirror.com/datasets/devoppro/Nature-Cinematic-Photography/raw/main/README.md",
    "https://hf-mirror.com/datasets/RayyanAhmed9477/pexels-advertisement-photography/resolve/main/README.md",
]


def main() -> int:
    ensure_utf8()
    for u in URLS:
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=40) as r:
                body = r.read().decode("utf-8", "replace")
            print("=" * 70)
            print(u, "->", len(body), "chars")
            print(body[:1200])
        except Exception as exc:  # noqa: BLE001
            print("=" * 70)
            print(u, "FAIL", type(exc).__name__, str(exc)[:80])
    return 0


if __name__ == "__main__":
    sys.path.insert(0, r"E:\通用型摄影师接单平台\ai-classifier")
    raise SystemExit(main())
