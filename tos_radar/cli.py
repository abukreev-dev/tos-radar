from __future__ import annotations

import argparse
import sys

from tos_radar.logging_utils import setup_logging
from tos_radar.runner import open_last_report, run_init, run_scan
from tos_radar.settings import load_settings


def main() -> int:
    parser = argparse.ArgumentParser(prog="tos-radar")
    parser.add_argument("command", choices=["init", "run", "report-open"])
    args = parser.parse_args()

    settings = load_settings()
    setup_logging(settings.log_level)

    if args.command == "init":
        return run_init(settings)
    if args.command == "run":
        return run_scan(settings)
    return open_last_report()


if __name__ == "__main__":
    sys.exit(main())
