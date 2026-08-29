"""Structured request logging and Prometheus-compatible metrics."""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

REQUEST_COUNT = Counter(
    "epp_http_requests_total",
    "Total HTTP requests",
    ("method", "route", "status"),
)
REQUEST_DURATION = Histogram(
    "epp_http_request_duration_seconds",
    "HTTP request duration",
    ("method", "route"),
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        document: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "client_ip",
        ):
            if hasattr(record, key):
                document[key] = getattr(record, key)
        if record.exc_info:
            document["exception"] = self.formatException(record.exc_info)
        return json.dumps(document, separators=(",", ":"), default=str)


def configure_logging(level: str, json_logs: bool) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter() if json_logs else logging.Formatter("%(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", "")
        if not request_id or len(request_id) > 64:
            request_id = str(uuid4())
        request.state.request_id = request_id
        started_at = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - started_at
        route = getattr(request.scope.get("route"), "path", "unmatched")
        REQUEST_COUNT.labels(request.method, route, str(response.status_code)).inc()
        REQUEST_DURATION.labels(request.method, route).observe(duration)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        logging.getLogger("enterprise_programming.api").info(
            "request.completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 3),
                "client_ip": request.client.host if request.client else "unknown",
            },
        )
        return response


def metrics_response() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
