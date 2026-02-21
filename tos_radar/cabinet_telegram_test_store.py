from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tos_radar.mariadb import connect_mariadb, ensure_cabinet_schema


@dataclass(frozen=True)
class TelegramTestSendState:
    last_sent_at: str | None = None
    day: str | None = None
    day_count: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TelegramTestSendState:
        last_sent_at = data.get("last_sent_at")
        day = data.get("day")
        day_count = data.get("day_count", 0)
        if last_sent_at is not None and not isinstance(last_sent_at, str):
            raise ValueError("invalid field 'last_sent_at'")
        if day is not None and not isinstance(day, str):
            raise ValueError("invalid field 'day'")
        if not isinstance(day_count, int) or day_count < 0:
            raise ValueError("invalid field 'day_count'")
        return cls(last_sent_at=last_sent_at, day=day, day_count=day_count)

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_sent_at": self.last_sent_at,
            "day": self.day,
            "day_count": self.day_count,
        }


def read_telegram_test_send_state(tenant_id: str, user_id: str) -> TelegramTestSendState:
    ensure_cabinet_schema()
    conn = connect_mariadb()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT last_sent_at, day_key, day_count
                FROM cabinet_telegram_test_send_state
                WHERE tenant_id=%s AND user_id=%s
                """,
                (tenant_id, user_id),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return TelegramTestSendState()
    return TelegramTestSendState(
        last_sent_at=row["last_sent_at"],
        day=row["day_key"],
        day_count=int(row["day_count"]),
    )


def write_telegram_test_send_state(
    tenant_id: str,
    user_id: str,
    state: TelegramTestSendState,
) -> None:
    ensure_cabinet_schema()
    conn = connect_mariadb()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO cabinet_telegram_test_send_state (
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
