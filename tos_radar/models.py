from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    NEW = "NEW"
    CHANGED = "CHANGED"
    UNCHANGED = "UNCHANGED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Service:
    domain: str
    url: str


@dataclass(frozen=True)
class Proxy:
    host: str
    port: int
    login: str | None = None
    password: str | None = None

    def to_playwright_proxy(self) -> dict[str, str]:
        server = f"http://{self.host}:{self.port}"
        if self.login and self.password:
            return {"server": server, "username": self.login, "password": self.password}
        return {"server": server}

    def to_proxy_url(self) -> str:
        if self.login and self.password:
            return f"http://{self.login}:{self.password}@{self.host}:{self.port}"
        return f"http://{self.host}:{self.port}"


@dataclass(frozen=True)
class AppSettings:
    tos_urls_file: str
    proxies_file: str
    concurrency: int
    timeout_sec: int
    retry_proxy_count: int
    log_level: str
