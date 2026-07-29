"""
DB-backed VeriFactu hash chain repository (COMP-02 / MT-02).

Public create/sign path must use this module — not process-level dicts.
Chain tips are scoped by (tenant_id, issuer_tax_id).
"""

from __future__ import annotations

from typing import Optional, Tuple

from sqlalchemy.orm import Session

from core_engine.db.models import ChainTipModel, InvoiceModel
from core_engine.exceptions import HashContinuityError


class ChainRepository:
    def __init__(self, db: Session, tenant_id: str = "default"):
        self.db = db
        self.tenant_id = tenant_id

    def get_tip(self, issuer_tax_id: str, *, for_update: bool = False) -> str:
        q = self.db.query(ChainTipModel).filter(
            ChainTipModel.tenant_id == self.tenant_id,
            ChainTipModel.issuer_tax_id == issuer_tax_id,
        )
        # with_for_update works on Postgres; SQLite ignores / may no-op
        if for_update:
            try:
                q = q.with_for_update()
            except Exception:
                pass
        row = q.one_or_none()
        return row.tip_hash if row else ""

    def assert_previous(
        self, issuer_tax_id: str, claimed_previous: Optional[str]
    ) -> str:
        """
        Return the authoritative tip. If client claimed a previous hash and it
        differs from the tip, raise HashContinuityError (HTTP 409 at API).
        Omitted claim → use DB tip (or empty for first invoice).
        """
        tip = self.get_tip(issuer_tax_id, for_update=True)
        if claimed_previous is None or claimed_previous == "":
            return tip
        if claimed_previous != tip:
            raise HashContinuityError(
                message="Hash chain broken: claimed previous does not match tip",
                expected_hash=tip,
                received_hash=claimed_previous,
            )
        return tip

    def set_tip(self, issuer_tax_id: str, new_hash: str) -> None:
        row = (
            self.db.query(ChainTipModel)
            .filter(
                ChainTipModel.tenant_id == self.tenant_id,
                ChainTipModel.issuer_tax_id == issuer_tax_id,
            )
            .one_or_none()
        )
        if row is None:
            self.db.add(
                ChainTipModel(
                    tenant_id=self.tenant_id,
                    issuer_tax_id=issuer_tax_id,
                    tip_hash=new_hash,
                )
            )
        else:
            row.tip_hash = new_hash
        self.db.flush()

    def get_invoice(self, invoice_id: str) -> Optional[InvoiceModel]:
        return (
            self.db.query(InvoiceModel)
            .filter(
                InvoiceModel.id == str(invoice_id),
                InvoiceModel.tenant_id == self.tenant_id,
            )
            .one_or_none()
        )

    def list_by_issuer(self, issuer_tax_id: str) -> list[InvoiceModel]:
        return (
            self.db.query(InvoiceModel)
            .filter(
                InvoiceModel.tenant_id == self.tenant_id,
                InvoiceModel.issuer_tax_id == issuer_tax_id,
            )
            .order_by(InvoiceModel.created_at.asc())
            .all()
        )
