"""Prometheus metrics middleware for HTTP request instrumentation."""

import time

from prometheus_client import Counter, Histogram, Gauge, make_asgi_app
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

# HTTP metrics
http_requests_total = Counter(
    "nexus_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

http_request_duration_seconds = Histogram(
    "nexus_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

http_requests_in_progress = Gauge(
    "nexus_http_requests_in_progress",
    "Number of HTTP requests currently in progress",
    ["method"],
)

_EXCLUDED_PATHS = frozenset({"/metrics", "/health"})


def _normalize_path(path: str) -> str:
    """Normalize path to reduce cardinality (replace UUIDs/IDs with placeholder)."""
    parts = path.split("/")
    normalized = []
    for part in parts:
        # Replace segments that look like IDs (hex, uuid, numeric)
        if len(part) > 8 and all(c in "0123456789abcdef-" for c in part.lower()):
            normalized.append("{id}")
        else:
            normalized.append(part)
    return "/".join(normalized)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Collects Prometheus metrics for every HTTP request."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _EXCLUDED_PATHS:
            return await call_next(request)

        method = request.method
        path = _normalize_path(request.url.path)

        http_requests_in_progress.labels(method=method).inc()
        start = time.perf_counter()

        try:
            response = await call_next(request)
            status = str(response.status_code)
        except Exception:
            status = "500"
            raise
        finally:
            duration = time.perf_counter() - start
            http_requests_total.labels(method=method, path=path, status=status).inc()
            http_request_duration_seconds.labels(method=method, path=path).observe(duration)
            http_requests_in_progress.labels(method=method).dec()

        return response


def get_metrics_app():
    """Create an ASGI app that exposes /metrics for Prometheus scraping."""
    return make_asgi_app()
