from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


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


def _state_path(tenant_id: str, user_id: str) -> Path:
    return (
        Path("data")
        / "cabinet"
        / tenant_id
        / "users"
        / user_id
        / "telegram_test_send_state.json"
    )


def read_telegram_test_send_state(tenant_id: str, user_id: str) -> TelegramTestSendState:
    path = _state_path(tenant_id, user_id)
    if not path.exists():
        return TelegramTestSendState()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("invalid telegram test-send payload: expected object")
    return TelegramTestSendState.from_dict(payload)


def write_telegram_test_send_state(
    tenant_id: str,
    user_id: str,
    state: TelegramTestSendState,
) -> None:
    path = _state_path(tenant_id, user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state.to_dict(), ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
