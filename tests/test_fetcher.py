from __future__ import annotations

import unittest

from tos_radar.fetcher import build_attempts
from tos_radar.models import Proxy


class FetcherTests(unittest.TestCase):
    def test_build_attempts_starts_without_proxy_then_limited_proxies(self) -> None:
        proxies = [
            Proxy(host="1.1.1.1", port=8080),
            Proxy(host="2.2.2.2", port=8080),
            Proxy(host="3.3.3.3", port=8080),
        ]
        attempts = build_attempts(proxies, retry_proxy_count=2)
        self.assertIsNone(attempts[0])
        self.assertEqual(len(attempts), 3)
        self.assertEqual(attempts[1].host, "1.1.1.1")
        self.assertEqual(attempts[2].host, "2.2.2.2")
