from __future__ import annotations

import json
from datetime import UTC, datetime
from http import HTTPStatus
from wsgiref.simple_server import make_server

from tos_radar.cabinet_service import (
    SettingsValidationError,
    apply_notification_settings_update,
)
from tos_radar.cabinet_account_lifecycle_service import (
    AccountLifecycleError,
    get_access_state,
    restore_account,
    start_soft_delete,
)
from tos_radar.cabinet_security_service import (
    create_session,
    get_active_sessions_count,
    revoke_all_sessions_for_password_change,
)
from tos_radar.cabinet_store import read_notification_settings, write_notification_settings
from tos_radar.cabinet_telegram_service import (
    TelegramLinkError,
    confirm_telegram_link,
    mark_telegram_disconnected,
    start_telegram_link,
    unlink_telegram,
)
from tos_radar.cabinet_telegram_test_service import validate_and_mark_telegram_test_send
from tos_radar.mariadb import ping_mariadb


def run_api_server(host: str, port: int) -> None:
    with make_server(host, port, app) as server:
        print(f"cabinet-api listening on http://{host}:{port}")
        server.serve_forever()


def app(environ: dict, start_response):  # type: ignore[no-untyped-def]
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "")
    try:
        if method == "GET" and path == "/api/v1/health":
            ping_mariadb()
            return _json(
                start_response,
                HTTPStatus.OK,
                {"status": "ok", "db": "up"},
            )

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

        if method == "POST" and path == "/api/v1/telegram/disconnected":
            payload = _read_json(environ)
            tenant_id = _require_str(payload, "tenant_id")
            user_id = _require_str(payload, "user_id")
            reason = payload.get("reason_message")
            if reason is not None and not isinstance(reason, str):
                raise ValueError("invalid 'reason_message': expected string")
            current = read_notification_settings(tenant_id, user_id)
            next_settings = mark_telegram_disconnected(
                tenant_id,
                user_id,
                current_settings=current,
                reason_message=reason or "Telegram channel disconnected. Reconnect is required.",
                now=datetime.now(UTC),
            )
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

        if method == "POST" and path == "/api/v1/security/sessions/create":
            payload = _read_json(environ)
            tenant_id = _require_str(payload, "tenant_id")
            user_id = _require_str(payload, "user_id")
            session_id = _require_str(payload, "session_id")
            create_session(tenant_id, user_id, session_id, now=datetime.now(UTC))
            return _json(start_response, HTTPStatus.OK, {"ok": True})

        if method == "POST" and path == "/api/v1/security/revoke-all-sessions":
            payload = _read_json(environ)
            tenant_id = _require_str(payload, "tenant_id")
            user_id = _require_str(payload, "user_id")
            revoked = revoke_all_sessions_for_password_change(
                tenant_id,
                user_id,
                now=datetime.now(UTC),
            )
            return _json(start_response, HTTPStatus.OK, {"revoked_sessions": revoked})

        if method == "GET" and path == "/api/v1/security/active-sessions":
            params = _parse_query(environ)
            tenant_id = _require_str(params, "tenant_id")
            user_id = _require_str(params, "user_id")
            count = get_active_sessions_count(tenant_id, user_id)
            return _json(start_response, HTTPStatus.OK, {"active_sessions": count})

        if method == "POST" and path == "/api/v1/account/soft-delete/start":
            payload = _read_json(environ)
            tenant_id = _require_str(payload, "tenant_id")
            user_id = _require_str(payload, "user_id")
            state = start_soft_delete(tenant_id, user_id, now=datetime.now(UTC))
            return _json(
                start_response,
                HTTPStatus.OK,
                {
                    "status": state.status.value,
                    "soft_deleted_at": state.soft_deleted_at,
                    "purge_at": state.purge_at,
                },
            )

        if method == "POST" and path == "/api/v1/account/soft-delete/restore":
            payload = _read_json(environ)
            tenant_id = _require_str(payload, "tenant_id")
            user_id = _require_str(payload, "user_id")
            state = restore_account(tenant_id, user_id, now=datetime.now(UTC))
            return _json(
                start_response,
                HTTPStatus.OK,
                {"status": state.status.value},
            )

        if method == "GET" and path == "/api/v1/account/access-state":
            params = _parse_query(environ)
            tenant_id = _require_str(params, "tenant_id")
            user_id = _require_str(params, "user_id")
            access = get_access_state(tenant_id, user_id, now=datetime.now(UTC))
            return _json(start_response, HTTPStatus.OK, access.to_dict())

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
    except AccountLifecycleError as exc:
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
