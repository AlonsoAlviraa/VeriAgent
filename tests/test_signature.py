"""
Tests para SignatureService.

Actualizado al contrato real (core_engine/services/signature.py): el servicio es
un helper ligero stub-capable que NO carga certificados PKCS12 en __init__.
La firma XAdES real (signxml) se introduce en Sprints 5-6 del plan de mejora.
"""
import sys
import os
import unittest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core_engine.services.signature import SignatureService


class TestSignature(unittest.TestCase):
    def test_service_constructs_without_cert(self):
        """El servicio se construye sin certificado (modo stub)."""
        service = SignatureService()
        self.assertIsNone(service.cert_path)
        self.assertIsNone(service.cert_pass)

    def test_service_constructs_with_cert_paths(self):
        """Acepta rutas de certificado para uso posterior (sin cargarlo aún)."""
        service = SignatureService("cert.p12", "pass")
        self.assertEqual(service.cert_path, "cert.p12")
        self.assertEqual(service.cert_pass, "pass")

    def test_sign_xml_appends_xades_stub_marker(self):
        """sign_xml produce un digest SHA-256 y lo anota como stub XAdES."""
        service = SignatureService()
        xml = b"<Facturae><Invoice/></Facturae>"
        signed = service.sign_xml(xml)

        # El contenido original se preserva.
        self.assertTrue(signed.startswith(xml))
        # Se añade el marcador de stub con un digest hexadecimal.
        self.assertIn(b"XAdES-STUB:", signed)
        # El digest tiene 64 chars (SHA-256 hex).
        marker = signed.split(b"XAdES-STUB:")[1].strip(b" -<>/\n")
        self.assertEqual(len(marker), 64)


if __name__ == '__main__':
    unittest.main()
