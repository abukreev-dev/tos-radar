from __future__ import annotations

import unittest
from unittest.mock import patch

from tos_radar.cabinet_models import ChannelError, ChannelStatus, NotificationSettings
from tos_radar.cabinet_store import read_notification_settings, write_notification_settings


class _FakeCursor:
    def __init__(self, storage: dict[tuple[str, str], dict]) -> None:
        self._storage = storage
        self._row: dict | None = None

    def __enter__(self) -> _FakeCursor:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        return None

    def execute(self, query: str, params: tuple) -> None:
        if "SELECT" in query:
            tenant_id, user_id = params
            self._row = self._storage.get((tenant_id, user_id))
            return

        (
            tenant_id,
            user_id,
            email_digest_enabled,
            telegram_digest_enabled,
            email_marketing_enabled,
            telegram_system_enabled,
            email_status,
            telegram_status,
            email_error_code,
            email_error_message,
            email_error_updated_at,
            telegram_error_code,
            telegram_error_message,
            telegram_error_updated_at,
        ) = params
        self._storage[(tenant_id, user_id)] = {
            "email_digest_enabled": email_digest_enabled,
            "telegram_digest_enabled": telegram_digest_enabled,
            "email_marketing_enabled": email_marketing_enabled,
            "telegram_system_enabled": telegram_system_enabled,
            "email_status": email_status,
            "telegram_status": telegram_status,
            "email_error_code": email_error_code,
            "email_error_message": email_error_message,
            "email_error_updated_at": email_error_updated_at,
            "telegram_error_code": telegram_error_code,
            "telegram_error_message": telegram_error_message,
            "telegram_error_updated_at": telegram_error_updated_at,
        }

    def fetchone(self) -> dict | None:
        return self._row


class _FakeConnection:
    def __init__(self, storage: dict[tuple[str, str], dict]) -> None:
        self._storage = storage

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self._storage)

    def close(self) -> None:
        return None


class CabinetStoreTests(unittest.TestCase):
    def test_read_returns_defaults_when_record_missing(self) -> None:
        storage: dict[tuple[str, str], dict] = {}
        with patch("tos_radar.cabinet_store.ensure_cabinet_schema"), patch(
            "tos_radar.cabinet_store.connect_mariadb",
            return_value=_FakeConnection(storage),
        ):
            settings = read_notification_settings("t1", "u1")
            self.assertFalse(settings.email_digest_enabled)
            self.assertFalse(settings.telegram_digest_enabled)
            self.assertEqual(settings.email_status, ChannelStatus.UNVERIFIED)
            self.assertEqual(settings.telegram_status, ChannelStatus.DISCONNECTED)

    def test_write_and_read_roundtrip(self) -> None:
        storage: dict[tuple[str, str], dict] = {}
        with patch("tos_radar.cabinet_store.ensure_cabinet_schema"), patch(
            "tos_radar.cabinet_store.connect_mariadb",
            return_value=_FakeConnection(storage),
        ):
            initial = NotificationSettings(
                email_digest_enabled=True,
                telegram_digest_enabled=True,
                email_marketing_enabled=False,
                telegram_system_enabled=True,
                email_status=ChannelStatus.ENABLED,
                telegram_status=ChannelStatus.ERROR,
                email_error=None,
                telegram_error=ChannelError(
                    code="TELEGRAM_DISCONNECTED",
                    message="Chat is unreachable",
                    updated_at="2026-02-21T10:20:30Z",
                ),
            )
            write_notification_settings("t1", "u1", initial)
            saved = read_notification_settings("t1", "u1")
            self.assertEqual(saved, initial)

    def test_read_invalid_status_raises_value_error(self) -> None:
        storage: dict[tuple[str, str], dict] = {
            ("t1", "u1"): {
                "email_digest_enabled": 0,
                "telegram_digest_enabled": 0,
                "email_marketing_enabled": 0,
                "telegram_system_enabled": 0,
                "email_status": "NOT_A_STATUS",
                "telegram_status": "DISCONNECTED",
                "email_error_code": None,
                "email_error_message": None,
                "email_error_updated_at": None,
                "telegram_error_code": None,
                "telegram_error_message": None,
                "telegram_error_updated_at": None,
            }
        }
        with patch("tos_radar.cabinet_store.ensure_cabinet_schema"), patch(
            "tos_radar.cabinet_store.connect_mariadb",
            return_value=_FakeConnection(storage),
        ):
            with self.assertRaises(ValueError):
                read_notification_settings("t1", "u1")


if __name__ == "__main__":
    unittest.main()
