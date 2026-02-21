from __future__ import annotations

import logging

from tos_radar.models import AppSettings


def run_init(settings: AppSettings) -> int:
    logging.getLogger(__name__).info("Init mode is not implemented yet.")
    _ = settings
    return 0


def run_scan(settings: AppSettings) -> int:
    logging.getLogger(__name__).info("Run mode is not implemented yet.")
    _ = settings
    return 0


def open_last_report() -> int:
    logging.getLogger(__name__).info("report-open is not implemented yet.")
    return 0
