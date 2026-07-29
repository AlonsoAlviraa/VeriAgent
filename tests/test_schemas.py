import sys
import os
import unittest
from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.schemas import (
    Invoice,
    InvoiceInput,
    Customer,
    Address,
    TaxLine,
    InvoiceLine,
)

# Valid Spanish fiscal IDs (check-digit verified)
ISSUER_CIF = "A11111119"
CUSTOMER_CIF = "B12345674"


class TestSchemas(unittest.TestCase):
    def test_invoice_creation(self):
        customer = Customer(
            tax_id=CUSTOMER_CIF,
            name="Test Corp",
            address=Address(street="Calle Test 1", city="Madrid", postal_code="28000")
        )
        
        lines = [
            InvoiceLine(description="Service 1", quantity=1, unit_price=100.0, total_amount=100.0)
        ]
        
        taxes = [
            TaxLine(tax_type="IVA", tax_rate=21.0, base_amount=100.0, tax_amount=21.0)
        ]
        
        invoice = Invoice(
            number="001",
            issue_date=date.today(),
            issuer_tax_id=ISSUER_CIF,
            customer=customer,
            lines=lines,
            taxes=taxes,
            total_base=100.0,
            total_tax=21.0,
            total_amount=121.0
        )
        
        self.assertEqual(invoice.number, "001")
        self.assertEqual(invoice.total_amount, 121.0)
        self.assertEqual(invoice.issuer_tax_id, ISSUER_CIF)
        self.assertEqual(invoice.customer.tax_id, CUSTOMER_CIF)

    def test_invoice_input_rejects_bad_issuer_tax_id(self):
        with self.assertRaises(ValidationError) as ctx:
            InvoiceInput(
                number="001",
                issue_date=date.today(),
                issuer_tax_id="B12345678",  # invalid CIF check digit
                customer=Customer(
                    tax_id=CUSTOMER_CIF,
                    name="Ok",
                    address=Address(street="S", city="C", postal_code="28001"),
                ),
                lines=[InvoiceLine(description="x", quantity=1, unit_price=1, total_amount=1)],
                taxes=[TaxLine(tax_rate=0, base_amount=1, tax_amount=0)],
                total_base=1.0,
                total_tax=0.0,
                total_amount=1.0,
            )
        self.assertIn("check-digit", str(ctx.exception).lower())

    def test_customer_tax_id_normalized(self):
        customer = Customer(
            tax_id="  b-123 4567-4 ",
            name="Norm Co",
            address=Address(street="S", city="C", postal_code="28001"),
        )
        self.assertEqual(customer.tax_id, "B12345674")


if __name__ == '__main__':
    unittest.main()
