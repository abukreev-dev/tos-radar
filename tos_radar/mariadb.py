from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MariaDbSettings:
    host: str
    port: int
    database: str
    user: str
    password: str


def load_mariadb_settings() -> MariaDbSettings:
    return MariaDbSettings(
        host=os.getenv("MARIADB_HOST", "127.0.0.1"),
        port=int(os.getenv("MARIADB_PORT", "3306")),
        database=os.getenv("MARIADB_DATABASE", "tos_radar"),
        user=os.getenv("MARIADB_USER", "tos_radar"),
        password=os.getenv("MARIADB_PASSWORD", ""),
    )


def connect_mariadb() -> Any:
    settings = load_mariadb_settings()
    try:
        import pymysql
        from pymysql.cursors import DictCursor
    except ImportError as exc:
        raise RuntimeError(
            "pymysql is required for MariaDB storage. Install dependency: pymysql==1.1.1"
        ) from exc

    return pymysql.connect(
        host=settings.host,
        port=settings.port,
        user=settings.user,
        password=settings.password,
        database=settings.database,
        autocommit=True,
        charset="utf8mb4",
        cursorclass=DictCursor,
    )


def ensure_cabinet_schema() -> None:
    conn = connect_mariadb()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS cabinet_notification_settings (
                    tenant_id VARCHAR(64) NOT NULL,
                    user_id VARCHAR(128) NOT NULL,
                    email_digest_enabled TINYINT(1) NOT NULL,
                    telegram_digest_enabled TINYINT(1) NOT NULL,
                    email_marketing_enabled TINYINT(1) NOT NULL,
                    telegram_system_enabled TINYINT(1) NOT NULL,
                    email_status VARCHAR(32) NOT NULL,
                    telegram_status VARCHAR(32) NOT NULL,
                    email_error_code VARCHAR(128) NULL,
                    email_error_message TEXT NULL,
                    email_error_updated_at VARCHAR(64) NULL,
                    telegram_error_code VARCHAR(128) NULL,
                    telegram_error_message TEXT NULL,
                    telegram_error_updated_at VARCHAR(64) NULL,
                    PRIMARY KEY (tenant_id, user_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS cabinet_telegram_link_state (
                    tenant_id VARCHAR(64) NOT NULL,
                    user_id VARCHAR(128) NOT NULL,
                    pending_code VARCHAR(16) NULL,
                    code_expires_at VARCHAR(64) NULL,
                    chat_id VARCHAR(128) NULL,
                    linked_at VARCHAR(64) NULL,
                    PRIMARY KEY (tenant_id, user_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS cabinet_telegram_test_send_state (
                    tenant_id VARCHAR(64) NOT NULL,
                    user_id VARCHAR(128) NOT NULL,
                    last_sent_at VARCHAR(64) NULL,
                    day_key VARCHAR(16) NULL,
                    day_count INT NOT NULL DEFAULT 0,
                    PRIMARY KEY (tenant_id, user_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS cabinet_user_sessions (
                    tenant_id VARCHAR(64) NOT NULL,
                    user_id VARCHAR(128) NOT NULL,
                    session_id VARCHAR(128) NOT NULL,
                    issued_at VARCHAR(64) NOT NULL,
                    revoked_at VARCHAR(64) NULL,
                    is_active TINYINT(1) NOT NULL DEFAULT 1,
                    PRIMARY KEY (tenant_id, user_id, session_id)
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS cabinet_account_lifecycle (
                    tenant_id VARCHAR(64) NOT NULL,
                    user_id VARCHAR(128) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    soft_deleted_at VARCHAR(64) NULL,
                    purge_at VARCHAR(64) NULL,
                    PRIMARY KEY (tenant_id, user_id)
                )
                """
            )
    finally:
        conn.close()
