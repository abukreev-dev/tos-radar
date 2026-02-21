from __future__ import annotations

from tos_radar.cabinet_models import AccountLifecycleState, AccountStatus
from tos_radar.mariadb import connect_mariadb


def read_account_lifecycle_state(tenant_id: str, user_id: str) -> AccountLifecycleState:
    conn = connect_mariadb()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT status, soft_deleted_at, purge_at
                FROM cabinet_account_lifecycle
                WHERE tenant_id=%s AND user_id=%s
                """,
                (tenant_id, user_id),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return AccountLifecycleState(status=AccountStatus.ACTIVE)
    return AccountLifecycleState(
        status=AccountStatus(row["status"]),
        soft_deleted_at=row["soft_deleted_at"],
        purge_at=row["purge_at"],
    )


def write_account_lifecycle_state(
    tenant_id: str,
    user_id: str,
    state: AccountLifecycleState,
) -> None:
    conn = connect_mariadb()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cabinet_account_lifecycle (
                    tenant_id, user_id, status, soft_deleted_at, purge_at
                ) VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    status=VALUES(status),
                    soft_deleted_at=VALUES(soft_deleted_at),
                    purge_at=VALUES(purge_at)
                """,
                (
                    tenant_id,
                    user_id,
                    state.status.value,
                    state.soft_deleted_at,
                    state.purge_at,
                ),
            )
    finally:
        conn.close()
