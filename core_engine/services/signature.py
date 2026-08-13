"""
[CORE-008 / Sprint 5] XAdES signature service for VeriFactu compliance.

Firma XAdES-BES real con `signxml` cuando la librería y los certificados están
disponibles. Si no, degrada a un stub determinista (digest SHA-256) para no
bloquear desarrollo/tests — mismo patrón de degradación opcional que el resto
del repositorio (vector_db, llm_router, web_search).

Uso de producción: cargar un certificado PKCS#12 (.p12) de la FNMT y usar
`sign_xml` para firmar el Facturae antes del envío a AEAT.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Dependencia opcional: signxml.
try:
    from signxml import xades  # type: ignore

    _HAS_SIGNXML = True
except Exception:
    xades = None  # type: ignore
    _HAS_SIGNXML = False

# Carga de certificados PKCS#12 opcional (cryptography es dependencia dura).
try:
    from cryptography.hazmat.primitives.serialization import pkcs12  # type: ignore
    from cryptography import x509  # type: ignore

    _HAS_CRYPTO = True
except Exception:
    pkcs12 = None  # type: ignore
    x509 = None  # type: ignore
    _HAS_CRYPTO = False


class SignatureService:
    """
    Servicio de firma XAdES.

    Modo real (certificados + signxml): firma XAdES-BES con el certificado cargado.
    Modo stub (sin certificados o sin signxml): digest SHA-256 anotado como stub.
    """

    def __init__(self, cert_path: Optional[str] = None, cert_pass: Optional[str] = None):
        self.cert_path = cert_path
        self.cert_pass = cert_pass
        self._key = None
        self._cert = None
        self._load_certificate()

    def _load_certificate(self) -> None:
        """Carga el certificado PKCS#12 si la ruta y las deps están disponibles."""
        if not (self.cert_path and _HAS_CRYPTO):
            return
        import os

        if not os.path.exists(self.cert_path):
            logger.debug("[Signature] Certificado no encontrado")
            return
        try:
            with open(self.cert_path, "rb") as f:
                p12_data = f.read()
            self._key, self._cert, _additional = pkcs12.load_key_and_certificates(
                p12_data, (self.cert_pass or "").encode("utf-8")
            )
            if self._key is None or self._cert is None:
                logger.warning("[Signature] PKCS#12 sin clave/cert principal.")
        except Exception:
            logger.warning("[Signature] No se pudo cargar el certificado")
            self._key = None
            self._cert = None

    @property
    def has_real_certificate(self) -> bool:
        return self._key is not None and self._cert is not None

    @property
    def can_sign_xades(self) -> bool:
        return self.has_real_certificate and _HAS_SIGNXML

    def sign_xml(self, xml_content: bytes) -> bytes:
        """
        Firma el XML.

        - Si hay certificado + signxml → XAdES-BES envuelta (XML firmado real).
        - En caso contrario → stub con digest SHA-256 (no válido para AEAT prod,
          pero determinista para desarrollo/tests).
        """
        if self.can_sign_xades:
            try:
                return self._sign_xades_real(xml_content)
            except Exception as exc:
                logger.error("[Signature] Fallo firma XAdES real, usando stub: %s", exc)
        return self._sign_stub(xml_content)

    def _sign_xades_real(self, xml_content: bytes) -> bytes:
        """Firma XAdES-BES con signxml usando el certificado cargado."""
        # signxml espera la clave y el cert como objetos de cryptography.
        signed = xades.sign(
            xml_content,
            key=self._key,
            cert=self._cert,
            reference_uri="",
        )
        return signed

    def _sign_stub(self, xml_content: bytes) -> bytes:
        """Stub determinista: anota el digest SHA-256 como comentario XAdES."""
        digest = hashlib.sha256(xml_content).hexdigest().upper()
        return xml_content + f"\n<!-- XAdES-STUB:{digest} -->".encode("utf-8")

    def verify_xml(self, signed_xml: bytes) -> Tuple[bool, str]:
        """
        Verifica la integridad de un XML firmado.

        Returns (valid: bool, reason: str).
        """
        # Detección de stub: si termina con el marcador, validamos el digest.
        text = signed_xml.decode("utf-8", errors="replace")
        if "XAdES-STUB:" in text:
            try:
                pre, marker = text.rsplit("XAdES-STUB:", 1)
                digest = marker.strip().rstrip("-<>/\n ")
                # El stub añade el sufijo "\n<!-- XAdES-STUB:{digest} -->".
                # Recortamos ese separador completo para reconstruir el XML
                # original sobre el que se calculó el digest.
                sep = "\n<!-- "
                if pre.endswith(sep):
                    pre = pre[: -len(sep)]
                computed = hashlib.sha256(pre.encode("utf-8")).hexdigest().upper()
                if computed == digest:
                    return True, "stub digest matches"
                return False, "stub digest mismatch"
            except Exception as exc:
                return False, f"stub parse error: {exc}"

        # Verificación XAdES real.
        if not _HAS_SIGNXML:
            return False, "signxml not installed; cannot verify real signature"
        try:
            xades.verify(signed_xml, x509_cert=self._cert)
            return True, "xades signature valid"
        except Exception as exc:
            return False, f"xades verification failed: {exc}"
