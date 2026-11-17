"""Canonical label metadata used by the classifier service.

The JSON dictionary remains the editable source of truth.  This module keeps
the public taxonomy rules in one small, importable place so inference code does
not accidentally expose disabled or training-only labels.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping


DEFAULT_DICT_PATH = Path(__file__).resolve().parents[1] / "labels" / "dictionary.json"

# The subject head was trained on these three non-person classes.  The enabled
# portrait entries in dictionary.json are used only as CLIP evidence for the
# safety gate; they are never emitted as a public subject prediction.
PUBLIC_SUBJECT_CODES = ("ARCHITECTURE", "LANDSCAPE", "STILL_FOOD")
PERSON_SUBJECT_CODES = (
    "STUDIO",
    "OUTDOOR",
    "CONVENTION",
    "STREET_PORTRAIT",
    "INTERIOR_PORTRAIT",
    "PORTRAIT",
)
STYLE_CODES = (
    "JAPANESE",
    "KOREAN",
    "INS",
    "FRESH",
    "FILM",
    "VINTAGE",
    "CINEMATIC",
    "DARK_MOOD",
    "MONO",
    "BLUE_TONE",
    "HK_RETRO",
    "CYBER",
    "WESTERN",
)
TONE_CODES = (
    "TONE_WARM",
    "TONE_COOL",
    "TONE_HIGH_SAT",
    "TONE_LOW_SAT",
    "TONE_HIGH_CONTRAST",
    "TONE_LOW_CONTRAST",
    "TONE_HIGH_KEY",
    "TONE_LOW_KEY",
    "TONE_LIFTED_BLACK",
)


def dictionary_path() -> Path:
    raw = os.environ.get("DICT_PATH")
    return Path(raw) if raw else DEFAULT_DICT_PATH


def load_dictionary(path: Path | None = None) -> Dict[str, Any]:
    """Load the editable dictionary with a stable absolute default path."""

    target = path or dictionary_path()
    return json.loads(target.read_text(encoding="utf-8"))


def _entries(data: Mapping[str, Any], group: str) -> Dict[str, Dict[str, Any]]:
    return {str(item["code"]): dict(item) for item in data.get(group, []) if item.get("code")}


def metadata(data: Mapping[str, Any] | None = None) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Return normalized metadata for the three public layers.

    Older dictionary files use ``definition`` instead of ``description`` and
    omit aliases.  Normalizing here lets the API and validation scripts work
    with both versions while the JSON is migrated gradually.
    """

    source = data or load_dictionary()
    out: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for group, codes in (
        ("SUBJECT", PUBLIC_SUBJECT_CODES),
        ("STYLE", STYLE_CODES),
        ("TONE", TONE_CODES),
    ):
        entries = _entries(source, group)
        out[group] = {}
        for code in codes:
            item = entries.get(code, {})
            out[group][code] = {
                "code": code,
                "name_cn": item.get("name_cn", code),
                "aliases": list(item.get("aliases") or []),
                "description": item.get("description", item.get("definition", item.get("note", ""))),
                "enabled": bool(item.get("enabled", True)),
            }
    return out


def prompt_entries(data: Mapping[str, Any] | None, group: str) -> Iterable[Dict[str, Any]]:
    """Yield enabled entries with prompts for zero-shot evidence."""

    source = data or load_dictionary()
    for item in source.get(group, []):
        if item.get("enabled", True) and item.get("prompt_en"):
            yield item

