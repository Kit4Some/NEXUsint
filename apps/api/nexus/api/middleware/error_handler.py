"""Global error handling middleware."""

import uuid
import traceback

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = structlog.get_logger()


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catches unhandled exceptions and returns structured JSON errors."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        try:
            return await call_next(request)
        except AssertionError as exc:
            logger.error(
                "service.unavailable",
                request_id=request_id,
                error=str(exc),
                path=request.url.path,
            )
            return JSONResponse(
                status_code=503,
                content={
                    "error": "Service Unavailable",
                    "detail": str(exc) or "A required service is not initialized",
                    "request_id": request_id,
                },
            )
        except Exception as exc:
            logger.error(
                "unhandled_exception",
                request_id=request_id,
                error=str(exc),
                path=request.url.path,
                traceback=traceback.format_exc(),
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal Server Error",
                    "detail": "An unexpected error occurred",
                    "request_id": request_id,
                },
            )
