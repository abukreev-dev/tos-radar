from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from tos_radar.cabinet_api import app
from tos_radar.cabinet_models import ChannelStatus, default_notification_settings


class CabinetApiTests(unittest.TestCase):
    def test_get_notification_settings(self) -> None:
        with patch(
            "tos_radar.cabinet_api.read_notification_settings",
            return_value=default_notification_settings(),
        ):
            status, body = _call(
                "GET",
                "/api/v1/notification-settings",
                query="tenant_id=t1&user_id=u1",
            )
        self.assertEqual(status, 200)
        self.assertIn("email_digest_enabled", body)

    def test_post_notification_settings_unverified_email_rejected(self) -> None:
        current = default_notification_settings()
        with patch(
            "tos_radar.cabinet_api.read_notification_settings",
            return_value=current,
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

    def test_post_telegram_start(self) -> None:
        with patch("tos_radar.cabinet_api.start_telegram_link", return_value="123456"):
            status, body = _call(
                "POST",
                "/api/v1/telegram/link/start",
                payload={"tenant_id": "t1", "user_id": "u1"},
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
        ) as mocked_disconnected, patch("tos_radar.cabinet_api.write_notification_settings"):
            status, body = _call(
                "POST",
                "/api/v1/telegram/disconnected",
                payload={
                    "tenant_id": "t1",
                    "user_id": "u1",
                    "reason_message": "Bot blocked by user",
                },
            )

        self.assertEqual(status, 200)
        self.assertFalse(body["telegram_digest_enabled"])
        mocked_disconnected.assert_called_once()


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
