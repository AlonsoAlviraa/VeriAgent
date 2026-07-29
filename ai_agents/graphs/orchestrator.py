"""
[AGENT-009 / PUX-04] LangGraph-style orchestrator wired to core_engine create/sign.
Works without LangGraph installed (callable node graph).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, Optional

from shared.schemas import Address, Customer, InvoiceInput, InvoiceLine, TaxLine
from core_engine.db.database import SessionLocal
from core_engine.services.invoice_service import InvoiceService
from core_engine.exceptions import HashContinuityError


@dataclass
class OrchestratorState:
    tenant_id: str = "default"
    raw_text: str = ""
    invoice_input: Optional[dict] = None
    invoice_id: Optional[str] = None
    invoice_hash: Optional[str] = None
    status: str = "NEW"
    error: Optional[str] = None
    events: list = field(default_factory=list)


def extract_node(state: OrchestratorState) -> OrchestratorState:
    """Minimal extractor: if FACTURA present, build a valid InvoiceInput dict."""
    if "FACTURA" not in state.raw_text.upper() and not state.invoice_input:
        state.error = "No Invoice detected"
        state.status = "ERROR"
        return state
    if state.invoice_input:
        return state
    state.invoice_input = {
        "series": "ORCH",
        "number": "1",
        "issue_date": date.today().isoformat(),
        "issuer_tax_id": "B12345674",
        "customer": {
            "tax_id": "A11111119",
            "name": "Orch Client",
            "address": {
                "street": "Calle 1",
                "city": "Madrid",
                "postal_code": "28001",
                "country": "ES",
            },
        },
        "lines": [
            {
                "description": "Servicio",
                "quantity": 1,
                "unit_price": 100.0,
                "total_amount": 100.0,
            }
        ],
        "taxes": [{"tax_rate": 21.0, "base_amount": 100.0, "tax_amount": 21.0}],
        "total_base": 100.0,
        "total_tax": 21.0,
        "total_amount": 121.0,
    }
    state.status = "EXTRACTED"
    state.events.append("extract")
    return state


def create_node(state: OrchestratorState) -> OrchestratorState:
    if state.error or not state.invoice_input:
        return state
    data = dict(state.invoice_input)
    if isinstance(data.get("issue_date"), str):
        data["issue_date"] = date.fromisoformat(data["issue_date"])
    inv = InvoiceInput(**data)
    db = SessionLocal()
    try:
        svc = InvoiceService(db, tenant_id=state.tenant_id)
        row, h, _xml, _qr = svc.create(inv)
        state.invoice_id = row.id
        state.invoice_hash = h
        state.status = "VALIDATED"
        state.events.append("create")
    except HashContinuityError as exc:
        state.error = f"HASH_CHAIN_BROKEN:{exc.expected_hash}:{exc.received_hash}"
        state.status = "ERROR"
    finally:
        db.close()
    return state


def sign_node(state: OrchestratorState) -> OrchestratorState:
    if state.error or not state.invoice_id:
        return state
    db = SessionLocal()
    try:
        svc = InvoiceService(db, tenant_id=state.tenant_id)
        ok, sig, err = svc.sign(state.invoice_id)
        if ok:
            state.status = "SIGNED"
            state.events.append("sign")
        else:
            state.error = err
            state.status = "ERROR"
    finally:
        db.close()
    return state


def run_orchestrator(
    raw_text: str = "FACTURA demo",
    tenant_id: str = "default",
    invoice_input: Optional[dict] = None,
) -> OrchestratorState:
    state = OrchestratorState(
        tenant_id=tenant_id, raw_text=raw_text, invoice_input=invoice_input
    )
    state = extract_node(state)
    state = create_node(state)
    state = sign_node(state)
    return state
