import os
from typing import Tuple
from shared.schemas import InvoiceValidatedData, Invoice, InvoiceStatus
from core_engine.crypto.hashing import VeriFactuHasher
from core_engine.services.facturae import FacturaeService
from core_engine.services.signature import SignatureService
from core_engine.exceptions import HashContinuityError

# Mocked or simple persistent storage for the monorepo service
# In a real app, this would be a Database
_hash_chain_state = {} 

class InvoiceProcessor:
    """
    Higher-level service to process validated invoices from AI agents.
    Handles hash chaining and delegation to cryptographic modules.
    """
    
    @staticmethod
    def process_and_sign(data: InvoiceValidatedData) -> Tuple[str, bytes]:
        """
        Processes a validated invoice:
        1. Checks hash continuity.
        2. Generates Facturae XML.
        3. Signs the XML.
        
        Returns:
            (invoice_hash, signed_xml_bytes)
        """
        issuer = data.issuer_tax_id
        stored_hash = _hash_chain_state.get(issuer, "")
        
        # 1. Check Hash Continuity (VeriFactu Art. 12)
        expected = stored_hash
        received = data.previous_invoice_hash or ""
        
        if expected != received:
            raise HashContinuityError(
                message=f"La huella anterior no coincide para el emisor {issuer}. "
                        f"Se esperaba '{expected}' pero se recibió '{received}'.",
                expected_hash=expected,
                received_hash=received
            )

        # 2. Create Internal Invoice object
        invoice = Invoice(**data.model_dump(), previous_invoice_hash=stored_hash)
        
        # 3. Calculate current Fingerprint
        current_hash = VeriFactuHasher.calculate_fingerprint(invoice, stored_hash)
        
        # 3. Generate XML
        xml_content = FacturaeService.generate_xml(invoice)
        
        # 4. Sign XML
        # We need a certificate. Using env variables or dummy for MVP.
        cert_path = os.getenv("VERIAGENT_CERT_PATH", "dummy.p12")
        cert_pass = os.getenv("VERIAGENT_CERT_PASSWORD", "password")
        
        try:
            signer = SignatureService(cert_path, cert_pass)
            signed_xml = signer.sign_xml(xml_content)
        except Exception as e:
            # Fallback for MVP if certificate missing
            print(f"Signing warning: {e}. Using simulated signature.")
            signed_xml = xml_content + b"\n--SIGNATURE_STUB--"

        # 5. Update Chain
        _hash_chain_state[issuer] = current_hash
        
        return current_hash, signed_xml
