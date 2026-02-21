from __future__ import annotations

import os

from dotenv import load_dotenv

from tos_radar.models import AppSettings


def load_settings() -> AppSettings:
    load_dotenv()
    return AppSettings(
        tos_urls_file=os.getenv("TOS_URLS_FILE", "config/tos_urls.txt"),
        proxies_file=os.getenv("PROXIES_FILE", "config/proxies.txt"),
        concurrency=int(os.getenv("CONCURRENCY", "20")),
        timeout_sec=int(os.getenv("TIMEOUT_SEC", "60")),
        retry_proxy_count=int(os.getenv("RETRY_PROXY_COUNT", "3")),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
