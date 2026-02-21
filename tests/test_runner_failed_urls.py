from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from tos_radar.models import RunEntry, Status
from tos_radar.runner import _read_last_failed_urls, _write_last_failed_urls


class RunnerFailedUrlsTests(unittest.TestCase):
    def test_write_and_read_failed_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old = os.getcwd()
            os.chdir(tmp)
            try:
                entries = [
                    RunEntry(
                        domain="a.com",
                        url="https://a.com/tos",
                        status=Status.FAILED,
                        source_type=None,
                        duration_sec=1.0,
                        text_length=None,
                        change_level=None,
                        change_ratio=None,
                        error_code=None,
                        error="x",
                        diff_html=None,
                    ),
                    RunEntry(
                        domain="b.com",
                        url="https://b.com/tos",
                        status=Status.UNCHANGED,
                        source_type=None,
                        duration_sec=1.0,
                        text_length=100,
                        change_level=None,
                        change_ratio=None,
                        error_code=None,
                        error=None,
                        diff_html=None,
                    ),
                ]
                _write_last_failed_urls("tenant-a", entries)
                self.assertTrue(Path("data/tenant-a/last_failed_urls.txt").exists())
                self.assertEqual(_read_last_failed_urls("tenant-a"), ["https://a.com/tos"])
            finally:
                os.chdir(old)
