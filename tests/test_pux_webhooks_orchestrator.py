"""PUX-03…05: webhooks, orchestrator, org switcher presence."""

from pathlib import Path

from core_engine.services.webhooks import WebhookEmitter, clear_event_log, get_event_log
from ai_agents.graphs.orchestrator import run_orchestrator


def test_webhook_emit_on_lifecycle(db_session):
    clear_event_log()
    from datetime import date
    from core_engine.services.invoice_service import InvoiceService
    from shared.schemas import Address, Customer, InvoiceInput, InvoiceLine, TaxLine

    svc = InvoiceService(db_session, tenant_id="wh-1")
    inv = InvoiceInput(
        series="W",
        number="1",
        issue_date=date.today(),
        issuer_tax_id="B12345674",
        customer=Customer(
            tax_id="A11111119",
            name="C",
            address=Address(street="S", city="M", postal_code="28001"),
        ),
        lines=[
            InvoiceLine(
                description="x", quantity=1, unit_price=1.0, total_amount=1.0
            )
        ],
        taxes=[TaxLine(tax_rate=0.0, base_amount=1.0, tax_amount=0.0)],
        total_base=1.0,
        total_tax=0.0,
        total_amount=1.0,
    )
    row, _, _, _ = svc.create(inv)
    svc.sign(row.id)
    events = [e["event"] for e in get_event_log()]
    assert "invoice.validated" in events
    assert "invoice.signed" in events


def test_orchestrator_invokes_core_engine(db_session, monkeypatch):
    class _Sess:
        def __call__(self):
            return db_session

    # SessionLocal() returns the fixture session; skip close in nodes
    real_close = db_session.close
    db_session.close = lambda: None  # type: ignore
    monkeypatch.setattr("ai_agents.graphs.orchestrator.SessionLocal", _Sess())
    try:
        state = run_orchestrator("FACTURA test", tenant_id="orch-1")
        assert state.error is None, state.error
        assert state.invoice_id
        assert state.invoice_hash
        assert "create" in state.events
        assert "sign" in state.events
        assert state.status == "SIGNED"
    finally:
        db_session.close = real_close  # type: ignore


def test_org_switcher_component_present():
    root = Path(__file__).resolve().parents[1]
    path = root / "frontend" / "src" / "components" / "org" / "org-switcher.tsx"
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "OrgSwitcher" in text
    assert "data-testid=\"org-switcher\"" in text
    assert "ChainIntegrityBadge" in text
    page = (root / "frontend" / "src" / "app" / "page.tsx").read_text(encoding="utf-8")
    assert "OrgSwitcher" in page


def test_status_enum_alignment():
    from shared.schemas import InvoiceStatus
    from core_engine.db.models import INVOICE_STATUSES

    for s in InvoiceStatus:
        assert s.value in INVOICE_STATUSES
