from __future__ import annotations

from difflib import HtmlDiff

from tos_radar.normalize import normalize_for_compare


def is_changed(previous: str, current: str) -> bool:
    return normalize_for_compare(previous) != normalize_for_compare(current)


def build_diff_html(previous: str, current: str) -> str:
    prev_lines = previous.splitlines() or [previous]
    curr_lines = current.splitlines() or [current]
    return HtmlDiff(wrapcolumn=100).make_table(
        prev_lines,
        curr_lines,
        fromdesc="Previous",
        todesc="Current",
        context=True,
        numlines=2,
    )
