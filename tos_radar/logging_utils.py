from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path


def setup_logging(level: str, tenant_id: str) -> Path:
    logs_dir = Path("logs") / tenant_id
    logs_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_file = logs_dir / f"run-{ts}.log"

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level.upper())

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(formatter)
    root.addHandler(fh)

    sh = logging.StreamHandler()
    sh.setFormatter(formatter)
    root.addHandler(sh)

    return log_file
