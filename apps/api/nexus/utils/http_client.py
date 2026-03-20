"""Async HTTP client with retry and circuit-breaker logic.

Adapted from Shadowbroker ``network_utils.py`` — uses ``aiohttp`` instead of
``requests`` + curl fallback since NEXUS runs inside Docker where TLS
fingerprinting issues don't apply.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from urllib.parse import urlparse

import aiohttp
import structlog

logger = structlog.get_logger()

# ── Circuit breaker state ────────────────────────────────────────────────

_domain_fail_count: dict[str, int] = {}
_domain_fail_time: dict[str, float] = {}
_CB_THRESHOLD = 5       # consecutive failures before tripping
_CB_COOLDOWN = 60.0     # seconds before retrying a tripped domain

_USER_AGENT = "NEXUS-OSINT/0.2 (multi-int-fusion)"


def _check_circuit(domain: str) -> None:
    """Raise if the circuit breaker is open for *domain*."""
    fail_t = _domain_fail_time.get(domain, 0.0)
    if _domain_fail_count.get(domain, 0) >= _CB_THRESHOLD:
        if time.monotonic() - fail_t < _CB_COOLDOWN:
            raise RuntimeError(f"Circuit breaker open for {domain}")
        # Cooldown elapsed — reset
        _domain_fail_count.pop(domain, None)
        _domain_fail_time.pop(domain, None)


def _record_failure(domain: str) -> None:
    _domain_fail_count[domain] = _domain_fail_count.get(domain, 0) + 1
    _domain_fail_time[domain] = time.monotonic()


def _record_success(domain: str) -> None:
    _domain_fail_count.pop(domain, None)
    _domain_fail_time.pop(domain, None)


# ── Public API ───────────────────────────────────────────────────────────


async def fetch_json(
    url: str,
    *,
    method: str = "GET",
    timeout: int = 30,
    headers: dict[str, str] | None = None,
    json_data: Any = None,
    retries: int = 3,
    backoff: float = 1.0,
) -> Any:
    """Fetch JSON from *url* with automatic retries and circuit breaking.

    Returns the parsed JSON payload on success.  Raises on permanent failure.
    """
    domain = urlparse(url).netloc
    _check_circuit(domain)

    merged_headers = {"User-Agent": _USER_AGENT}
    if headers:
        merged_headers.update(headers)

    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                kwargs: dict[str, Any] = {
                    "timeout": aiohttp.ClientTimeout(total=timeout),
                    "headers": merged_headers,
                }
                if json_data is not None:
                    kwargs["json"] = json_data

                async with session.request(method, url, **kwargs) as resp:
                    resp.raise_for_status()
                    _record_success(domain)
                    return await resp.json(content_type=None)
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                wait = backoff * (2 ** (attempt - 1))
                logger.debug(
                    "http_client.retry",
                    url=url,
                    attempt=attempt,
                    wait=wait,
                    error=str(exc),
                )
                await asyncio.sleep(wait)

    _record_failure(domain)
    logger.warning("http_client.failed", url=url, error=str(last_exc))
    raise last_exc  # type: ignore[misc]


async def fetch_text(
    url: str,
    *,
    timeout: int = 30,
    headers: dict[str, str] | None = None,
) -> str:
    """Fetch raw text (e.g. CSV) from *url*."""
    domain = urlparse(url).netloc
    _check_circuit(domain)

    merged_headers = {"User-Agent": _USER_AGENT}
    if headers:
        merged_headers.update(headers)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                headers=merged_headers,
            ) as resp:
                resp.raise_for_status()
                _record_success(domain)
                return await resp.text()
    except Exception as exc:
        _record_failure(domain)
        logger.warning("http_client.text_failed", url=url, error=str(exc))
        raise
