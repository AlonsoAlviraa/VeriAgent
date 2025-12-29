"""
[TEAM-A][CORE-007] VeriFactu Hashing Module
Implements deterministic fingerprint generation for invoice chaining.

This module is PROPERTY of Team A. Team B may NOT modify this code.
"""
import hashlib
from typing import Optional
from shared.schemas import Invoice

class VeriFactuHasher:
    """
    Generates the 'Huella' (Fingerprint) for VeriFactu compliance.
    Algorithm: SHA-256 of concatenated invoice fields.
    """
    
    @staticmethod
    def calculate_fingerprint(
        invoice: Invoice, 
        previous_hash: str = ""
    ) -> str:
        """
        Calculates the hash of the invoice record.
        
        Format: NIF_Emisor & Num_Factura & Serie & Fecha & Importe_Total & Huella_Anterior
        
        Args:
            invoice: The Invoice object to hash
            previous_hash: Hash of the previous invoice in the chain (empty for first)
            
        Returns:
            64-character uppercase hex string (SHA-256)
        """
        # Strict formatting to ensure determinism
        # If the AI sends a malformed decimal (e.g., 100.001), the hash will differ
        raw_data = (
            f"{invoice.issuer_tax_id.strip().upper()}&"
            f"{invoice.number.strip()}&"
            f"{invoice.series.strip()}&"
            f"{invoice.issue_date.isoformat()}&"
            f"{invoice.total_amount:.2f}&"
            f"{previous_hash}"
        )
        
        return hashlib.sha256(raw_data.encode('utf-8')).hexdigest().upper()
    
    @staticmethod
    def validate_chain(
        invoice: Invoice,
        claimed_hash: str,
        previous_hash: str = ""
    ) -> bool:
        """
        Validates that the claimed hash matches the calculated hash.
        
        Returns:
            True if valid, False if the hash doesn't match (chain broken)
        """
        calculated = VeriFactuHasher.calculate_fingerprint(invoice, previous_hash)
        return calculated == claimed_hash
    
    @staticmethod
    def format_amount(amount: float) -> str:
        """
        Formats an amount to exactly 2 decimal places.
        Rejects values with more precision (AI hallucination protection).
        """
        # Round to 2 decimals
        rounded = round(amount, 2)
        
        # Check if original had more precision
        if abs(amount - rounded) > 0.001:
            raise ValueError(
                f"Amount {amount} has more than 2 decimal places. "
                "VeriFactu requires exactly 2 decimals."
            )
        
        return f"{rounded:.2f}"
