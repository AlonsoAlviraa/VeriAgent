"""HTTP E2E: committed fixtures through POST /fleet/ingest with the model skipped."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from ai_agents.adk.consult import consult, skip_reason
from core_engine.db.models import InvoiceModel
from core_engine.main import app, get_db

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "demo" / "fixtures"
HEADERS = {
    "X-Tenant-Id": "default",
    "X-User-Id": "judge",
    "X-Roles": "issuer",
}


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_skip_helper_is_skip_llm_token():
    assert skip_reason() == "skip_llm"
    out = consult(redacted_invoice="x", memory={}, auditor_draft="SIGNED")
    assert out["invoked"] is False
    assert out["reason"] == "skip_llm"
    assert out["recommendation"] is None


def test_http_e2e_committed_fixtures_skip_llm(db_session):
    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    try:
        client = TestClient(app)

        queued = client.post(
            "/api/v1/fleet/ingest?wait=false",
            json={"invoice": _load_fixture("valid_invoice.json")},
            headers=HEADERS,
        )
        assert queued.status_code == 202
        assert queued.json()["status"] == "QUEUED"
        assert queued.json()["decision"] is None
        run_id = queued.json()["run_id"]

        from ai_agents.adk.queue import execute

        done = execute(run_id, db_session)
        assert done.decision == "SIGNED"
        assert done.signed is True
        assert done.invoice_hash
        got = client.get(f"/api/v1/fleet/runs/{run_id}", headers=HEADERS)
        assert got.status_code == 200
        body = got.json()
        assert body["status"] == "COMPLETED"
        assert body["decision"] == "SIGNED"
        consult_adk = (body.get("adk") or {}).get("consult") or {}
        assert consult_adk.get("invoked") is False
        assert consult_adk.get("reason") == "skip_llm"
        assert db_session.query(InvoiceModel).count() == 1

        math = client.post(
            "/api/v1/fleet/ingest",
            json={"invoice": _load_fixture("math_error.json")},
            headers=HEADERS,
        )
        assert math.status_code == 200
        math_body = math.json()
        assert math_body["decision"] == "ESCALATED"
        assert math_body["signed"] is False
        assert not math_body.get("invoice_hash")
        assert math_body["invoice_id"] is None
        math_consult = (math_body.get("adk") or {}).get("consult") or {}
        assert math_consult.get("invoked") is False
        assert math_consult.get("reason") == "skip_llm"
        assert db_session.query(InvoiceModel).count() == 1

        blocked = client.post(
            "/api/v1/fleet/ingest",
            json={"invoice": _load_fixture("injection.json")},
            headers=HEADERS,
        )
        assert blocked.status_code == 200
        inj_body = blocked.json()
        assert inj_body["decision"] == "BLOCKED"
        assert inj_body["signed"] is False
        assert inj_body["invoice_id"] is None
        # Armor returns before consult; the model is never called on this path.
        inj_consult = (inj_body.get("adk") or {}).get("consult") or {}
        assert inj_consult.get("invoked") in {None, False}
        assert db_session.query(InvoiceModel).count() == 1
    finally:
        app.dependency_overrides.clear()
