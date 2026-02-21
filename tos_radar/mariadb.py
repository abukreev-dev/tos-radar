from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
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


def ping_mariadb() -> None:
    conn = connect_mariadb()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 AS ok")
    finally:
        conn.close()


def apply_mariadb_migrations() -> int:
    conn = connect_mariadb()
    applied = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version VARCHAR(128) NOT NULL PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            migration_dir = Path(__file__).resolve().parent.parent / "migrations"
            for path in sorted(migration_dir.glob("*.sql")):
                version = path.name
                cur.execute(
                    "SELECT version FROM schema_migrations WHERE version=%s",
                    (version,),
                )
                if cur.fetchone():
                    continue

                sql = path.read_text(encoding="utf-8")
                for statement in [s.strip() for s in sql.split(";") if s.strip()]:
                    cur.execute(statement)
                cur.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)",
                    (version,),
                )
                applied += 1
    finally:
        conn.close()
    return applied
