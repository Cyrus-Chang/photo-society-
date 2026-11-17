"""可复跑的多模态识别回归与性能评估。

默认只使用仓库内已存在的图片和标签，不下载数据、不写模型：

    # 先启动服务（或传 --start-server 让脚本临时启动）
    python tools/eval_multimodal.py --start-server

输出 .review-tmp/multimodal-eval.json，包含 30 张分层样本的混淆表、
本地可发现的人像样本的门控前后误报率，以及冷/热/并发 4 的实测数字。
如果仓库没有 20 张带有「人像」人工标注的本地图片，脚本会明确写出
available/required，不会把不足的样本补成数字。

只使用 Python 标准库，避免为评估引入新依赖。
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import statistics
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib import error, request


TOOL_DIR = Path(__file__).resolve().parent
PKG_DIR = TOOL_DIR.parent
REPO_DIR = PKG_DIR.parent
DEFAULT_URL = os.environ.get("AI_SERVICE_URL", "http://127.0.0.1:8100").rstrip("/")
PORTRAIT_REQUIRED = 20


def _read_dataset_rows() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    labels_path = PKG_DIR / "labels.csv"
    if not labels_path.exists():
        return rows
    with labels_path.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            raw = (row.get("path") or "").strip()
            path = Path(raw)
            if not path.exists() and not path.is_absolute():
                path = PKG_DIR / path
            if path.exists() and path.is_file():
                rows.append({"path": str(path), "subject": row.get("subject", "").strip()})
    return rows


def _stratified(rows: Sequence[Dict[str, str]], n: int) -> List[Dict[str, str]]:
    """稳定地按 subject 轮流取样，确保 30 张不会只来自一个类别。"""
    groups: Dict[str, List[Dict[str, str]]] = {}
    for row in sorted(rows, key=lambda item: item["path"]):
        groups.setdefault(row["subject"], []).append(row)
    groups = {key: value for key, value in groups.items() if key}
    if not groups:
        return []
    keys = sorted(groups)
    picked: List[Dict[str, str]] = []
    cursor = {key: 0 for key in keys}
    while len(picked) < n:
        progressed = False
        for key in keys:
            index = cursor[key]
            if index < len(groups[key]) and len(picked) < n:
                picked.append(groups[key][index])
                cursor[key] += 1
                progressed = True
        if not progressed:
            break
    return picked


def _portrait_manifest(custom: Optional[str] = None) -> List[Dict[str, str]]:
    """从 mock 中读取有本地文件且人工标记为人像的作品。

    只把同一行同时出现 localWorkUrl 与 types: ['人像'] 的记录纳入，
    因此不会把标题或模型输出当成人工标签。
    """
    if custom:
        manifest = Path(custom)
        if not manifest.is_absolute():
            manifest = REPO_DIR / manifest
        if manifest.exists():
            paths: List[str] = []
            if manifest.suffix.lower() == ".json":
                payload = json.loads(manifest.read_text(encoding="utf-8"))
                values = payload if isinstance(payload, list) else payload.get("paths", [])
                paths = [str(value.get("path") if isinstance(value, dict) else value) for value in values]
            else:
                paths = [line.strip() for line in manifest.read_text(encoding="utf-8").splitlines()
                         if line.strip() and not line.lstrip().startswith("#")]
            result: List[Dict[str, str]] = []
            for raw in paths:
                path = Path(raw)
                if not path.is_absolute():
                    path = REPO_DIR / path
                if path.exists() and path.is_file():
                    result.append({"path": str(path), "subject": "PORTRAIT"})
            return result
    mock_path = REPO_DIR / "src" / "data" / "mock.ts"
    if not mock_path.exists():
        return []
    found: List[Dict[str, str]] = []
    pattern = re.compile(r"localWorkUrl\(['\"]([^'\"]+)['\"]\).*?types:\s*\[([^\]]*)\]")
    for line in mock_path.read_text(encoding="utf-8").splitlines():
        match = pattern.search(line)
        if not match or "人像" not in match.group(2):
            continue
        path = REPO_DIR / "public" / "works" / match.group(1)
        if path.exists():
            found.append({"path": str(path), "subject": "PORTRAIT"})
    unique: Dict[str, Dict[str, str]] = {item["path"]: item for item in found}
    return [unique[key] for key in sorted(unique)]


def _multipart(path: str) -> Tuple[bytes, str]:
    boundary = "----codex-multimodal-eval"
    filename = Path(path).name
    payload = Path(path).read_bytes()
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        "Content-Type: application/octet-stream\r\n\r\n"
    ).encode("utf-8")
    body = head + payload + f"\r\n--{boundary}--\r\n".encode("ascii")
    return body, f"multipart/form-data; boundary={boundary}"


def classify(base_url: str, path: str, timeout: float = 120.0) -> Tuple[Dict[str, Any], float]:
    body, content_type = _multipart(path)
    req = request.Request(
        f"{base_url}/v1/classify",
        data=body,
        headers={"Content-Type": content_type, "Accept": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with request.urlopen(req, timeout=timeout) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    return parsed, round((time.perf_counter() - started) * 1000, 1)


def _code(items: Any) -> Optional[str]:
    if not isinstance(items, list) or not items:
        return None
    first = items[0]
    return str(first.get("code")) if isinstance(first, dict) and first.get("code") else None


def _subject_pair(result: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """读取门控前/后的题材结果，兼容门控字段尚未部署的旧服务。"""
    raw = _code(result.get("subjectRaw")) or _code(result.get("subject"))
    visible = _code(result.get("subjectVisible"))
    if visible is None and "subjectVisible" not in result:
        visible = _code(result.get("subject"))
    return raw, visible


def _confusion(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, int]]:
    table: Dict[str, Dict[str, int]] = {}
    for row in rows:
        expected = row.get("expected") or "UNKNOWN"
        predicted = row.get("predicted") or "GATED_OUT"
        table.setdefault(expected, {})[predicted] = table.setdefault(expected, {}).get(predicted, 0) + 1
    return table


def _percent(numerator: int, denominator: int) -> Optional[float]:
    return round(numerator / denominator * 100, 1) if denominator else None


def _run_sample_eval(base_url: str, sample_rows: Sequence[Dict[str, str]]) -> Dict[str, Any]:
    output_rows: List[Dict[str, Any]] = []
    for item in sample_rows:
        try:
            result, elapsed = classify(base_url, item["path"])
            raw, visible = _subject_pair(result)
            output_rows.append({
                "path": str(Path(item["path"]).relative_to(REPO_DIR)) if Path(item["path"]).is_relative_to(REPO_DIR) else item["path"],
                "expected": item["subject"],
                "predictedRaw": raw,
                "predicted": visible,
                "needsReview": bool(result.get("needsReview", False)),
                "latencyMs": elapsed,
            })
        except (OSError, ValueError, error.URLError, json.JSONDecodeError) as exc:
            output_rows.append({"path": item["path"], "expected": item["subject"], "error": str(exc)})
    valid = [row for row in output_rows if "error" not in row]
    return {
        "requested": len(sample_rows),
        "evaluated": len(valid),
        "rows": output_rows,
        "confusion": _confusion({"expected": row["expected"], "predicted": row["predicted"]} for row in valid),
        "rawConfusion": _confusion({"expected": row["expected"], "predicted": row["predictedRaw"]} for row in valid),
        "latencyMs": {
            "p50": round(statistics.median([row["latencyMs"] for row in valid]), 1) if valid else None,
            "max": round(max(row["latencyMs"] for row in valid), 1) if valid else None,
        },
    }


def _run_portrait_eval(base_url: str, portrait_rows: Sequence[Dict[str, str]]) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for item in portrait_rows:
        try:
            result, elapsed = classify(base_url, item["path"])
            raw, visible = _subject_pair(result)
            rows.append({"path": item["path"], "raw": raw, "visible": visible, "latencyMs": elapsed})
        except (OSError, ValueError, error.URLError, json.JSONDecodeError) as exc:
            rows.append({"path": item["path"], "error": str(exc)})
    valid = [row for row in rows if "error" not in row]
    raw_fp = sum(row["raw"] is not None for row in valid)
    visible_fp = sum(row["visible"] is not None for row in valid)
    return {
        "required": PORTRAIT_REQUIRED,
        "available": len(portrait_rows),
        "evaluated": len(valid),
        "sufficientFor20": len(valid) >= PORTRAIT_REQUIRED,
        "before": {"falsePositive": raw_fp, "falsePositiveRate": _percent(raw_fp, len(valid))},
        "after": {"falsePositive": visible_fp, "falsePositiveRate": _percent(visible_fp, len(valid))},
        "rows": rows,
        "limitation": None if len(valid) >= PORTRAIT_REQUIRED else "仓库内只有本地人工标注人像样本，未达到 20 张；未用远程图片或模型猜测补齐。",
    }


def _performance(base_url: str, sample_path: Optional[str]) -> Dict[str, Any]:
    if not sample_path:
        return {"skipped": True, "reason": "没有可用图片样本"}
    result: Dict[str, Any] = {}
    try:
        _, cold = classify(base_url, sample_path)
        hot_times = [classify(base_url, sample_path)[1] for _ in range(4)]
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(classify, base_url, sample_path) for _ in range(4)]
            concurrent = [future.result()[1] for future in futures]
        wall = round((time.perf_counter() - started) * 1000, 1)
        result.update({
            "sample": sample_path,
            "coldFirstRequestMs": cold,
            "hotSequentialMs": hot_times,
            "hotSequentialP50Ms": round(statistics.median(hot_times), 1),
            "concurrency4": {
                "wallMs": wall,
                "requestMs": concurrent,
                "p50Ms": round(statistics.median(concurrent), 1),
                "maxMs": round(max(concurrent), 1),
                "degradationVsHotP50": round(statistics.median(concurrent) / max(statistics.median(hot_times), 0.1), 2),
            },
        })
    except (OSError, ValueError, error.URLError, json.JSONDecodeError) as exc:
        result["error"] = str(exc)
    return result


def _wait_for_service(base_url: str, process: Optional[subprocess.Popen[bytes]]) -> None:
    try:
        wait_seconds = max(1.0, float(os.environ.get("EVAL_HEALTH_TIMEOUT_SEC", "90")))
    except ValueError:
        wait_seconds = 90.0
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        try:
            req = request.Request(f"{base_url}/v1/health", method="GET")
            with request.urlopen(req, timeout=2):
                return
        except (OSError, error.URLError):
            if process and process.poll() is not None:
                raise RuntimeError("服务进程提前退出")
            time.sleep(0.5)
    raise RuntimeError(f"等待服务超时：{base_url}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="FastAPI 基地址")
    parser.add_argument("--start-server", action="store_true", help="临时启动 uvicorn，退出时终止")
    parser.add_argument("--output", default=str(REPO_DIR / ".review-tmp" / "multimodal-eval.json"))
    parser.add_argument("--sample-count", type=int, default=30)
    parser.add_argument("--portrait-manifest", help="可选的人像图片路径清单（每行一个，或 JSON 数组）")
    parser.add_argument("--skip-perf", action="store_true")
    args = parser.parse_args()

    process: Optional[subprocess.Popen[bytes]] = None
    if args.start_server:
        env = os.environ.copy()
        env.setdefault("HF_HUB_OFFLINE", "1")
        env.setdefault("TRANSFORMERS_OFFLINE", "1")
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "pipeline.serve:app", "--host", "127.0.0.1", "--port", "8100"],
            cwd=str(PKG_DIR), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        dataset = _stratified(_read_dataset_rows(), args.sample_count)
        portraits = _portrait_manifest(args.portrait_manifest)
        try:
            _wait_for_service(args.url, process)
        except Exception as exc:
            report = {
                "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "service": args.url,
                "serviceError": str(exc),
                "sampleInventory": {"available": len(_read_dataset_rows()), "requested": args.sample_count},
                "portraitGateEval": {
                    "required": PORTRAIT_REQUIRED,
                    "available": len(portraits),
                    "evaluated": 0,
                    "sufficientFor20": False,
                    "limitation": "识别服务未启动，未取得门控前后误报率。",
                },
                "performance": {"skipped": True, "reason": "识别服务未启动，未取得冷/热/并发数字。"},
                "limitations": [
                    "服务等待超时；没有把模型加载失败或性能数字当作成功结果。",
                    "人像真实对比仍需至少 20 张人工确认图片。",
                ],
            }
            output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"serviceError": str(exc), "portraitAvailable": len(portraits), "output": str(output)}, ensure_ascii=False))
            return 2
        sample_eval = _run_sample_eval(args.url, dataset)
        portrait_eval = _run_portrait_eval(args.url, portraits)
        perf = _performance(args.url, dataset[0]["path"] if dataset and not args.skip_perf else None)
        report = {
            "generatedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "service": args.url,
            "sampleEval": sample_eval,
            "portraitGateEval": portrait_eval,
            "performance": perf,
            "limitations": [
                "冷启动数字只有在 --start-server 时才代表本次进程的首个请求；未传该参数时是当前服务进程的首请求。",
                "人像前后误报率只对仓库内存在且 mock.ts 明确标记为人像的本地图片统计。",
            ],
        }
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({
            "samples": f"{sample_eval['evaluated']}/{sample_eval['requested']}",
            "portrait": f"{portrait_eval['evaluated']}/{portrait_eval['required']}",
            "portraitBeforeFalsePositiveRate": portrait_eval["before"]["falsePositiveRate"],
            "portraitAfterFalsePositiveRate": portrait_eval["after"]["falsePositiveRate"],
            "coldFirstRequestMs": perf.get("coldFirstRequestMs"),
            "hotP50Ms": perf.get("hotSequentialP50Ms"),
            "concurrency4Degradation": (perf.get("concurrency4") or {}).get("degradationVsHotP50"),
            "output": str(output),
        }, ensure_ascii=False))
        return 0
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    raise SystemExit(main())
