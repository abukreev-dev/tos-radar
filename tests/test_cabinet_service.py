from __future__ import annotations

import unittest

from tos_radar.cabinet_models import default_notification_settings
from tos_radar.cabinet_service import (
    SettingsValidationError,
    apply_notification_settings_update,
)


class CabinetServiceTests(unittest.TestCase):
    def test_reject_enable_email_digest_when_unverified(self) -> None:
        current = default_notification_settings()

        with self.assertRaises(SettingsValidationError) as ctx:
            apply_notification_settings_update(
                current,
                email_verified=False,
                email_digest_enabled=True,
            )

        self.assertEqual(ctx.exception.code, "EMAIL_UNVERIFIED")

    def test_allow_enable_email_digest_when_verified(self) -> None:
        current = default_notification_settings()
        next_settings = apply_notification_settings_update(
            current,
            email_verified=True,
            email_digest_enabled=True,
        )

        self.assertTrue(next_settings.email_digest_enabled)


if __name__ == "__main__":
    unittest.main()
