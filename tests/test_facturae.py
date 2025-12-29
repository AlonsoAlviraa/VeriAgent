import sys
import os
import unittest
from datetime import date
from lxml import etree

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.schemas import Invoice, Customer, Address, TaxLine, InvoiceLine
from core_engine.services.facturae import FacturaeService

class TestFacturae(unittest.TestCase):
    def test_xml_generation(self):
        customer = Customer(
            tax_id="B99999999",
            name="Cliente Pruebas S.L.",
            address=Address(street="Calle Falsa 123", city="Madrid", postal_code="28000")
        )
        
        lines = [
            InvoiceLine(description="Servicio Desarrollo", quantity=10, unit_price=50.0, total_amount=500.0)
        ]
        
        taxes = [
            TaxLine(tax_rate=21.0, base_amount=500.0, tax_amount=105.0)
        ]
        
        invoice = Invoice(
            number="1001",
            series="F25",
            issue_date=date(2025, 1, 1),
            issuer_tax_id="A11111111",
            customer=customer,
            lines=lines,
            taxes=taxes,
            total_base=500.0,
            total_tax=105.0,
            total_amount=605.0
        )
        
        xml_bytes = FacturaeService.generate_xml(invoice)
        
        # Verify it's valid XML
        root = etree.fromstring(xml_bytes)
        self.assertEqual(root.tag, "{http://www.facturae.es/Facturae/2014/v3.2.2/Facturae}Facturae")
        
        print("Generated XML:\n", xml_bytes.decode())

if __name__ == '__main__':
    unittest.main()
