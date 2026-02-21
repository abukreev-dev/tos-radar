from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from tos_radar.cabinet_email_verify_service import (
    EmailVerifyResendError,
    validate_and_mark_email_verify_resend,
)
from tos_radar.cabinet_email_verify_store import EmailVerifyResendState


class CabinetEmailVerifyServiceTests(unittest.TestCase):
    def test_rate_limit_min_interval_and_daily_limit(self) -> None:
        state = EmailVerifyResendState()

        def fake_read(_: str, __: str) -> EmailVerifyResendState:
            return state

        def fake_write(_: str, __: str, next_state: EmailVerifyResendState) -> None:
            nonlocal state
            state = next_state

        with patch("tos_radar.cabinet_email_verify_service.read_email_verify_resend_state", side_effect=fake_read), patch(
            "tos_radar.cabinet_email_verify_service.write_email_verify_resend_state", side_effect=fake_write
        ):
            now = datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC)
            validate_and_mark_email_verify_resend("t1", "u1", now=now)

            with self.assertRaises(EmailVerifyResendError) as rate_ctx:
                validate_and_mark_email_verify_resend(
                    "t1",
                    "u1",
                    now=now + timedelta(seconds=10),
                )
            self.assertEqual(rate_ctx.exception.code, "EMAIL_VERIFY_RESEND_RATE_LIMIT")

            validate_and_mark_email_verify_resend(
                "t1",
                "u1",
                now=now + timedelta(seconds=61),
                daily_limit=2,
            )
            with self.assertRaises(EmailVerifyResendError) as daily_ctx:
                validate_and_mark_email_verify_resend(
                    "t1",
                    "u1",
                    now=now + timedelta(seconds=130),
                    daily_limit=2,
                )
            self.assertEqual(daily_ctx.exception.code, "EMAIL_VERIFY_RESEND_DAILY_LIMIT")


if __name__ == "__main__":
    unittest.main()
