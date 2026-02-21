from __future__ import annotations

import json
from datetime import UTC, datetime
from http import HTTPStatus
from wsgiref.simple_server import make_server

from tos_radar.cabinet_service import (
    SettingsValidationError,
    apply_notification_settings_update,
)
from tos_radar.cabinet_store import read_notification_settings, write_notification_settings
from tos_radar.cabinet_telegram_service import (
    TelegramLinkError,
    confirm_telegram_link,
    start_telegram_link,
    unlink_telegram,
)
from tos_radar.cabinet_telegram_test_service import validate_and_mark_telegram_test_send
from tos_radar.mariadb import ensure_cabinet_schema


def run_api_server(host: str, port: int) -> None:
    ensure_cabinet_schema()
    with make_server(host, port, app) as server:
        print(f"cabinet-api listening on http://{host}:{port}")
        server.serve_forever()


def app(environ: dict, start_response):  # type: ignore[no-untyped-def]
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "")
    try:
        if method == "GET" and path == "/api/v1/notification-settings":
            params = _parse_query(environ)
            tenant_id = _require_str(params, "tenant_id")
            user_id = _require_str(params, "user_id")
            settings = read_notification_settings(tenant_id, user_id)
            return _json(start_response, HTTPStatus.OK, settings.to_dict())

        if method == "POST" and path == "/api/v1/notification-settings":
            payload = _read_json(environ)
            tenant_id = _require_str(payload, "tenant_id")
            user_id = _require_str(payload, "user_id")
            email_verified = _require_bool(payload, "email_verified")

            current = read_notification_settings(tenant_id, user_id)
            next_settings = apply_notification_settings_update(
                current,
                email_verified=email_verified,
                email_digest_enabled=payload.get("email_digest_enabled"),
                telegram_digest_enabled=payload.get("telegram_digest_enabled"),
                email_marketing_enabled=payload.get("email_marketing_enabled"),
                telegram_system_enabled=payload.get("telegram_system_enabled"),
            )
            write_notification_settings(tenant_id, user_id, next_settings)
            return _json(start_response, HTTPStatus.OK, next_settings.to_dict())

        if method == "POST" and path == "/api/v1/telegram/link/start":
            payload = _read_json(environ)
            tenant_id = _require_str(payload, "tenant_id")
            user_id = _require_str(payload, "user_id")
            code = start_telegram_link(tenant_id, user_id, now=datetime.now(UTC))
            return _json(start_response, HTTPStatus.OK, {"code": code})

        if method == "POST" and path == "/api/v1/telegram/link/confirm":
            payload = _read_json(environ)
            tenant_id = _require_str(payload, "tenant_id")
            user_id = _require_str(payload, "user_id")
            code = _require_str(payload, "code")
            chat_id = _require_str(payload, "chat_id")
            current = read_notification_settings(tenant_id, user_id)
            next_settings = confirm_telegram_link(
                tenant_id,
                user_id,
                code=code,
                chat_id=chat_id,
                current_settings=current,
                now=datetime.now(UTC),
            )
            write_notification_settings(tenant_id, user_id, next_settings)
            return _json(start_response, HTTPStatus.OK, next_settings.to_dict())

        if method == "POST" and path == "/api/v1/telegram/unlink":
            payload = _read_json(environ)
            tenant_id = _require_str(payload, "tenant_id")
            user_id = _require_str(payload, "user_id")
            current = read_notification_settings(tenant_id, user_id)
            next_settings = unlink_telegram(tenant_id, user_id, current_settings=current)
            write_notification_settings(tenant_id, user_id, next_settings)
            return _json(start_response, HTTPStatus.OK, next_settings.to_dict())

        if method == "POST" and path == "/api/v1/telegram/test-send":
            payload = _read_json(environ)
            tenant_id = _require_str(payload, "tenant_id")
            user_id = _require_str(payload, "user_id")
            validate_and_mark_telegram_test_send(
                tenant_id,
                user_id,
                now=datetime.now(UTC),
                min_interval_sec=60,
                daily_limit=20,
            )
            return _json(start_response, HTTPStatus.OK, {"ok": True})

        return _json(start_response, HTTPStatus.NOT_FOUND, {"error": "NOT_FOUND"})
    except SettingsValidationError as exc:
        return _json(
            start_response,
            HTTPStatus.BAD_REQUEST,
            {"error": exc.code, "message": str(exc)},
        )
    except TelegramLinkError as exc:
        return _json(
            start_response,
            HTTPStatus.BAD_REQUEST,
            {"error": exc.code, "message": str(exc)},
        )
    except ValueError as exc:
        return _json(
            start_response,
            HTTPStatus.BAD_REQUEST,
            {"error": "VALIDATION_ERROR", "message": str(exc)},
        )
    except Exception as exc:  # pragma: no cover
        return _json(
            start_response,
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {"error": "INTERNAL_ERROR", "message": str(exc)},
        )


def _parse_query(environ: dict) -> dict[str, str]:
    raw = environ.get("QUERY_STRING", "")
    out: dict[str, str] = {}
    for pair in raw.split("&"):
        if not pair:
            continue
        if "=" not in pair:
            out[pair] = ""
            continue
        key, val = pair.split("=", 1)
        out[key] = val
    return out


def _read_json(environ: dict) -> dict:
    body_size = int(environ.get("CONTENT_LENGTH", "0") or "0")
    body = environ["wsgi.input"].read(body_size) if body_size > 0 else b"{}"
    payload = json.loads(body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("request body must be JSON object")
    return payload


def _json(start_response, status: HTTPStatus, payload: dict):  # type: ignore[no-untyped-def]
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    start_response(
        f"{status.value} {status.phrase}",
        [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(body)))],
    )
    return [body]


def _require_str(payload: dict, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"invalid '{key}': expected non-empty string")
    return value


def _require_bool(payload: dict, key: str) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"invalid '{key}': expected bool")
    return value
