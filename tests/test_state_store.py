from __future__ import annotations

import os
import tempfile
import unittest

from tos_radar.state_store import read_current, write_current_and_rotate


class StateStoreTests(unittest.TestCase):
    def test_rotate_current_to_previous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                write_current_and_rotate("example.com", "v1")
                self.assertEqual(read_current("example.com"), "v1")
                write_current_and_rotate("example.com", "v2")
                self.assertEqual(read_current("example.com"), "v2")
            finally:
                os.chdir(old_cwd)
