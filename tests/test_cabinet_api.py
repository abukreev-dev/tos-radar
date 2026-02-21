from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from tos_radar.cabinet_api import app
from tos_radar.cabinet_email_verify_service import EmailVerifyResendError
from tos_radar.cabinet_models import ChannelStatus, default_notification_settings


class CabinetApiTests(unittest.TestCase):
    def test_health_endpoint(self) -> None:
        with patch("tos_radar.cabinet_api.ping_mariadb"):
            status, body = _call("GET", "/api/v1/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["db"], "up")

    def test_get_notification_settings(self) -> None:
        with patch(
            "tos_radar.cabinet_api.read_notification_settings",
            return_value=default_notification_settings(),
        ), patch(
            "tos_radar.cabinet_api.is_session_active",
            return_value=True,
        ), patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type(
                "A",
                (),
                {"mode": "FULL_ACCESS"},
            )(),
        ):
            status, body = _call(
                "GET",
                "/api/v1/notification-settings",
                query="tenant_id=t1&user_id=u1",
                headers={"X-Session-Id": "s1"},
            )
        self.assertEqual(status, 200)
        self.assertIn("email_digest_enabled", body)

    def test_post_notification_settings_unverified_email_rejected(self) -> None:
        current = default_notification_settings()
        with patch(
            "tos_radar.cabinet_api.read_notification_settings",
            return_value=current,
        ), patch(
            "tos_radar.cabinet_api.is_session_active",
            return_value=True,
        ), patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type("A", (), {"mode": "FULL_ACCESS"})(),
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
                headers={"X-Session-Id": "s1"},
            )
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "EMAIL_UNVERIFIED")

    def test_post_email_verify_resend(self) -> None:
        with patch("tos_radar.cabinet_api.validate_and_mark_email_verify_resend"), patch(
            "tos_radar.cabinet_api.is_session_active",
            return_value=True,
        ), patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type("A", (), {"mode": "FULL_ACCESS"})(),
        ):
            status, body = _call(
                "POST",
                "/api/v1/email/verify/resend",
                payload={"tenant_id": "t1", "user_id": "u1"},
                headers={"X-Session-Id": "s1"},
            )
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

    def test_post_email_verify_resend_rate_limit_error(self) -> None:
        with patch(
            "tos_radar.cabinet_api.validate_and_mark_email_verify_resend",
            side_effect=EmailVerifyResendError(
                "EMAIL_VERIFY_RESEND_RATE_LIMIT",
                "rate limited",
            ),
        ), patch(
            "tos_radar.cabinet_api.is_session_active",
            return_value=True,
        ), patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type("A", (), {"mode": "FULL_ACCESS"})(),
        ):
            status, body = _call(
                "POST",
                "/api/v1/email/verify/resend",
                payload={"tenant_id": "t1", "user_id": "u1"},
                headers={"X-Session-Id": "s1"},
            )
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "EMAIL_VERIFY_RESEND_RATE_LIMIT")

    def test_post_telegram_start(self) -> None:
        with patch("tos_radar.cabinet_api.start_telegram_link", return_value="123456"), patch(
            "tos_radar.cabinet_api.is_session_active",
            return_value=True,
        ), patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type("A", (), {"mode": "FULL_ACCESS"})(),
        ):
            status, body = _call(
                "POST",
                "/api/v1/telegram/link/start",
                payload={"tenant_id": "t1", "user_id": "u1"},
                headers={"X-Session-Id": "s1"},
            )
        self.assertEqual(status, 200)
        self.assertEqual(body["code"], "123456")

    def test_post_telegram_disconnected(self) -> None:
        current = default_notification_settings().__class__(
            email_digest_enabled=False,
            telegram_digest_enabled=True,
            email_marketing_enabled=False,
            telegram_system_enabled=True,
            email_status=ChannelStatus.UNVERIFIED,
            telegram_status=ChannelStatus.ENABLED,
            email_error=None,
            telegram_error=None,
        )
        next_settings = default_notification_settings().__class__(
            email_digest_enabled=False,
            telegram_digest_enabled=False,
            email_marketing_enabled=False,
            telegram_system_enabled=False,
            email_status=ChannelStatus.UNVERIFIED,
            telegram_status=ChannelStatus.DISCONNECTED,
            email_error=None,
            telegram_error=None,
        )
        with patch("tos_radar.cabinet_api.read_notification_settings", return_value=current), patch(
            "tos_radar.cabinet_api.mark_telegram_disconnected",
            return_value=next_settings,
        ) as mocked_disconnected, patch("tos_radar.cabinet_api.write_notification_settings"), patch(
            "tos_radar.cabinet_api.is_session_active",
            return_value=True,
        ), patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type("A", (), {"mode": "FULL_ACCESS"})(),
        ):
            status, body = _call(
                "POST",
                "/api/v1/telegram/disconnected",
                payload={
                    "tenant_id": "t1",
                    "user_id": "u1",
                    "reason_message": "Bot blocked by user",
                },
                headers={"X-Session-Id": "s1"},
            )

        self.assertEqual(status, 200)
        self.assertFalse(body["telegram_digest_enabled"])
        mocked_disconnected.assert_called_once()

    def test_revoke_all_sessions_endpoint(self) -> None:
        with patch("tos_radar.cabinet_api.revoke_all_sessions_for_password_change", return_value=4), patch(
            "tos_radar.cabinet_api.is_session_active",
            return_value=True,
        ), patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type("A", (), {"mode": "FULL_ACCESS"})(),
        ):
            status, body = _call(
                "POST",
                "/api/v1/security/revoke-all-sessions",
                payload={"tenant_id": "t1", "user_id": "u1"},
                headers={"X-Session-Id": "s1"},
            )
        self.assertEqual(status, 200)
        self.assertEqual(body["revoked_sessions"], 4)

    def test_telegram_test_send_calls_transport(self) -> None:
        with patch(
            "tos_radar.cabinet_api.validate_and_mark_telegram_test_send",
            return_value="chat-123",
        ), patch(
            "tos_radar.cabinet_api.send_telegram_test_message",
        ) as mocked_send, patch(
            "tos_radar.cabinet_api.is_session_active",
            return_value=True,
        ), patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type("A", (), {"mode": "FULL_ACCESS"})(),
        ):
            status, body = _call(
                "POST",
                "/api/v1/telegram/test-send",
                payload={"tenant_id": "t1", "user_id": "u1"},
                headers={"X-Session-Id": "s1"},
            )
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        mocked_send.assert_called_once()

    def test_soft_delete_start_and_access_state(self) -> None:
        with patch(
            "tos_radar.cabinet_api.start_soft_delete",
            return_value=type(
                "S",
                (),
                {
                    "status": type("St", (), {"value": "SOFT_DELETED"})(),
                    "soft_deleted_at": "2026-02-21T10:00:00+00:00",
                    "purge_at": "2026-03-23T10:00:00+00:00",
                },
            )(),
        ), patch(
            "tos_radar.cabinet_api.is_session_active",
            return_value=True,
        ), patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type("A", (), {"mode": "FULL_ACCESS"})(),
        ):
            status, body = _call(
                "POST",
                "/api/v1/account/soft-delete/start",
                payload={"tenant_id": "t1", "user_id": "u1"},
                headers={"X-Session-Id": "s1"},
            )
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "SOFT_DELETED")

        with patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type(
                "A",
                (),
                {
                    "to_dict": lambda self: {
                        "mode": "RECOVERY_ONLY",
                        "soft_deleted_at": "2026-02-21T10:00:00+00:00",
                        "purge_at": "2026-03-23T10:00:00+00:00",
                    }
                },
            )(),
        ):
            status, body = _call(
                "GET",
                "/api/v1/account/access-state",
                query="tenant_id=t1&user_id=u1",
            )
        self.assertEqual(status, 200)
        self.assertEqual(body["mode"], "RECOVERY_ONLY")

    def test_session_required_on_protected_endpoint(self) -> None:
        with patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type("A", (), {"mode": "FULL_ACCESS"})(),
        ):
            status, body = _call(
                "GET",
                "/api/v1/notification-settings",
                query="tenant_id=t1&user_id=u1",
            )
        self.assertEqual(status, 401)
        self.assertEqual(body["error"], "SESSION_REQUIRED")

    def test_get_billing_plan_endpoint(self) -> None:
        with patch("tos_radar.cabinet_api.get_billing_plan", return_value="PAID_30"), patch(
            "tos_radar.cabinet_api.is_session_active",
            return_value=True,
        ), patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type("A", (), {"mode": "FULL_ACCESS"})(),
        ):
            status, body = _call(
                "GET",
                "/api/v1/billing/plan",
                query="tenant_id=t1&user_id=u1",
                headers={"X-Session-Id": "s1"},
            )
        self.assertEqual(status, 200)
        self.assertEqual(body["plan_code"], "PAID_30")


def _call(
    method: str,
    path: str,
    *,
    query: str = "",
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict]:
    body_bytes = json.dumps(payload or {}).encode("utf-8")
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "CONTENT_LENGTH": str(len(body_bytes)),
        "wsgi.input": io.BytesIO(body_bytes),
    }
    for k, v in (headers or {}).items():
        environ[f"HTTP_{k.upper().replace('-', '_')}"] = v
    response_status: dict[str, str] = {}

    def start_response(status: str, headers):  # type: ignore[no-untyped-def]
        response_status["status"] = status

    chunks = app(environ, start_response)
    body = b"".join(chunks).decode("utf-8")
    status_code = int(response_status["status"].split(" ", 1)[0])
    return status_code, json.loads(body)


if __name__ == "__main__":
    unittest.main()
