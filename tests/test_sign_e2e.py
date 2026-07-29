"""
[CORE-009 E2E] Flujo completo create → sign → estado SIGNED.

Verifica el contrato de fin a fin del InvoiceService (el endpoint /internal/sign
lo usa internamente) y la emisión de webhooks del ciclo de vida, sin red ni
certificados reales.
"""

from datetime import date

import pytest

from core_engine.db.database import SessionLocal, init_db
from core_engine.services.invoice_service import InvoiceService
from shared.schemas import Address, Customer, InvoiceInput, InvoiceLine, TaxLine


@pytest.fixture
def db():
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        # Limpieza minimal: chain_tips e invoices.
        for tbl in ("chain_tips", "invoices"):
            session.execute(
                __import__("sqlalchemy").text(f"DELETE FROM {tbl}")
            )
        session.commit()
        session.close()


def _valid_invoice(series="E2E", number="1"):
    return InvoiceInput(
        series=series,
        number=number,
        issue_date=date(2026, 1, 15),
        issuer_tax_id="B12345674",
        customer=Customer(
            tax_id="A11111119",
            name="Cliente E2E",
            address=Address(street="S", city="M", postal_code="28001"),
        ),
        lines=[InvoiceLine(description="Serv", quantity=1, unit_price=100.0, total_amount=100.0)],
        taxes=[TaxLine(tax_rate=21.0, base_amount=100.0, tax_amount=21.0)],
        total_base=100.0,
        total_tax=21.0,
        total_amount=121.0,
    )


class TestCreateSignFlow:
    def test_create_then_sign_yields_signature_hash(self, db):
        svc = InvoiceService(db, tenant_id="e2e-tenant")
        row, current_hash, xml, qr = svc.create(_valid_invoice())

        assert row.status == "VALIDATED"
        assert len(current_hash) == 64
        assert b"Facturae" in xml if isinstance(xml, bytes) else "Facturae" in xml
        assert "huella=" in qr

        # Firmar la factura creada.
        ok, sig_hash, err = svc.sign(str(row.id))
        assert ok is True
        assert err is None
        assert len(sig_hash) == 64  # signature_hash = sha256(xml)

        db.refresh(row)
        assert row.status == "SIGNED"
        assert row.signature is not None

    def test_sign_requires_validated_status(self, db):
        svc = InvoiceService(db, tenant_id="e2e-tenant")
        row, _, _, _ = svc.create(_valid_invoice())
        svc.sign(str(row.id))  # → SIGNED
        # Intentar firmar de nuevo → debe fallar (ya está SIGNED).
        ok, sig, err = svc.sign(str(row.id))
        assert ok is False
        assert "SIGNED" in (err or "")

    def test_sign_unknown_invoice_returns_error(self, db):
        svc = InvoiceService(db, tenant_id="e2e-tenant")
        ok, sig, err = svc.sign("nonexistent-uuid")
        assert ok is False
        assert err == "Invoice not found"

    def test_webhook_emitted_on_validated_and_signed(self, db):
        from core_engine.services.webhooks import clear_event_log, get_event_log

        clear_event_log()
        svc = InvoiceService(db, tenant_id="e2e-tenant")
        row, _, _, _ = svc.create(_valid_invoice())
        svc.sign(str(row.id))

        events = [e["event"] for e in get_event_log()]
        assert "invoice.validated" in events
        assert "invoice.signed" in events

    def test_chain_continuity_second_invoice_links_first(self, db):
        svc = InvoiceService(db, tenant_id="e2e-tenant")
        row1, hash1, _, _ = svc.create(_valid_invoice(series="CH", number="1"))
        # Segunda factura encadenada con el hash anterior.
        inv2 = _valid_invoice(series="CH", number="2")
        inv2.previous_invoice_hash = hash1
        row2, hash2, _, _ = svc.create(inv2)

        assert row2.previous_invoice_hash == hash1
        assert hash2 != hash1
