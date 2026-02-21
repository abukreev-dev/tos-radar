from __future__ import annotations

from datetime import UTC, datetime

from tos_radar.cabinet_telegram_service import TelegramLinkError
from tos_radar.cabinet_telegram_store import read_telegram_link_state
from tos_radar.cabinet_telegram_test_store import (
    TelegramTestSendState,
    read_telegram_test_send_state,
    write_telegram_test_send_state,
)


def validate_and_mark_telegram_test_send(
    tenant_id: str,
    user_id: str,
    *,
    now: datetime | None = None,
    min_interval_sec: int = 60,
    daily_limit: int = 20,
) -> str:
    ts = now or datetime.now(UTC)
    link_state = read_telegram_link_state(tenant_id, user_id)
    if not link_state.chat_id:
        raise TelegramLinkError(
            code="TELEGRAM_NOT_LINKED",
            message="Telegram channel is not linked.",
        )

    state = read_telegram_test_send_state(tenant_id, user_id)
    _validate_rate_limits(
        ts=ts,
        state=state,
        min_interval_sec=min_interval_sec,
        daily_limit=daily_limit,
    )

    today = ts.date().isoformat()
    next_count = state.day_count + 1 if state.day == today else 1
    write_telegram_test_send_state(
        tenant_id,
        user_id,
        TelegramTestSendState(
            last_sent_at=ts.isoformat(),
            day=today,
            day_count=next_count,
        ),
    )
    return link_state.chat_id


def _validate_rate_limits(
    *,
    ts: datetime,
    state: TelegramTestSendState,
    min_interval_sec: int,
    daily_limit: int,
) -> None:
    if state.last_sent_at:
        last_sent_at = datetime.fromisoformat(state.last_sent_at)
        elapsed = (ts - last_sent_at).total_seconds()
        if elapsed < min_interval_sec:
            raise TelegramLinkError(
                code="TELEGRAM_TEST_RATE_LIMIT",
                message="Telegram test send rate limit exceeded.",
            )

    today = ts.date().isoformat()
    if state.day == today and state.day_count >= daily_limit:
        raise TelegramLinkError(
            code="TELEGRAM_TEST_DAILY_LIMIT",
            message="Telegram test send daily limit exceeded.",
        )
