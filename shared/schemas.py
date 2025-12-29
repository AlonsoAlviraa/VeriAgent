from datetime import date
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field, field_validator

class Address(BaseModel):
    street: str
    city: str
    postal_code: str
    country: str = "ES"

class Customer(BaseModel):
    """Represents a client/customer entity for the invoice."""
    tax_id: str = Field(..., description="NIF/CIF of the customer")
    name: str = Field(..., description="Legal name of the customer")
    address: Address
    email: Optional[EmailStr] = None

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

class Invoice(BaseModel):
    """
    Main Invoice Model.
    Represents the structured data comprising a valid invoice for VeriFactu.
    """
    id: UUID = Field(default_factory=uuid4, description="Internal unique identifier")
    series: str = Field(default="F24", description="Invoice series")
    number: str = Field(..., description="Invoice sequence number")
    
    issue_date: date = Field(..., description="Date of issuance")
    due_date: Optional[date] = None
    
    issuer_tax_id: str = Field(..., description="NIF of the issuer")
    customer: Customer
    
    lines: List[InvoiceLine]
    taxes: List[TaxLine]
    
    total_base: float = Field(..., description="Sum of all base amounts")
    total_tax: float = Field(..., description="Sum of all tax amounts")
    total_amount: float = Field(..., description="Grand total (Base + Tax)")
    
    currency: str = Field(default="EUR", description="ISO 4217 Currency Code")
    
    # Placeholder for VeriFactu specific fields
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
