"""Deterministic fleet runtime.

ADK agents provide the framework surface (Gemini 3.5 + google-adk).
Decisions that touch the hash chain are gates in this file: the LLM
cannot sign a mathematically invalid invoice or bypass Model Armor.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from ai_agents.adk import armor, consult as adk_consult, gateway, memory as memory_bank, registry
from ai_agents.adk.agents import adk_status, build_adk_root
from ai_agents.adk.config import HOSPITALITY_MARKERS
from ai_agents.adk.otel import SpanRecorder
from ai_agents.adk.tools import core_tools
from core_engine.db.fleet_models import FleetRunModel
from core_engine.exceptions import HashContinuityError

DECISIONS = ("SIGNED", "REJECTED", "ESCALATED", "BLOCKED")


@dataclass
class FleetResult:
    run_id: str
    tenant_id: str
    status: str
    decision: str
    reason: str
    invoice_id: Optional[str] = None
    invoice_hash: Optional[str] = None
    signed: bool = False
    events: List[dict] = field(default_factory=list)
    spans: List[dict] = field(default_factory=list)
    armor: dict = field(default_factory=dict)
    memory_hits: Dict[str, str] = field(default_factory=dict)
    registry: List[dict] = field(default_factory=list)
    adk: dict = field(default_factory=dict)
    denied_tools: List[str] = field(default_factory=list)
    pubsub: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "tenant_id": self.tenant_id,
            "status": self.status,
            "decision": self.decision,
            "reason": self.reason,
            "invoice_id": self.invoice_id,
            "invoice_hash": self.invoice_hash,
            "signed": self.signed,
            "events": self.events,
            "spans": self.spans,
            "armor": self.armor,
            "memory_hits": self.memory_hits,
            "registry": self.registry,
            "adk": self.adk,
            "denied_tools": self.denied_tools,
            "pubsub": self.pubsub,
        }


def _event(events: List[dict], agent: str, message: str, **extra: Any) -> None:
    events.append(
        {
            "agent": agent,
            "message": message,
            "at": datetime.now(timezone.utc).isoformat(),
            **extra,
        }
    )


def _math_ok(payload: dict) -> tuple[bool, str]:
    try:
        base = float(payload.get("total_base", 0) or 0)
        tax = float(payload.get("total_tax", 0) or 0)
        total = float(payload.get("total_amount", 0) or 0)
    except (TypeError, ValueError):
        return False, "totals are not numeric"
    expected = round(base + tax, 2)
    if abs(total - expected) > 0.01:
        return False, f"Base+Tax={expected} != Total={total}"
    return True, "math_ok"


def _hospitality_blocked(payload: dict, mem: Dict[str, str]) -> bool:
    denied = (mem.get("deny_categories") or "").lower()
    if "hospitality" not in denied and "hosteler" not in denied:
        return False
    blob = " ".join(
        str(line.get("description", ""))
        for line in (payload.get("lines") or [])
        if isinstance(line, dict)
    ).lower()
    blob += " " + str(payload.get("notes") or "").lower()
    return any(m in blob for m in HOSPITALITY_MARKERS)


def _stamp_file_number(payload: dict) -> dict:
    base = str(payload.get("number") or "001")
    payload["number"] = f"{base}-{int(time.time() * 1000) % 1_000_000:06d}"
    return payload


def _extract_payload(
    *,
    invoice: Optional[dict],
    raw_text: Optional[str],
    file_id: Optional[str],
) -> dict:
    if invoice:
        return dict(invoice)
    text = raw_text or ""
    if file_id:
        upload_dir = os.getenv("UPLOAD_DIR", "uploads")
        if os.path.isdir(upload_dir):
            try:
                names = os.listdir(upload_dir)
            except OSError:
                names = []
            for name in names:
                if not name.startswith(file_id):
                    continue
                path = os.path.join(upload_dir, name)
                try:
                    text = (text + "\n" + core_tools.extract_text(path)).strip()
                except Exception as exc:
                    return {
                        "raw_text": "",
                        "lines": [],
                        "extract_error": type(exc).__name__,
                        "extract_confidence": "low",
                    }
                break
    if text:
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and ("total_amount" in parsed or "issuer_tax_id" in parsed):
                if file_id:
                    return _stamp_file_number(parsed)
                return parsed
        except json.JSONDecodeError:
            pass
        from ai_agents.adk.tools.extract_invoice import extract_invoice_from_text

        extracted = extract_invoice_from_text(text)
        if file_id and extracted.get("number"):
            return _stamp_file_number(extracted)
        return extracted
    return {"raw_text": text, "lines": []}


def _unwrap_invoice(obj: Optional[dict]) -> dict:
    if not isinstance(obj, dict):
        return {}
    if "invoice" in obj and isinstance(obj["invoice"], dict):
        return dict(obj["invoice"])
    return dict(obj)


def _wrap_payload(
    existing: dict | None,
    payload: dict,
    *,
    roles,
    user_id,
    raw_text=None,
    file_id=None,
) -> dict:
    prev = existing if isinstance(existing, dict) else {}
    if "roles" not in prev and "invoice" not in prev and prev.get("issuer_tax_id"):
        prev = {"invoice": prev}
    if "issuer_tax_id" in payload or "total_amount" in payload:
        invoice = payload
    else:
        invoice = payload.get("invoice") or prev.get("invoice") or payload
    return {
        "invoice": invoice,
        "raw_text": raw_text if raw_text is not None else prev.get("raw_text"),
        "file_id": file_id if file_id is not None else prev.get("file_id"),
        "roles": list(roles if roles is not None else prev.get("roles") or []),
        "user_id": user_id if user_id else prev.get("user_id") or "anonymous",
    }


def _ensure_fleet_columns(db: Session) -> None:
    for col in ("adk_json", "pubsub_json", "denied_tools_json"):
        try:
            db.execute(text(f"ALTER TABLE fleet_runs ADD COLUMN IF NOT EXISTS {col} TEXT"))
            db.commit()
        except Exception:
            db.rollback()
            try:
                db.execute(text(f"ALTER TABLE fleet_runs ADD COLUMN {col} TEXT"))
                db.commit()
            except Exception:
                db.rollback()


def _persist(
    db: Session,
    result: FleetResult,
    payload: dict,
    *,
    roles=None,
    user_id: str = "anonymous",
    raw_text=None,
    file_id=None,
) -> None:
    _ensure_fleet_columns(db)
    row = db.get(FleetRunModel, result.run_id)
    prev = {}
    if row is not None and row.payload_json:
        try:
            prev = json.loads(row.payload_json)
        except json.JSONDecodeError:
            prev = {}
    envelope = _wrap_payload(
        prev, payload, roles=roles, user_id=user_id, raw_text=raw_text, file_id=file_id
    )
    now = datetime.now(timezone.utc)
    body = {
        "tenant_id": result.tenant_id,
        "status": result.status,
        "decision": result.decision if result.decision is not None else "",
        "reason": result.reason,
        "invoice_id": result.invoice_id,
        "invoice_hash": result.invoice_hash,
        "payload_json": json.dumps(envelope, default=str),
        "events_json": json.dumps(result.events, default=str),
        "spans_json": json.dumps(result.spans, default=str),
        "armor_json": json.dumps(result.armor, default=str),
        "memory_json": json.dumps(result.memory_hits, default=str),
        "updated_at": now,
    }
    extras = {
        "adk_json": json.dumps(result.adk, default=str),
        "pubsub_json": json.dumps(result.pubsub, default=str),
        "denied_tools_json": json.dumps(result.denied_tools, default=str),
    }
    if row is None:
        row = FleetRunModel(id=result.run_id, created_at=now, **body)
        db.add(row)
    else:
        for k, v in body.items():
            setattr(row, k, v)
    for k, v in extras.items():
        if hasattr(row, k):
            try:
                setattr(row, k, v)
            except Exception:
                pass
    db.commit()


def get_run(db: Session, run_id: str, tenant_id: Optional[str] = None) -> Optional[dict]:
    row = db.get(FleetRunModel, run_id)
    if row is None:
        return None
    if tenant_id is not None and row.tenant_id != tenant_id:
        return None

    def _load(raw: Optional[str], default):
        if not raw:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    return {
        "run_id": row.id,
        "tenant_id": row.tenant_id,
        "status": row.status,
        "decision": row.decision,
        "reason": row.reason,
        "invoice_id": row.invoice_id,
        "invoice_hash": row.invoice_hash,
        "signed": row.decision == "SIGNED",
        "events": _load(row.events_json, []),
        "spans": _load(row.spans_json, []),
        "armor": _load(row.armor_json, {}),
        "memory_hits": _load(row.memory_json, {}),
        "payload": _unwrap_invoice(_load(row.payload_json, {})),
        "adk": _load(getattr(row, "adk_json", None), {}),
        "pubsub": _load(getattr(row, "pubsub_json", None), {}),
        "denied_tools": _load(getattr(row, "denied_tools_json", None), []),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def list_runs(db: Session, tenant_id: str, limit: int = 20) -> List[dict]:
    q = (
        db.query(FleetRunModel)
        .filter(FleetRunModel.tenant_id == tenant_id)
        .order_by(FleetRunModel.created_at.desc())
        .limit(max(1, min(limit, 100)))
    )
    rows = q.all()
    return [
        {
            "run_id": r.id,
            "tenant_id": r.tenant_id,
            "status": r.status,
            "decision": r.decision,
            "reason": r.reason,
            "invoice_hash": r.invoice_hash,
            "signed": r.decision == "SIGNED",
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def run_fleet_batch(
    *,
    db: Session,
    tenant_id: str,
    invoices: Sequence[dict],
    roles: Sequence[str] | None = None,
    user_id: str = "anonymous",
) -> List[FleetResult]:
    results: List[FleetResult] = []
    for inv in list(invoices)[:5]:
        results.append(
            run_fleet(
                db=db,
                tenant_id=tenant_id,
                roles=roles,
                user_id=user_id,
                invoice=inv,
            )
        )
    return results


def run_fleet(
    *,
    db: Session,
    tenant_id: str,
    roles: Sequence[str] | None = None,
    user_id: str = "anonymous",
    invoice: Optional[dict] = None,
    raw_text: Optional[str] = None,
    file_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> FleetResult:
    roles_t = gateway.normalize_roles(roles)
    run_id = run_id or str(uuid.uuid4())
    events: List[dict] = []
    spans = SpanRecorder()
    catalog = registry.list_agents(db)
    adk_info = adk_status()
    # Construct the ADK graph so the mandatory framework is on the path.
    adk_root = build_adk_root()
    adk_info = {**adk_info, "root_built": adk_root is not None}

    result = FleetResult(
        run_id=run_id,
        tenant_id=tenant_id,
        status="RUNNING",
        decision="ESCALATED",
        reason="",
        registry=catalog,
        adk=adk_info,
        denied_tools=gateway.denied_tools(roles_t),
    )
    payload = _extract_payload(invoice=invoice, raw_text=raw_text, file_id=file_id)
    result.status = "RUNNING"
    result.decision = result.decision or ""
    _persist(
        db, result, payload, roles=roles_t, user_id=user_id, raw_text=raw_text, file_id=file_id
    )

    with spans.span("gateway", tenant_id=tenant_id, user_id=user_id):
        _event(events, "gateway", "identity resolved", roles=list(roles_t), user_id=user_id)
        blob = armor.flatten_payload(payload) + "\n" + (raw_text or "")
        verdict = armor.inspect(blob)
        result.armor = {
            "allowed": verdict.allowed,
            "reasons": verdict.reasons,
            "classifier": verdict.classifier,
            "pii_hits": verdict.pii_hits,
            "redacted_preview": verdict.redacted_text[:240],
        }
        if not verdict.allowed:
            result.status = "COMPLETED"
            result.decision = "BLOCKED"
            result.reason = "Model Armor blocked prompt injection or tool poisoning"
            result.events = events
            result.spans = spans.timeline()
            _event(events, "armor", result.reason, reasons=verdict.reasons)
            _persist(
                db, result, payload, roles=roles_t, user_id=user_id, raw_text=raw_text, file_id=file_id
            )
            return result

    with spans.span("ingestion"):
        _event(events, "ingestion", "payload extracted", keys=sorted(payload.keys()))

    mem = memory_bank.read_all(db, tenant_id)
    result.memory_hits = mem

    with spans.span("fiscal_auditor"):
        hits = core_tools.search_normative("verifactu hash chain")
        _event(events, "fiscal_auditor", "normative search", hits=[h["id"] for h in hits])

        missing = [k for k in ("issuer_tax_id", "total_base", "total_tax", "total_amount") if k not in payload]
        if missing:
            result.decision = "ESCALATED"
            result.reason = f"missing fields: {missing}"
            _event(events, "fiscal_auditor", result.reason)
        else:
            nif_ok, nif_msg = core_tools.nif_status(str(payload.get("issuer_tax_id", "")))
            customer = payload.get("customer") or {}
            cust_tax = customer.get("tax_id") if isinstance(customer, dict) else None
            if cust_tax:
                cust_ok, cust_msg = core_tools.nif_status(str(cust_tax))
            else:
                cust_ok, cust_msg = False, "customer.tax_id missing"
            math_ok, math_msg = _math_ok(payload)
            hosp = _hospitality_blocked(payload, mem)

            if not nif_ok or not cust_ok:
                result.decision = "ESCALATED"
                result.reason = f"fiscal id failed: issuer={nif_msg} customer={cust_msg}"
            elif not math_ok:
                result.decision = "ESCALATED"
                result.reason = math_msg
            elif hosp:
                result.decision = "ESCALATED"
                result.reason = "Memory Bank deny_categories=hospitality matched this invoice"
            else:
                result.decision = "SIGNED"
                result.reason = "auditor PASS"
            _event(
                events,
                "fiscal_auditor",
                result.reason,
                math_ok=math_ok,
                hospitality_blocked=hosp,
            )

    # Gemini 3.5 + ADK consult: may tighten SIGN → ESCALATE, never loosen a gate.
    with spans.span("adk_consult", model=adk_info.get("model")):
        redacted, _hits = armor.redact_pii(armor.flatten_payload(payload))
        advice = adk_consult.consult(
            redacted_invoice=redacted,
            memory=mem,
            auditor_draft=f"{result.decision}: {result.reason}",
        )
        result.adk = {**result.adk, "consult": advice}
        _event(
            events,
            "fiscal_fleet_orchestrator",
            "gemini-3.5 consult",
            invoked=advice.get("invoked"),
            recommendation=advice.get("recommendation"),
        )
        reco = advice.get("recommendation")
        if result.decision == "SIGNED" and reco in {"ESCALATE", "BLOCK"}:
            result.decision = "ESCALATED"
            result.reason = f"ADK consult tightened to ESCALATE: {(advice.get('text') or '')[:160]}"
            _event(events, "fiscal_fleet_orchestrator", result.reason)

    if result.decision == "SIGNED":
        sign_gate = gateway.allows("invoice.sign", roles_t)
        if not sign_gate.allowed:
            with spans.span("escalation"):
                result.decision = "ESCALATED"
                result.reason = sign_gate.reason
                _event(events, "escalation", result.reason)
        else:
            with spans.span("signer"):
                try:
                    signed = core_tools.create_and_sign(db, tenant_id, payload)
                    result.invoice_id = signed.get("invoice_id")
                    result.invoice_hash = signed.get("invoice_hash")
                    result.signed = bool(signed.get("signed"))
                    if not result.signed:
                        result.decision = "ESCALATED"
                        result.reason = signed.get("error") or "sign failed"
                    _event(
                        events,
                        "signer",
                        "core_engine signed" if result.signed else result.reason,
                        invoice_id=result.invoice_id,
                        invoice_hash=result.invoice_hash,
                    )
                except HashContinuityError as exc:
                    result.decision = "ESCALATED"
                    result.reason = f"HASH_CHAIN_BROKEN:{exc}"
                    result.signed = False
                    _event(events, "signer", result.reason)
                except Exception as exc:
                    result.decision = "ESCALATED"
                    result.reason = f"signer error: {exc}"
                    result.signed = False
                    _event(events, "signer", result.reason)

    if result.decision != "SIGNED":
        with spans.span("escalation"):
            _event(events, "escalation", "human review queued", reason=result.reason)
            try:
                from core_engine.services.webhooks import WebhookEmitter

                WebhookEmitter(db).emit(
                    "fleet.escalated",
                    {
                        "run_id": run_id,
                        "tenant_id": tenant_id,
                        "reason": result.reason,
                        "decision": result.decision,
                    },
                )
            except Exception:
                pass

    result.status = "COMPLETED"
    result.events = events
    result.spans = spans.timeline()
    result.pubsub = {"published": False, "reason": "receipt-only; enqueue publishes invoice.received"}
    _persist(
        db, result, payload, roles=roles_t, user_id=user_id, raw_text=raw_text, file_id=file_id
    )
    return result
