from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from tos_radar.cabinet_models import TelegramLinkState
from tos_radar.cabinet_telegram_service import TelegramLinkError
from tos_radar.cabinet_telegram_test_service import validate_and_mark_telegram_test_send
from tos_radar.cabinet_telegram_test_store import TelegramTestSendState


class CabinetTelegramTestServiceTests(unittest.TestCase):
    def test_reject_when_telegram_not_linked(self) -> None:
        with patch(
            "tos_radar.cabinet_telegram_test_service.read_telegram_link_state",
            return_value=TelegramLinkState(),
        ):
            with self.assertRaises(TelegramLinkError) as ctx:
                validate_and_mark_telegram_test_send(
                    "t1",
                    "u1",
                    now=datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC),
                )
        self.assertEqual(ctx.exception.code, "TELEGRAM_NOT_LINKED")

    def test_rate_limit_min_interval_and_daily_limit(self) -> None:
        state = TelegramTestSendState()

        def fake_read_state(_: str, __: str) -> TelegramTestSendState:
            return state

        def fake_write_state(_: str, __: str, next_state: TelegramTestSendState) -> None:
            nonlocal state
            state = next_state

        with patch(
            "tos_radar.cabinet_telegram_test_service.read_telegram_link_state",
            return_value=TelegramLinkState(chat_id="12345"),
        ), patch(
            "tos_radar.cabinet_telegram_test_service.read_telegram_test_send_state",
            side_effect=fake_read_state,
        ), patch(
            "tos_radar.cabinet_telegram_test_service.write_telegram_test_send_state",
            side_effect=fake_write_state,
        ):
            now = datetime(2026, 2, 21, 12, 0, 0, tzinfo=UTC)
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

    def test_daily_limit_resets_on_next_day(self) -> None:
        state = TelegramTestSendState()

        def fake_read_state(_: str, __: str) -> TelegramTestSendState:
            return state

        def fake_write_state(_: str, __: str, next_state: TelegramTestSendState) -> None:
            nonlocal state
            state = next_state

        with patch(
            "tos_radar.cabinet_telegram_test_service.read_telegram_link_state",
            return_value=TelegramLinkState(chat_id="12345"),
        ), patch(
            "tos_radar.cabinet_telegram_test_service.read_telegram_test_send_state",
            side_effect=fake_read_state,
        ), patch(
            "tos_radar.cabinet_telegram_test_service.write_telegram_test_send_state",
            side_effect=fake_write_state,
        ):
            now = datetime(2026, 2, 21, 23, 59, 0, tzinfo=UTC)
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
            self.assertEqual(state.day_count, 1)
            self.assertEqual(state.day, "2026-02-22")


if __name__ == "__main__":
    unittest.main()
