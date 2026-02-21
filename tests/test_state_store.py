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
                write_current_and_rotate("t1", "example.com", "v1")
                self.assertEqual(read_current("t1", "example.com"), "v1")
                write_current_and_rotate("t1", "example.com", "v2")
                self.assertEqual(read_current("t1", "example.com"), "v2")
            finally:
                os.chdir(old_cwd)
