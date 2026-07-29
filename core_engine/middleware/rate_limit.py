"""
[SEC / Sprint 10] In-memory token-bucket rate limiter middleware.

Protege la API contra abuso sin dependencias externas (Redis llega en prod).
Límite por identificador (IP del cliente o X-Tenant-Id). El bucket se resetea
por ventana deslizante.

Uso (en main.py):
    from core_engine.middleware.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware, requests=60, window_seconds=60)

Diseño: thread-safe con un lock; evict buckets inactivos para no crecer sin fin.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class TokenBucket:
    """Bucket por identificador con ventana deslizante."""

    __slots__ = ("timestamps",)

    def __init__(self):
        self.timestamps: list[float] = []

    def consume(self, now: float, max_requests: int, window: float) -> tuple[bool, int]:
        """Devuelve (allowed, remaining)."""
        cutoff = now - window
        self.timestamps = [t for t in self.timestamps if t > cutoff]
        if len(self.timestamps) >= max_requests:
            return False, 0
        self.timestamps.append(now)
        return True, max_requests - len(self.timestamps)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting por IP/tenant. Excluye /health del límite.

    Args:
        requests: nº máximo de peticiones por ventana.
        window_seconds: tamaño de la ventana.
        exempt_paths: rutas excluidas (default: /health).
    """

    def __init__(self, app, requests: int = 60, window_seconds: int = 60,
                 exempt_paths: Optional[list] = None):
        super().__init__(app)
        self.max_requests = requests
        self.window = window_seconds
        self.exempt = set(exempt_paths or ["/health"])
        self._buckets: dict[str, TokenBucket] = defaultdict(TokenBucket)
        self._lock = threading.Lock()
        self._last_eviction = time.time()

    def _client_id(self, request: Request) -> str:
        # Priorizar tenant si viene en header (multi-org), si no IP.
        tenant = request.headers.get("X-Tenant-Id")
        if tenant:
            return f"t:{tenant}"
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        client = request.client
        return f"ip:{client.host}" if client else "ip:unknown"

    def _evict_stale(self, now: float) -> None:
        """Evict buckets sin actividad reciente cada 5 min."""
        if now - self._last_eviction < 300:
            return
        cutoff = now - self.window
        stale = [
            k for k, b in self._buckets.items()
            if not b.timestamps or b.timestamps[-1] < cutoff
        ]
        for k in stale:
            self._buckets.pop(k, None)
        self._last_eviction = now

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.exempt:
            return await call_next(request)

        client_id = self._client_id(request)
        now = time.time()
        with self._lock:
            self._evict_stale(now)
            bucket = self._buckets[client_id]
            allowed, remaining = bucket.consume(now, self.max_requests, self.window)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error_code": "RATE_LIMITED",
                    "message": f"Rate limit exceeded: {self.max_requests}/{self.window}s",
                },
                headers={
                    "Retry-After": str(int(self.window)),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        return response
