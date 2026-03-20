"""Audit logging middleware — logs every request with correlation ID."""

import time
import uuid

import asyncpg
import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from nexus.dependencies import lifespan_state

logger = structlog.get_logger()

# Paths excluded from audit logging
_EXCLUDED_PATHS = frozenset({"/health", "/metrics", "/docs", "/openapi.json", "/redoc"})


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """Logs requests with correlation IDs and persists to PostgreSQL."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip excluded paths
        if request.url.path in _EXCLUDED_PATHS:
            return await call_next(request)

        # Generate or reuse correlation ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Extract user ID from JWT if present (best-effort)
        user_id = _extract_user_id(request)

        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            status_code = response.status_code if response else 500

            # Attach correlation ID to response
            if response:
                response.headers["X-Request-ID"] = request_id

            # Structured log
            logger.info(
                "http.request",
                request_id=request_id,
                user_id=user_id,
                method=request.method,
                path=request.url.path,
                status=status_code,
                duration_ms=duration_ms,
                ip=request.client.host if request.client else None,
            )

            # Persist to PostgreSQL (fire-and-forget)
            await _persist_audit_log(
                request_id=request_id,
                user_id=user_id,
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent", ""),
            )


def _extract_user_id(request: Request) -> str | None:
    """Best-effort user ID extraction from Authorization header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    try:
        from jose import jwt
        from nexus.config import settings

        payload = jwt.decode(
            auth[7:], settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload.get("sub")
    except Exception:
        return None


async def _persist_audit_log(
    *,
    request_id: str,
    user_id: str | None,
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    ip_address: str | None,
    user_agent: str,
) -> None:
    """Persist audit log entry to PostgreSQL."""
    pool = lifespan_state.pg_pool
    if not pool:
        return
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_log (request_id, user_id, method, path, status_code, duration_ms, ip_address, user_agent)
                VALUES ($1, $2::uuid, $3, $4, $5, $6, $7, $8)
                """,
                uuid.UUID(request_id),
                uuid.UUID(user_id) if user_id else None,
                method,
                path,
                status_code,
                duration_ms,
                ip_address,
                user_agent,
            )
    except (asyncpg.UndefinedTableError, asyncpg.PostgresError):
        # Table may not exist yet (first run before migration)
        pass
    except Exception:
        logger.warning("audit_log.persist_failed", request_id=request_id)
