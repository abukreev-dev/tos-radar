from __future__ import annotations

import asyncio
import logging
import os
import platform
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

from tos_radar.config import load_proxies, load_services
from tos_radar.change_classifier import classify_change
from tos_radar.diff_utils import build_diff_html, is_changed
from tos_radar.fetcher import fetch_with_retries
from tos_radar.models import AppSettings
from tos_radar.models import ErrorCode, RunEntry, Service, SourceType, Status
from tos_radar.normalize import normalize_for_storage
from tos_radar.report import find_latest_report, write_report
from tos_radar.state_store import read_current, write_current_and_rotate

LOGGER = logging.getLogger(__name__)
LAST_FAILED_URLS_PATH = Path("data/last_failed_urls.txt")


def run_init(settings: AppSettings) -> int:
    return asyncio.run(_run(mode="init", settings=settings))


def run_scan(settings: AppSettings) -> int:
    return asyncio.run(_run(mode="run", settings=settings))


def run_rerun_failed(settings: AppSettings) -> int:
    failed_urls = _read_last_failed_urls()
    if not failed_urls:
        LOGGER.info("No failed URLs from previous run.")
        return 0
    services = _services_from_urls(failed_urls)
    LOGGER.info("Rerun-failed mode services=%s", len(services))
    return asyncio.run(_run(mode="run", settings=settings, services_override=services))


def open_last_report() -> int:
    latest = find_latest_report()
    if latest is None:
        LOGGER.error("No reports found.")
        return 1

    LOGGER.info("Latest report: %s", latest)
    if os.name == "nt":
        os.startfile(str(latest))  # type: ignore[attr-defined]
        return 0

    opener = "open" if sys_platform() == "darwin" else "xdg-open"
    try:
        subprocess.run([opener, str(latest)], check=False)
    except FileNotFoundError:
        LOGGER.warning("Open command not found. Report path: %s", latest)
    return 0


