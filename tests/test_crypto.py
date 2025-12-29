import sys
import os
import unittest
from datetime import date

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.schemas import Invoice, Customer, Address
from core_engine.services.crypto import VeriFactuCrypto

class TestCrypto(unittest.TestCase):
    def test_chaining_hash(self):
        # Invoice 1
        inv1 = Invoice(
            number="001", series="F25",
            issue_date=date(2025, 1, 1),
            issuer_tax_id="A11111111",
            customer=Customer(tax_id="B22", name="C", address=Address(street="S", city="C", postal_code="00")),
            lines=[], taxes=[], total_base=100, total_tax=21, total_amount=121
        )
        
        hash1 = VeriFactuCrypto.calculate_invoice_fingerprint(inv1, previous_hash="")
        self.assertTrue(len(hash1) == 64) # SHA256 is 64 hex chars
        
        # Invoice 2 (Chained)
        inv2 = Invoice(
            number="002", series="F25",
            issue_date=date(2025, 1, 2),
            issuer_tax_id="A11111111",
            customer=Customer(tax_id="B22", name="C", address=Address(street="S", city="C", postal_code="00")),
            lines=[], taxes=[], total_base=200, total_tax=42, total_amount=242
        )
        
        hash2 = VeriFactuCrypto.calculate_invoice_fingerprint(inv2, previous_hash=hash1)
        self.assertNotEqual(hash1, hash2)
        
        print(f"Hash 1: {hash1}")
        print(f"Hash 2 (Chained): {hash2}")

if __name__ == '__main__':
    unittest.main()
