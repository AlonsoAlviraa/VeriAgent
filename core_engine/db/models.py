from sqlalchemy import Column, String, Date, Numeric, Text, LargeBinary, TIMESTAMP, ForeignKey, Index
from sqlalchemy.sql import func
import uuid

from .database import Base

# Lifecycle statuses aligned across DDL / ORM / API / AEAT audit (COMP-03)
INVOICE_STATUSES = (
    "PENDING",
    "VALIDATED",
    "SIGNED",
    "SENT",
    "SENT_OK",
    "REJECTED_AEAT",
    "ERROR",
)


class InvoiceModel(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_tenant_issuer", "tenant_id", "issuer_tax_id"),
        Index("ix_invoices_tenant_status", "tenant_id", "status"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True, default="default")
    series = Column(String(10), nullable=False)
    number = Column(String(50), nullable=False)
    issue_date = Column(Date, nullable=False)

    issuer_tax_id = Column(String(20), nullable=False)
    customer_tax_id = Column(String(20), nullable=False)
    customer_name = Column(String(255), nullable=False)

    total_base = Column(Numeric(15, 2), nullable=False)
    total_tax = Column(Numeric(15, 2), nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), server_default="EUR")

    invoice_hash = Column(String(64), nullable=False)
    previous_invoice_hash = Column(String(64))

    xml_content = Column(Text)
    signature = Column(LargeBinary)
    qr_payload = Column(Text)
    status = Column(String(20), server_default="PENDING")
    aeat_csv = Column(String(50))

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False, index=True, default="default")
    invoice_id = Column(String(36), ForeignKey("invoices.id"), nullable=True)
    action = Column(String(50), nullable=False)
    actor = Column(String(100), nullable=False)
    details = Column(Text)
    previous_log_hash = Column(String(64))
    log_hash = Column(String(64), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class ChainTipModel(Base):
    """Durable tip of hash chain per (tenant_id, issuer_tax_id) — COMP-02 / MT-02."""

    __tablename__ = "chain_tips"
    __table_args__ = (
        Index("uq_chain_tip_tenant_issuer", "tenant_id", "issuer_tax_id", unique=True),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), nullable=False)
    issuer_tax_id = Column(String(20), nullable=False)
    tip_hash = Column(String(64), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
