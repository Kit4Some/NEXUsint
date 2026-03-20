"""Integration test: WebSocket authentication enforcement."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from nexus.api.websocket.handlers import _authenticate_token


class TestWebSocketAuth:
    """Tests for WebSocket JWT authentication."""

    def test_authenticate_with_query_string(self):
        """Should extract token from query string."""
        from nexus.config import settings
        from jose import jwt
        from datetime import datetime, timedelta, timezone

        token = jwt.encode(
            {
                "sub": "user-123",
                "role": "analyst",
                "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            },
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

        environ = {"QUERY_STRING": f"token={token}"}
        result = _authenticate_token(environ)
        assert result is not None
        assert result["user_id"] == "user-123"
        assert result["role"] == "analyst"

    def test_authenticate_with_http_authorization(self):
        """Should extract token from HTTP_AUTHORIZATION header."""
        from nexus.config import settings
        from jose import jwt
        from datetime import datetime, timedelta, timezone

        token = jwt.encode(
            {
                "sub": "user-456",
                "role": "admin",
                "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
            },
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

        environ = {"HTTP_AUTHORIZATION": f"Bearer {token}"}
        result = _authenticate_token(environ)
        assert result is not None
        assert result["user_id"] == "user-456"

    def test_reject_no_token(self):
        """Should reject connection with no token."""
        environ = {}
        result = _authenticate_token(environ)
        assert result is None

    def test_reject_invalid_token(self):
        """Should reject connection with invalid token."""
        environ = {"QUERY_STRING": "token=invalid.jwt.token"}
        result = _authenticate_token(environ)
        assert result is None

    def test_reject_expired_token(self):
        """Should reject expired tokens."""
        from nexus.config import settings
        from jose import jwt
        from datetime import datetime, timedelta, timezone

        token = jwt.encode(
            {
                "sub": "user-expired",
                "role": "analyst",
                "exp": int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp()),
            },
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

        environ = {"QUERY_STRING": f"token={token}"}
        result = _authenticate_token(environ)
        assert result is None
