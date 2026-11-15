"""GitHub 上找可下载的摄影/场景数据集仓库，并探测直链是否还活着。"""
import json
import urllib.parse
import urllib.request

UA = "dsh-dataset-probe"


def gh_search(q: str, per: int = 8) -> dict:
    url = ("https://api.github.com/search/repositories?q=" + urllib.parse.quote(q)
           + f"&sort=stars&per_page={per}")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read())


def head(url: str) -> str:
    """只读前 1KB，判断链接是否可用 + 看是不是 zip。"""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            head = r.read(1024)
            ctype = r.headers.get("Content-Type", "")
            clen = r.headers.get("Content-Length", "?")
            kind = "ZIP" if head[:2] == b"PK" else repr(head[:24])
            return f"{r.status} {ctype} len={clen} {kind}"
    except Exception as exc:  # noqa: BLE001
        return f"FAIL {type(exc).__name__}: {str(exc)[:70]}"


def main() -> int:
    print("======== 1) GitHub 仓库搜索 ========")
    for q in ["photography dataset", "photo style dataset", "image style classification",
              "摄影 数据集", "camera scene detection dataset", "photo aesthetic dataset"]:
        try:
            d = gh_search(q)
        except Exception as exc:  # noqa: BLE001
            print(f"== {q}: FAIL {exc}")
            continue
        print(f"== {q}  (total {d['total_count']})")
        for it in d["items"][:6]:
            lic = (it.get("license") or {}).get("spdx_id")
            desc = (it.get("description") or "")[:64]
            print(f"   {it['stargazers_count']:>5}* {it['full_name']:46s} {str(lic):10s} {desc}")
        print()

    print("======== 2) 直链探测 ========")
    urls = [
        "http://data.vision.ee.ethz.ch/ihnatova/camera_scene_detection_train.zip",
        "https://data.vision.ee.ethz.ch/ihnatova/camera_scene_detection_train.zip",
        "https://data.vision.ee.ethz.ch/ihnatova/camera_scene_detection_validation.zip",
    ]
    for u in urls:
        print(f"   {u}\n      -> {head(u)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
