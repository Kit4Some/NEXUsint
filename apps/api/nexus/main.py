"""FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import socketio
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from nexus.config import settings
from nexus.dependencies import lifespan_state
from nexus.api.routes import router as api_router
from nexus.api.graphql.schema import graphql_app
from nexus.api.websocket.handlers import sio
from nexus.api.middleware import AuditLoggingMiddleware, ErrorHandlerMiddleware
from nexus.api.middleware.metrics import PrometheusMiddleware, get_metrics_app
from nexus.api.openapi_config import OPENAPI_CONFIG
from nexus.utils.logger import setup_logging

logger = structlog.get_logger()

_INSECURE_SECRET = "change-this-to-a-random-secret-key"

# Background scheduler handle — cancelled on shutdown
_scheduler_task: asyncio.Task | None = None


async def _run_live_feed_scheduler() -> None:
    """In-process live feed scheduler — runs collection directly in the API process.

    This eliminates the dependency on Celery workers for live feed data.
    Mirrors Shadowbroker's APScheduler approach: fast tier every 60s, slow tier every 300s.
    """
    from nexus.services.live_store import is_live_feed_active, set_live_feed_active

    fast_interval = settings.live_feed_fast_interval  # 60s
    slow_interval = settings.live_feed_slow_interval  # 300s

    fast_counter = 0
    logger.info("live_feed.scheduler.started", fast=fast_interval, slow=slow_interval)

    # Wait for services to be ready, then auto-activate live feed
    await asyncio.sleep(5)
    await set_live_feed_active(True)
    logger.info("live_feed.auto_activated")

    while True:
        try:
            if await is_live_feed_active():
                # Fast tier every cycle
                try:
                    from nexus.tasks.live_feed_tasks import _fast_collect
                    await _fast_collect()
                except Exception as exc:
                    logger.error("live_feed.scheduler.fast_failed", error=str(exc))

                # Slow tier every N cycles (slow_interval / fast_interval)
                fast_counter += 1
                if fast_counter >= (slow_interval // fast_interval):
                    fast_counter = 0
                    try:
                        from nexus.tasks.live_feed_tasks import _slow_collect
                        await _slow_collect()
                    except Exception as exc:
                        logger.error("live_feed.scheduler.slow_failed", error=str(exc))

        except asyncio.CancelledError:
            logger.info("live_feed.scheduler.cancelled")
            return
        except Exception as exc:
            logger.error("live_feed.scheduler.error", error=str(exc))

        await asyncio.sleep(fast_interval)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Manage application startup and shutdown."""
    global _scheduler_task
    setup_logging()

    # Refuse to start with empty or default JWT secret
    if not settings.jwt_secret or settings.jwt_secret == _INSECURE_SECRET:
        raise RuntimeError(
            "JWT_SECRET is not configured. Set the JWT_SECRET environment variable "
            "to a strong random value (min 32 characters)."
        )

    logger.info("nexus.startup", version="0.2.0")
    await lifespan_state.startup()

    # Start Redis → WebSocket bridge (forwards Celery events to Socket.IO)
    from nexus.api.websocket.handlers import start_redis_ws_bridge
    redis_bridge = None
    try:
        redis_bridge = await start_redis_ws_bridge()
    except Exception as exc:
        logger.warning("nexus.redis_bridge_failed", error=str(exc))

    # Start in-process live feed scheduler (no Celery worker needed)
    _scheduler_task = asyncio.create_task(_run_live_feed_scheduler())
    logger.info("nexus.live_feed_scheduler.started")

    yield

    # Shutdown
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            pass

    if redis_bridge:
        await redis_bridge.close()
    await lifespan_state.shutdown()
    logger.info("nexus.shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=OPENAPI_CONFIG["title"],
        version=OPENAPI_CONFIG["version"],
        description=OPENAPI_CONFIG["description"],
        contact=OPENAPI_CONFIG["contact"],
        license_info=OPENAPI_CONFIG["license_info"],
        openapi_tags=OPENAPI_CONFIG["openapi_tags"],
        lifespan=lifespan,
    )

    # Error handler middleware (outermost — catches everything)
    app.add_middleware(ErrorHandlerMiddleware)

    # Prometheus metrics middleware
    app.add_middleware(PrometheusMiddleware)

    # Audit logging middleware
    if settings.audit_log_enabled:
        app.add_middleware(AuditLoggingMiddleware)

    # CORS — allow all origins for Electron (file://) and dev compatibility
    # Note: credentials=False because auth uses Authorization header, not cookies
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting
    from nexus.utils.rate_limiter import limiter

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # REST API routes
    app.include_router(api_router, prefix="/api/v1")

    # GraphQL
    app.include_router(graphql_app, prefix="/graphql")

    # Prometheus metrics endpoint
    metrics_app = get_metrics_app()
    app.mount("/metrics", metrics_app)

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.2.0"}

    return app


_fastapi_app = create_app()
# Socket.IO ASGI wrapper — always included so `uvicorn nexus.main:app` works with WebSocket
sio_asgi_app = socketio.ASGIApp(sio, other_asgi_app=_fastapi_app)
app = sio_asgi_app
