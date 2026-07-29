"""
Tests de concurrencia / integridad del hash-chain (Sprint 7).

Verifica el contrato de aislamiento del ChainRepository:
- assert_previous devuelve el tip autoritativo.
- Dos creaciones encadenadas respetan el orden (la segunda enlaza la primera).
- Un claimed_previous incorrecto lanza HashContinuityError (409).
- El tip se actualiza atómicamente tras cada creación.

Nota: SQLite no soporta row-lock real (with_for_update es no-op), por lo que
estos tests validan el contrato secuencial; la protección de concurrencia real
se activa en Postgres. Lo dejamos documentado.
"""

from datetime import date

import pytest

from core_engine.db.database import SessionLocal, init_db
from core_engine.exceptions import HashContinuityError
from core_engine.services.chain_repository import ChainRepository
from shared.schemas import Address, Customer, InvoiceInput, InvoiceLine, TaxLine


@pytest.fixture
def repo():
    init_db()
    session = SessionLocal()
    try:
        yield ChainRepository(session, tenant_id="conc-tenant")
    finally:
        session.execute(
            __import__("sqlalchemy").text("DELETE FROM chain_tips")
        )
        session.commit()
        session.close()


def _invoice(series, number, prev=None):
    return InvoiceInput(
        series=series,
        number=number,
        issue_date=date(2026, 1, 15),
        issuer_tax_id="B12345674",
        previous_invoice_hash=prev,
        customer=Customer(
            tax_id="A11111119",
            name="C",
            address=Address(street="S", city="M", postal_code="28001"),
        ),
        lines=[InvoiceLine(description="x", quantity=1, unit_price=100.0, total_amount=100.0)],
        taxes=[],
        total_base=100.0,
        total_tax=0.0,
        total_amount=100.0,
    )


class TestChainConcurrencyContract:
    def test_first_invoice_has_empty_tip(self, repo):
        tip = repo.get_tip("B12345674")
        assert tip == ""

    def test_assert_previous_omitted_uses_tip(self, repo):
        # Sin claim → usa tip (vacío al inicio).
        assert repo.assert_previous("B12345674", None) == ""
        assert repo.assert_previous("B12345674", "") == ""

    def test_assert_previous_rejects_wrong_claim(self, repo):
        repo.set_tip("B12345674", "HASH_A")
        with pytest.raises(HashContinuityError) as exc:
            repo.assert_previous("B12345674", "WRONG")
        assert exc.value.expected_hash == "HASH_A"
        assert exc.value.received_hash == "WRONG"

    def test_assert_previous_accepts_correct_claim(self, repo):
        repo.set_tip("B12345674", "HASH_A")
        assert repo.assert_previous("B12345674", "HASH_A") == "HASH_A"

    def test_chained_creation_preserves_order(self, repo):
        # Simulamos el flujo de InvoiceService a nivel de chain tips.
        tip0 = repo.assert_previous("B12345674", None)  # ""
        repo.set_tip("B12345674", "HASH_1")
        tip1 = repo.assert_previous("B12345674", "HASH_1")  # debe ser HASH_1
        assert tip1 == "HASH_1"
        repo.set_tip("B12345674", "HASH_2")
        tip2 = repo.assert_previous("B12345674", "HASH_2")
        assert tip2 == "HASH_2"

    def test_tenant_isolation_between_issuers(self, repo):
        # Dos emisores distintos tienen tips independientes.
        repo.set_tip("B12345674", "HASH_B")
        repo.set_tip("A11111119", "HASH_A")
        assert repo.get_tip("B12345674") == "HASH_B"
        assert repo.get_tip("A11111119") == "HASH_A"
        # El tip de uno no es válido como claim del otro.
        with pytest.raises(HashContinuityError):
            repo.assert_previous("B12345674", "HASH_A")
