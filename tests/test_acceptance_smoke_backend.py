from __future__ import annotations

import io
import json
import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from tos_radar.cabinet_api import app
from tos_radar.cabinet_models import (
    AccountLifecycleState,
    AccountStatus,
    ChannelStatus,
    default_notification_settings,
)
from tos_radar.cabinet_telegram_service import TelegramLinkError


class _MemoryBackend:
    def __init__(self) -> None:
        self.settings: dict[tuple[str, str], object] = {}
        self.pending_codes: dict[tuple[str, str], tuple[str, datetime]] = {}
        self.linked_chats: dict[tuple[str, str], str] = {}
        self.last_test_sent: dict[tuple[str, str], datetime] = {}
        self.day_count: dict[tuple[str, str, str], int] = {}
        self.active_sessions: dict[tuple[str, str], set[str]] = {}
        self.lifecycle: dict[tuple[str, str], AccountLifecycleState] = {}

    def read_settings(self, tenant_id: str, user_id: str):
        return self.settings.get((tenant_id, user_id), default_notification_settings())

    def write_settings(self, tenant_id: str, user_id: str, settings):
        self.settings[(tenant_id, user_id)] = settings

    def start_link(self, tenant_id: str, user_id: str, now: datetime | None = None) -> str:
        code = "111111"
        ts = now or datetime.now(UTC)
        self.pending_codes[(tenant_id, user_id)] = (code, ts + timedelta(minutes=10))
        return code

    def confirm_link(
        self,
        tenant_id: str,
        user_id: str,
        *,
        code: str,
        chat_id: str,
        current_settings,
        now: datetime | None = None,
    ):
        expected = self.pending_codes.get((tenant_id, user_id))
        ts = now or datetime.now(UTC)
        if not expected:
            raise TelegramLinkError("TELEGRAM_LINK_NOT_STARTED", "not started")
        exp_code, exp_at = expected
        if code != exp_code:
            raise TelegramLinkError("TELEGRAM_LINK_CODE_INVALID", "invalid")
        if ts > exp_at:
            raise TelegramLinkError("TELEGRAM_LINK_CODE_EXPIRED", "expired")
        self.linked_chats[(tenant_id, user_id)] = chat_id
        self.pending_codes.pop((tenant_id, user_id), None)
        return current_settings.__class__(
            email_digest_enabled=current_settings.email_digest_enabled,
            telegram_digest_enabled=current_settings.telegram_digest_enabled,
            email_marketing_enabled=current_settings.email_marketing_enabled,
            telegram_system_enabled=current_settings.telegram_system_enabled,
            email_status=current_settings.email_status,
            telegram_status=ChannelStatus.ENABLED,
            email_error=current_settings.email_error,
            telegram_error=None,
        )

    def unlink(self, tenant_id: str, user_id: str, *, current_settings):
        self.linked_chats.pop((tenant_id, user_id), None)
        return current_settings.__class__(
            email_digest_enabled=current_settings.email_digest_enabled,
            telegram_digest_enabled=False,
            email_marketing_enabled=current_settings.email_marketing_enabled,
            telegram_system_enabled=False,
            email_status=current_settings.email_status,
            telegram_status=ChannelStatus.DISCONNECTED,
            email_error=current_settings.email_error,
            telegram_error=None,
        )

    def disconnected(self, tenant_id: str, user_id: str, *, current_settings, reason_message: str, now=None):
        return self.unlink(tenant_id, user_id, current_settings=current_settings)

    def validate_test_send(self, tenant_id: str, user_id: str, *, now: datetime | None = None, **_):
        ts = now or datetime.now(UTC)
        if (tenant_id, user_id) not in self.linked_chats:
            raise TelegramLinkError("TELEGRAM_NOT_LINKED", "not linked")
        last = self.last_test_sent.get((tenant_id, user_id))
        if last and (ts - last).total_seconds() < 60:
            raise TelegramLinkError("TELEGRAM_TEST_RATE_LIMIT", "rate limit")
        day_key = ts.date().isoformat()
        counter_key = (tenant_id, user_id, day_key)
        if self.day_count.get(counter_key, 0) >= 20:
            raise TelegramLinkError("TELEGRAM_TEST_DAILY_LIMIT", "daily limit")
        self.day_count[counter_key] = self.day_count.get(counter_key, 0) + 1
        self.last_test_sent[(tenant_id, user_id)] = ts

    def create_session(self, tenant_id: str, user_id: str, session_id: str, now=None):
        self.active_sessions.setdefault((tenant_id, user_id), set()).add(session_id)

    def revoke_sessions(self, tenant_id: str, user_id: str, now=None) -> int:
        sessions = self.active_sessions.setdefault((tenant_id, user_id), set())
        count = len(sessions)
        sessions.clear()
        return count

    def active_count(self, tenant_id: str, user_id: str) -> int:
        return len(self.active_sessions.get((tenant_id, user_id), set()))

    def start_soft_delete(self, tenant_id: str, user_id: str, now=None):
        ts = now or datetime.now(UTC)
        state = AccountLifecycleState(
            status=AccountStatus.SOFT_DELETED,
            soft_deleted_at=ts.isoformat(),
            purge_at=(ts + timedelta(days=30)).isoformat(),
        )
        self.lifecycle[(tenant_id, user_id)] = state
        return state

    def restore_account(self, tenant_id: str, user_id: str, now=None):
        self.lifecycle[(tenant_id, user_id)] = AccountLifecycleState(status=AccountStatus.ACTIVE)
        return self.lifecycle[(tenant_id, user_id)]

    def access_state(self, tenant_id: str, user_id: str, now=None):
        state = self.lifecycle.get((tenant_id, user_id))
        if not state or state.status == AccountStatus.ACTIVE:
            return type(
                "A",
                (),
                {"to_dict": lambda self: {"mode": "FULL_ACCESS", "soft_deleted_at": None, "purge_at": None}},
            )()
        return type(
            "A",
            (),
            {
                "to_dict": lambda self: {
                    "mode": "RECOVERY_ONLY",
                    "soft_deleted_at": state.soft_deleted_at,
                    "purge_at": state.purge_at,
                }
            },
        )()


