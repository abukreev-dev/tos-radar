from __future__ import annotations

import json
import os
import tempfile
import unittest

from tos_radar.cabinet_models import ChannelError, ChannelStatus, NotificationSettings
from tos_radar.cabinet_store import read_notification_settings, write_notification_settings


class CabinetStoreTests(unittest.TestCase):
    def test_read_returns_defaults_when_file_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                settings = read_notification_settings("t1", "u1")
                self.assertFalse(settings.email_digest_enabled)
                self.assertFalse(settings.telegram_digest_enabled)
                self.assertEqual(settings.email_status, ChannelStatus.UNVERIFIED)
                self.assertEqual(settings.telegram_status, ChannelStatus.DISCONNECTED)
                self.assertIsNone(settings.email_error)
                self.assertIsNone(settings.telegram_error)
            finally:
                os.chdir(old_cwd)

    def test_write_and_read_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
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
            finally:
                os.chdir(old_cwd)

    def test_read_invalid_payload_raises_validation_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_cwd = os.getcwd()
            os.chdir(tmp)
            try:
                path = (
                    "data/cabinet/t1/users/u1/notification_settings.json"
                )
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "email_digest_enabled": "yes",
                            "telegram_digest_enabled": False,
                            "email_marketing_enabled": False,
                            "telegram_system_enabled": False,
                            "email_status": "ENABLED",
                            "telegram_status": "DISCONNECTED",
                            "email_error": None,
                            "telegram_error": None,
                        },
                        f,
                    )

                with self.assertRaises(ValueError):
                    read_notification_settings("t1", "u1")
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
