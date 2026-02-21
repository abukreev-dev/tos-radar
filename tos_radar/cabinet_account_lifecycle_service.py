from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from tos_radar.cabinet_account_lifecycle_store import (
    read_account_lifecycle_state,
    write_account_lifecycle_state,
)
from tos_radar.cabinet_models import AccountLifecycleState, AccountStatus


class AccountLifecycleError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class AccessState:
    mode: str
    soft_deleted_at: str | None
    purge_at: str | None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "mode": self.mode,
            "soft_deleted_at": self.soft_deleted_at,
            "purge_at": self.purge_at,
        }


def start_soft_delete(
    tenant_id: str,
    user_id: str,
    *,
    now: datetime | None = None,
    ttl_days: int = 30,
) -> AccountLifecycleState:
    ts = now or datetime.now(UTC)
    state = AccountLifecycleState(
        status=AccountStatus.SOFT_DELETED,
        soft_deleted_at=ts.isoformat(),
        purge_at=(ts + timedelta(days=ttl_days)).isoformat(),
    )
    write_account_lifecycle_state(tenant_id, user_id, state)
    return state


def restore_account(
    tenant_id: str,
    user_id: str,
    *,
    now: datetime | None = None,
) -> AccountLifecycleState:
    ts = now or datetime.now(UTC)
    state = read_account_lifecycle_state(tenant_id, user_id)
    if state.status != AccountStatus.SOFT_DELETED:
        raise AccountLifecycleError(
            code="ACCOUNT_NOT_SOFT_DELETED",
            message="Account is not in soft-delete mode.",
        )
    if state.purge_at and ts > datetime.fromisoformat(state.purge_at):
        raise AccountLifecycleError(
            code="ACCOUNT_RESTORE_WINDOW_EXPIRED",
            message="Restore window is expired.",
        )

    active = AccountLifecycleState(status=AccountStatus.ACTIVE)
    write_account_lifecycle_state(tenant_id, user_id, active)
    return active


def get_access_state(
    tenant_id: str,
    user_id: str,
    *,
    now: datetime | None = None,
) -> AccessState:
    ts = now or datetime.now(UTC)
    state = read_account_lifecycle_state(tenant_id, user_id)
    if state.status == AccountStatus.SOFT_DELETED:
        if state.purge_at and ts > datetime.fromisoformat(state.purge_at):
            return AccessState(
                mode="PURGED",
                soft_deleted_at=state.soft_deleted_at,
                purge_at=state.purge_at,
            )
        return AccessState(
            mode="RECOVERY_ONLY",
            soft_deleted_at=state.soft_deleted_at,
            purge_at=state.purge_at,
        )
    return AccessState(mode="FULL_ACCESS", soft_deleted_at=None, purge_at=None)
