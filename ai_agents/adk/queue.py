"""Durable fleet queue: fleet_runs rows + optional FIFO thread / Pub/Sub push."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from ai_agents.adk import gateway, pubsub
from ai_agents.adk.runtime import (
    FleetResult,
    _ensure_fleet_columns,
    _unwrap_invoice,
    _wrap_payload,
    get_run,
    run_fleet,
)
from core_engine.db.database import SessionLocal
from core_engine.db.fleet_models import FleetRunModel

logger = logging.getLogger(__name__)
LEASE_SECONDS = 60
_COND = threading.Condition()
_QUEUE: list[str] = []
_WORKER_STARTED = False


class FleetInFlight(Exception):
    """Row is RUNNING inside the lease; Pub/Sub must retry (HTTP 503)."""


def _dispatch_off() -> bool:
    return os.getenv("VERIFLEET_QUEUE_DISPATCH", "1").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }


def _pubsub_push() -> bool:
    return os.getenv("VERIFLEET_PUBSUB_PUSH", "").strip().lower() in {"1", "true", "yes"}


def _queue_label() -> str:
    if _dispatch_off():
        return "test"
    if pubsub.topic_name() and _pubsub_push():
        return "pubsub"
    return "thread"


def enqueue(
    *,
    db: Session,
    tenant_id: str,
    roles: Sequence[str] | None,
    user_id: str,
    invoice: dict | None,
    raw_text: str | None,
    file_id: str | None,
    run_id: str | None = None,
) -> FleetResult:
    _ensure_fleet_columns(db)
    rid = run_id or str(uuid.uuid4())
    roles_t = list(gateway.normalize_roles(roles))
    envelope = _wrap_payload(
        None,
        invoice or {},
        roles=roles_t,
        user_id=user_id,
        raw_text=raw_text,
        file_id=file_id,
    )
    now = datetime.now(timezone.utc)
    row = FleetRunModel(
        id=rid,
        tenant_id=tenant_id,
        status="QUEUED",
        decision="",
        reason="",
        payload_json=json.dumps(envelope, default=str),
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()

    published = {"published": False, "reason": "not dispatched"}
    if not _dispatch_off():
        if pubsub.topic_name() and _pubsub_push():
            published = pubsub.publish(
                "invoice.received",
                {
                    "run_id": rid,
                    "tenant_id": tenant_id,
                    "invoice": invoice,
                    "raw_text": raw_text,
                    "file_id": file_id,
                    "roles": roles_t,
                    "user_id": user_id,
                },
            )
        else:
            _offer(rid)

    result = FleetResult(
        run_id=rid,
        tenant_id=tenant_id,
        status="QUEUED",
        decision="",
        reason="",
        pubsub=published,
    )
    return result


def execute(run_id: str, db: Session | None = None) -> FleetResult:
    own = db is None
    session = db or SessionLocal()
    try:
        _ensure_fleet_columns(session)
        row = session.get(FleetRunModel, run_id)
        if row is None:
            raise KeyError(run_id)
        now = datetime.now(timezone.utc)
        if row.status == "COMPLETED":
            loaded = get_run(session, run_id)
            return _result_from_row(loaded)

        if row.status == "RUNNING" and row.updated_at:
            updated = row.updated_at
            if updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            if now - updated < timedelta(seconds=LEASE_SECONDS):
                raise FleetInFlight(run_id)

        env = {}
        if row.payload_json:
            try:
                env = json.loads(row.payload_json)
            except json.JSONDecodeError:
                env = {}
        invoice = _unwrap_invoice(env)
        roles = env.get("roles")
        user_id = env.get("user_id") or "anonymous"
        return run_fleet(
            db=session,
            tenant_id=row.tenant_id,
            roles=roles,
            user_id=user_id,
            invoice=invoice if invoice else None,
            raw_text=env.get("raw_text"),
            file_id=env.get("file_id"),
            run_id=run_id,
        )
    finally:
        if own:
            session.close()


def _result_from_row(loaded: Optional[dict]) -> FleetResult:
    loaded = loaded or {}
    return FleetResult(
        run_id=loaded.get("run_id") or "",
        tenant_id=loaded.get("tenant_id") or "",
        status=loaded.get("status") or "COMPLETED",
        decision=loaded.get("decision") or "",
        reason=loaded.get("reason") or "",
        invoice_id=loaded.get("invoice_id"),
        invoice_hash=loaded.get("invoice_hash"),
        signed=bool(loaded.get("signed")),
        events=loaded.get("events") or [],
        spans=loaded.get("spans") or [],
        armor=loaded.get("armor") or {},
        memory_hits=loaded.get("memory_hits") or {},
        adk=loaded.get("adk") or {},
        denied_tools=loaded.get("denied_tools") or [],
        pubsub=loaded.get("pubsub") or {},
    )


def _offer(run_id: str) -> None:
    global _WORKER_STARTED
    with _COND:
        _QUEUE.append(run_id)
        if not _WORKER_STARTED:
            _WORKER_STARTED = True
            threading.Thread(target=_drain, name="verifleet-fifo", daemon=True).start()
        _COND.notify()


def _drain() -> None:
    while True:
        with _COND:
            while not _QUEUE:
                _COND.wait()
            rid = _QUEUE.pop(0)
        try:
            execute(rid)
        except FleetInFlight:
            logger.info("fleet run %s still in flight", rid)
            time.sleep(0.4)
            with _COND:
                _QUEUE.append(rid)
                _COND.notify()
        except Exception:
            logger.exception("fleet worker failed for %s", rid)
            _mark_worker_error(rid)


def _mark_worker_error(run_id: str) -> None:
    session = SessionLocal()
    try:
        row = session.get(FleetRunModel, run_id)
        if row is None or row.status == "COMPLETED":
            return
        row.status = "COMPLETED"
        row.decision = "ESCALATED"
        row.reason = "worker error: execute failed"
        row.updated_at = datetime.now(timezone.utc)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
