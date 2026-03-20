"""Cross-platform username resolver (Sherlock-style enumeration)."""

import asyncio
from typing import Any

import structlog

from nexus.collectors.base import BaseCollector, CollectionQuery, CollectionResult

logger = structlog.get_logger()

# Platform check definitions: URL template + expected status for existing account
PLATFORM_CHECKS: list[dict[str, Any]] = [
    {"name": "GitHub", "url": "https://github.com/{}", "status": 200, "category": "development"},
    {"name": "GitLab", "url": "https://gitlab.com/{}", "status": 200, "category": "development"},
    {"name": "Twitter", "url": "https://x.com/{}", "status": 200, "category": "social"},
    {"name": "Instagram", "url": "https://www.instagram.com/{}/", "status": 200, "category": "social"},
    {"name": "Reddit", "url": "https://www.reddit.com/user/{}", "status": 200, "category": "social"},
    {"name": "LinkedIn", "url": "https://www.linkedin.com/in/{}", "status": 200, "category": "professional"},
    {"name": "Pinterest", "url": "https://www.pinterest.com/{}/", "status": 200, "category": "social"},
    {"name": "TikTok", "url": "https://www.tiktok.com/@{}", "status": 200, "category": "social"},
    {"name": "YouTube", "url": "https://www.youtube.com/@{}", "status": 200, "category": "social"},
    {"name": "Twitch", "url": "https://www.twitch.tv/{}", "status": 200, "category": "social"},
    {"name": "Steam", "url": "https://steamcommunity.com/id/{}", "status": 200, "category": "gaming"},
    {"name": "Medium", "url": "https://medium.com/@{}", "status": 200, "category": "blog"},
    {"name": "DevTo", "url": "https://dev.to/{}", "status": 200, "category": "development"},
    {"name": "HackerNews", "url": "https://news.ycombinator.com/user?id={}", "status": 200, "category": "development"},
    {"name": "Keybase", "url": "https://keybase.io/{}", "status": 200, "category": "security"},
    {"name": "Mastodon.social", "url": "https://mastodon.social/@{}", "status": 200, "category": "social"},
    {"name": "Telegram", "url": "https://t.me/{}", "status": 200, "category": "messaging"},
    {"name": "Patreon", "url": "https://www.patreon.com/{}", "status": 200, "category": "social"},
    {"name": "Spotify", "url": "https://open.spotify.com/user/{}", "status": 200, "category": "social"},
    {"name": "SoundCloud", "url": "https://soundcloud.com/{}", "status": 200, "category": "social"},
    {"name": "Flickr", "url": "https://www.flickr.com/people/{}", "status": 200, "category": "social"},
    {"name": "Behance", "url": "https://www.behance.net/{}", "status": 200, "category": "creative"},
    {"name": "Dribbble", "url": "https://dribbble.com/{}", "status": 200, "category": "creative"},
    {"name": "VK", "url": "https://vk.com/{}", "status": 200, "category": "social"},
    {"name": "HackerOne", "url": "https://hackerone.com/{}", "status": 200, "category": "security"},
    {"name": "Bugcrowd", "url": "https://bugcrowd.com/{}", "status": 200, "category": "security"},
    {"name": "Gravatar", "url": "https://en.gravatar.com/{}", "status": 200, "category": "social"},
    {"name": "Docker Hub", "url": "https://hub.docker.com/u/{}", "status": 200, "category": "development"},
    {"name": "npm", "url": "https://www.npmjs.com/~{}", "status": 200, "category": "development"},
    {"name": "PyPI", "url": "https://pypi.org/user/{}/", "status": 200, "category": "development"},
    {"name": "Replit", "url": "https://replit.com/@{}", "status": 200, "category": "development"},
    {"name": "Codepen", "url": "https://codepen.io/{}", "status": 200, "category": "development"},
    {"name": "Bitbucket", "url": "https://bitbucket.org/{}/", "status": 200, "category": "development"},
    {"name": "About.me", "url": "https://about.me/{}", "status": 200, "category": "social"},
    {"name": "Kaggle", "url": "https://www.kaggle.com/{}", "status": 200, "category": "development"},
    {"name": "500px", "url": "https://500px.com/p/{}", "status": 200, "category": "creative"},
    {"name": "Trello", "url": "https://trello.com/{}", "status": 200, "category": "development"},
    {"name": "SlideShare", "url": "https://www.slideshare.net/{}", "status": 200, "category": "professional"},
    {"name": "Fiverr", "url": "https://www.fiverr.com/{}", "status": 200, "category": "professional"},
    {"name": "ProductHunt", "url": "https://www.producthunt.com/@{}", "status": 200, "category": "development"},
]


class CrossPlatformResolver(BaseCollector):
    """Resolves a username across multiple platforms (Sherlock-style)."""

    def __init__(self) -> None:
        super().__init__(rate_limit=10.0, max_retries=1)

    async def collect(self, query: CollectionQuery) -> list[CollectionResult]:
        username = query.query
        try:
            return await self._resolve_username(username, query.options)
        except Exception as e:
            logger.error("cross_platform.failed", error=str(e), username=username)
            return []

    async def _resolve_username(
        self, username: str, options: dict[str, Any]
    ) -> list[CollectionResult]:
        """Check a username across all platforms concurrently."""
        # Optionally filter by category
        categories = options.get("categories")
        platforms = PLATFORM_CHECKS
        if categories:
            platforms = [p for p in platforms if p["category"] in categories]

        # Fire all checks concurrently
        tasks = [
            self._check_platform(username, platform) for platform in platforms
        ]
        check_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[CollectionResult] = []
        for r in check_results:
            if isinstance(r, CollectionResult):
                results.append(r)

        logger.info(
            "cross_platform.resolve_complete",
            username=username,
            found=len(results),
            checked=len(platforms),
        )
        return results

    async def _check_platform(
        self, username: str, platform: dict[str, Any]
    ) -> CollectionResult | None:
        """Check if a username exists on a specific platform."""
        url = platform["url"].format(username)
        session = await self._get_session()

        try:
            await self._rate_limit_wait()
            async with session.get(
                url,
                allow_redirects=True,
                timeout=__import__("aiohttp").ClientTimeout(total=10),
            ) as resp:
                if resp.status == platform["status"]:
                    return CollectionResult(
                        source_int="SOCMINT",
                        source_id=f"crossplatform:{platform['name'].lower()}:{username}",
                        raw_data={
                            "platform": platform["name"],
                            "url": url,
                            "status_code": resp.status,
                            "username": username,
                        },
                        normalized={
                            "entity_type": "SocialAccount",
                            "platform": platform["name"].lower(),
                            "username": username,
                            "profile_url": url,
                            "category": platform["category"],
                        },
                        metadata={
                            "collector": "cross_platform_resolver",
                            "scan_type": "username_search",
                        },
                        reliability_grade="D",
                    )
        except Exception:
            pass  # Timeouts and errors are expected for non-existent profiles

        return None

    async def health_check(self) -> bool:
        """Always available — no API key required."""
        return True
