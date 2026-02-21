from __future__ import annotations

import os
import tempfile
import unittest
from datetime import UTC, datetime, timedelta

from tos_radar.cabinet_models import ChannelStatus, default_notification_settings
from tos_radar.cabinet_telegram_service import (
    TelegramLinkError,
    confirm_telegram_link,
    start_telegram_link,
    unlink_telegram,
)
from tos_radar.cabinet_telegram_store import read_telegram_link_state


class CabinetTelegramServiceTests(unittest.TestCase):
    def test_start_and_confirm_link_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                now = datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC)
                code = start_telegram_link("t1", "u1", now=now, ttl_sec=300)
                self.assertEqual(len(code), 6)

                settings = default_notification_settings()
                next_settings = confirm_telegram_link(
                    "t1",
                    "u1",
                    code=code,
                    chat_id="12345",
                    current_settings=settings,
                    now=now + timedelta(seconds=60),
                )

                self.assertEqual(next_settings.telegram_status, ChannelStatus.ENABLED)
                state = read_telegram_link_state("t1", "u1")
                self.assertEqual(state.chat_id, "12345")
                self.assertIsNotNone(state.linked_at)
                self.assertIsNone(state.pending_code)
            finally:
                os.chdir(old_cwd)

    def test_confirm_link_with_invalid_code_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                now = datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC)
                start_telegram_link("t1", "u1", now=now, ttl_sec=300)

                with self.assertRaises(TelegramLinkError) as ctx:
                    confirm_telegram_link(
                        "t1",
                        "u1",
                        code="000000",
                        chat_id="12345",
                        current_settings=default_notification_settings(),
                        now=now + timedelta(seconds=10),
                    )
                self.assertEqual(ctx.exception.code, "TELEGRAM_LINK_CODE_INVALID")
            finally:
                os.chdir(old_cwd)

    def test_confirm_link_with_expired_code_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                now = datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC)
                code = start_telegram_link("t1", "u1", now=now, ttl_sec=30)

                with self.assertRaises(TelegramLinkError) as ctx:
                    confirm_telegram_link(
                        "t1",
                        "u1",
                        code=code,
                        chat_id="12345",
                        current_settings=default_notification_settings(),
                        now=now + timedelta(seconds=31),
                    )
                self.assertEqual(ctx.exception.code, "TELEGRAM_LINK_CODE_EXPIRED")
            finally:
                os.chdir(old_cwd)

    def test_unlink_resets_telegram_toggles_and_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                now = datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC)
                code = start_telegram_link("t1", "u1", now=now, ttl_sec=300)
                linked = confirm_telegram_link(
                    "t1",
                    "u1",
                    code=code,
                    chat_id="12345",
                    current_settings=default_notification_settings(),
                    now=now + timedelta(seconds=10),
                )
                linked = linked.__class__(
                    email_digest_enabled=linked.email_digest_enabled,
                    telegram_digest_enabled=True,
                    email_marketing_enabled=linked.email_marketing_enabled,
                    telegram_system_enabled=True,
                    email_status=linked.email_status,
                    telegram_status=linked.telegram_status,
                    email_error=linked.email_error,
                    telegram_error=linked.telegram_error,
                )

                after_unlink = unlink_telegram("t1", "u1", current_settings=linked)
                self.assertFalse(after_unlink.telegram_digest_enabled)
                self.assertFalse(after_unlink.telegram_system_enabled)
                self.assertEqual(after_unlink.telegram_status, ChannelStatus.DISCONNECTED)
                state = read_telegram_link_state("t1", "u1")
                self.assertIsNone(state.chat_id)
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
