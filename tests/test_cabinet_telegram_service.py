from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from tos_radar.cabinet_models import ChannelStatus, TelegramLinkState, default_notification_settings
from tos_radar.cabinet_telegram_service import (
    TelegramLinkError,
    confirm_telegram_link,
    start_telegram_link,
    unlink_telegram,
)


class CabinetTelegramServiceTests(unittest.TestCase):
    def test_start_and_confirm_link_success(self) -> None:
        state = TelegramLinkState()

        def fake_read(_: str, __: str) -> TelegramLinkState:
            return state

        def fake_write(_: str, __: str, next_state: TelegramLinkState) -> None:
            nonlocal state
            state = next_state

        with patch("tos_radar.cabinet_telegram_service.read_telegram_link_state", side_effect=fake_read), patch(
            "tos_radar.cabinet_telegram_service.write_telegram_link_state", side_effect=fake_write
        ):
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
            self.assertEqual(state.chat_id, "12345")
            self.assertIsNotNone(state.linked_at)
            self.assertIsNone(state.pending_code)

    def test_confirm_link_with_invalid_code_raises(self) -> None:
        state = TelegramLinkState(
            pending_code="123456",
            code_expires_at=datetime(2026, 2, 21, 12, 5, 0, tzinfo=UTC).isoformat(),
            chat_id=None,
            linked_at=None,
        )
        with patch("tos_radar.cabinet_telegram_service.read_telegram_link_state", return_value=state):
            with self.assertRaises(TelegramLinkError) as ctx:
                confirm_telegram_link(
                    "t1",
                    "u1",
                    code="000000",
                    chat_id="12345",
                    current_settings=default_notification_settings(),
                    now=datetime(2026, 2, 21, 12, 1, 0, tzinfo=UTC),
                )
        self.assertEqual(ctx.exception.code, "TELEGRAM_LINK_CODE_INVALID")

    def test_confirm_link_with_expired_code_raises(self) -> None:
        state = TelegramLinkState(
            pending_code="123456",
            code_expires_at=datetime(2026, 2, 21, 12, 0, 30, tzinfo=UTC).isoformat(),
            chat_id=None,
            linked_at=None,
        )
        with patch("tos_radar.cabinet_telegram_service.read_telegram_link_state", return_value=state):
            with self.assertRaises(TelegramLinkError) as ctx:
                confirm_telegram_link(
                    "t1",
                    "u1",
                    code="123456",
                    chat_id="12345",
                    current_settings=default_notification_settings(),
                    now=datetime(2026, 2, 21, 12, 0, 31, tzinfo=UTC),
                )
        self.assertEqual(ctx.exception.code, "TELEGRAM_LINK_CODE_EXPIRED")

    def test_unlink_resets_telegram_toggles_and_status(self) -> None:
        captured: list[TelegramLinkState] = []
        with patch(
            "tos_radar.cabinet_telegram_service.write_telegram_link_state",
            side_effect=lambda _t, _u, s: captured.append(s),
        ):
            linked = default_notification_settings().__class__(
                email_digest_enabled=False,
                telegram_digest_enabled=True,
                email_marketing_enabled=False,
                telegram_system_enabled=True,
                email_status=ChannelStatus.UNVERIFIED,
                telegram_status=ChannelStatus.ENABLED,
                email_error=None,
                telegram_error=None,
            )
            after_unlink = unlink_telegram("t1", "u1", current_settings=linked)

        self.assertFalse(after_unlink.telegram_digest_enabled)
        self.assertFalse(after_unlink.telegram_system_enabled)
        self.assertEqual(after_unlink.telegram_status, ChannelStatus.DISCONNECTED)
        self.assertEqual(captured[-1], TelegramLinkState())


if __name__ == "__main__":
    unittest.main()
