from __future__ import annotations

import re
from difflib import SequenceMatcher

from tos_radar.models import ChangeLevel


def classify_change(previous: str, current: str) -> tuple[ChangeLevel, float]:
    prev_tokens = _tokenize(previous)
    curr_tokens = _tokenize(current)
    prev_s = " ".join(prev_tokens)
    curr_s = " ".join(curr_tokens)
    ratio = 1.0 - SequenceMatcher(None, prev_s, curr_s).ratio()

    if ratio < 0.015:
        return (ChangeLevel.NOISE, ratio)
    if ratio < 0.12:
        return (ChangeLevel.MINOR, ratio)
    return (ChangeLevel.MAJOR, ratio)


def is_suspicious_changed(change_level: ChangeLevel, change_ratio: float, text_length: int | None) -> bool:
    length = text_length or 0
    return change_level == ChangeLevel.MAJOR and change_ratio >= 0.3 and length < 2500


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-zА-Яа-я0-9]+", text.lower())
