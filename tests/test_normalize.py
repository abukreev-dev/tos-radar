from __future__ import annotations

import unittest

from tos_radar.normalize import normalize_for_compare, normalize_for_storage


class NormalizeTests(unittest.TestCase):
    def test_compare_normalization_ignores_case_spacing_punct(self) -> None:
        left = "Last updated: Jan 1, 2026.\n Terms!"
        right = "last   updated jan 1 2026 terms"
        self.assertEqual(normalize_for_compare(left), normalize_for_compare(right))

    def test_storage_normalization_collapse_spaces(self) -> None:
        value = "Hello \n\n world\t  again"
        self.assertEqual(normalize_for_storage(value), "Hello\nworld again")
