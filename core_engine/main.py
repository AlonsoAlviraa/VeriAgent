import os
import uuid
from typing import Optional
from uuid import UUID

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from shared.schemas import (
    CreateTenantRequest,
    DataPlaneResolveResponse,
    ErrorResponse,
    InvoiceInput,
    InvoiceOutput,
    InvoiceStatus,
    SignRequest,
    SignResponse,
    TenantResponse,
)
from core_engine.auth.rbac import OrgContext, parse_org_context, require_roles
from core_engine.control_plane.feature_flags import PROD_AEAT_ENABLED, FeatureFlagService
from core_engine.control_plane.registry import TenantRegistry
from core_engine.db.database import SessionLocal, get_db, init_db
from core_engine.exceptions import HashContinuityError
from core_engine.middleware.rate_limit import RateLimitMiddleware
from core_engine.services.invoice_service import InvoiceService
from core_engine.services.ocr import OCRService
from core_engine.services.webhooks import WebhookEmitter

app = FastAPI(
    title="VeriAgent Core Engine",
    version="0.3.0",
    description="Backend API for VeriFactu enterprise compliance",
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Rate limiting (SEC / Sprint 10): 120 req/min por IP/tenant, /health exento.
app.add_middleware(RateLimitMiddleware, requests=120, window_seconds=60)

ALLOWED_EXTENSIONS = {".pdf", ".xml"}
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = 20 * 1024 * 1024
CHUNK_SIZE = 64 * 1024

# NOTE: Public invoice create/sign path must NOT use process-level invoice_store/hash_chain.
# COMP-02 removed those globals from the compliance path.


def get_org_context(
    x_tenant_id: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None),
    x_roles: Optional[str] = Header(default=None),
) -> OrgContext:
    return parse_org_context(x_tenant_id, x_user_id, x_roles)


@app.on_event("startup")
def _startup():
    # Best-effort table create for sqlite/local; Postgres may use schema.sql
    try:
        if os.getenv("DATABASE_URL", "").startswith("sqlite") or os.getenv(
            "VERIAGENT_AUTO_INIT_DB", ""
        ) == "1":
            init_db()
    except Exception:
        pass


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "core_engine", "version": "0.3.0"}


@app.post("/api/v1/invoices/upload")
async def upload_invoice(file: UploadFile = File(...)):
    content_length = file.headers.get("content-length")
    if content_length and int(content_length) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum allowed: {MAX_FILE_SIZE / 1024 / 1024}MB",
        )
    _, ext = os.path.splitext((file.filename or "").lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension not allowed. Allowed: {ALLOWED_EXTENSIONS}",
        )
    try:
        header = await file.read(4)
        await file.seek(0)
        if not header == b"%PDF" and (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF format: Magic bytes mismatch.",
            )
        file_id = str(uuid.uuid4())
        extension = os.path.splitext(file.filename or "")[1]
        safe_filename = f"{file_id}{extension}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        actual_size = 0
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                actual_size += len(chunk)
                if actual_size > MAX_FILE_SIZE:
                    buffer.close()
                    os.remove(file_path)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="File content exceeds size limit.",
                    )
                buffer.write(chunk)
        return {
            "file_id": file_id,
            "id": file_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "size_bytes": actual_size,
            "status": "UPLOADED",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Streaming upload failed: {str(e)}")


@app.post("/api/v1/invoices/extract/{file_id}")
async def extract_content(file_id: str):
    found_file = None
    for filename in os.listdir(UPLOAD_DIR):
        if filename.startswith(file_id):
            found_file = os.path.join(UPLOAD_DIR, filename)
            break
    if not found_file:
        raise HTTPException(status_code=404, detail="File not found")
    text_content = OCRService.extract_text(found_file)
    return {"file_id": file_id, "text_content": text_content}


@app.post(
    "/api/v1/invoices",
    response_model=InvoiceOutput,
    responses={409: {"model": ErrorResponse}},
)
async def create_invoice(
    invoice_data: InvoiceInput,
    db: Session = Depends(get_db),
    org: OrgContext = Depends(get_org_context),
):
    """
    COMP-02 / PUX-01: durable DB hash chain; 409 on previous_hash mismatch.
    """
    require_roles(org, "issuer", "admin")
    svc = InvoiceService(db, tenant_id=org.tenant_id)
    try:
        row, current_hash, xml_content, qr = svc.create(invoice_data)
    except HashContinuityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "HASH_CHAIN_BROKEN",
                "message": str(exc),
                "expected": exc.expected_hash,
                "received": exc.received_hash,
            },
        )
    return InvoiceOutput(
        id=UUID(str(row.id)),
        series=row.series,
        number=row.number,
        status=InvoiceStatus(row.status),
        invoice_hash=current_hash,
        previous_invoice_hash=row.previous_invoice_hash,
        xml_preview=(
            xml_content[:500].decode()
            if isinstance(xml_content, bytes)
            else str(xml_content)[:500]
        ),
        message="Invoice created and validated successfully",
    )


