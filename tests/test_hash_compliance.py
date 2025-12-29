"""
[TEAM-A] Compliance Unit Tests for Hash Chaining
These tests MUST pass in CI/CD to approve any Pull Request.
"""
import sys
import os
import unittest
from datetime import date

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.schemas import Invoice, Customer, Address
from core_engine.crypto.hashing import VeriFactuHasher

class TestHashChainCompliance(unittest.TestCase):
    """
    5 Mandatory Unit Tests for VeriFactu Compliance
    """
    
    def setUp(self):
        self.customer = Customer(
            tax_id="B99999999",
            name="Test Corp",
            address=Address(street="Test St", city="Madrid", postal_code="28000")
        )
    
    def test_1_deterministic_hash(self):
        """Same invoice data MUST produce same hash."""
        inv = Invoice(
            number="001", series="F25", issue_date=date(2025, 1, 1),
            issuer_tax_id="A11111111", customer=self.customer,
            lines=[], taxes=[], total_base=100, total_tax=21, total_amount=121
        )
        
        hash1 = VeriFactuHasher.calculate_fingerprint(inv, "")
        hash2 = VeriFactuHasher.calculate_fingerprint(inv, "")
        
        self.assertEqual(hash1, hash2)
        print("✓ Test 1: Deterministic hash")
    
    def test_2_different_data_different_hash(self):
        """Different amounts MUST produce different hashes."""
        inv1 = Invoice(
            number="001", series="F25", issue_date=date(2025, 1, 1),
            issuer_tax_id="A11111111", customer=self.customer,
            lines=[], taxes=[], total_base=100, total_tax=21, total_amount=121
        )
        
        inv2 = Invoice(
            number="001", series="F25", issue_date=date(2025, 1, 1),
            issuer_tax_id="A11111111", customer=self.customer,
            lines=[], taxes=[], total_base=100, total_tax=22, total_amount=122  # Different!
        )
        
        hash1 = VeriFactuHasher.calculate_fingerprint(inv1, "")
        hash2 = VeriFactuHasher.calculate_fingerprint(inv2, "")
        
        self.assertNotEqual(hash1, hash2)
        print("✓ Test 2: Different data = different hash")
    
    def test_3_chain_link_validation(self):
        """Hash chain MUST include previous hash."""
        inv1 = Invoice(
            number="001", series="F25", issue_date=date(2025, 1, 1),
            issuer_tax_id="A11111111", customer=self.customer,
            lines=[], taxes=[], total_base=100, total_tax=21, total_amount=121
        )
        
        hash1 = VeriFactuHasher.calculate_fingerprint(inv1, "")
        
        inv2 = Invoice(
            number="002", series="F25", issue_date=date(2025, 1, 2),
            issuer_tax_id="A11111111", customer=self.customer,
            lines=[], taxes=[], total_base=200, total_tax=42, total_amount=242
        )
        
        hash2_correct = VeriFactuHasher.calculate_fingerprint(inv2, hash1)
        hash2_wrong = VeriFactuHasher.calculate_fingerprint(inv2, "WRONG_HASH")
        
        self.assertNotEqual(hash2_correct, hash2_wrong)
        print("✓ Test 3: Chain link validation")
    
    def test_4_validate_chain_function(self):
        """validate_chain MUST return False on tampered hash."""
        inv = Invoice(
            number="001", series="F25", issue_date=date(2025, 1, 1),
            issuer_tax_id="A11111111", customer=self.customer,
            lines=[], taxes=[], total_base=100, total_tax=21, total_amount=121
        )
        
        correct_hash = VeriFactuHasher.calculate_fingerprint(inv, "")
        
        self.assertTrue(VeriFactuHasher.validate_chain(inv, correct_hash, ""))
        self.assertFalse(VeriFactuHasher.validate_chain(inv, "TAMPERED_HASH", ""))
        print("✓ Test 4: Validate chain function")
    
    def test_5_decimal_precision_enforcement(self):
        """Amounts with >2 decimals MUST be rejected."""
        with self.assertRaises(ValueError):
            VeriFactuHasher.format_amount(100.001)  # 3 decimals
        
        # 2 decimals should work
        result = VeriFactuHasher.format_amount(100.01)
        self.assertEqual(result, "100.01")
        print("✓ Test 5: Decimal precision enforcement")

if __name__ == '__main__':
    unittest.main(verbosity=2)