async def _run(mode: str, settings: AppSettings, services_override: list[Service] | None = None) -> int:
    services = services_override if services_override is not None else load_services(settings.tos_urls_file)
    proxies = load_proxies(settings.proxies_file)
    if not services:
        LOGGER.error("No URLs found in %s", settings.tos_urls_file)
        return 1

    LOGGER.info(
        "Starting mode=%s services=%s concurrency=%s timeout=%ss proxy_retries=%s",
        mode,
        len(services),
        settings.concurrency,
        settings.timeout_sec,
        settings.retry_proxy_count,
    )

    semaphore = asyncio.Semaphore(settings.concurrency)
    entries: list[RunEntry] = []

    async def process(service_idx: int) -> RunEntry:
        service = services[service_idx]
        async with semaphore:
            started = time.perf_counter()
            try:
                service_hard_timeout = ((settings.retry_proxy_count + 1) * (settings.timeout_sec + 20)) + 15
                try:
                    result = await asyncio.wait_for(
                        fetch_with_retries(
                            service=service,
                            timeout_sec=settings.timeout_sec,
                            retry_proxy_count=settings.retry_proxy_count,
                            retry_backoff_base_sec=settings.retry_backoff_base_sec,
                            retry_backoff_max_sec=settings.retry_backoff_max_sec,
                            retry_jitter_sec=settings.retry_jitter_sec,
                            proxies=proxies,
                        ),
                        timeout=service_hard_timeout,
                    )
                except TimeoutError:
                    elapsed = time.perf_counter() - started
                    err = f"Service hard-timeout after {service_hard_timeout}s"
                    LOGGER.error("FAILED domain=%s error=%s", service.domain, err)
                    return RunEntry(
                        domain=service.domain,
                        url=service.url,
                        status=Status.FAILED,
                        source_type=None,
                        duration_sec=elapsed,
                        text_length=None,
                        change_level=None,
                        change_ratio=None,
                        error_code=ErrorCode.TIMEOUT,
                        error=err,
                        diff_html=None,
                    )
                elapsed = time.perf_counter() - started
                if not result.ok:
                    LOGGER.error("FAILED domain=%s error=%s", service.domain, result.error)
                    return RunEntry(
                        domain=service.domain,
                        url=service.url,
                        status=Status.FAILED,
                        source_type=None,
                        duration_sec=elapsed,
                        text_length=None,
                        change_level=None,
                        change_ratio=None,
                        error_code=result.error_code,
                        error=result.error,
                        diff_html=None,
                    )

                text = normalize_for_storage(result.text)
                quality_issue = _quality_gate_error(text, result.source_type, settings.min_text_length)
                if quality_issue is not None:
                    code, message = quality_issue
                    LOGGER.error("FAILED domain=%s error=%s", service.domain, message)
                    return RunEntry(
                        domain=service.domain,
                        url=service.url,
                        status=Status.FAILED,
                        source_type=result.source_type,
                        duration_sec=elapsed,
                        text_length=len(text),
                        change_level=None,
                        change_ratio=None,
                        error_code=code,
                        error=message,
                        diff_html=None,
                    )

                if mode == "init":
                    write_current_and_rotate(service.domain, text)
                    LOGGER.info("NEW domain=%s source=%s", service.domain, result.source_type.value)
                    return RunEntry(
                        domain=service.domain,
                        url=service.url,
                        status=Status.NEW,
                        source_type=result.source_type,
                        duration_sec=elapsed,
                        text_length=len(text),
                        change_level=None,
                        change_ratio=None,
                        error_code=None,
                        error=None,
                        diff_html=None,
                    )

                prev = read_current(service.domain)
                if prev is None:
                    write_current_and_rotate(service.domain, text)
                    LOGGER.info("NEW domain=%s source=%s", service.domain, result.source_type.value)
                    return RunEntry(
                        domain=service.domain,
                        url=service.url,
                        status=Status.NEW,
                        source_type=result.source_type,
                        duration_sec=elapsed,
                        text_length=len(text),
                        change_level=None,
                        change_ratio=None,
                        error_code=None,
                        error=None,
                        diff_html=None,
                    )

                if is_changed(prev, text):
                    change_level, change_ratio = classify_change(prev, text)
                    diff_html = build_diff_html(prev, text)
                    write_current_and_rotate(service.domain, text)
                    LOGGER.info(
                        "CHANGED domain=%s source=%s change_level=%s change_ratio=%.4f",
                        service.domain,
                        result.source_type.value,
                        change_level.value,
                        change_ratio,
                    )
                    return RunEntry(
                        domain=service.domain,
                        url=service.url,
                        status=Status.CHANGED,
                        source_type=result.source_type,
                        duration_sec=elapsed,
                        text_length=len(text),
                        change_level=change_level,
                        change_ratio=change_ratio,
                        error_code=None,
                        error=None,
                        diff_html=diff_html,
                    )

                LOGGER.info("UNCHANGED domain=%s source=%s", service.domain, result.source_type.value)
                return RunEntry(
                    domain=service.domain,
                    url=service.url,
                    status=Status.UNCHANGED,
                    source_type=result.source_type,
                    duration_sec=elapsed,
                    text_length=len(text),
                    change_level=None,
                    change_ratio=None,
                    error_code=None,
                    error=None,
                    diff_html=None,
                )
            except Exception as exc:  # noqa: BLE001
                elapsed = time.perf_counter() - started
                LOGGER.exception("FAILED domain=%s due to unhandled error", service.domain)
                return RunEntry(
                    domain=service.domain,
                    url=service.url,
                    status=Status.FAILED,
                    source_type=None,
                    duration_sec=elapsed,
                    text_length=None,
                    change_level=None,
                    change_ratio=None,
                    error_code=ErrorCode.UNKNOWN,
                    error=f"Unhandled runner error: {exc}",
                    diff_html=None,
                )

    tasks = [asyncio.create_task(process(i)) for i in range(len(services))]
    try:
        for task in asyncio.as_completed(tasks):
            entries.append(await task)
    except KeyboardInterrupt:
        LOGGER.warning("Interrupted by user. Cancelling pending tasks...")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    except asyncio.CancelledError:
        LOGGER.warning("Run cancelled. Cancelling pending tasks...")
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise

    if mode == "run":
        domain_to_index = {service.domain: idx for idx, service in enumerate(services)}
        failed_domains = sorted({entry.domain for entry in entries if entry.status == Status.FAILED})
        if failed_domains:
            LOGGER.info("Retrying failed domains once: %s", len(failed_domains))
            retry_tasks = [asyncio.create_task(process(domain_to_index[domain])) for domain in failed_domains]
            retry_entries: list[RunEntry] = []
            for task in asyncio.as_completed(retry_tasks):
                retry_entries.append(await task)
            merged_entries = {entry.domain: entry for entry in entries}
            for retried in retry_entries:
                merged_entries[retried.domain] = retried
            entries = list(merged_entries.values())

    entries.sort(key=lambda e: e.domain)
    _write_last_failed_urls(entries)
    report_path = write_report(entries, mode)
    LOGGER.info("Report generated: %s", report_path)
    return 0


def sys_platform() -> str:
    return platform.system().lower()


def _quality_gate_error(
    text: str,
    source_type: SourceType,
    min_text_length: int,
) -> tuple[ErrorCode, str] | None:
    length = len(text)
    if source_type == SourceType.HTML and length < min_text_length:
        return (
            ErrorCode.SHORT_CONTENT,
            f"Document is too short ({length} chars), min required is {min_text_length}",
        )

    lowered = text.lower()
    technical_markers = (
        "if you are not a bot",
        "forbidden",
        "access denied",
        "service unavailable",
        "temporarily unavailable",
        "technical maintenance",
        "проверка безопасности",
        "доступ запрещен",
        "технические работы",
        "сервис временно недоступен",
    )
    if any(marker in lowered for marker in technical_markers):
        return (ErrorCode.TECHNICAL_PAGE, "Technical/blocked page detected")

    return None


def _write_last_failed_urls(entries: list[RunEntry]) -> None:
    failed_urls = sorted({entry.url for entry in entries if entry.status == Status.FAILED})
    LAST_FAILED_URLS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_FAILED_URLS_PATH.write_text("\n".join(failed_urls), encoding="utf-8")


def _read_last_failed_urls() -> list[str]:
    if not LAST_FAILED_URLS_PATH.exists():
        return []
    lines = []
    for raw in LAST_FAILED_URLS_PATH.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line:
            lines.append(line)
    return lines


def _services_from_urls(urls: list[str]) -> list[Service]:
    services: list[Service] = []
    seen: set[str] = set()
    for url in urls:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if not parsed.scheme or not domain:
            continue
        if domain in seen:
            continue
        seen.add(domain)
        services.append(Service(domain=domain, url=url))
    return services
