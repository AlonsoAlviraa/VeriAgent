"""
[PR-MT-03] Hybrid data-plane resolver → SessionLocal factory per tenant.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core_engine.control_plane.registry import SHARED_CONNECTION_REF, TenantRegistry
from core_engine.db.database import SessionLocal, engine as default_engine


@dataclass
class ResolvedSession:
    tenant_id: str
    tier: str
    connection_ref: str
    session_factory: sessionmaker


class DataPlaneResolver:
    """
    Maps tenant → connection_ref → SQLAlchemy session factory.
    Enterprise refs can point at alternate SQLite/Postgres URLs via env
    DATA_PLANE_<REF> or tenant-specific provisioner registry.
    """

    def __init__(self, control_db: Session):
        self.control_db = control_db
        self.registry = TenantRegistry(control_db)
        self._factories: Dict[str, sessionmaker] = {
            SHARED_CONNECTION_REF: SessionLocal,
            "default": SessionLocal,
        }

    def register_connection(self, connection_ref: str, database_url: str) -> None:
        eng = create_engine(
            database_url,
            connect_args={"check_same_thread": False}
            if database_url.startswith("sqlite")
            else {},
        )
        self._factories[connection_ref] = sessionmaker(
            autocommit=False, autoflush=False, bind=eng
        )

    def resolve(self, tenant_id: str) -> ResolvedSession:
        res = self.registry.resolve_data_plane(tenant_id)
        factory = self._factories.get(res.connection_ref)
        if factory is None:
            # Env override: DATA_PLANE_URL__tenant-pending:slug or generic map
            env_key = "DATA_PLANE_URL__" + res.connection_ref.replace(":", "_").replace(
                "-", "_"
            )
            url = os.getenv(env_key) or os.getenv("DATABASE_URL")
            if url:
                self.register_connection(res.connection_ref, url)
                factory = self._factories[res.connection_ref]
            else:
                factory = SessionLocal
        return ResolvedSession(
            tenant_id=res.tenant_id,
            tier=res.tier,
            connection_ref=res.connection_ref,
            session_factory=factory,
        )

    def session_for_tenant(self, tenant_id: str) -> Session:
        resolved = self.resolve(tenant_id)
        return resolved.session_factory()
