from __future__ import annotations

import json
from pathlib import Path

from tos_radar.cabinet_models import NotificationSettings, default_notification_settings


def _settings_path(tenant_id: str, user_id: str) -> Path:
    return (
        Path("data")
        / "cabinet"
        / tenant_id
        / "users"
        / user_id
        / "notification_settings.json"
    )


def read_notification_settings(tenant_id: str, user_id: str) -> NotificationSettings:
    path = _settings_path(tenant_id, user_id)
    if not path.exists():
        return default_notification_settings()

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("invalid settings payload: expected object")
    return NotificationSettings.from_dict(payload)


def write_notification_settings(
    tenant_id: str, user_id: str, settings: NotificationSettings
) -> None:
    path = _settings_path(tenant_id, user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(settings.to_dict(), ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
