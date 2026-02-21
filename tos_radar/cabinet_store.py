from __future__ import annotations

from tos_radar.cabinet_models import (
    ChannelStatus,
    ChannelError,
    NotificationSettings,
    default_notification_settings,
)
from tos_radar.mariadb import connect_mariadb, ensure_cabinet_schema


def read_notification_settings(tenant_id: str, user_id: str) -> NotificationSettings:
    ensure_cabinet_schema()
    conn = connect_mariadb()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
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
                    telegram_error_updated_at
                FROM cabinet_notification_settings
                WHERE tenant_id=%s AND user_id=%s
                """,
                (tenant_id, user_id),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return default_notification_settings()
    return NotificationSettings(
        email_digest_enabled=bool(row["email_digest_enabled"]),
        telegram_digest_enabled=bool(row["telegram_digest_enabled"]),
        email_marketing_enabled=bool(row["email_marketing_enabled"]),
        telegram_system_enabled=bool(row["telegram_system_enabled"]),
        email_status=ChannelStatus(row["email_status"]),
        telegram_status=ChannelStatus(row["telegram_status"]),
        email_error=_build_error(
            row["email_error_code"],
            row["email_error_message"],
            row["email_error_updated_at"],
        ),
        telegram_error=_build_error(
            row["telegram_error_code"],
            row["telegram_error_message"],
            row["telegram_error_updated_at"],
        ),
    )


def write_notification_settings(
    tenant_id: str, user_id: str, settings: NotificationSettings
) -> None:
    ensure_cabinet_schema()
    conn = connect_mariadb()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cabinet_notification_settings (
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
                    telegram_error_updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    email_digest_enabled=VALUES(email_digest_enabled),
                    telegram_digest_enabled=VALUES(telegram_digest_enabled),
                    email_marketing_enabled=VALUES(email_marketing_enabled),
                    telegram_system_enabled=VALUES(telegram_system_enabled),
                    email_status=VALUES(email_status),
                    telegram_status=VALUES(telegram_status),
                    email_error_code=VALUES(email_error_code),
                    email_error_message=VALUES(email_error_message),
                    email_error_updated_at=VALUES(email_error_updated_at),
                    telegram_error_code=VALUES(telegram_error_code),
                    telegram_error_message=VALUES(telegram_error_message),
                    telegram_error_updated_at=VALUES(telegram_error_updated_at)
                """,
                (
                    tenant_id,
                    user_id,
                    int(settings.email_digest_enabled),
                    int(settings.telegram_digest_enabled),
                    int(settings.email_marketing_enabled),
                    int(settings.telegram_system_enabled),
                    settings.email_status.value,
                    settings.telegram_status.value,
                    settings.email_error.code if settings.email_error else None,
                    settings.email_error.message if settings.email_error else None,
                    settings.email_error.updated_at if settings.email_error else None,
                    settings.telegram_error.code if settings.telegram_error else None,
                    settings.telegram_error.message if settings.telegram_error else None,
                    settings.telegram_error.updated_at if settings.telegram_error else None,
                ),
            )
    finally:
        conn.close()


def _build_error(code: str | None, message: str | None, updated_at: str | None) -> ChannelError | None:
    if not code or not message or not updated_at:
        return None
    return ChannelError(code=code, message=message, updated_at=updated_at)
