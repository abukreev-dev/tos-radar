from __future__ import annotations

import asyncio
import logging
import math
import random
import re
from io import BytesIO
from typing import TYPE_CHECKING, Sequence
from urllib.error import URLError
from urllib.request import ProxyHandler, Request, build_opener

from tos_radar.models import ErrorCode, FetchResult, Proxy, Service, SourceType

if TYPE_CHECKING:
    from playwright.async_api import Page

LOGGER = logging.getLogger(__name__)
REALISTIC_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36"
)


class FetchError(RuntimeError):
    def __init__(self, code: ErrorCode, message: str):
        super().__init__(message)
        self.code = code


async def fetch_with_retries(
    service: Service,
    timeout_sec: int,
    retry_proxy_count: int,
    retry_backoff_base_sec: float,
    retry_backoff_max_sec: float,
    retry_jitter_sec: float,
    proxies: Sequence[Proxy],
) -> FetchResult:
    attempts = build_attempts(proxies, retry_proxy_count)
    total_attempts = len(attempts)
    last_error = "unknown error"
    last_error_code = ErrorCode.UNKNOWN

    for idx, proxy in enumerate(attempts, start=1):
        try:
            result = await asyncio.wait_for(
                _fetch_single_attempt(service=service, timeout_sec=timeout_sec, proxy=proxy, attempt=idx),
                timeout=timeout_sec + 20,
            )
            return result
        except TimeoutError:
            last_error = f"Attempt timed out after hard limit ({timeout_sec + 20}s)"
            last_error_code = ErrorCode.TIMEOUT
            LOGGER.warning(
                "Fetch failed domain=%s attempt=%s/%s proxy=%s code=%s error=%s",
                service.domain,
                idx,
                total_attempts,
                proxy.to_proxy_url() if proxy else "none",
                ErrorCode.TIMEOUT.value,
                last_error,
            )
        except FetchError as exc:
            last_error = str(exc)
            last_error_code = exc.code
            LOGGER.warning(
                "Fetch failed domain=%s attempt=%s/%s proxy=%s code=%s error=%s",
                service.domain,
                idx,
                total_attempts,
                proxy.to_proxy_url() if proxy else "none",
                exc.code.value,
                exc,
            )
        except Exception as exc:  # noqa: BLE001
            code = classify_untyped_error(exc)
            last_error = str(exc)
            last_error_code = code
            LOGGER.warning(
                "Fetch failed domain=%s attempt=%s/%s proxy=%s code=%s error=%s",
                service.domain,
                idx,
                total_attempts,
                proxy.to_proxy_url() if proxy else "none",
                code.value,
                exc,
            )

        if idx < total_attempts:
            delay = compute_retry_delay(
                attempt_index=idx,
                base_sec=retry_backoff_base_sec,
                max_sec=retry_backoff_max_sec,
                jitter_sec=retry_jitter_sec,
            )
            await asyncio.sleep(delay)

    return FetchResult(
        ok=False,
        text="",
        source_type=SourceType.HTML,
        attempt=len(attempts),
        proxy_used=None,
        error_code=last_error_code,
        error=last_error,
    )


