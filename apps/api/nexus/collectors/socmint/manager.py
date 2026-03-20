"""SOCMINT collection manager — orchestrates all SOCMINT collectors."""

import asyncio
from typing import Any

import structlog

from nexus.collectors.base import CollectionQuery, CollectionResult
from nexus.collectors.socmint.twitter_collector import TwitterCollector
from nexus.collectors.socmint.telegram_collector import TelegramCollector
from nexus.collectors.socmint.reddit_collector import RedditCollector
from nexus.collectors.socmint.cross_platform_resolver import CrossPlatformResolver

logger = structlog.get_logger()


class SocmintManager:
    """Orchestrates SOCMINT data collection across all sub-collectors."""

    def __init__(self) -> None:
        self.twitter = TwitterCollector()
        self.telegram = TelegramCollector()
        self.reddit = RedditCollector()
        self.cross_platform = CrossPlatformResolver()

    async def collect(
        self, query: str, scan_type: str, options: dict[str, Any] | None = None
    ) -> list[CollectionResult]:
        """Run appropriate collectors based on scan type."""
        cq = CollectionQuery(query=query, scan_type=scan_type, options=options or {})
        results: list[CollectionResult] = []

        if scan_type == "full":
            tasks = [
                self.twitter.collect(CollectionQuery(query=query, scan_type="keyword_search")),
                self.reddit.collect(
                    CollectionQuery(
                        query=query,
                        scan_type="subreddit_search",
                        options={"subreddit": "all"},
                    )
                ),
                self.cross_platform.collect(
                    CollectionQuery(query=query, scan_type="username_search")
                ),
            ]
            gathered = await asyncio.gather(*tasks, return_exceptions=True)
            for result in gathered:
                if isinstance(result, list):
                    results.extend(result)
                elif isinstance(result, Exception):
                    logger.error("socmint.collector_failed", error=str(result))

        elif scan_type in ("keyword_search", "user_timeline", "user_info", "followers"):
            results.extend(await self.twitter.collect(cq))

        elif scan_type in ("channel_messages", "channel_info"):
            results.extend(await self.telegram.collect(cq))

        elif scan_type in ("subreddit_search", "user_history"):
            results.extend(await self.reddit.collect(cq))

        elif scan_type == "username_search":
            results.extend(await self.cross_platform.collect(cq))

        else:
            # Default: try Twitter keyword search
            results.extend(
                await self.twitter.collect(
                    CollectionQuery(query=query, scan_type="keyword_search")
                )
            )

        logger.info(
            "socmint.collection_complete",
            query=query,
            scan_type=scan_type,
            total_results=len(results),
        )
        return results

    async def health_check(self) -> dict[str, bool]:
        """Check health of all SOCMINT collectors."""
        checks = await asyncio.gather(
            self.twitter.health_check(),
            self.telegram.health_check(),
            self.reddit.health_check(),
            self.cross_platform.health_check(),
            return_exceptions=True,
        )

        return {
            "twitter": checks[0] if isinstance(checks[0], bool) else False,
            "telegram": checks[1] if isinstance(checks[1], bool) else False,
            "reddit": checks[2] if isinstance(checks[2], bool) else False,
            "cross_platform": checks[3] if isinstance(checks[3], bool) else False,
        }

    async def close(self) -> None:
        """Close all collector sessions."""
        await asyncio.gather(
            self.twitter.close(),
            self.telegram.close(),
            self.reddit.close(),
            self.cross_platform.close(),
        )
