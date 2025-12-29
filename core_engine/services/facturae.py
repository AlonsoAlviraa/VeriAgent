from datetime import date
import xml.etree.ElementTree as ET
from shared.schemas import Invoice

class FacturaeService:
    """
    [CORE-006] Generates Facturae XML (v3.2.2 compliant structure) from Invoice model.
    Uses standard xml.etree.ElementTree to avoid external dependencies like lxml.
    """
    
    NAMESPACE = "http://www.facturae.es/Facturae/2014/v3.2.2/Facturae"

    @staticmethod
    def generate_xml(invoice: Invoice) -> bytes:
        # Register namespace
        ET.register_namespace('fe', FacturaeService.NAMESPACE)
        
        # Root element with namespace
        root = ET.Element(f"{{{FacturaeService.NAMESPACE}}}Facturae")
        
        # FileHeader
        header = ET.SubElement(root, "FileHeader")
        ET.SubElement(header, "SchemaVersion").text = "3.2.2"
        ET.SubElement(header, "Modality").text = "I" # Individual
        ET.SubElement(header, "InvoiceIssuerType").text = "EM" # Emisor
        
        # Batch
        batch = ET.SubElement(header, "Batch")
        ET.SubElement(batch, "BatchIdentifier").text = f"{invoice.series}{invoice.number}"
        ET.SubElement(batch, "InvoicesCount").text = "1"
        
        ts_amount = ET.SubElement(batch, "TotalInvoicesAmount")
        ET.SubElement(ts_amount, "TotalAmount").text = f"{invoice.total_amount:.2f}"
        
        # Parties
        parties = ET.SubElement(root, "Parties")
        
        # Seller (Issuer)
        seller = ET.SubElement(parties, "SellerParty")
        seller_tax_id = ET.SubElement(seller, "TaxIdentification")
        ET.SubElement(seller_tax_id, "PersonTypeCode").text = "J" # Persona Jurídica (simplified)
        ET.SubElement(seller_tax_id, "ResidenceTypeCode").text = "R" # Residente
        ET.SubElement(seller_tax_id, "TaxIdentificationNumber").text = invoice.issuer_tax_id
        
        # Buyer (Customer)
        buyer = ET.SubElement(parties, "BuyerParty")
        buyer_tax_id = ET.SubElement(buyer, "TaxIdentification")
        ET.SubElement(buyer_tax_id, "PersonTypeCode").text = "J"
        ET.SubElement(buyer_tax_id, "ResidenceTypeCode").text = "R"
        ET.SubElement(buyer_tax_id, "TaxIdentificationNumber").text = invoice.customer.tax_id
        
        legal_entity = ET.SubElement(buyer, "LegalEntity")
        ET.SubElement(legal_entity, "CorporateName").text = invoice.customer.name
        
        # Invoices
        invoices = ET.SubElement(root, "Invoices")
        inv_xml = ET.SubElement(invoices, "Invoice")
        
        inv_header = ET.SubElement(inv_xml, "InvoiceHeader")
        ET.SubElement(inv_header, "InvoiceNumber").text = invoice.number
        ET.SubElement(inv_header, "InvoiceSeriesCode").text = invoice.series
        ET.SubElement(inv_header, "InvoiceDocumentType").text = "FC" # Factura completa
        ET.SubElement(inv_header, "InvoiceClass").text = "OO" # Original
        
        # Totals
        inv_totals = ET.SubElement(inv_xml, "InvoiceTotals")
        inv_total = ET.SubElement(inv_totals, "InvoiceTotal")
        ET.SubElement(inv_total, "TotalGrossAmount").text = f"{invoice.total_base:.2f}"
        ET.SubElement(inv_total, "TotalTaxOutputs").text = f"{invoice.total_tax:.2f}"
        ET.SubElement(inv_total, "InvoiceTotalAmount").text = f"{invoice.total_amount:.2f}"
        
        # Lines
        inv_items = ET.SubElement(inv_xml, "Items")
        for line in invoice.lines:
            item = ET.SubElement(inv_items, "InvoiceLine")
            ET.SubElement(item, "ItemDescription").text = line.description
            ET.SubElement(item, "Quantity").text = f"{line.quantity:.2f}"
            ET.SubElement(item, "UnitOfMeasure").text = "01"
            ET.SubElement(item, "UnitPriceWithoutTax").text = f"{line.unit_price:.4f}"
            ET.SubElement(item, "TotalCost").text = f"{line.total_amount:.2f}"
            ET.SubElement(item, "GrossAmount").text = f"{line.total_amount:.2f}"
            
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)
