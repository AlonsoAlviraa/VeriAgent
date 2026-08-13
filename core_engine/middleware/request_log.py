"""Access log middleware: method + path + status. No secrets, no body."""

from __future__ import annotations

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from shared.redact import sanitize_log

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log request line only. Never log Authorization, bodies, NIFs, or PEMs."""

    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        # Path only — query strings can carry key= / tokens.
        path = sanitize_log(request.url.path)
        method = request.method
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 1)
        logger.info(
            "%s %s -> %s %sms",
            method,
            path,
            response.status_code,
            duration_ms,
        )
        return response
