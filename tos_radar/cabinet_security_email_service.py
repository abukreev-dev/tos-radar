from __future__ import annotations

import logging
from datetime import UTC, datetime

from tos_radar.cabinet_email_transport import send_email

logger = logging.getLogger(__name__)


def notify_password_changed(
    tenant_id: str,
    user_id: str,
    email: str,
    *,
    changed_at: datetime | None = None,
) -> dict[str, int]:
    ts = (changed_at or datetime.now(UTC)).isoformat()
    return _deliver(
        tenant_id=tenant_id,
        user_id=user_id,
        recipients=[email],
        subject="Security alert: password changed",
        body=f"Password changed for account {user_id} at {ts}. If this was not you, contact support.",
    )


def notify_email_changed(
    tenant_id: str,
    user_id: str,
    old_email: str,
    new_email: str,
    *,
    changed_at: datetime | None = None,
) -> dict[str, int]:
    ts = (changed_at or datetime.now(UTC)).isoformat()
    return _deliver(
        tenant_id=tenant_id,
        user_id=user_id,
        recipients=[old_email, new_email],
        subject="Security alert: email changed",
        body=f"Email changed for account {user_id} at {ts}. If this was not you, contact support.",
    )


def _deliver(
    *,
    tenant_id: str,
    user_id: str,
    recipients: list[str],
    subject: str,
    body: str,
) -> dict[str, int]:
    sent = 0
    failed = 0
    for recipient in recipients:
        try:
            send_email(to_email=recipient, subject=subject, body=body)
            sent += 1
        except Exception:
            failed += 1
            logger.exception(
                "security email delivery failed tenant_id=%s user_id=%s recipient=%s",
                tenant_id,
                user_id,
                recipient,
            )
    return {"sent": sent, "failed": failed}
