from datetime import date
from typing import List, Optional
from uuid import UUID, uuid4
from enum import Enum

from pydantic import BaseModel, Field, field_validator

# ============================================
# ENUMS
# ============================================
class InvoiceStatus(str, Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    SIGNED = "SIGNED"
    SENT = "SENT"
    ERROR = "ERROR"

# ============================================
# SHARED MODELS (Input/Output Contracts)
# ============================================

class Address(BaseModel):
    street: str
    city: str
    postal_code: str
    country: str = "ES"

class Customer(BaseModel):
    """Represents a client/customer entity for the invoice."""
    tax_id: str = Field(..., description="NIF/CIF of the customer", min_length=8, max_length=20)
    name: str = Field(..., description="Legal name of the customer")
    address: Address
    email: Optional[str] = None  # Changed from EmailStr to avoid dependency

class TaxLine(BaseModel):
    """Represents a tax breakdown line (e.g., IVA 21%)."""
    tax_type: str = Field(default="IVA", description="Type of tax")
    tax_rate: float = Field(..., description="Tax rate percentage (e.g., 21.0)")
    base_amount: float = Field(..., description="Base amount subject to tax")
    tax_amount: float = Field(..., description="Calculated tax amount")

class InvoiceLine(BaseModel):
    """Represents a line item in the invoice."""
    description: str
    quantity: float
    unit_price: float
    total_amount: float

# ============================================
# INVOICE SCHEMA (Main Contract)
# ============================================

class InvoiceInput(BaseModel):
    """
    INPUT Contract: What the AI Agent sends to Core Engine.
    Used by Team B to structure data for processing.
    """
    series: str = Field(default="F24", description="Invoice series")
    number: str = Field(..., description="Invoice sequence number")
    issue_date: date = Field(..., description="Date of issuance")
    
    issuer_tax_id: str = Field(..., description="NIF of the issuer")
    customer: Customer
    
    lines: List[InvoiceLine]
    taxes: List[TaxLine]
    
    total_base: float = Field(..., description="Sum of all base amounts")
    total_tax: float = Field(..., description="Sum of all tax amounts")
    total_amount: float = Field(..., description="Grand total (Base + Tax)")
    
    @field_validator('total_amount')
    @classmethod
    def validate_total(cls, v, info):
        base = info.data.get('total_base', 0)
        tax = info.data.get('total_tax', 0)
        expected = base + tax
        if abs(v - expected) > 0.01:
            raise ValueError(f'total_amount ({v}) must equal total_base + total_tax ({expected})')
        return v

class InvoiceOutput(BaseModel):
    """
    OUTPUT Contract: What Core Engine returns to AI Agent.
    """
    id: UUID
    series: str
    number: str
    status: InvoiceStatus
    invoice_hash: str
    previous_invoice_hash: Optional[str] = None
    xml_preview: Optional[str] = None # First 500 chars
    message: str = "OK"

class SignRequest(BaseModel):
    """Request to sign an invoice (Team B -> Team A)."""
    invoice_id: UUID
    
class SignResponse(BaseModel):
    """Response after signing (Team A -> Team B)."""
    invoice_id: UUID
    signed: bool
    signature_hash: Optional[str] = None
    error: Optional[str] = None

class ErrorResponse(BaseModel):
    """Standard error response."""
    error_code: str
    message: str
    details: Optional[dict] = None

# ============================================
# LEGACY COMPATIBILITY (Keep existing tests working)
# ============================================
class Invoice(InvoiceInput):
    """Full Invoice model for internal use."""
    id: UUID = Field(default_factory=uuid4, description="Internal unique identifier")
    currency: str = Field(default="EUR", description="ISO 4217 Currency Code")
    previous_invoice_hash: Optional[str] = Field(None, description="Hash of the previous invoice for chaining")

    class Config:
        json_schema_extra = {
            "example": {
                "series": "F24",
                "number": "001",
                "issue_date": "2024-01-15",
                "issuer_tax_id": "B12345678",
                "customer": {
                    "tax_id": "A98765432",
                    "name": "Empresa Cliente S.L.",
                    "address": {
                        "street": "Calle Mayor 1",
                        "city": "Madrid",
                        "postal_code": "28001"
                    }
                },
                "lines": [
                    {"description": "Consultoría", "quantity": 10, "unit_price": 50.0, "total_amount": 500.0}
                ],
                "taxes": [
                    {"tax_rate": 21.0, "base_amount": 500.0, "tax_amount": 105.0}
                ],
                "total_base": 500.0,
                "total_tax": 105.0,
                "total_amount": 605.0
            }
        }
