"""Thin tools. Hashing and XML stay in core_engine; agents only call these."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ai_agents.adk import gateway, memory as memory_bank
from ai_agents.normative.corpus import NormativeCorpus
from core_engine.services.invoice_service import InvoiceService
from core_engine.services.ocr import OCRService
from core_engine.validators.fiscal_id import FiscalIdError, validate_fiscal_id
from shared.schemas import InvoiceInput


def extract_text(file_path: str) -> str:
    return OCRService.extract_text(file_path)


def search_normative(query: str, limit: int = 3) -> list:
    corpus = NormativeCorpus()
    corpus.load_seeds()
    q = (query or "").lower()
    hits = []
    for doc in corpus.documents:
        blob = f"{doc.title} {doc.text} {' '.join(doc.topics)}".lower()
        if not q or any(tok in blob for tok in q.split()):
            hits.append(
                {
                    "id": doc.id,
                    "title": doc.title,
                    "source": doc.source,
                    "excerpt": doc.text[:280],
                }
            )
        if len(hits) >= limit:
            break
    if not hits:
        hits = [
            {
                "id": d.id,
                "title": d.title,
                "source": d.source,
                "excerpt": d.text[:280],
            }
            for d in corpus.documents[:limit]
        ]
    return hits


def create_and_sign(
    db: Session,
    tenant_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    data = dict(payload)
    if isinstance(data.get("issue_date"), str):
        data["issue_date"] = date.fromisoformat(data["issue_date"])
    inv = InvoiceInput(**data)
    svc = InvoiceService(db, tenant_id=tenant_id)
    row, current_hash, _xml, _qr = svc.create(inv)
    ok, sig, err = svc.sign(row.id)
    return {
        "invoice_id": row.id,
        "invoice_hash": current_hash,
        "signed": ok,
        "signature_hash": sig,
        "error": err,
        "status": row.status,
    }


def nif_status(value: str) -> tuple[bool, str]:
    try:
        return True, validate_fiscal_id(value)
    except FiscalIdError as exc:
        return False, str(exc)


def memory_get(db: Session, tenant_id: str, key: str) -> Optional[str]:
    return memory_bank.read(db, tenant_id, key)


def memory_put(db: Session, tenant_id: str, key: str, value: str) -> None:
    memory_bank.write(db, tenant_id, key, value)


def check_tool(roles, tool: str) -> dict:
    d = gateway.allows(tool, roles)
    return {"allowed": d.allowed, "reason": d.reason, "tool": tool}
