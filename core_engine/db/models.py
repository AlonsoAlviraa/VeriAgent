from sqlalchemy import Column, String, Date, Numeric, Text, LargeBinary, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from .database import Base

class InvoiceModel(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    series = Column(String(10), nullable=False)
    number = Column(String(50), nullable=False)
    issue_date = Column(Date, nullable=False)
    
    issuer_tax_id = Column(String(20), nullable=False)
    customer_tax_id = Column(String(20), nullable=False)
    customer_name = Column(String(255), nullable=False)
    
    total_base = Column(Numeric(15, 2), nullable=False)
    total_tax = Column(Numeric(15, 2), nullable=False)
    total_amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), server_default='EUR')
    
    invoice_hash = Column(String(64), nullable=False)
    previous_invoice_hash = Column(String(64))
    
    xml_content = Column(Text)
    signature = Column(LargeBinary)
    status = Column(String(20), server_default='PENDING')
    aeat_csv = Column(String(50))  # Codigo Seguro de Verificacion from AEAT
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

