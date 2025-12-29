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
    CHUNK_SIZE = 64 * 1024  # 64KB chunks for streaming
    
    @staticmethod
    def calculate_fingerprint(
        invoice: Invoice, 
        previous_hash: str = ""
    ) -> str:
        """
        Calculates the hash of the invoice record.
        
        Format: NIF_Emisor & Num_Factura & Serie & Fecha & Importe_Total & Huella_Anterior
        """
        # Data concatenation
        raw_data = (
            f"{invoice.issuer_tax_id.strip().upper()}&"
            f"{invoice.number.strip()}&"
            f"{invoice.series.strip()}&"
            f"{invoice.issue_date.isoformat()}&"
            f"{invoice.total_amount:.2f}&"
            f"{previous_hash}"
        )
        
        # Use incremental update for better memory practices even on small strings
        hasher = hashlib.sha256()
        hasher.update(raw_data.encode('utf-8'))
        return hasher.hexdigest().upper()

    @staticmethod
    async def calculate_file_hash(upload_file) -> str:
        """
        [PERF-001] Calculates SHA-256 of a file using STREAMING (64KB chunks).
        Never loads the full file into RAM.
        
        Args:
            upload_file: A FastAPI UploadFile or object with a read(size) method.
        """
        hasher = hashlib.sha256()
        
        # Ensure we are at the start of the file
        await upload_file.seek(0)
        
        while True:
            chunk = await upload_file.read(VeriFactuHasher.CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
            
        # Reset pointer for subsequent reads (e.g., saving to disk)
        await upload_file.seek(0)
        return hasher.hexdigest().upper()
    
    @staticmethod
    def validate_chain(
        invoice: Invoice,
        claimed_hash: str,
        previous_hash: str = ""
    ) -> bool:
        """
        Validates that the claimed hash matches the calculated hash.
        """
        calculated = VeriFactuHasher.calculate_fingerprint(invoice, previous_hash)
        return calculated == claimed_hash.upper()
    
    @staticmethod
    def format_amount(amount: float) -> str:
        """
        Formats an amount to exactly 2 decimal places.
        """
        rounded = round(amount, 2)
        if abs(amount - rounded) > 0.001:
            raise ValueError(
                f"Amount {amount} has more than 2 decimal places. "
                "VeriFactu requires exactly 2 decimals."
            )
        return f"{rounded:.2f}"
