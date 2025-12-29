from datetime import date
from lxml import etree
from shared.schemas import Invoice

class FacturaeService:
    """
    [CORE-006] Generates Facturae XML (v3.2.2 compliant structure) from Invoice model.
    """
    
    NAMESPACE_MAP = {
        "fe": "http://www.facturae.es/Facturae/2014/v3.2.2/Facturae"
    }

    @staticmethod
    def generate_xml(invoice: Invoice) -> bytes:
        root = etree.Element("Facturae", nsmap={None: FacturaeService.NAMESPACE_MAP["fe"]})
        
        # FileHeader
        header = etree.SubElement(root, "FileHeader")
        etree.SubElement(header, "SchemaVersion").text = "3.2.2"
        etree.SubElement(header, "Modality").text = "I" # Individual
        etree.SubElement(header, "InvoiceIssuerType").text = "EM" # Emisor
        
        # Batch
        batch = etree.SubElement(header, "Batch")
        etree.SubElement(batch, "BatchIdentifier").text = f"{invoice.series}{invoice.number}"
        etree.SubElement(batch, "InvoicesCount").text = "1"
        
        ts_amount = etree.SubElement(batch, "TotalInvoicesAmount")
        etree.SubElement(ts_amount, "TotalAmount").text = f"{invoice.total_amount:.2f}"
        
        # Parties
        parties = etree.SubElement(root, "Parties")
        
        # Seller (Issuer)
        seller = etree.SubElement(parties, "SellerParty")
        seller_tax_id = etree.SubElement(seller, "TaxIdentification")
        etree.SubElement(seller_tax_id, "PersonTypeCode").text = "J" # Persona Jurídica (simplified)
        etree.SubElement(seller_tax_id, "ResidenceTypeCode").text = "R" # Residente
        etree.SubElement(seller_tax_id, "TaxIdentificationNumber").text = invoice.issuer_tax_id
        
        # Buyer (Customer)
        buyer = etree.SubElement(parties, "BuyerParty")
        buyer_tax_id = etree.SubElement(buyer, "TaxIdentification")
        etree.SubElement(buyer_tax_id, "PersonTypeCode").text = "J"
        etree.SubElement(buyer_tax_id, "ResidenceTypeCode").text = "R"
        etree.SubElement(buyer_tax_id, "TaxIdentificationNumber").text = invoice.customer.tax_id
        
        legal_entity = etree.SubElement(buyer, "LegalEntity")
        etree.SubElement(legal_entity, "CorporateName").text = invoice.customer.name
        
        # Invoices
        invoices = etree.SubElement(root, "Invoices")
        inv_xml = etree.SubElement(invoices, "Invoice")
        
        inv_header = etree.SubElement(inv_xml, "InvoiceHeader")
        etree.SubElement(inv_header, "InvoiceNumber").text = invoice.number
        etree.SubElement(inv_header, "InvoiceSeriesCode").text = invoice.series
        etree.SubElement(inv_header, "InvoiceDocumentType").text = "FC" # Factura completa
        etree.SubElement(inv_header, "InvoiceClass").text = "OO" # Original
        
        # Totals
        inv_totals = etree.SubElement(inv_xml, "InvoiceTotals")
        inv_total = etree.SubElement(inv_totals, "InvoiceTotal")
        etree.SubElement(inv_total, "TotalGrossAmount").text = f"{invoice.total_base:.2f}"
        etree.SubElement(inv_total, "TotalTaxOutputs").text = f"{invoice.total_tax:.2f}"
        etree.SubElement(inv_total, "InvoiceTotalAmount").text = f"{invoice.total_amount:.2f}"
        
        # Lines
        inv_items = etree.SubElement(inv_xml, "Items")
        for line in invoice.lines:
            item = etree.SubElement(inv_items, "InvoiceLine")
            etree.SubElement(item, "ItemDescription").text = line.description
            etree.SubElement(item, "Quantity").text = f"{line.quantity:.2f}"
            etree.SubElement(item, "UnitOfMeasure").text = "01"
            etree.SubElement(item, "UnitPriceWithoutTax").text = f"{line.unit_price:.4f}"
            etree.SubElement(item, "TotalCost").text = f"{line.total_amount:.2f}"
            etree.SubElement(item, "GrossAmount").text = f"{line.total_amount:.2f}"
            
        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8")
