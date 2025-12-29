import hashlib
from shared.schemas import Invoice

class VeriFactuCrypto:
    """
    [CORE-007] Implements cryptographic functions for VeriFactu.
    """
    
    @staticmethod
    def calculate_invoice_fingerprint(
        invoice: Invoice, 
        previous_hash: str = ""
    ) -> str:
        """
        Calculates the 'Huella' (Fingerprint) of the invoice record.
        Format: ID_Emisor | Num_Factura | Serie | Fecha | Importe_Total | Huella_Anterior
        """
        # Data concatenation according to technical specs (simplified for MVP)
        raw_data = (
            f"{invoice.issuer_tax_id}&"
            f"{invoice.number}&"
            f"{invoice.series}&"
            f"{invoice.issue_date.isoformat()}&"
            f"{invoice.total_amount:.2f}&"
            f"{previous_hash}"
        )
        
        # SHA-256 Hash
        return hashlib.sha256(raw_data.encode('utf-8')).hexdigest().upper()
