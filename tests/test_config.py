from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tos_radar.config import load_proxies, load_services


class ConfigTests(unittest.TestCase):
    def test_load_services_and_validate_domain_uniqueness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tos_urls.txt"
            path.write_text(
                "https://example.com/terms\nhttps://sub.domain.org/tos\n",
                encoding="utf-8",
            )
            services = load_services(str(path))
            self.assertEqual([s.domain for s in services], ["example.com", "sub.domain.org"])

    def test_duplicate_domain_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tos_urls.txt"
            path.write_text(
                "https://example.com/terms\nhttps://example.com/another\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "Duplicate domain"):
                load_services(str(path))

    def test_load_proxies_formats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proxies.txt"
            path.write_text("1.1.1.1:8080\n2.2.2.2:3128:user:pass\n", encoding="utf-8")
            proxies = load_proxies(str(path))
            self.assertEqual(len(proxies), 2)
            self.assertEqual(proxies[0].host, "1.1.1.1")
            self.assertEqual(proxies[1].login, "user")
