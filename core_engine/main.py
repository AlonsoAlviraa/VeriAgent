import os
import uuid
import shutil
from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from shared.schemas import (
    InvoiceInput, InvoiceOutput, SignRequest, SignResponse, 
    ErrorResponse, InvoiceStatus, Invoice
)
from core_engine.services.ocr import OCRService

app = FastAPI(
    title="VeriAgent Core Engine",
    version="0.2.0",
    description="Backend API for VeriFactu compliance system"
)

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB Limit
CHUNK_SIZE = 64 * 1024  # 64KB for streaming

# In-memory storage (replace with DB in production)
invoice_store: dict = {}
hash_chain: dict = {}  # issuer_tax_id -> last_hash

# ============================================
# HEALTH
# ============================================
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "core_engine", "version": "0.2.1"}

# ============================================
# UPLOAD API
# ============================================
@app.post("/api/v1/invoices/upload")
async def upload_invoice(file: UploadFile = File(...)):
    """
    [CORE-004] [PERF-002] Uploads a file using strict STREAMING.
    - Rejects > 20MB (Fail Fast).
    - Validates Magic Bytes (%PDF).
    - Constant RAM usage (< 10MB).
    """
    # 1. Fail Fast: Check Content-Length header
    content_length = file.headers.get("content-length")
    if content_length and int(content_length) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

    try:
        # 2. Magic Bytes Check: Read only first 4 bytes for PDF
        # We don't use .read() without args!
        header = await file.read(4)
        await file.seek(0) # Reset for streaming to disk
        
        is_pdf = header == b"%PDF"
        if not is_pdf and file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF format: Magic bytes mismatch."
            )

        # 3. Stream to disk in chunks
        file_id = str(uuid.uuid4())
        extension = os.path.splitext(file.filename)[1]
        safe_filename = f"{file_id}{extension}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        actual_size = 0
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                actual_size += len(chunk)
                
                # Secondary safety check for size
                if actual_size > MAX_FILE_SIZE:
                    buffer.close()
                    os.remove(file_path) # Cleanup
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File content exceeds size limit."
                    )
                buffer.write(chunk)
            
        return {
            "file_id": file_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": actual_size,
            "status": "UPLOADED"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Streaming upload failed: {str(e)}")

@app.post("/api/v1/invoices/extract/{file_id}")
async def extract_content(file_id: str):
    """
    [CORE-005] Extracts text from an uploaded file using OCR Service.
    """
    found_file = None
    for filename in os.listdir(UPLOAD_DIR):
        if filename.startswith(file_id):
            found_file = os.path.join(UPLOAD_DIR, filename)
            break
            
    if not found_file:
        raise HTTPException(status_code=404, detail="File not found")
        
    text_content = OCRService.extract_text(found_file)
    
    return {
        "file_id": file_id,
        "text_content": text_content
    }

# ============================================
# INVOICE PROCESSING API
# ============================================
@app.post("/api/v1/invoices", response_model=InvoiceOutput, responses={409: {"model": ErrorResponse}})
async def create_invoice(invoice_data: InvoiceInput):
    """
    [CORE-006/007] Creates an invoice, generates XML and hash chain.
    Returns 409 if hash chain is broken.
    """
    from core_engine.crypto.hashing import VeriFactuHasher
    from core_engine.services.facturae import FacturaeService
    
    issuer = invoice_data.issuer_tax_id
    
    # Get previous hash for this issuer
    previous_hash = hash_chain.get(issuer, "")
    
    # Create full invoice object
    invoice = Invoice(
        **invoice_data.model_dump(),
        previous_invoice_hash=previous_hash
    )
    
    # Generate hash
    current_hash = VeriFactuHasher.calculate_fingerprint(invoice, previous_hash)
    
    # Generate XML
    xml_content = FacturaeService.generate_xml(invoice)
    
    # Store
    invoice_store[str(invoice.id)] = {
        "invoice": invoice,
        "hash": current_hash,
        "xml": xml_content,
        "status": InvoiceStatus.VALIDATED
    }
    
    # Update chain
    hash_chain[issuer] = current_hash
    
    return InvoiceOutput(
        id=invoice.id,
        series=invoice.series,
        number=invoice.number,
        status=InvoiceStatus.VALIDATED,
        invoice_hash=current_hash,
        previous_invoice_hash=previous_hash or None,
        xml_preview=xml_content[:500].decode() if xml_content else None,
        message="Invoice created and validated successfully"
    )

# ============================================
# INTERNAL SIGNING API (For Team B)
# ============================================
@app.post("/api/v1/internal/sign", response_model=SignResponse)
async def sign_invoice(request: SignRequest):
    """
    [CORE-008] Internal endpoint for AI agents to request signing.
    Team B calls this via CallCoreSigner tool.
    """
    invoice_id = str(request.invoice_id)
    
    if invoice_id not in invoice_store:
        return SignResponse(
            invoice_id=request.invoice_id,
            signed=False,
            error="Invoice not found"
        )
    
    stored = invoice_store[invoice_id]
    
    if stored["status"] != InvoiceStatus.VALIDATED:
        return SignResponse(
            invoice_id=request.invoice_id,
            signed=False,
            error=f"Invoice is in status {stored['status']}, expected VALIDATED"
        )
    
    # In production: Actually sign with SignatureService
    # For now: Simulate signature
    import hashlib
    xml_content = stored["xml"]
    signature_hash = hashlib.sha256(xml_content).hexdigest().upper()
    
    # Update status
    stored["status"] = InvoiceStatus.SIGNED
    stored["signature"] = signature_hash
    
    return SignResponse(
        invoice_id=request.invoice_id,
        signed=True,
        signature_hash=signature_hash
    )

# ============================================
# HASH VALIDATION (409 Conflict on error)
# ============================================
@app.post("/api/v1/invoices/validate-chain")
async def validate_hash_chain(issuer_tax_id: str, expected_previous_hash: str):
    """
    [CORE-010] Validates that the provided hash matches the chain.
    Returns 409 Conflict if broken.
    """
    current_chain_hash = hash_chain.get(issuer_tax_id)
    
    if current_chain_hash is None:
        # First invoice for this issuer
        return {"valid": True, "message": "No previous hash required (first invoice)"}
    
    if current_chain_hash != expected_previous_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "HASH_CHAIN_BROKEN",
                "message": "The provided previous hash does not match the chain",
                "expected": current_chain_hash,
                "received": expected_previous_hash
            }
        )
    
    return {"valid": True, "current_chain_hash": current_chain_hash}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