async def _fetch_single_attempt(service: Service, timeout_sec: int, proxy: Proxy | None, attempt: int) -> FetchResult:
    if service.url.lower().endswith(".pdf"):
        text = await _fetch_pdf_text(service.url, timeout_sec, proxy)
        cleaned_text = _clean_extracted_text(text)
        if not cleaned_text:
            raise FetchError(ErrorCode.EMPTY_CONTENT, "PDF contains no extractable text")
        return FetchResult(
            ok=True,
            text=cleaned_text,
            source_type=SourceType.PDF,
            attempt=attempt,
            proxy_used=proxy.to_proxy_url() if proxy else None,
        )

    html_text, maybe_pdf = await _fetch_html_text(service.url, timeout_sec, proxy)
    if maybe_pdf:
        text = await _fetch_pdf_text(service.url, timeout_sec, proxy)
        cleaned_text = _clean_extracted_text(text)
        if not cleaned_text:
            raise FetchError(ErrorCode.EMPTY_CONTENT, "PDF contains no extractable text")
        return FetchResult(
            ok=True,
            text=cleaned_text,
            source_type=SourceType.PDF,
            attempt=attempt,
            proxy_used=proxy.to_proxy_url() if proxy else None,
        )

    cleaned_text = _clean_extracted_text(html_text)
    if not cleaned_text:
        if _looks_like_binary_doc_url(service.url):
            pdf_text = await _fetch_pdf_text_with_browser(service.url, timeout_sec, proxy)
            if not pdf_text:
                pdf_text = await _fetch_pdf_text(service.url, timeout_sec, proxy)
            cleaned_pdf_text = _clean_extracted_text(pdf_text)
            if cleaned_pdf_text:
                return FetchResult(
                    ok=True,
                    text=cleaned_pdf_text,
                    source_type=SourceType.PDF,
                    attempt=attempt,
                    proxy_used=proxy.to_proxy_url() if proxy else None,
                )
        raise FetchError(ErrorCode.EMPTY_CONTENT, "Page contains no extractable text")

    return FetchResult(
        ok=True,
        text=cleaned_text,
        source_type=SourceType.HTML,
        attempt=attempt,
        proxy_used=proxy.to_proxy_url() if proxy else None,
    )


def build_attempts(proxies: Sequence[Proxy], retry_proxy_count: int) -> list[Proxy | None]:
    attempts: list[Proxy | None] = [None]
    attempts.extend(list(proxies)[:retry_proxy_count])
    return attempts


def compute_retry_delay(
    attempt_index: int,
    base_sec: float = 0.8,
    max_sec: float = 8.0,
    jitter_sec: float = 0.4,
) -> float:
    exp_delay = base_sec * math.pow(2.0, max(0, attempt_index - 1))
    capped = min(max_sec, exp_delay)
    jitter = random.uniform(0.0, max(0.0, jitter_sec))
    return capped + jitter


def classify_untyped_error(exc: Exception) -> ErrorCode:
    message = str(exc).lower()
    if any(
        token in message
        for token in (
            "captcha",
            "verify you are human",
            "are you human",
            "access denied",
            "bot",
            "unusual traffic",
        )
    ):
        return ErrorCode.BOT_DETECTED
    if "timeout" in message:
        return ErrorCode.TIMEOUT
    if "proxy" in message or "407" in message:
        return ErrorCode.PROXY
    if "net::" in message or "connection" in message or "dns" in message:
        return ErrorCode.NETWORK
    if "browser" in message or "chromium" in message:
        return ErrorCode.BROWSER
    return ErrorCode.UNKNOWN


