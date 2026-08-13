"""
[TEAM-AGENTS][TOOL-002] SignerTool with AEAT Integration
Herramienta del agente para firmar facturas y enviarlas automaticamente a la AEAT.
Implementa la logica de semaforo: SENT_OK vs REJECTED_AEAT.

Version: 2.0 (AEAT Integration)
"""

import os
import logging
from typing import Type
from crewai_tools import BaseTool
from pydantic import BaseModel, Field

from shared.schemas import InvoiceValidatedData
from core_engine.services.processor import InvoiceProcessor
from core_engine.exceptions import HashContinuityError
from core_engine.aeat_connector import send_invoice_to_aeat, InvoiceData

from shared.redact import redact_secret

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CallCoreSigner(BaseTool):
    name: str = "core_signer"
    description: str = (
        "Delegates the final signing of a VALIDATED invoice to the Core Engine. "
        "After signing, attempts to send the invoice to AEAT (Hacienda). "
        "Returns the final invoice hash and AEAT CSV, or a critical error if failed."
    )
    args_schema: Type[BaseModel] = InvoiceValidatedData

    def _run(self, **kwargs) -> str:
        """
        Executes the signing and AEAT submission workflow.
        
        Flow:
        1. Sign invoice with Core Engine (generates hash)
        2. Attempt AEAT submission (if certificates are available)
        3. Update status based on AEAT response (SENT_OK / REJECTED_AEAT)
        """
        try:
            # ============================================
            # STEP 1: Parse and Sign Invoice
            # ============================================
            data = InvoiceValidatedData(**kwargs)
            
            invoice_hash, invoice_record = InvoiceProcessor.process_and_sign(data)
            
            logger.info(f"[SignerTool] Factura firmada: {data.series}-{data.number}")
            logger.info("[SignerTool] Hash generado: %s", redact_secret(invoice_hash))
            
            # ============================================
            # STEP 2: Check for AEAT Certificates
            # ============================================
            cert_path = os.getenv("AEAT_CERT_PATH")
            key_path = os.getenv("AEAT_KEY_PATH")
            
            if not cert_path or not key_path:
                logger.warning("[SignerTool] No AEAT certificates configured - Skipping AEAT submission")
                return (
                    f"SUCCESS: Factura firmada digitalmente.\n"
                    f"Huella (Hash): {invoice_hash}\n"
                    f"Estado: SIGNED (Pendiente de envio a AEAT - Sin certificados configurados)"
                )
            
            if not os.path.exists(cert_path) or not os.path.exists(key_path):
                logger.warning("[SignerTool] Certificate files not found")
                return (
                    f"SUCCESS: Factura firmada digitalmente.\n"
                    f"Huella (Hash): {invoice_hash}\n"
                    f"Estado: SIGNED (Pendiente de envio a AEAT - Certificados no encontrados)"
                )
            
            # ============================================
            # STEP 3: Send to AEAT
            # ============================================
            logger.info("[SignerTool] Enviando factura a AEAT...")
            
            aeat_response = send_invoice_to_aeat(
                issuer_nif=data.issuer_tax_id,
                issuer_name=getattr(data, 'issuer_name', data.issuer_tax_id),
                series=data.series,
                number=data.number,
                issue_date=str(data.issue_date),
                total_amount=data.total_amount,
                invoice_hash=invoice_hash,
                previous_hash=data.previous_invoice_hash,
                environment=os.getenv("AEAT_ENV", "SANDBOX")
            )
            
            # ============================================
            # STEP 4: Traffic Light Logic
            # ============================================
            status = aeat_response.get("status")
            
            if status == "ACCEPTED":
                # GREEN LIGHT: AEAT accepted the invoice
                csv = aeat_response.get("csv", "N/A")
                
                # Update DB status to SENT_OK and store CSV
                self._update_invoice_status(
                    invoice_hash=invoice_hash,
                    new_status="SENT_OK",
                    csv=csv
                )
                
                logger.info(f"[SignerTool] AEAT acepto la factura - CSV: {csv}")
                
                return (
                    f"SUCCESS: Factura firmada y ENVIADA A HACIENDA con exito.\n"
                    f"Huella (Hash): {invoice_hash}\n"
                    f"CSV (Codigo Seguro de Verificacion): {csv}\n"
                    f"Estado: SENT_OK"
                )
            
            elif status == "REJECTED":
                # RED LIGHT: AEAT rejected the invoice
                error_code = aeat_response.get("error_code", "UNKNOWN")
                error_desc = aeat_response.get("error_description", "Sin descripcion")
                
                # Update DB status to REJECTED_AEAT
                self._update_invoice_status(
                    invoice_hash=invoice_hash,
                    new_status="REJECTED_AEAT",
                    error_message=f"[{error_code}] {error_desc}"
                )
                
                # Log to audit_logs
                self._log_aeat_rejection(
                    invoice_hash=invoice_hash,
                    error_code=error_code,
                    error_description=error_desc
                )
                
                logger.error(f"[SignerTool] AEAT rechazo la factura: {error_code} - {error_desc}")
                
                return (
                    f"ERROR DE HACIENDA: [{error_code}] {error_desc}\n"
                    f"Huella (Hash): {invoice_hash}\n"
                    f"Estado: REJECTED_AEAT\n"
                    f"ACCION REQUERIDA: Se requiere intervencion humana para corregir el error."
                )
            
            else:
                # YELLOW LIGHT: Connection/Transport error
                error_desc = aeat_response.get("error_description", "Error de conexion")
                
                logger.warning(f"[SignerTool] Error de conexion con AEAT: {error_desc}")
                
                return (
                    f"WARNING: Factura firmada pero NO ENVIADA a AEAT.\n"
                    f"Huella (Hash): {invoice_hash}\n"
                    f"Error de conexion: {error_desc}\n"
                    f"Estado: SIGNED (Reintentar envio manualmente)"
                )
                
        except HashContinuityError as e:
            # [CRITICAL] VeriFactu chain integrity failure
            logger.critical(f"[SignerTool] CADENA DE HASHES ROTA: {e}")
            return (
                f"ERROR CRITICO: La cadena de hashes esta rota. "
                f"No se puede firmar para evitar incumplimiento normativo. "
                f"Alerta al humano. Detalles: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"[SignerTool] Error inesperado: {e}")
            return f"ERROR en el proceso de firma del Core: {str(e)}"

    def _update_invoice_status(
        self,
        invoice_hash: str,
        new_status: str,
        csv: str = None,
        error_message: str = None
    ):
        """Updates the invoice status in the database."""
        try:
            from core_engine.db.database import SessionLocal
            from core_engine.db.models import InvoiceModel
            
            db = SessionLocal()
            invoice = db.query(InvoiceModel).filter(
                InvoiceModel.invoice_hash == invoice_hash
            ).first()
            
            if invoice:
                invoice.status = new_status
                if csv:
                    # Store CSV in a field (add to model if needed)
                    invoice.aeat_csv = csv
                db.commit()
                logger.info(f"[SignerTool] Status actualizado a {new_status}")
            
            db.close()
        except Exception as e:
            logger.error(f"[SignerTool] Error actualizando status en DB: {e}")

    def _log_aeat_rejection(
        self,
        invoice_hash: str,
        error_code: str,
        error_description: str
    ):
        """Logs AEAT rejection to audit_logs table."""
        try:
            from core_engine.db.database import SessionLocal
            from sqlalchemy import text
            
            db = SessionLocal()
            db.execute(
                text("""
                    INSERT INTO audit_logs (invoice_hash, action, details, created_at)
                    VALUES (:hash, 'AEAT_REJECTION', :details, NOW())
                """),
                {
                    "hash": invoice_hash,
                    "details": f"[{error_code}] {error_description}"
                }
            )
            db.commit()
            db.close()
            logger.info("[SignerTool] Rechazo AEAT registrado en audit_logs")
        except Exception as e:
            logger.error(f"[SignerTool] Error registrando en audit_logs: {e}")
