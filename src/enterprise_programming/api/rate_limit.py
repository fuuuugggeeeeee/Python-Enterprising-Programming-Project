"""A bounded in-process fixed-window rate limiter for the demo deployment."""

import threading
import time
from typing import Dict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, requests_per_minute: int) -> None:
        super().__init__(app)
        self.limit = requests_per_minute
        self._clients: Dict[str, int] = {}
        self._window = int(time.time() // 60)
        self._lock = threading.Lock()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in {"/health/live", "/health/ready", "/metrics"}:
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        window = int(time.time() // 60)
        with self._lock:
            if self._window != window:
                self._clients.clear()
                self._window = window
            count = self._clients.get(client, 0) + 1
            self._clients[client] = count
            allowed = count <= self.limit
            remaining = max(0, self.limit - count)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Too many requests; retry in the next minute",
                    }
                },
                headers={
                    "Retry-After": str(60 - int(time.time() % 60)),
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                },
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