class BackendAcceptanceSmokeTests(unittest.TestCase):
    def test_smoke_core_flows(self) -> None:
        mem = _MemoryBackend()
        with patch("tos_radar.cabinet_api.read_notification_settings", side_effect=mem.read_settings), patch(
            "tos_radar.cabinet_api.write_notification_settings", side_effect=mem.write_settings
        ), patch("tos_radar.cabinet_api.start_telegram_link", side_effect=mem.start_link), patch(
            "tos_radar.cabinet_api.confirm_telegram_link", side_effect=mem.confirm_link
        ), patch("tos_radar.cabinet_api.unlink_telegram", side_effect=mem.unlink), patch(
            "tos_radar.cabinet_api.mark_telegram_disconnected", side_effect=mem.disconnected
        ), patch(
            "tos_radar.cabinet_api.validate_and_mark_telegram_test_send",
            side_effect=mem.validate_test_send,
        ), patch(
            "tos_radar.cabinet_api.create_session", side_effect=mem.create_session
        ), patch(
            "tos_radar.cabinet_api.revoke_all_sessions_for_password_change",
            side_effect=mem.revoke_sessions,
        ), patch(
            "tos_radar.cabinet_api.get_active_sessions_count", side_effect=mem.active_count
        ), patch(
            "tos_radar.cabinet_api.start_soft_delete", side_effect=mem.start_soft_delete
        ), patch(
            "tos_radar.cabinet_api.restore_account", side_effect=mem.restore_account
        ), patch(
            "tos_radar.cabinet_api.get_access_state", side_effect=mem.access_state
        ):
            status, body = _call(
                "POST",
                "/api/v1/notification-settings",
                payload={
                    "tenant_id": "t1",
                    "user_id": "u1",
                    "email_verified": False,
                    "email_digest_enabled": True,
                },
            )
            self.assertEqual(status, 400)
            self.assertEqual(body["error"], "EMAIL_UNVERIFIED")

            status, body = _call(
                "POST",
                "/api/v1/telegram/link/start",
                payload={"tenant_id": "t1", "user_id": "u1"},
            )
            self.assertEqual(status, 200)
            self.assertEqual(body["code"], "111111")

            status, _ = _call(
                "POST",
                "/api/v1/telegram/link/confirm",
                payload={
                    "tenant_id": "t1",
                    "user_id": "u1",
                    "code": "111111",
                    "chat_id": "chat-1",
                },
            )
            self.assertEqual(status, 200)

            status, _ = _call(
                "POST",
                "/api/v1/telegram/test-send",
                payload={"tenant_id": "t1", "user_id": "u1"},
            )
            self.assertEqual(status, 200)

            _call(
                "POST",
                "/api/v1/security/sessions/create",
                payload={"tenant_id": "t1", "user_id": "u1", "session_id": "s1"},
            )
            _call(
                "POST",
                "/api/v1/security/sessions/create",
                payload={"tenant_id": "t1", "user_id": "u1", "session_id": "s2"},
            )
            status, body = _call(
                "GET",
                "/api/v1/security/active-sessions",
                query="tenant_id=t1&user_id=u1",
            )
            self.assertEqual(status, 200)
            self.assertEqual(body["active_sessions"], 2)

            status, body = _call(
                "POST",
                "/api/v1/security/revoke-all-sessions",
                payload={"tenant_id": "t1", "user_id": "u1"},
            )
            self.assertEqual(status, 200)
            self.assertEqual(body["revoked_sessions"], 2)

            status, body = _call(
                "POST",
                "/api/v1/account/soft-delete/start",
                payload={"tenant_id": "t1", "user_id": "u1"},
            )
            self.assertEqual(status, 200)
            self.assertEqual(body["status"], "SOFT_DELETED")

            status, body = _call(
                "GET",
                "/api/v1/account/access-state",
                query="tenant_id=t1&user_id=u1",
            )
            self.assertEqual(status, 200)
            self.assertEqual(body["mode"], "RECOVERY_ONLY")

            status, body = _call(
                "POST",
                "/api/v1/account/soft-delete/restore",
                payload={"tenant_id": "t1", "user_id": "u1"},
            )
            self.assertEqual(status, 200)
            self.assertEqual(body["status"], "ACTIVE")


def _call(
    method: str,
    path: str,
    *,
    query: str = "",
    payload: dict | None = None,
) -> tuple[int, dict]:
    body_bytes = json.dumps(payload or {}).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": str(len(body_bytes)),
        "wsgi.input": io.BytesIO(body_bytes),
    }
    response_status: dict[str, str] = {}

    def start_response(status: str, headers):  # type: ignore[no-untyped-def]
        response_status["status"] = status

    chunks = app(environ, start_response)
    body = b"".join(chunks).decode("utf-8")
    status_code = int(response_status["status"].split(" ", 1)[0])
    return status_code, json.loads(body)


if __name__ == "__main__":
    unittest.main()
