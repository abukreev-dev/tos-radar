from __future__ import annotations

import asyncio
import logging
import os
import platform
import subprocess
import time

from tos_radar.config import load_proxies, load_services
from tos_radar.diff_utils import build_diff_html, is_changed
from tos_radar.fetcher import fetch_with_retries
from tos_radar.models import AppSettings
from tos_radar.models import ErrorCode, RunEntry, Status
from tos_radar.normalize import normalize_for_storage
from tos_radar.report import find_latest_report, write_report
from tos_radar.state_store import read_current, write_current_and_rotate

LOGGER = logging.getLogger(__name__)


def run_init(settings: AppSettings) -> int:
    return asyncio.run(_run(mode="init", settings=settings))


def run_scan(settings: AppSettings) -> int:
    return asyncio.run(_run(mode="run", settings=settings))


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


async def _run(mode: str, settings: AppSettings) -> int:
    services = load_services(settings.tos_urls_file)
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
                    error_code=result.error_code,
                    error=result.error,
                    diff_html=None,
                )

                text = normalize_for_storage(result.text)
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
                        error_code=None,
                        error=None,
                        diff_html=None,
                    )

                if is_changed(prev, text):
                    diff_html = build_diff_html(prev, text)
                    write_current_and_rotate(service.domain, text)
                    LOGGER.info("CHANGED domain=%s source=%s", service.domain, result.source_type.value)
                    return RunEntry(
                        domain=service.domain,
                        url=service.url,
                        status=Status.CHANGED,
                        source_type=result.source_type,
                        duration_sec=elapsed,
                        text_length=len(text),
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

    entries.sort(key=lambda e: e.domain)
    report_path = write_report(entries, mode)
    LOGGER.info("Report generated: %s", report_path)
    return 0


def sys_platform() -> str:
    return platform.system().lower()