async def _fetch_html_text(url: str, timeout_sec: int, proxy: Proxy | None) -> tuple[str, bool]:
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except Exception as exc:  # noqa: BLE001
        msg = "Playwright is not installed. Run: python -m playwright install chromium"
        raise FetchError(ErrorCode.BROWSER, msg) from exc

    launch_kwargs: dict[str, object] = {
        "headless": True,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-first-run",
        ],
    }
    if proxy is not None:
        launch_kwargs["proxy"] = proxy.to_playwright_proxy()

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(**launch_kwargs)
            try:
                context = await browser.new_context(
                    user_agent=REALISTIC_USER_AGENT,
                    locale="ru-RU",
                    timezone_id="Europe/Moscow",
                    viewport={"width": 1366, "height": 768},
                    java_script_enabled=True,
                    extra_http_headers={
                        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                        "Upgrade-Insecure-Requests": "1",
                        "DNT": "1",
                    },
                )
                await context.add_init_script(
                    """
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'platform', {get: () => 'MacIntel'});
                    Object.defineProperty(navigator, 'language', {get: () => 'ru-RU'});
                    Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU', 'ru', 'en-US', 'en']});
                    window.chrome = window.chrome || { runtime: {} };
                    """
                )
                page = await context.new_page()
                response = await page.goto(url, timeout=timeout_sec * 1000, wait_until="domcontentloaded")
                if response is None:
                    raise FetchError(ErrorCode.NETWORK, "No response from target page")

                content_type = response.headers.get("content-type", "").lower()
                if "application/pdf" in content_type:
                    return "", True

                await _simulate_human_interaction(page)
                if await _looks_like_bot_block(page):
                    raise FetchError(ErrorCode.BOT_DETECTED, "Anti-bot page detected")

                text = await page.evaluate(
                    """() => {
                      const selectorsToDrop = [
                        'script', 'style', 'noscript', 'svg', 'nav', 'footer', 'header', 'aside',
                        'form', 'button', 'input', 'select', 'textarea', 'a', 'iframe',
                        '[role="navigation"]', '[role="banner"]', '[role="contentinfo"]',
                        '.cookie', '#cookie', '.cookies', '.consent', '.banner', '.modal', '.popup',
                        '.newsletter', '.subscribe', '.social', '.breadcrumbs', '.breadcrumb'
                      ];
                      const body = document.body;
                      if (!body) return '';
                      const clone = body.cloneNode(true);
                      clone.querySelectorAll(selectorsToDrop.join(',')).forEach((node) => node.remove());

                      const candidates = Array.from(
                        clone.querySelectorAll(
                          'main, article, [role="main"], .content, .main-content, .terms, .tos, .legal'
                        )
                      );
                      const blocks = candidates.length > 0 ? candidates : [clone];

                      let bestText = '';
                      for (const block of blocks) {
                        const lines = (block.innerText || '')
                          .split('\\n')
                          .map((x) => x.trim())
                          .filter(Boolean);
                        const scored = lines.filter((line) => {
                          if (line.length < 25) return false;
                          const words = line.split(/\\s+/).filter(Boolean);
                          const urlTokens = words.filter((w) => /https?:\\/\\//i.test(w)).length;
                          const navLike = /(home|about|contact|pricing|blog|careers|help|support)/i.test(line);
                          return !(urlTokens > 0 && words.length <= 8) && !navLike;
                        });
                        const candidateText = scored.join('\\n');
                        if (candidateText.length > bestText.length) {
                          bestText = candidateText;
                        }
                      }
                      return bestText;
                    }"""
                )
                if not text or not text.strip():
                    text = await _extract_with_fallback(page, timeout_sec)
                await context.close()
                return text, False
            except PlaywrightTimeoutError as exc:
                raise FetchError(ErrorCode.TIMEOUT, f"Page timeout after {timeout_sec}s") from exc
            except FetchError:
                raise
            except Exception as exc:  # noqa: BLE001
                raise FetchError(classify_untyped_error(exc), str(exc)) from exc
            finally:
                await browser.close()
    except FetchError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise FetchError(classify_untyped_error(exc), str(exc)) from exc


async def _fetch_pdf_text(url: str, timeout_sec: int, proxy: Proxy | None) -> str:
    data = await asyncio.to_thread(_download_pdf, url, timeout_sec, proxy)
    return await asyncio.to_thread(_extract_text_from_pdf, data)


async def _fetch_pdf_text_with_browser(url: str, timeout_sec: int, proxy: Proxy | None) -> str:
    try:
        from playwright.async_api import async_playwright
    except Exception:
        return ""

    launch_kwargs: dict[str, object] = {
        "headless": True,
        "args": [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-first-run",
        ],
    }
    if proxy is not None:
        launch_kwargs["proxy"] = proxy.to_playwright_proxy()

    async with async_playwright() as p:
        browser = await p.chromium.launch(**launch_kwargs)
        try:
            context = await browser.new_context(
                user_agent=REALISTIC_USER_AGENT,
                locale="ru-RU",
                timezone_id="Europe/Moscow",
                extra_http_headers={
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                    "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
                },
            )
            response = await context.request.get(url, timeout=timeout_sec * 1000)
            body = await response.body()
            content_type = (response.headers.get("content-type") or "").lower()
            if "application/pdf" in content_type or body.startswith(b"%PDF"):
                return await asyncio.to_thread(_extract_text_from_pdf, body)

            if _looks_like_bot_block_text(_safe_decode(body)):
                raise FetchError(ErrorCode.BOT_DETECTED, "Anti-bot page detected for binary document URL")
            return ""
        finally:
            await browser.close()


