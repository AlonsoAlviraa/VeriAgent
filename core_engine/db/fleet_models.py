"""VeriFleet tables: runs, agent catalog, per-tenant memory."""

from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, Index, String, Text
from sqlalchemy.sql import func

from .database import Base


class FleetRunModel(Base):
    __tablename__ = "fleet_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="RUNNING")
    decision = Column(String(20), nullable=False, default="ESCALATED")
    reason = Column(Text)
    invoice_id = Column(String(36))
    invoice_hash = Column(String(64))
    payload_json = Column(Text)
    events_json = Column(Text)
    spans_json = Column(Text)
    armor_json = Column(Text)
    memory_json = Column(Text)
    adk_json = Column(Text)
    pubsub_json = Column(Text)
    denied_tools_json = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AgentRegistryModel(Base):
    __tablename__ = "agent_registry"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String(64), nullable=False, unique=True)
    name = Column(String(120), nullable=False)
    version = Column(String(20), nullable=False)
    role = Column(Text, nullable=False)
    tools = Column(Text, nullable=False, default="")
    model = Column(String(80), nullable=False)
    status = Column(String(20), nullable=False, default="published")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class AgentMemoryModel(Base):
    __tablename__ = "agent_memories"
    __table_args__ = (
        Index("uq_agent_memory_tenant_key", "tenant_id", "key", unique=True),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False)
    key = Column(String(120), nullable=False)
    value = Column(Text, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
