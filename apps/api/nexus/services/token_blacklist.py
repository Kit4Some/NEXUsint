"""JWT token blacklist backed by Redis."""

import redis.asyncio as aioredis


class TokenBlacklist:
    """Manages revoked JWT tokens using Redis with automatic TTL expiry."""

    _PREFIX = "nexus:token:blacklist:"

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def blacklist(self, jti: str, ttl_seconds: int) -> None:
        """Add a token JTI to the blacklist with matching TTL."""
        await self._redis.setex(f"{self._PREFIX}{jti}", ttl_seconds, "1")

    async def is_blacklisted(self, jti: str) -> bool:
        """Check if a token JTI has been revoked."""
        return await self._redis.exists(f"{self._PREFIX}{jti}") > 0
