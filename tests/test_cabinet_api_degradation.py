from __future__ import annotations

import io
import json
import unittest
from unittest.mock import patch

from tos_radar.cabinet_api import app
from tos_radar.cabinet_models import default_notification_settings


class CabinetApiDegradationTests(unittest.TestCase):
    def test_notification_settings_returns_400_on_validation_error(self) -> None:
        with patch("tos_radar.cabinet_api.is_session_active", return_value=True), patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type("A", (), {"mode": "FULL_ACCESS"})(),
        ):
            status, body = _call(
                "POST",
                "/api/v1/notification-settings",
                payload={
                    "tenant_id": "t1",
                    "user_id": "u1",
                    "email_verified": "yes",
                    "email_digest_enabled": True,
                },
                headers={"X-Session-Id": "s1"},
            )
        self.assertEqual(status, 400)
        self.assertEqual(body["error"], "VALIDATION_ERROR")

    def test_notification_settings_returns_400_on_business_rule_error(self) -> None:
        with patch(
            "tos_radar.cabinet_api.read_notification_settings",
            return_value=default_notification_settings(),
        ), patch("tos_radar.cabinet_api.is_session_active", return_value=True), patch(
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

    def test_notification_settings_returns_504_on_timeout(self) -> None:
        with patch(
            "tos_radar.cabinet_api.read_notification_settings",
            side_effect=TimeoutError("db timeout"),
        ), patch("tos_radar.cabinet_api.is_session_active", return_value=True), patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type("A", (), {"mode": "FULL_ACCESS"})(),
        ):
            status, body = _call(
                "POST",
                "/api/v1/notification-settings",
                payload={
                    "tenant_id": "t1",
                    "user_id": "u1",
                    "email_verified": True,
                    "email_digest_enabled": True,
                },
                headers={"X-Session-Id": "s1"},
            )
        self.assertEqual(status, 504)
        self.assertEqual(body["error"], "UPSTREAM_TIMEOUT")

    def test_notification_settings_returns_503_on_network_error(self) -> None:
        with patch(
            "tos_radar.cabinet_api.read_notification_settings",
            return_value=default_notification_settings(),
        ), patch(
            "tos_radar.cabinet_api.write_notification_settings",
            side_effect=ConnectionError("db unavailable"),
        ), patch("tos_radar.cabinet_api.is_session_active", return_value=True), patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type("A", (), {"mode": "FULL_ACCESS"})(),
        ):
            status, body = _call(
                "POST",
                "/api/v1/notification-settings",
                payload={
                    "tenant_id": "t1",
                    "user_id": "u1",
                    "email_verified": True,
                    "email_digest_enabled": True,
                },
                headers={"X-Session-Id": "s1"},
            )
        self.assertEqual(status, 503)
        self.assertEqual(body["error"], "UPSTREAM_UNAVAILABLE")

    def test_notification_settings_returns_500_on_unhandled_error(self) -> None:
        with patch(
            "tos_radar.cabinet_api.read_notification_settings",
            side_effect=RuntimeError("unexpected"),
        ), patch("tos_radar.cabinet_api.is_session_active", return_value=True), patch(
            "tos_radar.cabinet_api.get_access_state",
            return_value=type("A", (), {"mode": "FULL_ACCESS"})(),
        ):
            status, body = _call(
                "POST",
                "/api/v1/notification-settings",
                payload={
                    "tenant_id": "t1",
                    "user_id": "u1",
                    "email_verified": True,
                    "email_digest_enabled": True,
                },
                headers={"X-Session-Id": "s1"},
            )
        self.assertEqual(status, 500)
        self.assertEqual(body["error"], "INTERNAL_ERROR")


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
