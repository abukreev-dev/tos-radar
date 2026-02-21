from __future__ import annotations

import argparse
import sys

from tos_radar.cabinet_api import run_api_server
from tos_radar.logging_utils import setup_logging
from tos_radar.runner import open_last_report, run_init, run_rerun_failed, run_scan
from tos_radar.settings import load_settings


def main() -> int:
    parser = argparse.ArgumentParser(prog="tos-radar")
    parser.add_argument(
        "command", choices=["init", "run", "rerun-failed", "report-open", "api-run"]
    )
    args = parser.parse_args()

    settings = load_settings()
    setup_logging(settings.log_level, settings.tenant_id)

    if args.command == "init":
        return run_init(settings)
    if args.command == "run":
        return run_scan(settings)
    if args.command == "rerun-failed":
        return run_rerun_failed(settings)
    if args.command == "api-run":
        run_api_server(settings.api_host, settings.api_port)
        return 0
    return open_last_report(settings)


if __name__ == "__main__":
    sys.exit(main())
