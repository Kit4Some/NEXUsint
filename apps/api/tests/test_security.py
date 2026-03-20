"""Security hardening tests — JWT, token blacklist, password policy, audit logging."""

import uuid
from datetime import timedelta, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from jose import jwt

from nexus.services.token_blacklist import TokenBlacklist
from nexus.services.password_policy import PasswordPolicy, PasswordPolicyError


class TestTokenBlacklist:
    @pytest.fixture
    def mock_redis(self):
        return AsyncMock()

    @pytest.fixture
    def blacklist(self, mock_redis):
        return TokenBlacklist(mock_redis)

    @pytest.mark.asyncio
    async def test_blacklist_token(self, blacklist, mock_redis):
        jti = str(uuid.uuid4())
        await blacklist.blacklist(jti, ttl_seconds=1800)
        mock_redis.setex.assert_called_once_with(
            f"nexus:token:blacklist:{jti}", 1800, "1"
        )

    @pytest.mark.asyncio
    async def test_is_blacklisted_true(self, blacklist, mock_redis):
        mock_redis.exists = AsyncMock(return_value=1)
        result = await blacklist.is_blacklisted("some-jti")
        assert result is True

    @pytest.mark.asyncio
    async def test_is_blacklisted_false(self, blacklist, mock_redis):
        mock_redis.exists = AsyncMock(return_value=0)
        result = await blacklist.is_blacklisted("some-jti")
        assert result is False


class TestPasswordPolicy:
    def test_valid_password(self):
        PasswordPolicy.validate("SecureP@ss123!")
        # Should not raise

    def test_too_short(self):
        with pytest.raises(PasswordPolicyError, match="at least"):
            PasswordPolicy.validate("Sh0rt!")

    def test_no_uppercase(self):
        with pytest.raises(PasswordPolicyError, match="uppercase"):
            PasswordPolicy.validate("nouppercase1234!")

    def test_no_lowercase(self):
        with pytest.raises(PasswordPolicyError, match="lowercase"):
            PasswordPolicy.validate("NOLOWERCASE1234!")

    def test_no_digit(self):
        with pytest.raises(PasswordPolicyError, match="digit"):
            PasswordPolicy.validate("NoDigitsHere!!abc")

    def test_no_special(self):
        with pytest.raises(PasswordPolicyError, match="special"):
            PasswordPolicy.validate("NoSpecialChars12")

    def test_hash_and_verify(self):
        password = "TestPassword123!"
        hashed = PasswordPolicy.hash(password)
        assert hashed != password
        assert PasswordPolicy.verify(password, hashed)
        assert not PasswordPolicy.verify("wrong", hashed)


class TestJWTTokenClaims:
    """Tests that JWT tokens include required claims (jti, sub, role)."""

    def test_token_has_jti_claim(self):
        """Tokens should include a unique JWT ID for blacklisting."""
        from nexus.config import settings

        jti = str(uuid.uuid4())
        payload = {
            "sub": "user-123",
            "role": "analyst",
            "jti": jti,
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        decoded = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        assert decoded["jti"] == jti

    def test_expired_token_rejected(self):
        from nexus.config import settings

        payload = {
            "sub": "user-123",
            "role": "analyst",
            "jti": str(uuid.uuid4()),
            "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        with pytest.raises(Exception):
            jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


class TestAuditLogging:
    @pytest.mark.asyncio
    async def test_audit_log_persist(self):
        """Audit log entry should be persisted to PostgreSQL."""
        from nexus.api.middleware.audit_logging import _persist_audit_log

        mock_conn = AsyncMock()
        mock_pool = AsyncMock()
        mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch("nexus.api.middleware.audit_logging.lifespan_state") as mock_state:
            mock_state.pg_pool = mock_pool
            await _persist_audit_log(
                request_id=str(uuid.uuid4()),
                user_id=None,
                method="GET",
                path="/api/v1/entities",
                status_code=200,
                duration_ms=45.2,
                ip_address="127.0.0.1",
                user_agent="TestClient",
            )
            mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_audit_log_skips_when_no_pool(self):
        """Should not raise when pg_pool is None."""
        from nexus.api.middleware.audit_logging import _persist_audit_log

        with patch("nexus.api.middleware.audit_logging.lifespan_state") as mock_state:
            mock_state.pg_pool = None
            await _persist_audit_log(
                request_id=str(uuid.uuid4()),
                user_id=None,
                method="GET",
                path="/test",
                status_code=200,
                duration_ms=10.0,
                ip_address=None,
                user_agent="",
            )
            # Should complete without error
