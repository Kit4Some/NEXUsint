"""Base collector interface for all INT collection modules."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

import aiohttp
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger()


class CollectionQuery(BaseModel):
    query: str
    scan_type: str
    options: dict[str, Any] = Field(default_factory=dict)


class CollectionResult(BaseModel):
    source_int: str
    source_id: str
    raw_data: dict[str, Any]
    normalized: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)
    collected_at: datetime = Field(default_factory=datetime.utcnow)
    reliability_grade: str = "F"


class BaseCollector(ABC):
    """Abstract base for all data collectors."""

    def __init__(self, rate_limit: float = 1.0, max_retries: int = 3) -> None:
        self._rate_limit = rate_limit  # requests per second
        self._max_retries = max_retries
        self._last_request_time = 0.0
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={"User-Agent": "NEXUS-OSINT/0.1"},
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _rate_limit_wait(self) -> None:
        """Enforce rate limiting between requests."""
        now = asyncio.get_event_loop().time()
        elapsed = now - self._last_request_time
        min_interval = 1.0 / self._rate_limit
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an HTTP request with exponential backoff retry."""
        session = await self._get_session()

        for attempt in range(self._max_retries):
            await self._rate_limit_wait()
            try:
                async with session.request(method, url, **kwargs) as resp:
                    if resp.status == 429:
                        retry_after = int(resp.headers.get("Retry-After", 2 ** (attempt + 1)))
                        logger.warning(
                            "collector.rate_limited",
                            url=url,
                            retry_after=retry_after,
                        )
                        await asyncio.sleep(retry_after)
                        continue
                    resp.raise_for_status()
                    return await resp.json()
            except aiohttp.ClientError as e:
                wait_time = 2 ** (attempt + 1)
                logger.warning(
                    "collector.request_failed",
                    url=url,
                    attempt=attempt + 1,
                    error=str(e),
                    retry_in=wait_time,
                )
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(wait_time)
                else:
                    raise

        raise RuntimeError(f"Max retries exceeded for {url}")

    @abstractmethod
    async def collect(self, query: CollectionQuery) -> list[CollectionResult]:
        """Execute a collection operation and return normalized results."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the collector's data source is reachable."""
        ...
