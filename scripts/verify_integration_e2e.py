import os
import sys
from datetime import date
from sqlalchemy import text

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_agents.crew import veriagent_crew
from core_engine.db.database import SessionLocal, engine
from core_engine.db.models import Base, InvoiceModel

def verify_e2e():
    print("--- E2E INTEGRATION VERIFICATION ---")
    
    # 1. Setup: Clean DB
    print("[1/4] Cleaning test database...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    # 2. Input Data (Simulating correct OCR result)
    invoice_data = {
        "series": "E2E",
        "number": "001",
        "issue_date": date.today().isoformat(),
        "issuer_tax_id": "B12345674",
        "customer": {
            "tax_id": "A11111119",
            "name": "QA Test Client",
            "address": {
                "street": "Calle Falsa 123",
                "city": "Madrid",
                "postal_code": "28001",
                "country": "ES"
            }
        },
        "lines": [
            {"description": "Servicio de QA", "quantity": 1, "unit_price": 1000.0, "total_amount": 1000.0}
        ],
        "taxes": [
            {"tax_rate": 21.0, "base_amount": 1000.0, "tax_amount": 210.0}
        ],
        "total_base": 1000.0,
        "total_tax": 210.0,
        "total_amount": 1210.0,
        "previous_invoice_hash": "" # First invoice
    }
    
    # 3. Execution: Run Agentic Workflow
    print("[2/4] Running Fiscal Auditor Crew...")
    # Passing real dict to verify the tool's parser
    result = veriagent_crew.kickoff(inputs={"invoice_data": invoice_data})
    
    print(f"--- Agent Response ---\n{result}\n-----------------------")
    
    # 4. Asserts (Verification)
    print("[3/4] Verifying SQL Database state...")
    db = SessionLocal()
    try:
        # Check direct SQL
        query = text("SELECT count(*) FROM invoices WHERE status = 'SIGNED'")
        count = db.execute(query).scalar()
        
        # Consultamos el registro persistido
        invoice = db.query(InvoiceModel).filter(InvoiceModel.series == "E2E").first()
        
        assert count > 0, "ERROR: No hay facturas con estado SIGNED en la base de datos."
        assert invoice is not None, "ERROR: La factura no se guardó en la DB."
        assert invoice.invoice_hash is not None, "ERROR: current_invoice_hash es nulo."
        assert len(invoice.invoice_hash) == 64, f"ERROR: Hash inválido: {invoice.invoice_hash}"
        assert invoice.status == "SIGNED", f"ERROR: Estado incorrecto: {invoice.status}"
        
        print(f"[4/4] SUCCESS: Factura registrada y firmada.")
        print(f"      ID: {invoice.id}")
        print(f"      Hash: {invoice.invoice_hash}")
        
        # ====================================================
        # [STEP 5] OPCIONAL: Envío a AEAT (Si hay certificados)
        # ====================================================
        aeat_cert = os.getenv("AEAT_CERT_PATH", "./certs/test_cert.pem")
        aeat_key = os.getenv("AEAT_KEY_PATH", "./certs/test_key.pem")
        
        if os.path.exists(aeat_cert) and os.path.exists(aeat_key):
            print("\n[5/5] Enviando a AEAT (Sandbox)...")
            from core_engine.aeat_connector import send_to_aeat
            
            # Construir un XML de demo para la prueba
            demo_xml = f"""<RegistroAlta>
                <IDFactura>
                    <IDEmisorFactura>{invoice.issuer_tax_id}</IDEmisorFactura>
                    <NumSerieFactura>{invoice.series}-{invoice.number}</NumSerieFactura>
                    <FechaExpedicionFactura>{invoice.issue_date}</FechaExpedicionFactura>
                </IDFactura>
                <Huella>{invoice.invoice_hash}</Huella>
            </RegistroAlta>"""
            
            success, message, csv = send_to_aeat(
                xml_content=demo_xml,
                certificate_path=aeat_cert,
                private_key_path=aeat_key,
                environment=os.getenv("AEAT_ENV", "SANDBOX")
            )
            
            if success:
                print(f"      ✅ AEAT Response: {message}")
                print(f"      CSV: {csv}")
            else:
                print(f"      ⚠️ AEAT Error: {message}")
        else:
            print("\n[5/5] SKIPPED: No se encontraron certificados para envío AEAT.")
            print(f"      Esperados: {aeat_cert}, {aeat_key}")

    except Exception as e:
        print(f"!!! VERIFICATION FAILED: {str(e)}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    verify_e2e()
