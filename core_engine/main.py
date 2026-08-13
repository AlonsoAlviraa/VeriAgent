import logging
import os
import uuid
from typing import Optional
from uuid import UUID

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile, status
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
from ai_agents.adk.config import GCP_SERVICES, GEMINI_MODEL, GOOGLE_AGENT_FRAMEWORK
from core_engine.aeat_connector import is_aeat_remitting
from core_engine.control_plane.feature_flags import PROD_AEAT_ENABLED, FeatureFlagService
from core_engine.control_plane.registry import TenantRegistry
from core_engine.db.database import SessionLocal, get_db, init_db
from core_engine.exceptions import HashContinuityError
from core_engine.middleware.rate_limit import RateLimitMiddleware
from core_engine.services.invoice_service import InvoiceService
from core_engine.services.ocr import OCRService
from core_engine.services.webhooks import WebhookEmitter

app = FastAPI(
    title="VeriFleet / VeriAgent Core Engine",
    version="0.4.0",
    description="VeriFactu kernel + Google ADK fiscal-compliance fleet",
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
_cors = os.getenv("CORS_ORIGINS", "http://localhost:3000")
_cors_origins = [o.strip() for o in _cors.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["http://localhost:3000"],
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
    return {
        "status": "ok",
        "service": "core_engine",
        "version": "0.4.0",
        "fleet": "verifleet",
        "model": GEMINI_MODEL,
        "framework": GOOGLE_AGENT_FRAMEWORK,
        "runner": "InMemoryRunner",
        "gcp_services": list(GCP_SERVICES),
        "track": "Fortified Enterprise Fleet",
        "aeat_remitting": is_aeat_remitting(),
    }


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


def _effective_wait(query_wait: bool, body_wait: Optional[bool]) -> bool:
    """Body wait wins when set so a proxy that drops ?wait=false still queues."""
    if body_wait is not None:
        return body_wait
    return query_wait


class FleetIngestRequest(BaseModel):
    invoice: Optional[dict] = None
    raw_text: Optional[str] = None
    file_id: Optional[str] = None
    wait: Optional[bool] = None


class FleetMemoryRequest(BaseModel):
    key: str
    value: str


class FleetBatchRequest(BaseModel):
    invoices: list
    wait: Optional[bool] = None


@app.post("/api/v1/fleet/ingest")
def fleet_ingest(
    body: FleetIngestRequest,
    db: Session = Depends(get_db),
    org: OrgContext = Depends(get_org_context),
    wait: bool = Query(True),
):
    """Enqueue + run the ADK fiscal fleet. wait=false returns 202 QUEUED."""
    from fastapi.responses import JSONResponse

    from ai_agents.adk.queue import _queue_label, enqueue
    from ai_agents.adk.runtime import run_fleet

    if body.invoice is None and not body.raw_text and not body.file_id:
        raise HTTPException(
            status_code=400,
            detail="Provide invoice, raw_text, or file_id",
        )
    if not _effective_wait(wait, body.wait):
        queued = enqueue(
            db=db,
            tenant_id=org.tenant_id,
            roles=org.roles,
            user_id=org.user_id,
            invoice=body.invoice,
            raw_text=body.raw_text,
            file_id=body.file_id,
        )
        return JSONResponse(
            status_code=202,
            content={
                "run_id": queued.run_id,
                "tenant_id": queued.tenant_id,
                "status": "QUEUED",
                "decision": None,
                "poll": "/api/v1/fleet/runs",
                "queue": _queue_label(),
            },
        )
    result = run_fleet(
        db=db,
        tenant_id=org.tenant_id,
        roles=org.roles,
        user_id=org.user_id,
        invoice=body.invoice,
        raw_text=body.raw_text,
        file_id=body.file_id,
    )
    return result.to_dict()


@app.get("/api/v1/fleet/runs/{run_id}")
def fleet_get_run(
    run_id: str,
    db: Session = Depends(get_db),
    org: OrgContext = Depends(get_org_context),
):
    from ai_agents.adk.queue import FleetInFlight, execute
    from ai_agents.adk.runtime import get_run

    row = get_run(db, run_id, tenant_id=org.tenant_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Fleet run not found")
    # Same-process drain: in-memory FIFO may live on another uvicorn worker.
    # Poll GET from :3000 must still complete the durable fleet_runs row.
    if row.get("status") == "QUEUED":
        try:
            execute(run_id, db)
        except FleetInFlight:
            pass
        except KeyError:
            pass
        except Exception:
            logging.getLogger("verifleet").exception("lazy execute failed for %s", run_id)
        row = get_run(db, run_id, tenant_id=org.tenant_id) or row
    return row


@app.post("/api/v1/fleet/ingest/batch")
def fleet_ingest_batch(
    body: FleetBatchRequest,
    db: Session = Depends(get_db),
    org: OrgContext = Depends(get_org_context),
    wait: bool = Query(True),
):
    """Run up to 5 invoices. wait=false queues them (202)."""
    from fastapi.responses import JSONResponse

    from ai_agents.adk.queue import _queue_label, enqueue
    from ai_agents.adk.runtime import run_fleet_batch

    invoices = [i for i in (body.invoices or []) if isinstance(i, dict)]
    if not invoices:
        raise HTTPException(status_code=400, detail="invoices must be a non-empty list")
    if not _effective_wait(wait, body.wait):
        ids = []
        for inv in invoices[:5]:
            q = enqueue(
                db=db,
                tenant_id=org.tenant_id,
                roles=org.roles,
                user_id=org.user_id,
                invoice=inv,
                raw_text=None,
                file_id=None,
            )
            ids.append(q.run_id)
        return JSONResponse(
            status_code=202,
            content={
                "count": len(ids),
                "run_ids": ids,
                "status": "QUEUED",
                "poll": "/api/v1/fleet/runs",
                "queue": _queue_label(),
            },
        )
    results = run_fleet_batch(
        db=db,
        tenant_id=org.tenant_id,
        invoices=invoices,
        roles=org.roles,
        user_id=org.user_id,
    )
    return {
        "count": len(results),
        "decisions": [r.decision for r in results],
        "runs": [r.to_dict() for r in results],
    }


@app.get("/api/v1/fleet/runs")
def fleet_list_runs(
    db: Session = Depends(get_db),
    org: OrgContext = Depends(get_org_context),
    limit: int = 20,
):
    from ai_agents.adk.runtime import list_runs

    return {"tenant_id": org.tenant_id, "runs": list_runs(db, org.tenant_id, limit=limit)}


@app.get("/api/v1/fleet/compliance")
def fleet_compliance():
    from ai_agents.adk.compliance import checklist

    return checklist()


@app.get("/api/v1/fleet/identity")
def fleet_identity(org: OrgContext = Depends(get_org_context)):
    from ai_agents.adk.compliance import identity

    return identity(org.tenant_id, org.user_id, org.roles)


@app.get("/api/v1/fleet/registry")
def fleet_registry(db: Session = Depends(get_db)):
    from ai_agents.adk.registry import list_agents
    from ai_agents.adk.agents import adk_status
    from ai_agents.adk.config import GEMINI_MODEL, GOOGLE_AGENT_FRAMEWORK, GCP_SERVICES

    return {
        "agents": list_agents(db),
        "model": GEMINI_MODEL,
        "framework": GOOGLE_AGENT_FRAMEWORK,
        "gcp_services": list(GCP_SERVICES),
        "adk": adk_status(),
    }


@app.get("/api/v1/fleet/memory")
def fleet_memory_list(
    db: Session = Depends(get_db),
    org: OrgContext = Depends(get_org_context),
):
    from ai_agents.adk import memory as memory_bank

    return {"tenant_id": org.tenant_id, "memories": memory_bank.read_all(db, org.tenant_id)}


@app.post("/api/v1/fleet/pubsub/push")
def fleet_pubsub_push(
    body: dict,
    db: Session = Depends(get_db),
    org: OrgContext = Depends(get_org_context),
):
    """Cloud Pub/Sub push target. run_id resumes envelope roles, not headers."""
    from ai_agents.adk.pubsub import unwrap_push
    from ai_agents.adk.queue import FleetInFlight, execute
    from ai_agents.adk.runtime import run_fleet

    payload = unwrap_push(body)
    if payload.get("run_id"):
        try:
            return execute(str(payload["run_id"]), db).to_dict()
        except FleetInFlight:
            raise HTTPException(status_code=503, detail="run in flight")
        except KeyError:
            raise HTTPException(status_code=404, detail="Fleet run not found")
    invoice = payload.get("invoice")
    raw_text = payload.get("raw_text")
    file_id = payload.get("file_id")
    if invoice is None and not raw_text and not file_id:
        return {"status": "ignored", "reason": "no invoice payload"}
    result = run_fleet(
        db=db,
        tenant_id=payload.get("tenant_id") or org.tenant_id,
        roles=org.roles,
        user_id=org.user_id,
        invoice=invoice,
        raw_text=raw_text,
        file_id=file_id,
    )
    return result.to_dict()


@app.post("/api/v1/fleet/memory")
def fleet_memory_write(
    body: FleetMemoryRequest,
    db: Session = Depends(get_db),
    org: OrgContext = Depends(get_org_context),
):
    from ai_agents.adk import gateway, memory as memory_bank

    gate = gateway.allows("memory.write", org.roles)
    if not gate.allowed:
        raise HTTPException(status_code=403, detail=gate.reason)
    memory_bank.write(db, org.tenant_id, body.key, body.value)
    return {"tenant_id": org.tenant_id, "key": body.key, "value": body.value}


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
