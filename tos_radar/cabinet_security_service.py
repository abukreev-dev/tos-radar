from __future__ import annotations

from datetime import UTC, datetime

from tos_radar.cabinet_security_store import (
    count_active_sessions,
    create_session_record,
    revoke_all_active_sessions,
)


def create_session(
    tenant_id: str,
    user_id: str,
    session_id: str,
    *,
    now: datetime | None = None,
) -> None:
    ts = now or datetime.now(UTC)
    create_session_record(tenant_id, user_id, session_id, ts.isoformat())


def revoke_all_sessions_for_password_change(
    tenant_id: str,
    user_id: str,
    *,
    now: datetime | None = None,
) -> int:
    ts = now or datetime.now(UTC)
    return revoke_all_active_sessions(tenant_id, user_id, ts.isoformat())


def get_active_sessions_count(tenant_id: str, user_id: str) -> int:
    return count_active_sessions(tenant_id, user_id)
