from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from random import randint

from tos_radar.cabinet_models import (
    ChannelError,
    ChannelStatus,
    NotificationSettings,
    TelegramLinkState,
)
from tos_radar.cabinet_telegram_store import (
    read_telegram_link_state,
    write_telegram_link_state,
)


class TelegramLinkError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def start_telegram_link(
    tenant_id: str,
    user_id: str,
    *,
    now: datetime | None = None,
    ttl_sec: int = 600,
) -> str:
    ts = now or datetime.now(UTC)
    code = f"{randint(0, 999999):06d}"
    state = TelegramLinkState(
        pending_code=code,
        code_expires_at=(ts + timedelta(seconds=ttl_sec)).isoformat(),
        chat_id=None,
        linked_at=None,
    )
    write_telegram_link_state(tenant_id, user_id, state)
    return code


def confirm_telegram_link(
    tenant_id: str,
    user_id: str,
    *,
    code: str,
    chat_id: str,
    current_settings: NotificationSettings,
    now: datetime | None = None,
) -> NotificationSettings:
    state = read_telegram_link_state(tenant_id, user_id)
    ts = now or datetime.now(UTC)
    _validate_code(code=code, state=state, now=ts)

    next_state = TelegramLinkState(
        pending_code=None,
        code_expires_at=None,
        chat_id=chat_id,
        linked_at=ts.isoformat(),
    )
    write_telegram_link_state(tenant_id, user_id, next_state)
    return replace(
        current_settings,
        telegram_status=ChannelStatus.ENABLED,
        telegram_error=None,
    )


def unlink_telegram(
    tenant_id: str,
    user_id: str,
    *,
    current_settings: NotificationSettings,
) -> NotificationSettings:
    write_telegram_link_state(tenant_id, user_id, TelegramLinkState())
    return replace(
        current_settings,
        telegram_digest_enabled=False,
        telegram_system_enabled=False,
        telegram_status=ChannelStatus.DISCONNECTED,
        telegram_error=None,
    )


def mark_telegram_disconnected(
    tenant_id: str,
    user_id: str,
    *,
    current_settings: NotificationSettings,
    reason_message: str = "Telegram channel disconnected. Reconnect is required.",
    now: datetime | None = None,
) -> NotificationSettings:
    ts = now or datetime.now(UTC)
    write_telegram_link_state(tenant_id, user_id, TelegramLinkState())
    return replace(
        current_settings,
        telegram_digest_enabled=False,
        telegram_system_enabled=False,
        telegram_status=ChannelStatus.DISCONNECTED,
        telegram_error=ChannelError(
            code="TELEGRAM_DISCONNECTED",
            message=reason_message,
            updated_at=ts.isoformat(),
        ),
    )


def _validate_code(*, code: str, state: TelegramLinkState, now: datetime) -> None:
    if not state.pending_code or not state.code_expires_at:
        raise TelegramLinkError(
            code="TELEGRAM_LINK_NOT_STARTED",
            message="Telegram link flow is not started.",
        )
    if state.pending_code != code:
        raise TelegramLinkError(
            code="TELEGRAM_LINK_CODE_INVALID",
            message="Invalid Telegram link code.",
        )

    expires_at = datetime.fromisoformat(state.code_expires_at)
    if now > expires_at:
        raise TelegramLinkError(
            code="TELEGRAM_LINK_CODE_EXPIRED",
            message="Telegram link code is expired.",
        )
