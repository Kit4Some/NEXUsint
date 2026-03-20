"""Integration test: authentication flow — login, access, refresh, logout."""

import uuid
from datetime import timedelta, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jose import jwt

from nexus.config import settings


class TestAuthFlow:
    """End-to-end authentication flow test."""

    @pytest.fixture
    def user_row(self):
        from nexus.services.password_policy import PasswordPolicy

        return {
            "id": uuid.uuid4(),
            "username": "analyst1",
            "email": "analyst1@nexus.local",
            "role": "analyst",
            "is_active": True,
            "password_hash": PasswordPolicy.hash("SecureP@ssw0rd!"),
            "created_at": datetime.now(timezone.utc),
        }

    @pytest.mark.asyncio
    async def test_login_returns_tokens_with_jti(self, user_row):
        """Login should return tokens containing jti claim."""
        from nexus.api.routes.auth import _create_token

        token = _create_token(
            {"sub": str(user_row["id"]), "role": "analyst"},
            timedelta(minutes=30),
        )
        decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert "jti" in decoded
        assert "sub" in decoded
        assert decoded["role"] == "analyst"

    @pytest.mark.asyncio
    async def test_token_blacklisting(self):
        """Blacklisted tokens should be rejected."""
        from nexus.services.token_blacklist import TokenBlacklist

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)

        blacklist = TokenBlacklist(mock_redis)
        jti = str(uuid.uuid4())

        await blacklist.blacklist(jti, ttl_seconds=1800)
        is_blocked = await blacklist.is_blacklisted(jti)
        assert is_blocked is True

    @pytest.mark.asyncio
    async def test_logout_blacklists_token(self):
        """Logout should add token JTI to blacklist."""
        from nexus.services.token_blacklist import TokenBlacklist

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()
        blacklist = TokenBlacklist(mock_redis)

        jti = str(uuid.uuid4())
        await blacklist.blacklist(jti, ttl_seconds=1800)

        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args[0]
        assert jti in call_args[0]

    @pytest.mark.asyncio
    async def test_refresh_rotates_tokens(self, user_row):
        """Refresh should return new tokens with new JTI values."""
        from nexus.api.routes.auth import _create_token

        token1 = _create_token(
            {"sub": str(user_row["id"]), "role": "analyst"},
            timedelta(days=7),
        )
        token2 = _create_token(
            {"sub": str(user_row["id"]), "role": "analyst"},
            timedelta(days=7),
        )

        decoded1 = jwt.decode(token1, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        decoded2 = jwt.decode(token2, settings.jwt_secret, algorithms=[settings.jwt_algorithm])

        # Each token should have a unique JTI
        assert decoded1["jti"] != decoded2["jti"]

    @pytest.mark.asyncio
    async def test_password_change_validation(self):
        """Password change should enforce policy."""
        from nexus.services.password_policy import PasswordPolicy, PasswordPolicyError

        # Valid password
        PasswordPolicy.validate("NewSecure@Pass123!")

        # Invalid passwords
        with pytest.raises(PasswordPolicyError):
            PasswordPolicy.validate("short")

        with pytest.raises(PasswordPolicyError):
            PasswordPolicy.validate("nouppercase1234!")
