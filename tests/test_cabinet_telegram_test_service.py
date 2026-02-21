from __future__ import annotations

import os
import tempfile
import unittest
from datetime import UTC, datetime, timedelta

from tos_radar.cabinet_models import default_notification_settings
from tos_radar.cabinet_telegram_service import TelegramLinkError, confirm_telegram_link, start_telegram_link
from tos_radar.cabinet_telegram_test_service import validate_and_mark_telegram_test_send
from tos_radar.cabinet_telegram_test_store import read_telegram_test_send_state


class CabinetTelegramTestServiceTests(unittest.TestCase):
    def test_reject_when_telegram_not_linked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                with self.assertRaises(TelegramLinkError) as ctx:
                    validate_and_mark_telegram_test_send(
                        "t1",
                        "u1",
                        now=datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC),
                    )
                self.assertEqual(ctx.exception.code, "TELEGRAM_NOT_LINKED")
            finally:
                os.chdir(old_cwd)

    def test_rate_limit_min_interval_and_daily_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                now = datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC)
                code = start_telegram_link("t1", "u1", now=now, ttl_sec=300)
                confirm_telegram_link(
                    "t1",
                    "u1",
                    code=code,
                    chat_id="12345",
                    current_settings=default_notification_settings(),
                    now=now + timedelta(seconds=1),
                )

                validate_and_mark_telegram_test_send("t1", "u1", now=now)

                with self.assertRaises(TelegramLinkError) as rate_ctx:
                    validate_and_mark_telegram_test_send(
                        "t1",
                        "u1",
                        now=now + timedelta(seconds=10),
                    )
                self.assertEqual(rate_ctx.exception.code, "TELEGRAM_TEST_RATE_LIMIT")

                validate_and_mark_telegram_test_send(
                    "t1",
                    "u1",
                    now=now + timedelta(seconds=61),
                    daily_limit=2,
                )

                with self.assertRaises(TelegramLinkError) as daily_ctx:
                    validate_and_mark_telegram_test_send(
                        "t1",
                        "u1",
                        now=now + timedelta(seconds=130),
                        daily_limit=2,
                    )
                self.assertEqual(daily_ctx.exception.code, "TELEGRAM_TEST_DAILY_LIMIT")
            finally:
                os.chdir(old_cwd)

    def test_daily_limit_resets_on_next_day(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                now = datetime(2026, 2, 21, 23, 59, 0, tzinfo=UTC)
                code = start_telegram_link("t1", "u1", now=now, ttl_sec=300)
                confirm_telegram_link(
                    "t1",
                    "u1",
                    code=code,
                    chat_id="12345",
                    current_settings=default_notification_settings(),
                    now=now + timedelta(seconds=1),
                )

                validate_and_mark_telegram_test_send(
                    "t1",
                    "u1",
                    now=now,
                    daily_limit=1,
                )
                validate_and_mark_telegram_test_send(
                    "t1",
                    "u1",
                    now=now + timedelta(minutes=2),
                    daily_limit=1,
                )

                state = read_telegram_test_send_state("t1", "u1")
                self.assertEqual(state.day_count, 1)
                self.assertEqual(state.day, "2026-02-22")
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
