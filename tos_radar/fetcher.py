from __future__ import annotations

import asyncio
import logging
from io import BytesIO
from typing import Sequence
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener

from tos_radar.models import FetchResult, Proxy, Service, SourceType

LOGGER = logging.getLogger(__name__)


async def fetch_with_retries(
    service: Service,
    timeout_sec: int,
    retry_proxy_count: int,
    proxies: Sequence[Proxy],
) -> FetchResult:
    attempts = build_attempts(proxies, retry_proxy_count)
    last_error = "unknown error"

    for idx, proxy in enumerate(attempts, start=1):
        try:
            if service.url.lower().endswith(".pdf"):
                text = await _fetch_pdf_text(service.url, timeout_sec, proxy)
                return FetchResult(
                    ok=True,
                    text=text,
                    source_type=SourceType.PDF,
                    attempt=idx,
                    proxy_used=proxy.to_proxy_url() if proxy else None,
                )

            html_text, maybe_pdf = await _fetch_html_text(service.url, timeout_sec, proxy)
            if maybe_pdf:
                text = await _fetch_pdf_text(service.url, timeout_sec, proxy)
                return FetchResult(
                    ok=True,
                    text=text,
                    source_type=SourceType.PDF,
                    attempt=idx,
                    proxy_used=proxy.to_proxy_url() if proxy else None,
                )

            return FetchResult(
                ok=True,
                text=html_text,
                source_type=SourceType.HTML,
                attempt=idx,
                proxy_used=proxy.to_proxy_url() if proxy else None,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            LOGGER.warning(
                "Fetch failed domain=%s attempt=%s proxy=%s error=%s",
                service.domain,
                idx,
                proxy.to_proxy_url() if proxy else "none",
                exc,
            )

    return FetchResult(
        ok=False,
        text="",
        source_type=SourceType.HTML,
        attempt=len(attempts),
        proxy_used=None,
        error=last_error,
    )


def build_attempts(proxies: Sequence[Proxy], retry_proxy_count: int) -> list[Proxy | None]:
    attempts: list[Proxy | None] = [None]
    attempts.extend(list(proxies)[:retry_proxy_count])
    return attempts


async def _fetch_html_text(url: str, timeout_sec: int, proxy: Proxy | None) -> tuple[str, bool]:
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except Exception as exc:  # noqa: BLE001
        msg = "Playwright is not installed. Run: python -m playwright install chromium"
        raise RuntimeError(msg) from exc

    launch_kwargs: dict[str, object] = {"headless": True}
    if proxy is not None:
        launch_kwargs["proxy"] = proxy.to_playwright_proxy()

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        try:
            page = await browser.new_page()
            response = await page.goto(url, timeout=timeout_sec * 1000, wait_until="domcontentloaded")
            if response is None:
                raise RuntimeError("No response from target page")

            content_type = response.headers.get("content-type", "").lower()
            if "application/pdf" in content_type:
                return "", True

            await page.wait_for_timeout(1200)
            text = await page.evaluate(
                """() => {
                  const body = document.body;
                  if (!body) return '';
                  const clone = body.cloneNode(true);
                  clone.querySelectorAll(
                    'script,style,noscript,svg,nav,footer,header,aside,form,' +
                    'button,input,select,textarea,a'
                  ).forEach((node) => node.remove());
                  return clone.innerText || '';
                }"""
            )
            if not text or not text.strip():
                text = await page.evaluate("() => document.body ? document.body.innerText : ''")
            return text, False
        except PlaywrightTimeoutError as exc:
            raise TimeoutError(f"Page timeout after {timeout_sec}s") from exc
        finally:
            await browser.close()


async def _fetch_pdf_text(url: str, timeout_sec: int, proxy: Proxy | None) -> str:
    data = await asyncio.to_thread(_download_pdf, url, timeout_sec, proxy)
    return await asyncio.to_thread(_extract_text_from_pdf, data)


def _download_pdf(url: str, timeout_sec: int, proxy: Proxy | None) -> bytes:
    handlers = []
    if proxy is not None:
        proxy_url = proxy.to_proxy_url()
        handlers.append(ProxyHandler({"http": proxy_url, "https": proxy_url}))

    opener = build_opener(*handlers)
    req = Request(
        url,
        headers={"User-Agent": "tos-radar/0.1 (+https://example.local)"},
    )
    try:
        with opener.open(req, timeout=timeout_sec) as response:  # type: ignore[arg-type]
            return response.read()
    except URLError as exc:
        raise RuntimeError(f"PDF download failed: {exc}") from exc


def _extract_text_from_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data))
    chunks: list[str] = []
    for page in reader.pages:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks)
