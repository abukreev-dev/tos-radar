from __future__ import annotations

from tos_radar.mariadb import connect_mariadb


def create_session_record(
    tenant_id: str,
    user_id: str,
    session_id: str,
    issued_at: str,
) -> None:
    conn = connect_mariadb()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cabinet_user_sessions (
                    tenant_id, user_id, session_id, issued_at, revoked_at, is_active
                ) VALUES (%s, %s, %s, %s, NULL, 1)
                ON DUPLICATE KEY UPDATE
                    issued_at=VALUES(issued_at),
                    revoked_at=NULL,
                    is_active=1
                """,
                (tenant_id, user_id, session_id, issued_at),
            )
    finally:
        conn.close()


def revoke_all_active_sessions(tenant_id: str, user_id: str, revoked_at: str) -> int:
    conn = connect_mariadb()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE cabinet_user_sessions
                SET is_active=0, revoked_at=%s
                WHERE tenant_id=%s AND user_id=%s AND is_active=1
                """,
                (revoked_at, tenant_id, user_id),
            )
            return int(cur.rowcount)
    finally:
        conn.close()


def count_active_sessions(tenant_id: str, user_id: str) -> int:
    conn = connect_mariadb()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS cnt
                FROM cabinet_user_sessions
                WHERE tenant_id=%s AND user_id=%s AND is_active=1
                """,
                (tenant_id, user_id),
            )
            row = cur.fetchone()
            return int(row["cnt"]) if row else 0
    finally:
        conn.close()
