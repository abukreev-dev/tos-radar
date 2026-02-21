from __future__ import annotations

from dataclasses import dataclass

from tos_radar.mariadb import connect_mariadb


@dataclass(frozen=True)
class EmailVerifyResendState:
    last_sent_at: str | None = None
    day: str | None = None
    day_count: int = 0


def read_email_verify_resend_state(tenant_id: str, user_id: str) -> EmailVerifyResendState:
    conn = connect_mariadb()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT last_sent_at, day_key, day_count
                FROM cabinet_email_verify_resend_state
                WHERE tenant_id=%s AND user_id=%s
                """,
                (tenant_id, user_id),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return EmailVerifyResendState()
    return EmailVerifyResendState(
        last_sent_at=row["last_sent_at"],
        day=row["day_key"],
        day_count=int(row["day_count"]),
    )


def write_email_verify_resend_state(
    tenant_id: str,
    user_id: str,
    state: EmailVerifyResendState,
) -> None:
    conn = connect_mariadb()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cabinet_email_verify_resend_state (
                    tenant_id,
                    user_id,
                    last_sent_at,
                    day_key,
                    day_count
                ) VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    last_sent_at=VALUES(last_sent_at),
                    day_key=VALUES(day_key),
                    day_count=VALUES(day_count)
                """,
                (
                    tenant_id,
                    user_id,
                    state.last_sent_at,
                    state.day,
                    state.day_count,
                ),
            )
    finally:
        conn.close()
