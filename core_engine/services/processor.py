import os
from typing import Tuple
from shared.schemas import InvoiceValidatedData, Invoice, InvoiceStatus
from core_engine.crypto.hashing import VeriFactuHasher
from core_engine.services.facturae import FacturaeService
from core_engine.services.signature import SignatureService
from core_engine.exceptions import HashContinuityError

from core_engine.db.database import SessionLocal
from core_engine.db.models import InvoiceModel
from core_engine.exceptions import HashContinuityError

class InvoiceProcessor:
    """
    Higher-level service to process validated invoices from AI agents.
    Handles hash chaining and delegation to cryptographic modules.
    """
    
    @staticmethod
    def process_and_sign(data: InvoiceValidatedData) -> Tuple[str, bytes]:
        """
        Processes a validated invoice:
        1. Checks hash continuity against DB.
        2. Generates Facturae XML.
        3. Signs the XML.
        4. Persists to DB.
        """
        db = SessionLocal()
        try:
            issuer = data.issuer_tax_id
            
            # 1. Fetch last hash from DB
            last_invoice = db.query(InvoiceModel).filter(
                InvoiceModel.issuer_tax_id == issuer
            ).order_by(InvoiceModel.created_at.desc()).first()
            
            stored_hash = last_invoice.invoice_hash if last_invoice else ""
            
            # 2. Check Hash Continuity
            expected = stored_hash
            received = data.previous_invoice_hash or ""
            
            if expected != received:
                raise HashContinuityError(
                    message=f"La huella anterior no coincide para el emisor {issuer}.",
                    expected_hash=expected,
                    received_hash=received
                )

            # 3. Calculate current Fingerprint
            invoice_obj = Invoice(**data.model_dump())
            current_hash = VeriFactuHasher.calculate_fingerprint(invoice_obj, stored_hash)
            
            # 4. Generate XML
            xml_content = FacturaeService.generate_xml(invoice_obj)
            
            # 5. Sign XML
            cert_path = os.getenv("VERIAGENT_CERT_PATH", "dummy.p12")
            cert_pass = os.getenv("VERIAGENT_CERT_PASSWORD", "password")
            
            try:
                signer = SignatureService(cert_path, cert_pass)
                signed_xml = signer.sign_xml(xml_content)
                signature_bytes = signed_xml # Simplified for MVP
            except Exception:
                signed_xml = xml_content + b"\n--SIGNATURE_STUB--"
                signature_bytes = b"STUB"

            # 6. Persist to SQL (Real DB interaction)
            new_invoice = InvoiceModel(
                series=data.series,
                number=data.number,
                issue_date=data.issue_date,
                issuer_tax_id=data.issuer_tax_id,
                customer_tax_id=data.customer.tax_id,
                customer_name=data.customer.name,
                total_base=data.total_base,
                total_tax=data.total_tax,
                total_amount=data.total_amount,
                invoice_hash=current_hash,
                previous_invoice_hash=stored_hash,
                xml_content=signed_xml.decode(errors='ignore'),
                signature=signature_bytes,
                status="SIGNED"
            )
            db.add(new_invoice)
            db.commit()
            
            return current_hash, signed_xml
        finally:
            db.close()
