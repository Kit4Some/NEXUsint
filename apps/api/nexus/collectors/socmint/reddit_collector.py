"""Reddit data collector using async OAuth2 API."""

import base64
from typing import Any

import structlog

from nexus.collectors.base import BaseCollector, CollectionQuery, CollectionResult
from nexus.config import settings

logger = structlog.get_logger()

REDDIT_API_BASE = "https://oauth.reddit.com"
REDDIT_AUTH_URL = "https://www.reddit.com/api/v1/access_token"


class RedditCollector(BaseCollector):
    """Collects data from Reddit via OAuth2 API."""

    def __init__(self) -> None:
        super().__init__(rate_limit=1.0, max_retries=3)
        self._client_id = settings.reddit_client_id
        self._client_secret = settings.reddit_client_secret
        self._access_token: str | None = None

    async def _authenticate(self) -> str:
        """Get OAuth2 access token for Reddit API."""
        if self._access_token:
            return self._access_token

        session = await self._get_session()
        auth = base64.b64encode(
            f"{self._client_id}:{self._client_secret}".encode()
        ).decode()

        async with session.post(
            REDDIT_AUTH_URL,
            data={"grant_type": "client_credentials"},
            headers={
                "Authorization": f"Basic {auth}",
                "User-Agent": "NEXUS-OSINT/0.1",
            },
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            self._access_token = data["access_token"]
            return self._access_token

    async def _get_headers(self) -> dict[str, str]:
        token = await self._authenticate()
        return {
            "Authorization": f"Bearer {token}",
            "User-Agent": "NEXUS-OSINT/0.1",
        }

    async def collect(self, query: CollectionQuery) -> list[CollectionResult]:
        if not self._client_id or not self._client_secret:
            logger.warning("reddit.no_api_credentials")
            return []

        scan_type = query.scan_type
        try:
            if scan_type == "subreddit_search":
                subreddit = query.options.get("subreddit", "all")
                return await self._search_subreddit(subreddit, query.query, query.options)
            elif scan_type == "user_history":
                return await self._get_user_history(query.query, query.options)
            else:
                logger.warning("reddit.unknown_scan_type", scan_type=scan_type)
                return []
        except Exception as e:
            logger.error("reddit.collection_failed", error=str(e), scan_type=scan_type)
            return []

    async def _search_subreddit(
        self, subreddit: str, search_query: str, options: dict[str, Any]
    ) -> list[CollectionResult]:
        """Search posts in a subreddit."""
        params: dict[str, Any] = {
            "q": search_query,
            "limit": min(options.get("limit", 100), 100),
            "sort": options.get("sort", "relevance"),
            "t": options.get("time_filter", "all"),
        }

        data = await self._request_with_retry(
            "GET",
            f"{REDDIT_API_BASE}/r/{subreddit}/search",
            params=params,
            headers=await self._get_headers(),
        )

        results: list[CollectionResult] = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            results.append(CollectionResult(
                source_int="SOCMINT",
                source_id=f"reddit:post:{post.get('id', '')}",
                raw_data=post,
                normalized={
                    "entity_type": "Post",
                    "platform": "reddit",
                    "subreddit": post.get("subreddit", ""),
                    "title": post.get("title", ""),
                    "text": post.get("selftext", ""),
                    "author": post.get("author", ""),
                    "url": post.get("url", ""),
                    "score": post.get("score", 0),
                    "num_comments": post.get("num_comments", 0),
                    "created_utc": post.get("created_utc", 0),
                    "is_nsfw": post.get("over_18", False),
                },
                metadata={
                    "collector": "reddit",
                    "scan_type": "subreddit_search",
                    "subreddit": subreddit,
                },
                reliability_grade="D",
            ))

        logger.info(
            "reddit.search_complete",
            subreddit=subreddit,
            query=search_query,
            count=len(results),
        )
        return results

    async def _get_user_history(
        self, username: str, options: dict[str, Any]
    ) -> list[CollectionResult]:
        """Get a user's recent post and comment history."""
        results: list[CollectionResult] = []

        # Get submitted posts
        data = await self._request_with_retry(
            "GET",
            f"{REDDIT_API_BASE}/user/{username}/submitted",
            params={
                "limit": min(options.get("limit", 50), 100),
                "sort": "new",
            },
            headers=await self._get_headers(),
        )

        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            results.append(CollectionResult(
                source_int="SOCMINT",
                source_id=f"reddit:post:{post.get('id', '')}",
                raw_data=post,
                normalized={
                    "entity_type": "Post",
                    "platform": "reddit",
                    "subreddit": post.get("subreddit", ""),
                    "title": post.get("title", ""),
                    "text": post.get("selftext", ""),
                    "author": username,
                    "score": post.get("score", 0),
                    "created_utc": post.get("created_utc", 0),
                },
                metadata={"collector": "reddit", "scan_type": "user_history"},
                reliability_grade="D",
            ))

        # Get comments
        comments_data = await self._request_with_retry(
            "GET",
            f"{REDDIT_API_BASE}/user/{username}/comments",
            params={"limit": min(options.get("limit", 50), 100), "sort": "new"},
            headers=await self._get_headers(),
        )

        for child in comments_data.get("data", {}).get("children", []):
            comment = child.get("data", {})
            results.append(CollectionResult(
                source_int="SOCMINT",
                source_id=f"reddit:comment:{comment.get('id', '')}",
                raw_data=comment,
                normalized={
                    "entity_type": "Post",
                    "platform": "reddit",
                    "subreddit": comment.get("subreddit", ""),
                    "text": comment.get("body", ""),
                    "author": username,
                    "score": comment.get("score", 0),
                    "created_utc": comment.get("created_utc", 0),
                    "parent_id": comment.get("parent_id", ""),
                    "is_comment": True,
                },
                metadata={"collector": "reddit", "scan_type": "user_history"},
                reliability_grade="D",
            ))

        logger.info("reddit.user_history_complete", username=username, count=len(results))
        return results

    async def health_check(self) -> bool:
        if not self._client_id or not self._client_secret:
            return False
        try:
            await self._authenticate()
            return True
        except Exception:
            return False
