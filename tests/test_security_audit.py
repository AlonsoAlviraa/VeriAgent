"""
[SEC / Sprint 10] Security audit automatizado (pytest).

Convierte scripts/security_tests.py (que solo tenía prints) en asserts reales:
1. Cabeceras de seguridad en /health (X-Content-Type-Options, X-Frame-Options,
   HSTS, CSP).
2. Protección de upload: bloquea .exe, valida magic bytes en .pdf.
3. Rate limiting: 429 tras exceder el límite con umbral bajo (test aislado).
4. Endpoints protegidos por RBAC devuelven 403 sin roles.
"""

import io

import pytest
from fastapi import Header
from fastapi.testclient import TestClient

from core_engine.main import app


client = TestClient(app)


class TestSecurityHeaders:
    def test_health_has_security_headers(self):
        r = client.get("/health")
        assert r.status_code == 200
        h = r.headers
        assert h.get("X-Content-Type-Options") == "nosniff"
        assert h.get("X-Frame-Options") == "DENY"
        assert h.get("Strict-Transport-Security") == (
            "max-age=31536000; includeSubDomains"
        )
        assert h.get("Content-Security-Policy") == "default-src 'self'"

    def test_health_headers_survive_repeated_gets(self):
        """Limiter exempts /health; nosniff/DENY/HSTS/CSP stay on every response."""
        for _ in range(3):
            h = client.get("/health").headers
            assert h.get("X-Content-Type-Options") == "nosniff"
            assert h.get("X-Frame-Options") == "DENY"
            assert "max-age=31536000" in h.get("Strict-Transport-Security", "")
            assert h.get("Content-Security-Policy") == "default-src 'self'"


class TestUploadSecurity:
    def test_blocks_executable(self):
        files = {"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")}
        r = client.post("/api/v1/invoices/upload", files=files)
        assert r.status_code == 400

    def test_blocks_fake_pdf_magic(self):
        files = {"file": ("fake.pdf", b"not a pdf header", "application/pdf")}
        r = client.post("/api/v1/invoices/upload", files=files)
        assert r.status_code == 400

    def test_accepts_real_pdf_magic(self):
        files = {"file": ("ok.pdf", b"%PDF-1.4 real", "application/pdf")}
        r = client.post("/api/v1/invoices/upload", files=files)
        assert r.status_code == 200


class TestRateLimiting:
    def test_rate_limit_returns_429_after_threshold(self):
        """Con un limiter muy estricto, el exceso devuelve 429."""
        from core_engine.middleware.rate_limit import RateLimitMiddleware
        from starlette.applications import Starlette
        from starlette.routing import Route
        from starlette.responses import PlainTextResponse

        async def ping(request):
            return PlainTextResponse("pong")

        limited = Starlette(routes=[Route("/ping", ping)])
        limited.add_middleware(RateLimitMiddleware, requests=3, window_seconds=60)

        c = TestClient(limited)
        # Las 3 primeras pasan, la 4ª se limita.
        codes = [c.get("/ping").status_code for _ in range(4)]
        assert codes[:3] == [200, 200, 200]
        assert codes[3] == 429
        assert c.get("/ping").headers.get("Retry-After") is not None

    def test_health_exempt_from_rate_limit(self):
        """/health no se ve afectado por el rate limit de producción."""
        # Aunque hagamos muchas peticiones, /health siempre responde 200.
        codes = [client.get("/health").status_code for _ in range(5)]
        assert all(c == 200 for c in codes)

    def test_production_limiter_does_not_exempt_ingest(self):
        """Wired RateLimitMiddleware stays on; ingest is not in exempt_paths."""
        from core_engine.middleware.rate_limit import RateLimitMiddleware

        wired = [
            m for m in app.user_middleware if m.cls is RateLimitMiddleware
        ]
        assert wired, "RateLimitMiddleware must stay enabled on the fleet app"
        kwargs = wired[0].kwargs
        exempt = set(kwargs.get("exempt_paths") or ["/health"])
        assert "/health" in exempt
        assert "/api/v1/fleet/ingest" not in exempt
        assert "/api/v1/fleet/ingest/batch" not in exempt

    def test_fleet_ingest_returns_429_without_disabling_limiter(self):
        """POST /api/v1/fleet/ingest is limited by RateLimitMiddleware (still enabled)."""
        from fastapi import FastAPI

        from core_engine.middleware.rate_limit import RateLimitMiddleware

        ingest_app = FastAPI()

        @ingest_app.post("/api/v1/fleet/ingest")
        def ingest():
            return {"status": "ok"}

        ingest_app.add_middleware(RateLimitMiddleware, requests=2, window_seconds=60)
        c = TestClient(ingest_app)
        assert c.post("/api/v1/fleet/ingest", json={"invoice": {}}).status_code == 200
        assert c.post("/api/v1/fleet/ingest", json={"invoice": {}}).status_code == 200
        limited = c.post("/api/v1/fleet/ingest", json={"invoice": {}})
        assert limited.status_code == 429
        assert limited.json()["error_code"] == "RATE_LIMITED"
        assert limited.headers.get("Retry-After") is not None
        assert limited.headers.get("X-RateLimit-Remaining") == "0"


class TestRBACProtection:
    def test_create_invoice_requires_issuer_role(self):
        """Sin roles válidos, /invoices devuelve 403."""
        # Por defecto parse_org_context asigna rol 'issuer', así que forzamos
        # un rol sin permiso mediante el header X-Roles.
        payload = {
            "number": "RBAC-1",
            "series": "X",
            "issue_date": "2026-01-15",
            "issuer_tax_id": "B12345674",
            "customer": {
                "tax_id": "A11111119",
                "name": "C",
                "address": {"street": "S", "city": "M", "postal_code": "28001"},
            },
            "lines": [],
            "taxes": [],
            "total_base": 0.0,
            "total_tax": 0.0,
            "total_amount": 0.0,
        }
        r = client.post("/api/v1/invoices", json=payload, headers={"X-Roles": "auditor"})
        assert r.status_code == 403
        assert r.json()["detail"]["error_code"] == "RBAC_FORBIDDEN"
