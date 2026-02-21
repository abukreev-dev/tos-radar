from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Status(str, Enum):
    NEW = "NEW"
    CHANGED = "CHANGED"
    UNCHANGED = "UNCHANGED"
    FAILED = "FAILED"


class ChangeLevel(str, Enum):
    NOISE = "NOISE"
    MINOR = "MINOR"
    MAJOR = "MAJOR"


@dataclass(frozen=True)
class Service:
    domain: str
    url: str


class SourceType(str, Enum):
    HTML = "HTML"
    PDF = "PDF"


class ErrorCode(str, Enum):
    BOT_DETECTED = "BOT_DETECTED"
    TECHNICAL_PAGE = "TECHNICAL_PAGE"
    SHORT_CONTENT = "SHORT_CONTENT"
    TIMEOUT = "TIMEOUT"
    NETWORK = "NETWORK"
    PROXY = "PROXY"
    BROWSER = "BROWSER"
    PDF_DOWNLOAD = "PDF_DOWNLOAD"
    PDF_PARSE = "PDF_PARSE"
    EMPTY_CONTENT = "EMPTY_CONTENT"
    PARSER = "PARSER"
    UNKNOWN = "UNKNOWN"


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
    retry_backoff_base_sec: float
    retry_backoff_max_sec: float
    retry_jitter_sec: float
    min_text_length: int
    log_level: str


@dataclass(frozen=True)
class FetchResult:
    ok: bool
    text: str
    source_type: SourceType
    attempt: int
    proxy_used: str | None = None
    error_code: ErrorCode | None = None
    error: str | None = None


@dataclass(frozen=True)
class RunEntry:
    domain: str
    url: str
    status: Status
    source_type: SourceType | None
    duration_sec: float
    text_length: int | None
    change_level: ChangeLevel | None
    change_ratio: float | None
    error_code: ErrorCode | None
    error: str | None
    diff_html: str | None
