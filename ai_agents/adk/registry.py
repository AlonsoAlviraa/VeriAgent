"""Agent Registry: catalog + semver for the four fleet agents.

This is not the tenant registry. Tenants live in control_plane.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List

from sqlalchemy.orm import Session

from core_engine.db.fleet_models import AgentRegistryModel

from .config import GEMINI_MODEL

CATALOG = (
    {
        "agent_id": "ingestion",
        "name": "IngestionAgent",
        "version": "1.0.0",
        "role": "Extract structured invoice fields from PDF/XML/text.",
        "tools": ["ocr.extract"],
        "model": GEMINI_MODEL,
    },
    {
        "agent_id": "fiscal_auditor",
        "name": "FiscalAuditorAgent",
        "version": "1.0.0",
        "role": "Validate math, NIF, and tenant policy. Never signs.",
        "tools": ["normative.search", "memory.read"],
        "model": GEMINI_MODEL,
    },
    {
        "agent_id": "signer",
        "name": "SignerAgent",
        "version": "1.0.0",
        "role": "Call core_engine create/sign only after auditor PASS.",
        "tools": ["invoice.create", "invoice.sign"],
        "model": GEMINI_MODEL,
    },
    {
        "agent_id": "escalation",
        "name": "EscalationAgent",
        "version": "1.0.0",
        "role": "Queue human review and emit webhook. Never signs.",
        "tools": ["memory.read"],
        "model": GEMINI_MODEL,
    },
)


def seed_catalog(db: Session) -> List[AgentRegistryModel]:
    now = datetime.now(timezone.utc)
    rows: List[AgentRegistryModel] = []
    for spec in CATALOG:
        row = (
            db.query(AgentRegistryModel)
            .filter(AgentRegistryModel.agent_id == spec["agent_id"])
            .one_or_none()
        )
        if row is None:
            row = AgentRegistryModel(
                id=str(uuid.uuid4()),
                agent_id=spec["agent_id"],
                name=spec["name"],
                version=spec["version"],
                role=spec["role"],
                tools=",".join(spec["tools"]),
                model=spec["model"],
                status="published",
                updated_at=now,
            )
            db.add(row)
        else:
            row.version = spec["version"]
            row.role = spec["role"]
            row.tools = ",".join(spec["tools"])
            row.model = spec["model"]
            row.status = "published"
            row.updated_at = now
        rows.append(row)
    db.commit()
    return rows


def list_agents(db: Session) -> List[dict]:
    seed_catalog(db)
    rows = db.query(AgentRegistryModel).order_by(AgentRegistryModel.agent_id).all()
    return [
        {
            "agent_id": r.agent_id,
            "name": r.name,
            "version": r.version,
            "role": r.role,
            "tools": [t for t in (r.tools or "").split(",") if t],
            "model": r.model,
            "status": r.status,
        }
        for r in rows
    ]