def _download_pdf(url: str, timeout_sec: int, proxy: Proxy | None) -> bytes:
    handlers = []
    if proxy is not None:
        proxy_url = proxy.to_proxy_url()
        handlers.append(ProxyHandler({"http": proxy_url, "https": proxy_url}))

    opener = build_opener(*handlers)
    req = Request(
        url,
        headers={
            "User-Agent": REALISTIC_USER_AGENT,
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
        },
    )
    try:
        with opener.open(req, timeout=timeout_sec) as response:  # type: ignore[arg-type]
            return response.read()
    except URLError as exc:
        code = ErrorCode.PROXY if "407" in str(exc) or "proxy" in str(exc).lower() else ErrorCode.PDF_DOWNLOAD
        raise FetchError(code, f"PDF download failed: {exc}") from exc


def _extract_text_from_pdf(data: bytes) -> str:
    from pypdf import PdfReader

    try:
        reader = PdfReader(BytesIO(data))
        chunks: list[str] = []
        for page in reader.pages:
            chunks.append(page.extract_text() or "")
        return "\n".join(chunks)
    except Exception as exc:  # noqa: BLE001
        raise FetchError(ErrorCode.PDF_PARSE, f"PDF parsing failed: {exc}") from exc


def _clean_extracted_text(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    noise_tokens = (
        "cookie",
        "privacy center",
        "all rights reserved",
        "follow us",
        "subscribe",
        "newsletter",
        "accept all",
        "reject all",
        "мы сохраняем «куки»",
        "мы сохраняем \"куки\"",
        "help and feedback",
    )
    for raw in lines:
        line = re.sub(r"\s+", " ", raw).strip()
        if not line:
            continue
        lower = line.lower()
        if lower.startswith("©") or "лицензия банка россии" in lower:
            continue
        if "помощь и обратная связь" in lower and len(line) < 220:
            continue
        if any(token in lower for token in noise_tokens) and len(line) < 160:
            continue
        if any(token in lower for token in ("сохраняем «куки»", "сохраняем \"куки\"")):
            continue
        words = line.split()
        url_like = sum(1 for w in words if "http://" in w.lower() or "https://" in w.lower())
        if url_like > 0 and len(words) <= 8:
            continue
        if len(line) < 3:
            continue
        out.append(line)
    return "\n".join(out).strip()


def _looks_like_binary_doc_url(url: str) -> bool:
    lower = url.lower()
    return any(token in lower for token in ("/file/", "/attachment", ".pdf", "download"))


async def _simulate_human_interaction(page: "Page") -> None:
    # A short random delay + scroll often reduces naive automation checks.
    wait_ms = random.randint(1400, 2600)
    await page.wait_for_timeout(wait_ms)
    await page.mouse.move(random.randint(120, 500), random.randint(120, 420))
    await page.evaluate("window.scrollTo(0, Math.min(450, document.body.scrollHeight || 0));")
    await page.wait_for_timeout(random.randint(250, 700))


async def _extract_with_fallback(page: "Page", timeout_sec: int) -> str:
    # Some pages render legal text after delayed JS execution.
    baseline = await page.evaluate("() => document.body ? document.body.innerText : ''")
    if baseline and baseline.strip():
        return baseline

    extra_wait_ms = min(12000, max(2500, int(timeout_sec * 200)))
    await page.wait_for_timeout(extra_wait_ms)

    text = await page.evaluate("() => document.body ? document.body.innerText : ''")
    if text and text.strip():
        return text

    return await page.evaluate("() => document.documentElement ? document.documentElement.innerText : ''")


async def _looks_like_bot_block(page: "Page") -> bool:
    title = (await page.title()).lower()
    body_text = await page.evaluate("() => (document.body ? document.body.innerText : '')")
    sample = f"{title}\n{body_text[:2000]}".lower()
    return _looks_like_bot_block_text(sample)


def _looks_like_bot_block_text(sample: str) -> bool:
    markers = (
        "captcha",
        "cloudflare",
        "ddos-guard",
        "verify you are human",
        "if you are not a bot",
        "are you human",
        "security check",
        "access denied",
        "подтвердите, что вы не робот",
        "проверка безопасности",
        "необычный трафик",
    )
    return any(marker in sample for marker in markers)


def _safe_decode(data: bytes) -> str:
    try:
        return data.decode("utf-8", errors="ignore").lower()
    except Exception:
        return ""
