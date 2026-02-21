from __future__ import annotations

from dataclasses import replace

from tos_radar.cabinet_models import NotificationSettings


class SettingsValidationError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def apply_notification_settings_update(
    current: NotificationSettings,
    *,
    email_verified: bool,
    email_digest_enabled: bool | None = None,
    telegram_digest_enabled: bool | None = None,
    email_marketing_enabled: bool | None = None,
    telegram_system_enabled: bool | None = None,
) -> NotificationSettings:
    next_settings = replace(
        current,
        email_digest_enabled=(
            email_digest_enabled
            if email_digest_enabled is not None
            else current.email_digest_enabled
        ),
        telegram_digest_enabled=(
            telegram_digest_enabled
            if telegram_digest_enabled is not None
            else current.telegram_digest_enabled
        ),
        email_marketing_enabled=(
            email_marketing_enabled
            if email_marketing_enabled is not None
            else current.email_marketing_enabled
        ),
        telegram_system_enabled=(
            telegram_system_enabled
            if telegram_system_enabled is not None
            else current.telegram_system_enabled
        ),
    )

    if next_settings.email_digest_enabled and not email_verified:
        raise SettingsValidationError(
            code="EMAIL_UNVERIFIED",
            message="Email digest requires a verified email address.",
        )

    return next_settings
