"""Memory Bank: durable per-tenant key/value used across fleet runs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy.orm import Session

from core_engine.db.fleet_models import AgentMemoryModel

# Demo seed: enterprise tenant refuses hospitality invoices.
DEFAULT_SEEDS = {
    "enterprise-demo": {
        "deny_categories": "hospitality",
        "default_vat": "21",
    }
}


def seed_defaults(db: Session, tenant_id: str) -> None:
    defaults = DEFAULT_SEEDS.get(tenant_id)
    if not defaults:
        return
    for key, value in defaults.items():
        if read(db, tenant_id, key) is None:
            write(db, tenant_id, key, value)


def read(db: Session, tenant_id: str, key: str) -> Optional[str]:
    row = (
        db.query(AgentMemoryModel)
        .filter(
            AgentMemoryModel.tenant_id == tenant_id,
            AgentMemoryModel.key == key,
        )
        .one_or_none()
    )
    return None if row is None else row.value


def read_all(db: Session, tenant_id: str) -> Dict[str, str]:
    seed_defaults(db, tenant_id)
    rows = (
        db.query(AgentMemoryModel)
        .filter(AgentMemoryModel.tenant_id == tenant_id)
        .all()
    )
    return {r.key: r.value for r in rows}


def write(db: Session, tenant_id: str, key: str, value: str) -> AgentMemoryModel:
    row = (
        db.query(AgentMemoryModel)
        .filter(
            AgentMemoryModel.tenant_id == tenant_id,
            AgentMemoryModel.key == key,
        )
        .one_or_none()
    )
    now = datetime.now(timezone.utc)
    if row is None:
        row = AgentMemoryModel(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            key=key,
            value=value,
            updated_at=now,
        )
        db.add(row)
    else:
        row.value = value
        row.updated_at = now
    db.commit()
    db.refresh(row)
    return row
