import os
from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12

class SignatureService:
    """
    [CORE-008] Handles XAdES-BES digital signatures for Facturae XMLs.
    """
    
    def __init__(self, p12_path: str, password: str):
        self.p12_path = p12_path
        self.password = password.encode()
        self._load_certificate()
        
    def _load_certificate(self):
        if not os.path.exists(self.p12_path):
            raise FileNotFoundError(f"Certificate not found at {self.p12_path}")
            
        with open(self.p12_path, "rb") as f:
            p12_data = f.read()
            
        self.private_key, self.certificate, self.additional_certs = pkcs12.load_key_and_certificates(
            p12_data, 
            self.password
        )

    def sign_xml(self, xml_content: bytes) -> bytes:
        """
        Signs the XML content. 
        NOTE: Full XAdES implementation requires XML-DSig structure injection.
        For MVP, we are simulating the signature calculation pending XAdES library integration.
        Returns the simplified signed hash for now.
        """
        hasher = hashes.Hash(hashes.SHA256())
        hasher.update(xml_content)
        digest = hasher.finalize()
        
        signature = self.private_key.sign(
            digest,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        # In a real implementation we would modify the XML to insert the <ds:Signature> block.
        # For now, we return the signature to prove the cryptographic capability.
        return signature

    def get_certificate_info(self):
        return self.certificate.subject.rfc4514_string()
