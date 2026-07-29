"""
Higher-level service: validated invoice → hash chain → Facturae → sign → DB.
Uses the same InvoiceService path as FastAPI (no dual volatile store).
"""

from __future__ import annotations

from typing import Tuple

from shared.schemas import InvoiceValidatedData
from core_engine.db.database import SessionLocal
from core_engine.exceptions import HashContinuityError
from core_engine.services.invoice_service import InvoiceService


class InvoiceProcessor:
    @staticmethod
    def process_and_sign(
        data: InvoiceValidatedData, tenant_id: str = "default"
    ) -> Tuple[str, bytes]:
        db = SessionLocal()
        try:
            svc = InvoiceService(db, tenant_id=tenant_id)
            try:
                row, current_hash, xml_content, _qr = svc.create(data)
            except HashContinuityError:
                raise
            signed_ok, _sig, err = svc.sign(row.id)
            if not signed_ok:
                # still return hash; signature may be partial
                return current_hash, xml_content
            refreshed = svc.chain.get_invoice(row.id)
            xml = (refreshed.xml_content or "").encode("utf-8") if refreshed else xml_content
            return current_hash, xml
        finally:
            db.close()
