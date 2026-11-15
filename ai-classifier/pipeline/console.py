"""控制台编码兜底。

Windows 下 Python 的 stdout 默认跟着控制台代码页走（中文系统是 cp936/GBK），
而 prepare.py 的报告里有 `⚠`——GBK 打不出来，会直接 UnicodeEncodeError 崩掉，
且崩在"报告最后一段"，最容易让人误以为是数据有问题。

在进入 main() 时调用 ensure_utf8()，把两个流切成 UTF-8 + replace，
实在切不动也不至于因为一个符号把整条命令搞挂。
"""

from __future__ import annotations

import sys


def ensure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        enc = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        if enc in ("utf8", "utf8mb4"):
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")   # type: ignore[attr-defined]
        except Exception:   # 被重定向成管道/文件、或非 TextIOWrapper 时忽略
            pass
