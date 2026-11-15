"""风格锚图目录名 → 标签字典 code 的别名表。

锚图目录给人看，用中文最省事；但训练/推理里用的是字典 code（JAPANESE、HK_RETRO…）。
这里做一层映射，中文、英文、大小写混写都能认。
"""
from __future__ import annotations

from pathlib import Path

# code -> 可接受的目录名（第一个是推荐的中文名）
STYLE_NAMES: dict[str, list[str]] = {
    "JAPANESE":  ["日系", "JAPANESE", "japanese", "jp"],
    "KOREAN":    ["韩系", "KOREAN", "korean", "kr"],
    "INS":       ["ins风", "INS", "ins", "instagram"],
    "FRESH":     ["清新", "FRESH", "fresh"],
    "FILM":      ["胶片", "FILM", "film"],
    "VINTAGE":   ["复古", "VINTAGE", "vintage"],
    "CINEMATIC": ["电影感", "CINEMATIC", "cinematic"],
    "DARK_MOOD": ["暗调", "DARK_MOOD", "dark_mood", "dark"],
    "MONO":      ["黑白", "MONO", "mono", "bw", "黑白照"],
    "BLUE_TONE": ["蓝调", "BLUE_TONE", "blue_tone", "blue"],
    "HK_RETRO":  ["港风", "HK_RETRO", "hk_retro", "hk"],
    "CYBER":     ["赛博", "赛博朋克", "CYBER", "cyber", "cyberpunk"],
    "WESTERN":   ["欧美", "WESTERN", "western"],
}

# 反查表：小写别名 -> code
_LOOKUP = {}
for _code, _names in STYLE_NAMES.items():
    for _n in _names:
        _LOOKUP[_n.strip().lower()] = _code

CODES = list(STYLE_NAMES.keys())


def style_code(dirname: str) -> str | None:
    """把目录名解析成标签 code；认不出返回 None。"""
    key = dirname.strip().lower()
    if key in _LOOKUP:
        return _LOOKUP[key]
    # 容忍 "01-日系" / "日系_锚图" 这类前缀后缀
    for alias, code in _LOOKUP.items():
        if alias and alias in key:
            return code
    return None


def preferred_dirname(code: str) -> str:
    return STYLE_NAMES[code][0]


def scan(root: Path) -> dict[str, list[Path]]:
    """扫描锚图根目录，返回 {code: [图片路径…]}。空目录也会以空列表出现。"""
    from PIL import Image  # noqa: F401  仅为类型可用性，调用方自己读图

    exts = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    out: dict[str, list[Path]] = {c: [] for c in CODES}
    if not root.exists():
        return out
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        code = style_code(d.name)
        if code is None:
            continue
        out[code] = sorted(p for p in d.rglob("*") if p.suffix.lower() in exts)
    return out
