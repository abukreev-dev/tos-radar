from __future__ import annotations

import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from tos_radar.cabinet_security_service import (
    create_session,
    get_active_sessions_count,
    revoke_all_sessions_for_password_change,
)


class CabinetSecurityServiceTests(unittest.TestCase):
    def test_create_session_calls_store(self) -> None:
        with patch("tos_radar.cabinet_security_service.create_session_record") as mocked:
            now = datetime(2026, 2, 21, 14, 0, 0, tzinfo=UTC)
            create_session("t1", "u1", "s1", now=now)
        mocked.assert_called_once_with("t1", "u1", "s1", now.isoformat())

    def test_revoke_all_sessions_returns_count(self) -> None:
        with patch(
            "tos_radar.cabinet_security_service.revoke_all_active_sessions",
            return_value=3,
        ) as mocked:
            now = datetime(2026, 2, 21, 14, 5, 0, tzinfo=UTC)
            revoked = revoke_all_sessions_for_password_change("t1", "u1", now=now)
        self.assertEqual(revoked, 3)
        mocked.assert_called_once_with("t1", "u1", now.isoformat())

    def test_get_active_sessions_count(self) -> None:
        with patch("tos_radar.cabinet_security_service.count_active_sessions", return_value=2):
            self.assertEqual(get_active_sessions_count("t1", "u1"), 2)


if __name__ == "__main__":
    unittest.main()
