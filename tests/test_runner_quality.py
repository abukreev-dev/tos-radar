from __future__ import annotations

import unittest

from tos_radar.models import ErrorCode, SourceType
from tos_radar.runner import _quality_gate_error


class RunnerQualityTests(unittest.TestCase):
    def test_short_html_content_fails_quality_gate(self) -> None:
        issue = _quality_gate_error("short page", SourceType.HTML, min_text_length=100)
        self.assertIsNotNone(issue)
        assert issue is not None
        self.assertEqual(issue[0], ErrorCode.SHORT_CONTENT)

    def test_short_pdf_content_does_not_fail_short_content_gate(self) -> None:
        issue = _quality_gate_error("short", SourceType.PDF, min_text_length=100)
        self.assertIsNone(issue)

    def test_technical_page_marker_fails_quality_gate(self) -> None:
        issue = _quality_gate_error(
            "Forbidden. If you are not a bot, contact support",
            SourceType.HTML,
            min_text_length=10,
        )
        self.assertIsNotNone(issue)
        assert issue is not None
        self.assertEqual(issue[0], ErrorCode.TECHNICAL_PAGE)
