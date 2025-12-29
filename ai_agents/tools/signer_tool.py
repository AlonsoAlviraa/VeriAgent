from typing import Type
from crewai_tools import BaseTool
from pydantic import BaseModel, Field
from shared.schemas import InvoiceValidatedData
from core_engine.services.processor import InvoiceProcessor
from core_engine.exceptions import HashContinuityError

class CallCoreSigner(BaseTool):
    name: str = "core_signer"
    description: str = (
        "Delegates the final signing of a VALIDATED invoice to the Core Engine. "
        "MUST be used only after all fiscal and compliance checks have passed. "
        "Returns the final invoice hash or a critical error if the chain is broken."
    )
    args_schema: Type[BaseModel] = InvoiceValidatedData

    def _run(self, **kwargs) -> str:
        """
        Executes the direct call to the Core Engine processing service.
        """
        try:
            # 1. Parse data (FastAPI/CrewAI might pass it as dict/kwargs)
            data = InvoiceValidatedData(**kwargs)
            
            # 2. Direct Service Call for efficiency
            invoice_hash, _ = InvoiceProcessor.process_and_sign(data)
            
            return (
                f"SUCCESS: La factura ha sido firmada digitalmente.\n"
                f"Huella (Hash) generada: {invoice_hash}\n"
                f"Estado: Registrada en el sistema Facturae/VeriFactu."
            )
            
        except HashContinuityError as e:
            # [CRITICAL] VeriFactu chain integrity failure
            return (
                f"ERROR CRÍTICO: La cadena de hashes está rota. "
                f"No se puede firmar para evitar incumplimiento normativo. "
                f"Alerta al humano. Detalles: {str(e)}"
            )
        except Exception as e:
            # Other errors (e.g., validation, storage)
            return f"ERROR en el proceso de firma del Core: {str(e)}"
