from __future__ import annotations

import re
import string

_PUNCT_TABLE = str.maketrans("", "", string.punctuation)


def normalize_for_compare(text: str) -> str:
    normalized = text.lower().translate(_PUNCT_TABLE)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def normalize_for_storage(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
