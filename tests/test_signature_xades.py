"""
Tests para SignatureService (CORE-008) con firma XAdES real + degradación.

Cubre:
- Sin signxml/certificados → stub determinista.
- Con certificado simulado + signxml mockeado → path de firma real.
- Verificación de stub digest y firma real.
"""

import hashlib
from unittest.mock import MagicMock, patch

import pytest

from core_engine.services.signature import SignatureService, _HAS_CRYPTO, _HAS_SIGNXML


XML = b"<Facturae><Invoice/></Facturae>"


class TestStubDegradation:
    def test_stub_when_no_cert(self):
        svc = SignatureService()
        assert not svc.has_real_certificate
        signed = svc.sign_xml(XML)
        assert signed.startswith(XML)
        assert b"XAdES-STUB:" in signed

    def test_stub_when_cert_missing_file(self, tmp_path):
        # Ruta inexistente → sin cert → stub.
        svc = SignatureService(cert_path=str(tmp_path / "nope.p12"), cert_pass="x")
        assert not svc.has_real_certificate
        signed = svc.sign_xml(XML)
        assert b"XAdES-STUB:" in signed

    def test_stub_digest_is_sha256(self):
        svc = SignatureService()
        signed = svc.sign_xml(XML)
        pre, marker = signed.decode().rsplit("XAdES-STUB:", 1)
        digest = marker.strip().rstrip("-<>/\n ")
        # El digest se calcula sobre el XML original. El stub añade el sufijo
        # "\n<!-- XAdES-STUB:{digest} -->"; lo recortamos para reconstruirlo.
        sep = "\n<!-- "
        if pre.endswith(sep):
            pre = pre[: -len(sep)]
        assert len(digest) == 64
        assert digest == hashlib.sha256(pre.encode()).hexdigest().upper()


class TestVerify:
    def test_verify_stub_matches(self):
        svc = SignatureService()
        signed = svc.sign_xml(XML)
        ok, reason = svc.verify_xml(signed)
        assert ok is True
        assert "stub" in reason

    def test_verify_stub_mismatch_on_tamper(self):
        svc = SignatureService()
        signed = svc.sign_xml(XML)
        tampered = signed.replace(b"<Invoice/>", b"<Invoice><!--x--/>")
        ok, reason = svc.verify_xml(tampered)
        assert ok is False

    def test_verify_real_without_signxml_returns_false(self):
        if _HAS_SIGNXML:
            pytest.skip("signxml instalado; este test cubre su ausencia")
        svc = SignatureService()
        ok, reason = svc.verify_xml(b"<xml>not a stub</xml>")
        assert ok is False
        assert "signxml" in reason


class TestRealSignaturePath:
    """Simula el path de firma XAdES real mockeando signxml + certificados."""

    def test_sign_uses_xades_when_available(self, tmp_path):
        """Si signxml + cert están disponibles, se invoca xades.sign."""
        # Crear un .p12 falso para que exista el fichero (la carga fallará y
        # dejará _key/_cert None, así que parcheamos has_real_certificate).
        p12 = tmp_path / "cert.p12"
        p12.write_bytes(b"fake-p12")

        svc = SignatureService(cert_path=str(p12), cert_pass="x")
        # Forzar el estado "tengo cert real" sin cargarlo de verdad.
        svc._key = MagicMock()
        svc._cert = MagicMock()

        # Parchear el flag de disponibilidad de signxml y el método real.
        with patch("core_engine.services.signature._HAS_SIGNXML", True), \
             patch.object(svc, "_sign_xades_real", return_value=b"<signed/>") as mock_real:
            signed = svc.sign_xml(XML)

        assert signed == b"<signed/>"
        mock_real.assert_called_once_with(XML)

    def test_real_sign_falls_back_to_stub_on_error(self, tmp_path):
        p12 = tmp_path / "cert.p12"
        p12.write_bytes(b"fake-p12")
        svc = SignatureService(cert_path=str(p12), cert_pass="x")
        svc._key = MagicMock()
        svc._cert = MagicMock()

        with patch("core_engine.services.signature._HAS_SIGNXML", True), \
             patch.object(svc, "_sign_xades_real", side_effect=RuntimeError("boom")):
            signed = svc.sign_xml(XML)

        # Cae al stub pero no rompe.
        assert b"XAdES-STUB:" in signed

    def test_can_sign_xades_requires_both_cert_and_signxml(self):
        svc = SignatureService()
        # Sin cert ni signxml.
        assert svc.can_sign_xades is False
