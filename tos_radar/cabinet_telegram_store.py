from __future__ import annotations

from tos_radar.cabinet_models import TelegramLinkState
from tos_radar.mariadb import connect_mariadb


def read_telegram_link_state(tenant_id: str, user_id: str) -> TelegramLinkState:
    conn = connect_mariadb()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT pending_code, code_expires_at, chat_id, linked_at
                FROM cabinet_telegram_link_state
                WHERE tenant_id=%s AND user_id=%s
                """,
                (tenant_id, user_id),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return TelegramLinkState()
    return TelegramLinkState(
        pending_code=row["pending_code"],
        code_expires_at=row["code_expires_at"],
        chat_id=row["chat_id"],
        linked_at=row["linked_at"],
    )


def write_telegram_link_state(tenant_id: str, user_id: str, state: TelegramLinkState) -> None:
    conn = connect_mariadb()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cabinet_telegram_link_state (
                    tenant_id,
                    user_id,
                    pending_code,
                    code_expires_at,
                    chat_id,
                    linked_at
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    pending_code=VALUES(pending_code),
                    code_expires_at=VALUES(code_expires_at),
                    chat_id=VALUES(chat_id),
                    linked_at=VALUES(linked_at)
                """,
                (
                    tenant_id,
                    user_id,
                    state.pending_code,
                    state.code_expires_at,
                    state.chat_id,
                    state.linked_at,
                ),
            )
    finally:
        conn.close()
