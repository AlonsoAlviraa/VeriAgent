"""Shared invoice create/sign service used by FastAPI and agents (no dual path)."""

from __future__ import annotations

import hashlib
import uuid
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from core_engine.crypto.hashing import VeriFactuHasher
from core_engine.db.models import InvoiceModel
from core_engine.exceptions import HashContinuityError
from core_engine.services.chain_repository import ChainRepository
from core_engine.services.facturae import FacturaeService
from core_engine.services.webhooks import WebhookEmitter
from shared.schemas import Invoice, InvoiceInput, InvoiceStatus


class InvoiceService:
    def __init__(self, db: Session, tenant_id: str = "default"):
        self.db = db
        self.tenant_id = tenant_id
        self.chain = ChainRepository(db, tenant_id=tenant_id)
        self.webhooks = WebhookEmitter(db)

    def create(self, data: InvoiceInput) -> Tuple[InvoiceModel, str, bytes, str]:
        tip = self.chain.assert_previous(
            data.issuer_tax_id, data.previous_invoice_hash
        )
        payload = data.model_dump()
        payload["previous_invoice_hash"] = tip or None
        invoice = Invoice(**payload)
        current_hash = VeriFactuHasher.calculate_fingerprint(invoice, tip)
        xml_content = FacturaeService.generate_xml(invoice)
        qr = FacturaeService.build_qr_payload(invoice, current_hash)

        row = InvoiceModel(
            id=str(invoice.id),
            tenant_id=self.tenant_id,
            series=invoice.series,
            number=invoice.number,
            issue_date=invoice.issue_date,
            issuer_tax_id=invoice.issuer_tax_id,
            customer_tax_id=invoice.customer.tax_id,
            customer_name=invoice.customer.name,
            total_base=invoice.total_base,
            total_tax=invoice.total_tax,
            total_amount=invoice.total_amount,
            invoice_hash=current_hash,
            previous_invoice_hash=tip or None,
            xml_content=xml_content.decode("utf-8"),
            qr_payload=qr,
            status=InvoiceStatus.VALIDATED.value,
        )
        self.db.add(row)
        self.chain.set_tip(invoice.issuer_tax_id, current_hash)
        self.db.commit()
        self.db.refresh(row)
        self.webhooks.emit(
            "invoice.validated",
            {
                "invoice_id": row.id,
                "tenant_id": self.tenant_id,
                "status": row.status,
                "invoice_hash": current_hash,
            },
        )
        return row, current_hash, xml_content, qr

    def sign(self, invoice_id: str) -> Tuple[bool, Optional[str], Optional[str]]:
        row = self.chain.get_invoice(str(invoice_id))
        if row is None:
            return False, None, "Invoice not found"
        if row.status != InvoiceStatus.VALIDATED.value:
            return (
                False,
                None,
                f"Invoice is in status {row.status}, expected VALIDATED",
            )
        xml = (row.xml_content or "").encode("utf-8")
        signature_hash = hashlib.sha256(xml).hexdigest().upper()
        row.status = InvoiceStatus.SIGNED.value
        row.signature = signature_hash.encode("utf-8")
        self.db.commit()
        self.webhooks.emit(
            "invoice.signed",
            {
                "invoice_id": row.id,
                "tenant_id": self.tenant_id,
                "status": row.status,
                "signature_hash": signature_hash,
            },
        )
        return True, signature_hash, None

    def update_status(self, invoice_id: str, status: str, **extra) -> Optional[InvoiceModel]:
        row = self.chain.get_invoice(str(invoice_id))
        if row is None:
            return None
        row.status = status
        if "aeat_csv" in extra:
            row.aeat_csv = extra["aeat_csv"]
        self.db.commit()
        self.webhooks.emit(
            f"invoice.{status.lower()}",
            {"invoice_id": row.id, "tenant_id": self.tenant_id, "status": status, **extra},
        )
        return row
