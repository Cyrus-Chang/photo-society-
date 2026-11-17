"""Check the public Python/TypeScript label contract without third-party packages."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DICT_PATH = ROOT / "ai-classifier" / "labels" / "dictionary.json"
TS_PATH = ROOT / "src" / "utils" / "aiLabels.ts"
PUBLIC = {
    "STYLE": [
        "JAPANESE", "KOREAN", "INS", "FRESH", "FILM", "VINTAGE", "CINEMATIC",
        "DARK_MOOD", "MONO", "BLUE_TONE", "HK_RETRO", "CYBER", "WESTERN",
    ],
    "TONE": [
        "TONE_WARM", "TONE_COOL", "TONE_HIGH_SAT", "TONE_LOW_SAT",
        "TONE_HIGH_CONTRAST", "TONE_LOW_CONTRAST", "TONE_HIGH_KEY", "TONE_LOW_KEY",
        "TONE_LIFTED_BLACK",
    ],
    "SUBJECT": ["ARCHITECTURE", "LANDSCAPE", "STILL_FOOD"],
}


def _python_contract() -> dict[str, dict[str, dict[str, object]]]:
    data = json.loads(DICT_PATH.read_text(encoding="utf-8"))
    result: dict[str, dict[str, dict[str, object]]] = {}
    for group, codes in PUBLIC.items():
        items = {item["code"]: item for item in data[group]}
        result[group] = {
            code: {
                "name": items[code].get("name_cn", code),
                "aliases": items[code].get("aliases", []),
                "description": items[code].get(
                    "description", items[code].get("definition", items[code].get("note", ""))
                ),
            }
            for code in codes
        }
    return result


def _typescript_contract() -> dict[str, dict[str, dict[str, object]]]:
    source = TS_PATH.read_text(encoding="utf-8")
    groups: dict[str, dict[str, dict[str, object]]] = {}
    for group in PUBLIC:
        start = source.index(f"  {group}: {{")
        endings = [index for index in (source.find("\n  },", start), source.find("\n  }\n} as const", start)) if index >= 0]
        end = min(endings)
        block = source[start:end]
        rows: dict[str, dict[str, object]] = {}
        for match in re.finditer(
            r"^    ([A-Z0-9_]+): \{ name: '([^']*)', aliases: (\[[^\]]*\]), description: '([^']*)' \},?$",
            block,
            flags=re.MULTILINE,
        ):
            code, name, aliases, description = match.groups()
            rows[code] = {
                "name": name,
                "aliases": ast.literal_eval(aliases),
                "description": description,
            }
        groups[group] = rows
    return groups


def main() -> int:
    py = _python_contract()
    ts = _typescript_contract()
    mismatches: list[str] = []
    for group, codes in PUBLIC.items():
        if set(ts[group]) != set(codes):
            mismatches.append(f"{group}: code set Python={codes} TypeScript={sorted(ts[group])}")
        for code in codes:
            if py[group].get(code) != ts[group].get(code):
                mismatches.append(
                    f"{group}.{code}: Python={py[group].get(code)!r} TypeScript={ts[group].get(code)!r}"
                )
    print(f"public labels: style={len(PUBLIC['STYLE'])} tone={len(PUBLIC['TONE'])} subject={len(PUBLIC['SUBJECT'])}")
    if mismatches:
        print("mismatches:")
        print("\n".join(mismatches))
        return 1
    print("contract: PASS (names, aliases, descriptions match)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
