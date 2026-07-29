"""
[CORE-006 / COMP-04] Facturae XML generator + VeriFactu QR payload.
"""

from __future__ import annotations

import hashlib
import urllib.parse
from typing import Union
from xml.etree.ElementTree import Element, SubElement, tostring

from shared.schemas import Invoice


class FacturaeService:
    """Generates Facturae-compatible XML and VeriFactu QR payload strings."""

    NS = "http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml"

    @classmethod
    def generate_xml(cls, invoice: Invoice) -> bytes:
        root = Element("Facturae")
        root.set("xmlns", cls.NS)

        header = SubElement(root, "FileHeader")
        SubElement(header, "SchemaVersion").text = "3.2.2"
        SubElement(header, "Modality").text = "I"
        SubElement(header, "InvoiceIssuerType").text = "EM"

        parties = SubElement(root, "Parties")
        seller = SubElement(parties, "SellerParty")
        tax_id = SubElement(seller, "TaxIdentification")
        SubElement(tax_id, "PersonTypeCode").text = "J"
        SubElement(tax_id, "ResidenceTypeCode").text = "R"
        SubElement(tax_id, "TaxIdentificationNumber").text = invoice.issuer_tax_id

        buyer = SubElement(parties, "BuyerParty")
        btax = SubElement(buyer, "TaxIdentification")
        SubElement(btax, "PersonTypeCode").text = "J"
        SubElement(btax, "ResidenceTypeCode").text = "R"
        SubElement(btax, "TaxIdentificationNumber").text = invoice.customer.tax_id
        SubElement(buyer, "CorporateName").text = invoice.customer.name

        invoices = SubElement(root, "Invoices")
        inv = SubElement(invoices, "Invoice")
        header_inv = SubElement(inv, "InvoiceHeader")
        SubElement(header_inv, "InvoiceNumber").text = invoice.number
        SubElement(header_inv, "InvoiceSeriesCode").text = invoice.series
        SubElement(header_inv, "InvoiceDocumentType").text = "FC"
        SubElement(header_inv, "InvoiceClass").text = "OO"

        issue = SubElement(inv, "InvoiceIssueData")
        SubElement(issue, "IssueDate").text = invoice.issue_date.isoformat()
        SubElement(issue, "InvoiceCurrencyCode").text = getattr(
            invoice, "currency", "EUR"
        ) or "EUR"

        totals = SubElement(inv, "InvoiceTotals")
        SubElement(totals, "TotalGrossAmount").text = f"{invoice.total_base:.2f}"
        SubElement(totals, "TotalTaxOutputs").text = f"{invoice.total_tax:.2f}"
        SubElement(totals, "InvoiceTotal").text = f"{invoice.total_amount:.2f}"

        # VeriFactu huella block (normative fields for chaining)
        vf = SubElement(inv, "VeriFactuHuella")
        SubElement(vf, "IDEmisorFactura").text = invoice.issuer_tax_id
        SubElement(vf, "NumSerieFactura").text = f"{invoice.series}{invoice.number}"
        SubElement(vf, "FechaExpedicionFactura").text = invoice.issue_date.isoformat()
        SubElement(vf, "ImporteTotal").text = f"{invoice.total_amount:.2f}"
        if invoice.previous_invoice_hash:
            SubElement(vf, "HuellaAnterior").text = invoice.previous_invoice_hash

        return tostring(root, encoding="utf-8", xml_declaration=True)

    @classmethod
    def build_qr_payload(
        cls,
        invoice: Invoice,
        invoice_hash: str,
        nif_aeat_url: str = "https://www2.agenciatributaria.gob.es/wlpl/TIKE-CONT/ValidarQR",
    ) -> str:
        """
        Compact VeriFactu QR payload (URL query form used by AEAT validation tools).
        """
        params = {
            "nif": invoice.issuer_tax_id,
            "numserie": f"{invoice.series}{invoice.number}",
            "fecha": invoice.issue_date.strftime("%d-%m-%Y"),
            "importe": f"{invoice.total_amount:.2f}",
            "huella": invoice_hash[:16],
        }
        return f"{nif_aeat_url}?{urllib.parse.urlencode(params)}"

    @classmethod
    def huella_fields(cls, invoice: Invoice, previous_hash: str = "") -> dict:
        """Normative field set used for fingerprint composition."""
        return {
            "IDEmisorFactura": invoice.issuer_tax_id.strip().upper(),
            "NumSerieFactura": f"{invoice.series.strip()}{invoice.number.strip()}",
            "FechaExpedicionFactura": invoice.issue_date.isoformat(),
            "TipoFactura": "F1",
            "CuotaTotal": f"{invoice.total_tax:.2f}",
            "ImporteTotal": f"{invoice.total_amount:.2f}",
            "Huella": previous_hash or "",
        }
