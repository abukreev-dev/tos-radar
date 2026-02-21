from __future__ import annotations

import json
from pathlib import Path

from tos_radar.cabinet_models import TelegramLinkState


def _telegram_state_path(tenant_id: str, user_id: str) -> Path:
    return Path("data") / "cabinet" / tenant_id / "users" / user_id / "telegram_link.json"


def read_telegram_link_state(tenant_id: str, user_id: str) -> TelegramLinkState:
    path = _telegram_state_path(tenant_id, user_id)
    if not path.exists():
        return TelegramLinkState()

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("invalid telegram link payload: expected object")
    return TelegramLinkState.from_dict(payload)


def write_telegram_link_state(tenant_id: str, user_id: str, state: TelegramLinkState) -> None:
    path = _telegram_state_path(tenant_id, user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state.to_dict(), ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
