from __future__ import annotations

from pathlib import Path


def _service_dir(domain: str) -> Path:
    return Path("data") / "state" / domain


def read_current(domain: str) -> str | None:
    path = _service_dir(domain) / "current.txt"
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def write_current_and_rotate(domain: str, text: str) -> None:
    service_dir = _service_dir(domain)
    service_dir.mkdir(parents=True, exist_ok=True)

    current = service_dir / "current.txt"
    previous = service_dir / "previous.txt"
    if current.exists():
        previous.write_text(current.read_text(encoding="utf-8"), encoding="utf-8")

    current.write_text(text, encoding="utf-8")
