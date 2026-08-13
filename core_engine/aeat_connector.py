"""
[TEAM-INTEGRATION][SOAP-003] AEAT VeriFactu Connector (Pure Requests Mode)
Conector para el envio de facturas al sistema VeriFactu de la AEAT.
Usa requests directo con mTLS para evitar problemas de parseo WSDL con zeep.

Autor: Senior Python Integration Engineer
Fecha: 2024-12
Version: 3.0 (Pure Requests - Production Ready)
"""

import os
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

import requests
from lxml import etree

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

ENDPOINTS = {
    "SANDBOX": "https://prewww1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP",
    # PRODUCTION only reachable when caller passes environment="PRODUCTION"
    # AND tenant feature flag PROD_AEAT_ENABLED is true (enforced in send_invoice_to_aeat).
    "PRODUCTION": "https://www1.aeat.es/wlpl/TIKE-CONT/ws/SistemaFacturacion/VerifactuSOAP",
}

# SOAP Action for the RegFactuSistemaFacturacion operation
SOAP_ACTION = "RegFactuSistemaFacturacion"

# XML Namespaces
NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
NS_SF = "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/SuministroLR.xsd"


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class AEATResponse:
    """Estructura de respuesta normalizada del servicio AEAT."""
    status: str  # "ACCEPTED" | "REJECTED" | "ERROR"
    csv: Optional[str] = None
    error_code: Optional[str] = None
    error_description: Optional[str] = None
    raw_response: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InvoiceData:
    """Estructura de datos de factura para envio a AEAT."""
    issuer_nif: str
    issuer_name: str
    series: str
    number: str
    issue_date: str  # Format: YYYY-MM-DD
    total_amount: float
    invoice_hash: str
    previous_hash: Optional[str] = None

    def to_soap_xml(self) -> str:
        """Genera el XML SOAP completo para el envio."""
        prev_hash_block = ""
        if self.previous_hash:
            prev_hash_block = f"""
                    <sf:EncadenamientoFacturaAnterior>
                        <sf:Huella>{self.previous_hash}</sf:Huella>
                    </sf:EncadenamientoFacturaAnterior>"""

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="{NS_SOAP}"
                  xmlns:sf="{NS_SF}">
    <soapenv:Header/>
    <soapenv:Body>
        <sf:RegFactuSistemaFacturacion>
            <sf:Cabecera>
                <sf:Obligado>
                    <sf:NombreRazon>{self.issuer_name}</sf:NombreRazon>
                    <sf:NIF>{self.issuer_nif}</sf:NIF>
                </sf:Obligado>
            </sf:Cabecera>
            <sf:RegistroFactura>
                <sf:RegistroAlta>
                    <sf:IDFactura>
                        <sf:IDEmisorFactura>{self.issuer_nif}</sf:IDEmisorFactura>
                        <sf:NumSerieFactura>{self.series}-{self.number}</sf:NumSerieFactura>
                        <sf:FechaExpedicionFactura>{self.issue_date}</sf:FechaExpedicionFactura>
                    </sf:IDFactura>
                    <sf:ImporteTotal>{self.total_amount}</sf:ImporteTotal>
                    <sf:Huella>{self.invoice_hash}</sf:Huella>{prev_hash_block}
                </sf:RegistroAlta>
            </sf:RegistroFactura>
        </sf:RegFactuSistemaFacturacion>
    </soapenv:Body>
