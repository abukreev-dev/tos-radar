from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from tos_radar.models import Proxy, Service


def _read_non_empty_lines(path: str) -> list[str]:
    p = Path(path)
    if not p.exists():
        return []
    lines = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def load_services(path: str) -> list[Service]:
    lines = _read_non_empty_lines(path)
    services: list[Service] = []
    seen_domains: set[str] = set()

    for line in lines:
        parsed = urlparse(line)
        domain = parsed.netloc.lower()
        if not parsed.scheme or not domain:
            msg = f"Invalid URL in {path}: {line}"
            raise ValueError(msg)
        if domain in seen_domains:
            msg = f"Duplicate domain in {path}: {domain}"
            raise ValueError(msg)
        seen_domains.add(domain)
        services.append(Service(domain=domain, url=line))

    return services


def load_proxies(path: str) -> list[Proxy]:
    lines = _read_non_empty_lines(path)
    proxies: list[Proxy] = []
    for line in lines:
        parts = line.split(":")
        if len(parts) == 2:
            host, port = parts
            proxies.append(Proxy(host=host, port=int(port)))
            continue
        if len(parts) == 4:
            host, port, login, password = parts
            proxies.append(Proxy(host=host, port=int(port), login=login, password=password))
            continue
        msg = f"Invalid proxy entry in {path}: {line}"
        raise ValueError(msg)
    return proxies
