from __future__ import annotations

import unittest
from unittest.mock import patch

from tos_radar.cabinet_security_email_service import notify_email_changed, notify_password_changed


class CabinetSecurityEmailServiceTests(unittest.TestCase):
    def test_notify_password_changed_sends_single_email(self) -> None:
        with patch("tos_radar.cabinet_security_email_service.send_email") as mocked_send:
            result = notify_password_changed("t1", "u1", "user@example.com")
        self.assertEqual(result, {"sent": 1, "failed": 0})
        mocked_send.assert_called_once()

    def test_notify_email_changed_sends_to_old_and_new(self) -> None:
        with patch("tos_radar.cabinet_security_email_service.send_email") as mocked_send:
            result = notify_email_changed("t1", "u1", "old@example.com", "new@example.com")
        self.assertEqual(result, {"sent": 2, "failed": 0})
        self.assertEqual(mocked_send.call_count, 2)

    def test_delivery_failures_are_logged_and_counted(self) -> None:
        with patch(
            "tos_radar.cabinet_security_email_service.send_email",
            side_effect=RuntimeError("smtp failed"),
        ), patch("tos_radar.cabinet_security_email_service.logger") as mocked_logger:
            result = notify_password_changed("t1", "u1", "user@example.com")
        self.assertEqual(result, {"sent": 0, "failed": 1})
        mocked_logger.exception.assert_called_once()


if __name__ == "__main__":
    unittest.main()
