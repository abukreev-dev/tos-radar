from __future__ import annotations

import re
import string

_PUNCT_TABLE = str.maketrans("", "", string.punctuation)


def normalize_for_compare(text: str) -> str:
    normalized = text.lower().translate(_PUNCT_TABLE)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def normalize_for_storage(text: str) -> str:
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"[ \t]+", " ", raw).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)
