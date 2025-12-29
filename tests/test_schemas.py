import sys
import os
import unittest
from datetime import date
from uuid import uuid4

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.schemas import Invoice, Customer, Address, TaxLine, InvoiceLine

class TestSchemas(unittest.TestCase):
    def test_invoice_creation(self):
        customer = Customer(
            tax_id="B12345678",
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
            issuer_tax_id="A11122233",
            customer=customer,
            lines=lines,
            taxes=taxes,
            total_base=100.0,
            total_tax=21.0,
            total_amount=121.0
        )
        
        self.assertEqual(invoice.number, "001")
        self.assertEqual(invoice.total_amount, 121.0)
        print("Invoice created successfully!")

if __name__ == '__main__':
    unittest.main()
