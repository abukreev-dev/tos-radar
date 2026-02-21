from __future__ import annotations

import unittest

from tos_radar.diff_utils import build_diff_html, is_changed


class DiffTests(unittest.TestCase):
    def test_is_changed_false_on_normalized_equivalent(self) -> None:
        self.assertFalse(is_changed("Hello, World!", "hello world"))

    def test_is_changed_true_when_text_differs(self) -> None:
        self.assertTrue(is_changed("terms v1", "terms v2"))

    def test_build_diff_html_has_table(self) -> None:
        html = build_diff_html("old", "new")
        self.assertIn("<table class=\"diff\"", html)

    def test_build_diff_html_handles_very_long_lines(self) -> None:
        long_old = "a" * 20000
        long_new = "a" * 19999 + "b"
        html = build_diff_html(long_old, long_new)
        self.assertIn("<table class=\"diff\"", html)
