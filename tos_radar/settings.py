from __future__ import annotations

import os

from dotenv import load_dotenv

from tos_radar.models import AppSettings


def load_settings() -> AppSettings:
    load_dotenv()
    return AppSettings(
        tenant_id=os.getenv("TENANT_ID", "default"),
        tos_urls_file=os.getenv("TOS_URLS_FILE", "config/tos_urls.txt"),
        proxies_file=os.getenv("PROXIES_FILE", "config/proxies.txt"),
        concurrency=int(os.getenv("CONCURRENCY", "20")),
        timeout_sec=int(os.getenv("TIMEOUT_SEC", "60")),
        retry_proxy_count=int(os.getenv("RETRY_PROXY_COUNT", "3")),
        retry_backoff_base_sec=float(os.getenv("RETRY_BACKOFF_BASE_SEC", "0.8")),
        retry_backoff_max_sec=float(os.getenv("RETRY_BACKOFF_MAX_SEC", "8.0")),
        retry_jitter_sec=float(os.getenv("RETRY_JITTER_SEC", "0.4")),
        min_text_length=int(os.getenv("MIN_TEXT_LENGTH", "350")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        api_host=os.getenv("API_HOST", "127.0.0.1"),
        api_port=int(os.getenv("API_PORT", "8080")),
        mariadb_host=os.getenv("MARIADB_HOST", "127.0.0.1"),
        mariadb_port=int(os.getenv("MARIADB_PORT", "3306")),
        mariadb_database=os.getenv("MARIADB_DATABASE", "tos_radar"),
        mariadb_user=os.getenv("MARIADB_USER", "tos_radar"),
        mariadb_password=os.getenv("MARIADB_PASSWORD", ""),
    )
