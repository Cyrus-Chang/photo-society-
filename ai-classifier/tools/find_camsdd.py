"""找 CamSDD（相机场景检测，30 类 9897 张）的可用镜像，并探测备用下载地址。"""
import json
import sys
import urllib.parse
import urllib.request

from pipeline.console import ensure_utf8

UA = "dsh-probe"
CANDIDATE_URLS = [
    "https://data.vision.ee.ethz.ch/ihnatova/camera_scene_detection_train.zip",
    "https://data.vision.ee.ethz.ch/cvl/ihnatova/camera_scene_detection_train.zip",
    "http://data.vision.ee.ethz.ch/cvl/camera_scene_detection_train.zip",
    "https://www.kaggle.com/datasets/ihnatova/camera-scene-detection",
]


def gh(q: str, kind: str = "repositories") -> dict:
    url = f"https://api.github.com/search/{kind}?q=" + urllib.parse.quote(q) + "&per_page=8"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def probe(url: str) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            head = r.read(256)
            size = r.headers.get("Content-Length")
            mb = f"{int(size)/1024/1024:.0f}MB" if size and size.isdigit() else "?"
            print(f"  OK  {mb:>8s}  {url}")
            print(f"      首字节 {head[:16]!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"  404/FAIL {type(exc).__name__}: {str(exc)[:44]:46s} {url}")


def main() -> int:
    ensure_utf8()
    print("== GitHub 仓库搜索")
    for q in ["camera scene detection", "CamSDD", "camera_scene_detection dataset mirror"]:
        try:
            d = gh(q)
        except Exception as exc:  # noqa: BLE001
            print(f"   {q}: FAIL {exc}")
            continue
        print(f"   [{q}] total={d['total_count']}")
        for it in d["items"][:6]:
            print(f"      {it['stargazers_count']:>4}* {it['full_name']:48s} {(it.get('description') or '')[:60]}")

    print("\n== 直链探测")
    for u in CANDIDATE_URLS:
        probe(u)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, r"E:\通用型摄影师接单平台\ai-classifier")
    raise SystemExit(main())
