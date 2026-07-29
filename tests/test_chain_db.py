"""COMP-02 / PUX-01: durable DB hash chain + 409 on mismatch."""

from __future__ import annotations

from datetime import date

import pytest
from fastapi.testclient import TestClient

from core_engine.exceptions import HashContinuityError
from core_engine.services.invoice_service import InvoiceService
from shared.schemas import Address, Customer, InvoiceInput, InvoiceLine, TaxLine


def _inv(number: str, previous=None) -> InvoiceInput:
    return InvoiceInput(
        series="C",
        number=number,
        issue_date=date.today(),
        issuer_tax_id="B12345674",
        previous_invoice_hash=previous,
        customer=Customer(
            tax_id="A11111119",
            name="Cliente",
            address=Address(street="S", city="M", postal_code="28001"),
        ),
        lines=[
            InvoiceLine(
                description="x", quantity=1, unit_price=10.0, total_amount=10.0
            )
        ],
        taxes=[TaxLine(tax_rate=0.0, base_amount=10.0, tax_amount=0.0)],
        total_base=10.0,
        total_tax=0.0,
        total_amount=10.0,
    )


def test_create_invoice_persists_to_db(db_session):
    svc = InvoiceService(db_session, tenant_id="t1")
    row, h1, xml, qr = svc.create(_inv("1"))
    assert row.id
    assert h1
    assert b"Facturae" in xml or b"VeriFactu" in xml or "Facturae" in xml.decode()
    assert qr and "nif=" in qr
    tip = svc.chain.get_tip("B12345674")
    assert tip == h1


def test_create_invoice_uses_db_tip_when_client_omits_previous(db_session):
    svc = InvoiceService(db_session, tenant_id="t1")
    _, h1, _, _ = svc.create(_inv("1"))
    row2, h2, _, _ = svc.create(_inv("2", previous=None))
    assert row2.previous_invoice_hash == h1
    assert h2 != h1


def test_create_invoice_409_on_previous_hash_mismatch(db_session):
    svc = InvoiceService(db_session, tenant_id="t1")
    svc.create(_inv("1"))
    with pytest.raises(HashContinuityError) as exc:
        svc.create(_inv("2", previous="DEADBEEF" * 8))
    assert exc.value.expected_hash


def test_chain_survives_new_session(db_session):
    svc = InvoiceService(db_session, tenant_id="t1")
    _, h1, _, _ = svc.create(_inv("1"))
    # New session on the same bind (process restart simulation for sqlite)
    Session = db_session.__class__
    s2 = Session(bind=db_session.get_bind())
    try:
        svc2 = InvoiceService(s2, tenant_id="t1")
        assert svc2.chain.get_tip("B12345674") == h1
    finally:
        s2.close()


def test_api_create_and_409(db_session):
    from core_engine import main as mainmod

    def _get_db():
        try:
            yield db_session
        finally:
            pass

    mainmod.app.dependency_overrides[mainmod.get_db] = _get_db
    try:
        client = TestClient(mainmod.app)
        payload = _inv("10").model_dump(mode="json")
        r1 = client.post(
            "/api/v1/invoices",
            json=payload,
            headers={"X-Tenant-Id": "api-t", "X-Roles": "issuer"},
        )
        assert r1.status_code == 200, r1.text
        body = r1.json()
        h1 = body["invoice_hash"]
        bad = dict(payload)
        bad["number"] = "11"
        bad["previous_invoice_hash"] = "00" * 32
        r2 = client.post(
            "/api/v1/invoices",
            json=bad,
            headers={"X-Tenant-Id": "api-t", "X-Roles": "issuer"},
        )
        assert r2.status_code == 409
        detail = r2.json()["detail"]
        assert detail["error_code"] == "HASH_CHAIN_BROKEN"
        assert h1
    finally:
        mainmod.app.dependency_overrides.clear()
