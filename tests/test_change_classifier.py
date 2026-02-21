from __future__ import annotations

import unittest

from tos_radar.change_classifier import classify_change, is_suspicious_changed
from tos_radar.models import ChangeLevel


class ChangeClassifierTests(unittest.TestCase):
    def test_noise_change(self) -> None:
        level, ratio = classify_change("terms version 1", "terms version 1.")
        self.assertEqual(level, ChangeLevel.NOISE)
        self.assertLess(ratio, 0.05)

    def test_minor_change(self) -> None:
        base = " ".join(["term"] * 80) + " alpha beta gamma delta epsilon zeta eta theta"
        changed = " ".join(["term"] * 80) + " alpha beta gamma delta iota kappa lambda mu"
        level, _ = classify_change(base, changed)
        self.assertEqual(level, ChangeLevel.MINOR)

    def test_major_change(self) -> None:
        level, ratio = classify_change("old terms text", "completely different legal document content")
        self.assertEqual(level, ChangeLevel.MAJOR)
        self.assertGreater(ratio, 0.12)

    def test_suspicious_changed_rule(self) -> None:
        self.assertTrue(is_suspicious_changed(ChangeLevel.MAJOR, 0.5, 900))
        self.assertFalse(is_suspicious_changed(ChangeLevel.MINOR, 0.5, 900))