@app.post("/api/v1/internal/sign", response_model=SignResponse)
async def sign_invoice(
    request: SignRequest,
    db: Session = Depends(get_db),
    org: OrgContext = Depends(get_org_context),
):
    require_roles(org, "issuer", "admin")
    svc = InvoiceService(db, tenant_id=org.tenant_id)
    signed, signature_hash, error = svc.sign(str(request.invoice_id))
    return SignResponse(
        invoice_id=request.invoice_id,
        signed=signed,
        signature_hash=signature_hash,
        error=error,
    )


@app.post("/api/v1/invoices/validate-chain")
async def validate_hash_chain(
    issuer_tax_id: str,
    expected_previous_hash: str,
    db: Session = Depends(get_db),
    org: OrgContext = Depends(get_org_context),
):
    from core_engine.services.chain_repository import ChainRepository

    tip = ChainRepository(db, tenant_id=org.tenant_id).get_tip(issuer_tax_id)
    if not tip:
        return {"valid": True, "message": "No previous hash required (first invoice)"}
    if tip != expected_previous_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "HASH_CHAIN_BROKEN",
                "message": "The provided previous hash does not match the chain",
                "expected": tip,
                "received": expected_previous_hash,
            },
        )
    return {"valid": True, "current_chain_hash": tip}


@app.get("/api/v1/chain/status")
async def chain_status(
    issuer_tax_id: str,
    db: Session = Depends(get_db),
    org: OrgContext = Depends(get_org_context),
):
    """PUX-05: chain integrity status for multi-org UX."""
    from core_engine.services.chain_repository import ChainRepository

    repo = ChainRepository(db, tenant_id=org.tenant_id)
    tip = repo.get_tip(issuer_tax_id)
    return {
        "tenant_id": org.tenant_id,
        "issuer_tax_id": issuer_tax_id,
        "tip_hash": tip or None,
        "has_chain": bool(tip),
        "integrity": "ok" if tip is not None or tip == "" else "unknown",
    }


# ---------- Control plane (MT-01 surface) ----------
@app.post("/api/v1/tenants", response_model=TenantResponse)
async def create_tenant(body: CreateTenantRequest, db: Session = Depends(get_db)):
    reg = TenantRegistry(db)
    tenant = reg.create_tenant(
        name=body.name,
        slug=body.slug,
        plan_id=body.plan_id.value if hasattr(body.plan_id, "value") else body.plan_id,
        connection_ref=body.connection_ref,
    )
    res = reg.resolve_data_plane(tenant.id)
    return TenantResponse(
        id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        plan_id=tenant.plan_id,
        status=tenant.status,
        tier=res.tier,
        connection_ref=res.connection_ref,
    )


@app.get("/api/v1/tenants/{tenant_id}/data-plane", response_model=DataPlaneResolveResponse)
async def resolve_tenant_data_plane(tenant_id: str, db: Session = Depends(get_db)):
    reg = TenantRegistry(db)
    res = reg.resolve_data_plane(tenant_id)
    return DataPlaneResolveResponse(
        tenant_id=res.tenant_id,
        plan_id=res.plan_id,
        tier=res.tier,
        connection_ref=res.connection_ref,
    )


