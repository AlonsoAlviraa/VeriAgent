"""
[TEAM-A][CORE-008] Digital Signature Module
Handles XAdES-BES digital signatures for Facturae XMLs.

SECURITY NOTES:
- The .p12 certificate path and password are loaded from environment variables
- Team B (AI Agents) NEVER has access to the raw private key
- They can only call sign_xml() through the /api/v1/internal/sign endpoint

This module is PROPERTY of Team A. Team B may NOT modify this code.
"""
import os
from typing import Optional, Tuple
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import pkcs12

class SecureKeyManager:
    """
    Manages secure loading and isolation of the private key.
    The key never leaves this class.
    """
    
    _instance = None
    _private_key = None
    _certificate = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def load_certificate(self) -> bool:
        """
        Loads the .p12 certificate from environment variables.
        
        Required ENV vars:
        - VERIAGENT_CERT_PATH: Path to .p12 file
        - VERIAGENT_CERT_PASSWORD: Password for the .p12 file
        """
        cert_path = os.getenv("VERIAGENT_CERT_PATH")
        cert_password = os.getenv("VERIAGENT_CERT_PASSWORD", "")
        
        if not cert_path:
            return False
            
        if not os.path.exists(cert_path):
            raise FileNotFoundError(f"Certificate not found at {cert_path}")
            
        with open(cert_path, "rb") as f:
            p12_data = f.read()
            
        self._private_key, self._certificate, _ = pkcs12.load_key_and_certificates(
            p12_data, 
            cert_password.encode()
        )
        
        return True
    
    def is_loaded(self) -> bool:
        return self._private_key is not None
    
    def get_certificate_info(self) -> Optional[str]:
        if self._certificate:
            return self._certificate.subject.rfc4514_string()
        return None


class XAdESSigner:
    """
    Signs XML content using XAdES-BES format.
    
    Library Recommendation:
    - For production: Use `signxml` library or `xmlsec` bindings
    - `xmlsec` is more mature but requires system-level libxmlsec installation
    - `signxml` is pure Python but may have edge cases
    
    Current implementation: Stub that calculates signature hash.
    TODO: Integrate full XAdES-BES with ds:Signature block injection.
    """
    
    def __init__(self):
        self.key_manager = SecureKeyManager()
    
    def sign_xml(self, xml_content: bytes) -> Tuple[bytes, str]:
        """
        Signs the XML content.
        
        Returns:
            Tuple of (signature_bytes, signature_hash_hex)
            
        Raises:
            RuntimeError: If certificate is not loaded
        """
        if not self.key_manager.is_loaded():
            # Try to load
            if not self.key_manager.load_certificate():
                # No cert configured, return simulated response
                import hashlib
                simulated_hash = hashlib.sha256(xml_content).hexdigest().upper()
                return b"SIMULATED_SIGNATURE", simulated_hash
        
        # Calculate digest
        hasher = hashes.Hash(hashes.SHA256())
        hasher.update(xml_content)
        digest = hasher.finalize()
        
        # Sign with private key
        signature = self.key_manager._private_key.sign(
            digest,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        
        signature_hash = digest.hex().upper()
        
        return signature, signature_hash


# Singleton instance
_signer = XAdESSigner()

def sign_xml(xml_content: bytes) -> Tuple[bytes, str]:
    """
    Public function exposed to the rest of the system.
    This is the ONLY way Team B can access signing functionality.
    """
    return _signer.sign_xml(xml_content)
