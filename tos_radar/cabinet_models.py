from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ChannelStatus(str, Enum):
    ENABLED = "ENABLED"
    DISABLED = "DISABLED"
    UNVERIFIED = "UNVERIFIED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class ChannelError:
    code: str
    message: str
    updated_at: str


@dataclass(frozen=True)
class TelegramLinkState:
    pending_code: str | None = None
    code_expires_at: str | None = None
    chat_id: str | None = None
    linked_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pending_code": self.pending_code,
            "code_expires_at": self.code_expires_at,
            "chat_id": self.chat_id,
            "linked_at": self.linked_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TelegramLinkState:
        return cls(
            pending_code=_expect_optional_str(data, "pending_code"),
            code_expires_at=_expect_optional_str(data, "code_expires_at"),
            chat_id=_expect_optional_str(data, "chat_id"),
            linked_at=_expect_optional_str(data, "linked_at"),
        )


@dataclass(frozen=True)
class NotificationSettings:
    email_digest_enabled: bool
    telegram_digest_enabled: bool
    email_marketing_enabled: bool
    telegram_system_enabled: bool
    email_status: ChannelStatus
    telegram_status: ChannelStatus
    email_error: ChannelError | None = None
    telegram_error: ChannelError | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "email_digest_enabled": self.email_digest_enabled,
            "telegram_digest_enabled": self.telegram_digest_enabled,
            "email_marketing_enabled": self.email_marketing_enabled,
            "telegram_system_enabled": self.telegram_system_enabled,
            "email_status": self.email_status.value,
            "telegram_status": self.telegram_status.value,
            "email_error": _error_to_dict(self.email_error),
            "telegram_error": _error_to_dict(self.telegram_error),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotificationSettings:
        return cls(
            email_digest_enabled=_expect_bool(data, "email_digest_enabled"),
            telegram_digest_enabled=_expect_bool(data, "telegram_digest_enabled"),
            email_marketing_enabled=_expect_bool(data, "email_marketing_enabled"),
            telegram_system_enabled=_expect_bool(data, "telegram_system_enabled"),
            email_status=_expect_status(data, "email_status"),
            telegram_status=_expect_status(data, "telegram_status"),
            email_error=_expect_optional_error(data, "email_error"),
            telegram_error=_expect_optional_error(data, "telegram_error"),
        )


def default_notification_settings() -> NotificationSettings:
    return NotificationSettings(
        email_digest_enabled=False,
        telegram_digest_enabled=False,
        email_marketing_enabled=False,
        telegram_system_enabled=False,
        email_status=ChannelStatus.UNVERIFIED,
        telegram_status=ChannelStatus.DISCONNECTED,
        email_error=None,
        telegram_error=None,
    )


def _error_to_dict(error: ChannelError | None) -> dict[str, str] | None:
    if error is None:
        return None
    return {"code": error.code, "message": error.message, "updated_at": error.updated_at}


def _expect_bool(data: dict[str, Any], key: str) -> bool:
    value = data.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"invalid field '{key}': expected bool")
    return value


def _expect_status(data: dict[str, Any], key: str) -> ChannelStatus:
    value = data.get(key)
    if not isinstance(value, str):
        raise ValueError(f"invalid field '{key}': expected str")
    try:
        return ChannelStatus(value)
    except ValueError as exc:
        raise ValueError(f"invalid field '{key}': unknown status '{value}'") from exc


def _expect_optional_error(data: dict[str, Any], key: str) -> ChannelError | None:
    raw = data.get(key)
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"invalid field '{key}': expected object or null")

    code = raw.get("code")
    message = raw.get("message")
    updated_at = raw.get("updated_at")
    if not isinstance(code, str) or not code:
        raise ValueError(f"invalid field '{key}.code': expected non-empty str")
    if not isinstance(message, str) or not message:
        raise ValueError(f"invalid field '{key}.message': expected non-empty str")
    if not isinstance(updated_at, str) or not updated_at:
        raise ValueError(f"invalid field '{key}.updated_at': expected non-empty str")
    return ChannelError(code=code, message=message, updated_at=updated_at)


def _expect_optional_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"invalid field '{key}': expected str or null")
    return value