@app.get("/api/v1/tenants/{tenant_id}/flags/{flag_key}")
async def get_feature_flag(tenant_id: str, flag_key: str, db: Session = Depends(get_db)):
    flags = FeatureFlagService(db)
    return {
        "tenant_id": tenant_id,
        "flag_key": flag_key,
        "enabled": flags.get(tenant_id, flag_key, default=False),
    }


@app.post("/api/v1/webhooks/test-emit")
async def test_emit_webhook(event: str = "invoice.test", invoice_id: str = "n/a"):
    """PUX-03: demonstrate lifecycle emit registration."""
    emitter = WebhookEmitter()
    return emitter.emit(event, {"invoice_id": invoice_id})


# ---------- ProductGraph API (Sprint 5-V2) ----------
class ProductGraphRunRequest(BaseModel):
    """Request para disparar una run del ProductGraph."""
    goal: str
    prompt: str = "Investiga tendencias y oportunidades."
    budget: int = 50000
    max_iterations: int = 6


@app.post("/api/v1/product-graph/runs", status_code=202)
async def submit_graph_run(req: ProductGraphRunRequest):
    """Dispara una ejecución asíncrona del ProductGraph. Devuelve el job_id."""
    from ai_agents.graphs.jobs import get_job_store
    store = get_job_store()
    job = store.submit(req.goal, req.prompt, budget=req.budget,
                       max_iterations=req.max_iterations, background=True)
    return {"job_id": job.id, "status": job.status, "goal": req.goal}


@app.get("/api/v1/product-graph/runs/{job_id}")
async def get_graph_run(job_id: str):
    """Estado + resultado de una run del grafo."""
    from ai_agents.graphs.jobs import get_job_store
    job = get_job_store().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Graph run not found")
    out = job.to_dict()
    # Exponer el reporte y el budget; recortar blobs grandes.
    if job.result:
        out["final_report"] = job.result.get("final_report", "")
        out["quality_score"] = job.result.get("quality_score", 0.0)
        out["iteration"] = job.result.get("iteration", 0)
        out["budget"] = (job.result.get("_meta") or {}).get("budget", {})
    return out


@app.get("/api/v1/product-graph/runs")
async def list_graph_runs():
    """Histórico de runs del grafo (metadata ligera)."""
    from ai_agents.graphs.jobs import get_job_store
    return get_job_store().list()


@app.get("/api/v1/product-graph/health")
async def graph_health():
    """Health del ProductGraph: proveedores activos + runs recientes."""
    from ai_agents.graphs.jobs import get_job_store
    store = get_job_store()
    listing = store.list(limit=10)
    return {
        "status": "ok",
        "service": "product_graph",
        "recent_runs": listing["count"],
        "recent_statuses": [j["status"] for j in listing["jobs"]],
    }


@app.get("/api/v1/product-graph/dashboard")
async def graph_dashboard():
    """
    Dashboard del ProductGraph (Sprint 10-V2): histórico de runs con scores,
    tokens y coste agregado.
    """
    from ai_agents.graphs.jobs import get_job_store
    store = get_job_store()
    listing = store.list(limit=100)

    # Agregados sobre las runs completadas.
    scores = []
    tokens_total = 0
    completed = 0
    for j in listing["jobs"]:
        job = store.get(j["id"])
        if job and job.result:
            scores.append(job.result.get("quality_score", 0.0))
            budget = (job.result.get("_meta") or {}).get("budget") or {}
            tokens_total += budget.get("used", 0)
            completed += 1

    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0
    return {
        "total_runs": listing["count"],
        "completed_runs": completed,
        "avg_quality_score": avg_score,
        "total_tokens_used": tokens_total,
        "estimated_cost_usd": 0.0,  # router zero-cost
        "recent_runs": listing["jobs"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
