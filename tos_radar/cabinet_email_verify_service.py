from __future__ import annotations

from datetime import UTC, datetime

from tos_radar.cabinet_email_verify_store import (
    EmailVerifyResendState,
    read_email_verify_resend_state,
    write_email_verify_resend_state,
)


class EmailVerifyResendError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def validate_and_mark_email_verify_resend(
    tenant_id: str,
    user_id: str,
    *,
    now: datetime | None = None,
    min_interval_sec: int = 60,
    daily_limit: int = 10,
) -> None:
    ts = now or datetime.now(UTC)
    state = read_email_verify_resend_state(tenant_id, user_id)
    _validate_rate_limits(ts=ts, state=state, min_interval_sec=min_interval_sec, daily_limit=daily_limit)

    today = ts.date().isoformat()
    next_count = state.day_count + 1 if state.day == today else 1
    write_email_verify_resend_state(
        tenant_id,
        user_id,
        EmailVerifyResendState(
            last_sent_at=ts.isoformat(),
            day=today,
            day_count=next_count,
        ),
    )


def _validate_rate_limits(
    *,
    ts: datetime,
    state: EmailVerifyResendState,
    min_interval_sec: int,
    daily_limit: int,
) -> None:
    if state.last_sent_at:
        elapsed = (ts - datetime.fromisoformat(state.last_sent_at)).total_seconds()
        if elapsed < min_interval_sec:
            raise EmailVerifyResendError(
                code="EMAIL_VERIFY_RESEND_RATE_LIMIT",
                message="Email verify resend rate limit exceeded.",
            )

    today = ts.date().isoformat()
    if state.day == today and state.day_count >= daily_limit:
        raise EmailVerifyResendError(
            code="EMAIL_VERIFY_RESEND_DAILY_LIMIT",
            message="Email verify resend daily limit exceeded.",
        )
