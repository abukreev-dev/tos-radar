from __future__ import annotations

from difflib import HtmlDiff
from itertools import islice

from tos_radar.normalize import normalize_for_compare


def is_changed(previous: str, current: str) -> bool:
    return normalize_for_compare(previous) != normalize_for_compare(current)


def build_diff_html(previous: str, current: str) -> str:
    prev_lines = _prepare_lines(previous)
    curr_lines = _prepare_lines(current)
    return HtmlDiff(wrapcolumn=100).make_table(
        prev_lines,
        curr_lines,
        fromdesc="Previous",
        todesc="Current",
        context=True,
        numlines=2,
    )


def _prepare_lines(text: str, chunk_size: int = 800, max_lines: int = 4000) -> list[str]:
    raw_lines = text.splitlines() or [text]
    out: list[str] = []
    for line in raw_lines:
        if not line:
            out.append("")
            continue
        if len(line) <= chunk_size:
            out.append(line)
            continue
        # Protect HtmlDiff from deep recursion on very long tokens/lines.
        for i in range(0, len(line), chunk_size):
            out.append(line[i : i + chunk_size])
    if len(out) > max_lines:
        truncated = list(islice(out, max_lines))
        truncated.append("[... diff truncated ...]")
        return truncated
    return out
