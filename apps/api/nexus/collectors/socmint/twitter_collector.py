"""Twitter/X data collector using Twitter API v2."""

from datetime import datetime
from typing import Any

import structlog

from nexus.collectors.base import BaseCollector, CollectionQuery, CollectionResult
from nexus.config import settings

logger = structlog.get_logger()

TWITTER_API_BASE = "https://api.twitter.com/2"


class TwitterCollector(BaseCollector):
    """Collects data from Twitter/X via API v2."""

    def __init__(self) -> None:
        super().__init__(rate_limit=1.0, max_retries=3)
        self._bearer_token = settings.twitter_bearer_token

    async def _get_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._bearer_token}"}

    async def collect(self, query: CollectionQuery) -> list[CollectionResult]:
        if not self._bearer_token:
            logger.warning("twitter.no_api_key")
            return []

        scan_type = query.scan_type
        try:
            if scan_type == "keyword_search":
                return await self._search_tweets(query.query, query.options)
            elif scan_type == "user_timeline":
                return await self._get_user_timeline(query.query, query.options)
            elif scan_type == "user_info":
                return await self._get_user_info(query.query)
            elif scan_type == "followers":
                return await self._get_followers(query.query, query.options)
            else:
                logger.warning("twitter.unknown_scan_type", scan_type=scan_type)
                return []
        except Exception as e:
            logger.error("twitter.collection_failed", error=str(e), scan_type=scan_type)
            return []

    async def _search_tweets(
        self, query_str: str, options: dict[str, Any]
    ) -> list[CollectionResult]:
        """Search recent tweets matching a query."""
        params: dict[str, Any] = {
            "query": query_str,
            "max_results": options.get("max_results", 100),
            "tweet.fields": "created_at,author_id,public_metrics,entities,geo,lang",
            "expansions": "author_id,geo.place_id",
            "user.fields": "name,username,location,description,public_metrics,verified",
        }

        data = await self._request_with_retry(
            "GET",
            f"{TWITTER_API_BASE}/tweets/search/recent",
            params=params,
            headers=await self._get_headers(),
        )

        results: list[CollectionResult] = []
        tweets = data.get("data", [])
        includes = data.get("includes", {})
        users_map = {u["id"]: u for u in includes.get("users", [])}

        for tweet in tweets:
            author = users_map.get(tweet.get("author_id", ""), {})
            hashtags = [
                t["tag"]
                for t in (tweet.get("entities") or {}).get("hashtags", [])
            ]

            results.append(CollectionResult(
                source_int="SOCMINT",
                source_id=f"twitter:tweet:{tweet['id']}",
                raw_data=tweet,
                normalized={
                    "entity_type": "Post",
                    "platform": "twitter",
                    "text": tweet.get("text", ""),
                    "author_username": author.get("username", ""),
                    "author_name": author.get("name", ""),
                    "author_id": tweet.get("author_id", ""),
                    "created_at": tweet.get("created_at", ""),
                    "lang": tweet.get("lang", ""),
                    "metrics": tweet.get("public_metrics", {}),
                    "hashtags": hashtags,
                    "geo": tweet.get("geo"),
                },
                metadata={
                    "collector": "twitter",
                    "scan_type": "keyword_search",
                    "query": query_str,
                },
                reliability_grade="C",
            ))

        logger.info("twitter.search_complete", query=query_str, count=len(results))
        return results

    async def _get_user_timeline(
        self, username: str, options: dict[str, Any]
    ) -> list[CollectionResult]:
        """Get recent tweets from a specific user."""
        user_data = await self._request_with_retry(
            "GET",
            f"{TWITTER_API_BASE}/users/by/username/{username}",
            params={"user.fields": "id"},
            headers=await self._get_headers(),
        )

        user_id = user_data.get("data", {}).get("id")
        if not user_id:
            return []

        data = await self._request_with_retry(
            "GET",
            f"{TWITTER_API_BASE}/users/{user_id}/tweets",
            params={
                "max_results": options.get("max_results", 100),
                "tweet.fields": "created_at,public_metrics,entities,geo,lang",
            },
            headers=await self._get_headers(),
        )

        results: list[CollectionResult] = []
        for tweet in data.get("data", []):
            results.append(CollectionResult(
                source_int="SOCMINT",
                source_id=f"twitter:tweet:{tweet['id']}",
                raw_data=tweet,
                normalized={
                    "entity_type": "Post",
                    "platform": "twitter",
                    "text": tweet.get("text", ""),
                    "author_username": username,
                    "created_at": tweet.get("created_at", ""),
                    "metrics": tweet.get("public_metrics", {}),
                },
                metadata={"collector": "twitter", "scan_type": "user_timeline"},
                reliability_grade="C",
            ))

        return results

    async def _get_user_info(self, username: str) -> list[CollectionResult]:
        """Get user profile information."""
        data = await self._request_with_retry(
            "GET",
            f"{TWITTER_API_BASE}/users/by/username/{username}",
            params={
                "user.fields": (
                    "created_at,description,location,name,public_metrics,"
                    "profile_image_url,url,verified,verified_type"
                ),
            },
            headers=await self._get_headers(),
        )

        user = data.get("data")
        if not user:
            return []

        return [CollectionResult(
            source_int="SOCMINT",
            source_id=f"twitter:user:{user['id']}",
            raw_data=user,
            normalized={
                "entity_type": "SocialAccount",
                "platform": "twitter",
                "username": user.get("username", ""),
                "display_name": user.get("name", ""),
                "description": user.get("description", ""),
                "location": user.get("location", ""),
                "followers_count": user.get("public_metrics", {}).get("followers_count", 0),
                "following_count": user.get("public_metrics", {}).get("following_count", 0),
                "tweet_count": user.get("public_metrics", {}).get("tweet_count", 0),
                "created_at": user.get("created_at", ""),
                "verified": user.get("verified", False),
                "profile_image_url": user.get("profile_image_url", ""),
            },
            metadata={"collector": "twitter", "scan_type": "user_info"},
            reliability_grade="C",
        )]

    async def _get_followers(
        self, username: str, options: dict[str, Any]
    ) -> list[CollectionResult]:
        """Get followers of a user."""
        user_data = await self._request_with_retry(
            "GET",
            f"{TWITTER_API_BASE}/users/by/username/{username}",
            params={"user.fields": "id"},
            headers=await self._get_headers(),
        )

        user_id = user_data.get("data", {}).get("id")
        if not user_id:
            return []

        data = await self._request_with_retry(
            "GET",
            f"{TWITTER_API_BASE}/users/{user_id}/followers",
            params={
                "max_results": min(options.get("max_results", 100), 1000),
                "user.fields": "name,username,location,description,public_metrics,verified",
            },
            headers=await self._get_headers(),
        )

        results: list[CollectionResult] = []
        for follower in data.get("data", []):
            results.append(CollectionResult(
                source_int="SOCMINT",
                source_id=f"twitter:user:{follower['id']}",
                raw_data=follower,
                normalized={
                    "entity_type": "SocialAccount",
                    "platform": "twitter",
                    "username": follower.get("username", ""),
                    "display_name": follower.get("name", ""),
                    "description": follower.get("description", ""),
                    "location": follower.get("location", ""),
                    "followers_count": follower.get("public_metrics", {}).get("followers_count", 0),
                    "verified": follower.get("verified", False),
                    "relationship": {"type": "FOLLOWS", "target": username},
                },
                metadata={"collector": "twitter", "scan_type": "followers"},
                reliability_grade="C",
            ))

        return results

    async def health_check(self) -> bool:
        if not self._bearer_token:
            return False
        try:
            await self._request_with_retry(
                "GET",
                f"{TWITTER_API_BASE}/tweets/search/recent",
                params={"query": "test", "max_results": 10},
                headers=await self._get_headers(),
            )
            return True
        except Exception:
            return False
