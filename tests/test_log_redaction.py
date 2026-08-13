"""SEC: request logs must not leak hashes, NIFs, PEMs, or Authorization."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_redact_secret_first8_last8():
    from shared.redact import redact_secret

    value = "ABCDEFGH12345678IJKLMNOP"
    assert redact_secret(value) == "ABCDEFGH…IJKLMNOP"
    assert "12345678" not in redact_secret(value)


def test_redact_secret_omits_short_values():
    from shared.redact import redact_secret

    assert redact_secret("short") == "[omitted]"
    assert redact_secret("") == ""
    assert redact_secret(None) == ""


def test_sanitize_log_omits_authorization():
    from shared.redact import sanitize_log

    token = "supersecret-bearer-token-value-xyz"
    out = sanitize_log(f"Authorization: Bearer {token}")
    assert token not in out
    assert "Bearer" not in out


def test_sanitize_log_redacts_pem_blocks():
    from shared.redact import sanitize_log

    pem = (
        "-----BEGIN CERTIFICATE-----\n"
        "MIIFakePEMDATAShouldNeverAppearInLogs\n"
        "-----END CERTIFICATE-----"
    )
    out = sanitize_log(f"uploaded {pem}")
    assert "MIIFakePEMDATAShouldNeverAppearInLogs" not in out
    assert "BEGIN CERTIFICATE" not in out


def test_sanitize_log_redacts_nif():
    from shared.redact import sanitize_log

    out = sanitize_log("issuer_tax_id=B12345674 customer=A11111119")
    assert "B12345674" not in out
    assert "A11111119" not in out


def test_sanitize_log_redacts_full_hash():
    from shared.redact import sanitize_log

    digest = "A" * 32 + "B" * 32
    out = sanitize_log(f"invoice_hash={digest}")
    assert digest not in out
    assert "AAAAAAAA" in out
    assert "BBBBBBBB" in out
    assert "…" in out


def test_sanitize_log_omits_cert_paths():
    from shared.redact import sanitize_log

    out = sanitize_log("AEAT_CERT_PATH=./certs/test_cert.pem key=/secret/fnmt.key")
    assert "test_cert.pem" not in out
    assert "/secret/fnmt.key" not in out


def test_sanitize_log_strips_api_key_query():
    from shared.redact import sanitize_log

    out = sanitize_log(
        "https://generativelanguage.googleapis.com/v1beta/models/x:generateContent?key=AIza-SHOULD-NOT-LEAK"
    )
    assert "AIza-SHOULD-NOT-LEAK" not in out
    assert "key=" not in out or "[redacted]" in out


def test_request_logging_omits_authorization_and_body(caplog):
    from core_engine.middleware.request_log import RequestLoggingMiddleware

    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware)

    @app.post("/api/v1/fleet/ingest")
    def ingest():
        return {"ok": True}

    token = "leak-me-authorization-header-token"
    nif = "B12345674"
    pem_blob = "-----BEGIN CERTIFICATE-----\nMIIShouldNotLog\n-----END CERTIFICATE-----"
    digest = "C" * 64

    with caplog.at_level(logging.INFO, logger="core_engine.middleware.request_log"):
        client = TestClient(app)
        client.post(
            "/api/v1/fleet/ingest",
            json={
                "issuer_tax_id": nif,
                "invoice_hash": digest,
                "cert_pem": pem_blob,
            },
            headers={"Authorization": f"Bearer {token}"},
        )

    blob = caplog.text
    assert token not in blob
    assert "Authorization" not in blob
    assert nif not in blob
    assert digest not in blob
    assert "MIIShouldNotLog" not in blob
    assert "POST" in blob
    assert "/api/v1/fleet/ingest" in blob


def test_gemini_exception_log_does_not_include_api_key(caplog, monkeypatch):
    import ai_agents.gemini_direct as gemini_direct

    monkeypatch.setenv("GEMINI_API_KEY", "AIza-SHOULD-NOT-LEAK-KEY-VALUE")
    monkeypatch.setattr(gemini_direct, "_load_dotenv", lambda: None)

    class Boom(Exception):
        def __str__(self) -> str:
            return (
                "POST https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini:generateContent?key=AIza-SHOULD-NOT-LEAK-KEY-VALUE failed"
            )

    def _boom(*_a, **_k):
        raise Boom()

    import requests as requests_mod

    monkeypatch.setattr(requests_mod, "post", _boom)
    with caplog.at_level(logging.WARNING):
        gemini_direct.chat_completion(
            [{"role": "user", "content": "hi"}],
            retries=0,
        )
    assert "AIza-SHOULD-NOT-LEAK-KEY-VALUE" not in caplog.text
    assert "key=" not in caplog.text.lower() or "[redacted]" in caplog.text.lower()