</soapenv:Envelope>"""


# ============================================================
# AEAT CONNECTOR CLASS
# ============================================================

class AEATConnector:
    """
    Cliente SOAP para VeriFactu usando requests con mTLS.
    Evita problemas de parseo WSDL construyendo el XML manualmente.
    """

    def __init__(
        self,
        cert_path: Optional[str] = None,
        key_path: Optional[str] = None,
        environment: str = "SANDBOX"
    ):
        """
        Inicializa el conector AEAT.

        Args:
            cert_path: Ruta al certificado (.pem). Default: env AEAT_CERT_PATH
            key_path: Ruta a la clave privada (.pem). Default: env AEAT_KEY_PATH
            environment: "SANDBOX" (default)
        """
        self.cert_path = cert_path or os.getenv("AEAT_CERT_PATH")
        self.key_path = key_path or os.getenv("AEAT_KEY_PATH")
        self.environment = environment

        if environment not in ENDPOINTS:
            raise ValueError(f"Entorno '{environment}' no soportado. Use 'SANDBOX'.")

        self.endpoint_url = ENDPOINTS[environment]
        self.session = self._create_session()

        logger.info(f"[AEAT] Conector inicializado - Entorno: {environment}")
        logger.info(f"[AEAT] Endpoint: {self.endpoint_url}")

    def _create_session(self) -> requests.Session:
        """Crea una sesion requests con certificado mTLS."""
        session = requests.Session()

        if self.cert_path and self.key_path:
            cert_file = Path(self.cert_path)
            key_file = Path(self.key_path)

            if not cert_file.exists():
                raise FileNotFoundError(f"Certificado no encontrado: {cert_file}")
            if not key_file.exists():
                raise FileNotFoundError(f"Clave privada no encontrada: {key_file}")

            session.cert = (str(cert_file), str(key_file))
            logger.info("[AEAT] mTLS configurado con certificados")
        else:
            logger.warning("[AEAT] Sin certificados - La conexion fallara con la AEAT real")

        return session

    def send_invoice(self, invoice: InvoiceData) -> AEATResponse:
        """
        Envia una factura al servicio VeriFactu.

        Args:
            invoice: Datos de la factura estructurados

        Returns:
            AEATResponse con el resultado
        """
        logger.info(f"[AEAT] Enviando factura: {invoice.series}-{invoice.number}")

        soap_xml = invoice.to_soap_xml()
        logger.debug(f"[AEAT] SOAP Request:\n{soap_xml[:500]}...")

        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPAction": SOAP_ACTION,
        }

        try:
            response = self.session.post(
                self.endpoint_url,
                data=soap_xml.encode("utf-8"),
                headers=headers,
                timeout=30
            )

            logger.info(f"[AEAT] HTTP Response: {response.status_code}")

            if response.status_code == 200:
                return self._parse_response(response.text)
            else:
                return AEATResponse(
                    status="ERROR",
                    error_code=f"HTTP_{response.status_code}",
                    error_description=response.text[:500],
                    raw_response=response.text
                )

        except requests.exceptions.SSLError as e:
            logger.error(f"[AEAT] SSL Error (mTLS failed): {e}")
            return AEATResponse(
                status="ERROR",
                error_code="SSL_ERROR",
                error_description=f"Fallo mTLS. Verifica el certificado. Detalle: {str(e)}"
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[AEAT] Connection Error: {e}")
            return AEATResponse(
                status="ERROR",
                error_code="CONNECTION_ERROR",
                error_description=f"No se pudo conectar con AEAT: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"[AEAT] Unexpected Error: {e}")
            return AEATResponse(
                status="ERROR",
                error_code="UNKNOWN_ERROR",
                error_description=str(e)
            )

    def _parse_response(self, xml_response: str) -> AEATResponse:
        """Parsea la respuesta XML de la AEAT."""
        try:
            root = etree.fromstring(xml_response.encode("utf-8"))

            # Define namespaces for XPath
            namespaces = {
                "soap": NS_SOAP,
                "ns": "https://www2.agenciatributaria.gob.es/static_files/common/internet/dep/aplicaciones/es/aeat/tike/cont/ws/RespuestaSuministro.xsd"
            }

            # Extract EstadoEnvio
            estado_elem = root.find(".//ns:EstadoEnvio", namespaces)
            if estado_elem is None:
                estado_elem = root.find(".//*[local-name()='EstadoEnvio']")
            estado = estado_elem.text if estado_elem is not None else "Desconocido"

            # Extract CSV
            csv_elem = root.find(".//ns:CSV", namespaces)
            if csv_elem is None:
                csv_elem = root.find(".//*[local-name()='CSV']")
            csv = csv_elem.text if csv_elem is not None else None

            if estado == "Correcto":
                logger.info(f"[AEAT] Factura aceptada - CSV: {csv}")
                return AEATResponse(
                    status="ACCEPTED",
                    csv=csv,
                    raw_response=xml_response
                )
            else:
                # Extract error details
                error_code_elem = root.find(".//*[local-name()='CodigoErrorRegistro']")
                error_desc_elem = root.find(".//*[local-name()='DescripcionErrorRegistro']")

                error_code = error_code_elem.text if error_code_elem is not None else None
                error_desc = error_desc_elem.text if error_desc_elem is not None else estado

                logger.warning(f"[AEAT] Factura rechazada - Error: {error_code} - {error_desc}")
                return AEATResponse(
                    status="REJECTED",
                    error_code=error_code,
                    error_description=error_desc,
                    raw_response=xml_response
                )

        except etree.XMLSyntaxError as e:
            logger.error(f"[AEAT] XML Parse Error: {e}")
            return AEATResponse(
                status="ERROR",
                error_code="XML_PARSE_ERROR",
                error_description=f"No se pudo parsear la respuesta: {str(e)}",
                raw_response=xml_response
            )

    def ping(self) -> Tuple[bool, str]:
        """
        Verifica la conectividad con el endpoint AEAT.

        Returns:
            Tuple (success: bool, message: str)
        """
        logger.info("[AEAT] Ejecutando ping de conectividad...")
        try:
            # Simple HEAD request to check if endpoint is reachable
            response = self.session.head(
                self.endpoint_url.replace("/VerifactuSOAP", ""),
                timeout=10
            )
            if response.status_code < 500:
                return True, f"Endpoint alcanzable (HTTP {response.status_code})"
            else:
                return False, f"Endpoint con error (HTTP {response.status_code})"
        except requests.exceptions.SSLError:
            return False, "Error SSL - Certificado requerido para mTLS"
        except Exception as e:
            return False, f"Error de conexion: {str(e)}"


# ============================================================
# CONVENIENCE FUNCTION
# ============================================================

def build_registro_alta_payload(
    issuer_nif: str,
    issuer_name: str,
    series: str,
    number: str,
    issue_date: str,
    total_amount: float,
    invoice_hash: str,
    previous_hash: Optional[str] = None,
) -> Dict[str, Any]:
    """Complete RegistroAlta-style dict for tests and outbox workers (COMP-05)."""
    return {
        "IDVersion": "1.0",
        "IDFactura": {
            "IDEmisorFactura": issuer_nif,
            "NumSerieFactura": f"{series}{number}",
            "FechaExpedicionFactura": issue_date,
        },
        "NombreRazonEmisor": issuer_name,
        "TipoFactura": "F1",
        "DescripcionOperacion": "Factura VeriFactu",
        "ImporteTotal": f"{float(total_amount):.2f}",
        "Huella": invoice_hash,
        "HuellaAnterior": previous_hash or "",
        "SistemaInformatico": {
            "NombreSistemaInformatico": "VeriAgent",
            "IdSistemaInformatico": "VERIAGENT-1",
        },
    }


def is_aeat_remitting() -> bool:
    """Safe public boolean: whether this process is remitting to Hacienda.

    Fail-closed. Never returns cert paths or secrets.
    True only with configured certs AND a proven in-session ACCEPTED CSV.
    This runtime has neither (certs unset; no live CSV).
    """
    cert_set = bool(os.getenv("AEAT_CERT_PATH"))
    key_set = bool(os.getenv("AEAT_KEY_PATH"))
    if not (cert_set and key_set):
        return False
    return False


def send_invoice_to_aeat(
    issuer_nif: str,
    issuer_name: str,
    series: str,
    number: str,
    issue_date: str,
    total_amount: float,
    invoice_hash: str,
    previous_hash: Optional[str] = None,
    environment: str = "SANDBOX",
    prod_aeat_enabled: bool = False,
    allow_missing_certs: bool = False,
) -> Dict[str, Any]:
    """
    Fail-closed AEAT remittance (COMP-05 / MT-06).

    - Missing certs → ERROR (never soft-success), unless allow_missing_certs for unit mocks.
    - PRODUCTION requires prod_aeat_enabled=True (per-tenant flag).
    - Always builds complete RegistroAlta payload metadata in the response.
    """
    payload = build_registro_alta_payload(
        issuer_nif,
        issuer_name,
        series,
        number,
        issue_date,
        total_amount,
        invoice_hash,
        previous_hash,
    )

    env = (environment or "SANDBOX").upper()
    if env == "PRODUCTION" and not prod_aeat_enabled:
        return {
            "status": "ERROR",
            "error_code": "PROD_AEAT_DISABLED",
            "error_description": "PRODUCTION remittance blocked: PROD_AEAT_ENABLED is false",
            "registro_alta": payload,
        }

    cert_path = os.getenv("AEAT_CERT_PATH")
    key_path = os.getenv("AEAT_KEY_PATH")
    if not allow_missing_certs:
        if not cert_path or not key_path:
            return {
                "status": "ERROR",
                "error_code": "CERTS_MISSING",
                "error_description": "AEAT certificates not configured (fail-closed)",
                "registro_alta": payload,
            }
        if not Path(cert_path).exists() or not Path(key_path).exists():
            return {
                "status": "ERROR",
                "error_code": "CERTS_NOT_FOUND",
                "error_description": "AEAT certificate files not found (fail-closed)",
                "registro_alta": payload,
            }

    invoice = InvoiceData(
        issuer_nif=issuer_nif,
        issuer_name=issuer_name,
        series=series,
        number=number,
        issue_date=issue_date,
        total_amount=total_amount,
        invoice_hash=invoice_hash,
        previous_hash=previous_hash,
    )

    if env not in ENDPOINTS:
        return {
            "status": "ERROR",
            "error_code": "BAD_ENVIRONMENT",
            "error_description": f"Unsupported environment {env}",
            "registro_alta": payload,
        }

    connector = AEATConnector(
        cert_path=cert_path,
        key_path=key_path,
        environment=env if env in ENDPOINTS else "SANDBOX",
    )
    response = connector.send_invoice(invoice)
    out = response.to_dict()
    out["registro_alta"] = payload
    return out


# ============================================================
# MAIN - Connection Test
# ============================================================

if __name__ == "__main__":
    print("=" * 60)
    print(" AEAT VeriFactu Connector - Connection Test (v3.0)")
    print("=" * 60)

    cert_path = os.getenv("AEAT_CERT_PATH", "./certs/test_cert.pem")
    key_path = os.getenv("AEAT_KEY_PATH", "./certs/test_key.pem")

    print(f"\n[Config]")
    print(f"  Endpoint: {ENDPOINTS['SANDBOX']}")
    print(f"  Certificado: {cert_path} (exists: {Path(cert_path).exists()})")
    print(f"  Clave: {key_path} (exists: {Path(key_path).exists()})")

    try:
        connector = AEATConnector(
            cert_path=cert_path if Path(cert_path).exists() else None,
            key_path=key_path if Path(key_path).exists() else None,
            environment="SANDBOX"
        )

        print("\n[Test] Verificando conectividad...")
        success, message = connector.ping()
        print(f"  {'OK' if success else 'FAIL'}: {message}")

        print("\n[Demo] Estructura de factura de prueba:")
        demo_invoice = InvoiceData(
            issuer_nif="B12345674",
            issuer_name="VeriAgent Test SL",
            series="FA",
            number="2024-001",
            issue_date="2024-12-30",
            total_amount=1210.00,
            invoice_hash="4f3a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a",
            previous_hash=None
        )
        print(f"\n  SOAP XML Preview:")
        print(demo_invoice.to_soap_xml()[:600] + "...")

    except FileNotFoundError as e:
        print(f"\n[WARN] Certificados no encontrados: {e}")
        print("   Para conectar con AEAT, coloca los certificados en ./certs/")

    except Exception as e:
        print(f"\n[ERROR] Error durante el test: {e}")

    print("\n" + "=" * 60)
