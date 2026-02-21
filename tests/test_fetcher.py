from __future__ import annotations

import unittest

from tos_radar.fetcher import build_attempts, classify_untyped_error, compute_retry_delay
from tos_radar.models import ErrorCode, Proxy


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

    def test_retry_delay_grows_exponentially_with_cap(self) -> None:
        d1 = compute_retry_delay(attempt_index=1, base_sec=0.5, max_sec=2.0, jitter_sec=0.0)
        d2 = compute_retry_delay(attempt_index=2, base_sec=0.5, max_sec=2.0, jitter_sec=0.0)
        d4 = compute_retry_delay(attempt_index=4, base_sec=0.5, max_sec=2.0, jitter_sec=0.0)
        self.assertEqual(d1, 0.5)
        self.assertEqual(d2, 1.0)
        self.assertEqual(d4, 2.0)

    def test_classify_untyped_error(self) -> None:
        self.assertEqual(classify_untyped_error(RuntimeError("request timeout")), ErrorCode.TIMEOUT)
        self.assertEqual(classify_untyped_error(RuntimeError("proxy auth 407")), ErrorCode.PROXY)
        self.assertEqual(classify_untyped_error(RuntimeError("connection reset")), ErrorCode.NETWORK)
