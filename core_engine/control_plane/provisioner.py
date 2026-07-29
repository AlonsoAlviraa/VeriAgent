"""
[PR-MT-04] DB-per-tenant provisioner: allocate + initialize a dedicated data
plane for enterprise tenants.

Responsabilidades (Sprint 7-9):
- Reservar una conexión física (sqlite local por defecto; postgres real en prod).
- Inicializar el schema del tenant (crear las tablas de data plane).
- Devolver una Engine SQLAlchemy lista para usar + referencias lógicas.
- Material de certificados: referencia lógica al vault (los secretos no entran
  en la tabla).
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from core_engine.control_plane.models import DataPlaneBindingModel, TenantModel
from core_engine.control_plane.registry import PLAN_ENTERPRISE

logger = logging.getLogger(__name__)


@dataclass
class ProvisionResult:
    tenant_id: str
    connection_ref: str
    cert_vault_ref: str
    database_url_hint: str
    engine: Optional[Engine] = None


def _build_tenant_engine(database_url: str) -> Engine:
    """Crea una Engine SQLAlchemy para el data plane del tenant."""
    return create_engine(database_url, future=True)


def _init_tenant_schema(engine: Engine) -> None:
    """Crea las tablas del data plane del tenant (mismo schema que el shared)."""
    from core_engine.db.database import Base
    # Importamos los modelos para que estén registrados en el metadata de Base.
    import core_engine.db.models  # noqa: F401
    import core_engine.control_plane.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


class TenantProvisioner:
    """Allocates a dedicated data plane for enterprise tenants."""

    def __init__(self, db: Session):
        self.db = db

    def provision_enterprise_db(
        self,
        tenant_id: str,
        *,
        sqlite_path: Optional[str] = None,
        database_url: Optional[str] = None,
        init_schema: bool = True,
    ) -> ProvisionResult:
        """
        Provisiona (o reaprovisiona) una DB dedicada para un tenant enterprise.

        Args:
            tenant_id: tenant a provisionar (debe ser plan enterprise).
            sqlite_path: path del .db sqlite (por defecto data/tenants/<slug>.db).
            database_url: URL explícita (ej. postgres); tiene prioridad sobre sqlite.
            init_schema: si True, crea las tablas en la nueva DB.
        """
        tenant = self.db.get(TenantModel, tenant_id)
        if tenant is None:
            raise KeyError(tenant_id)
        if tenant.plan_id != PLAN_ENTERPRISE:
            raise ValueError("Only enterprise tenants get dedicated DB provisioning")

        ref = f"tenant:{tenant.slug}:{uuid.uuid4().hex[:8]}"

        # Resolver URL física: postgres real > sqlite local.
        if database_url:
            url = database_url
        else:
            path = sqlite_path or os.path.join(
                os.getenv("TENANT_DB_DIR", "data/tenants"), f"{tenant.slug}.db"
            )
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            url = f"sqlite:///{path}"

        engine: Optional[Engine] = None
        if init_schema:
            try:
                engine = _build_tenant_engine(url)
                _init_tenant_schema(engine)
                logger.info("[Provisioner] Schema inicializado para tenant %s", tenant.slug)
            except Exception as exc:
                logger.error("[Provisioner] Fallo inicializando schema: %s", exc)
                engine = None

        binding = (
            self.db.query(DataPlaneBindingModel)
            .filter(DataPlaneBindingModel.tenant_id == tenant_id)
            .one_or_none()
        )
        if binding is None:
            binding = DataPlaneBindingModel(
                tenant_id=tenant_id, tier=PLAN_ENTERPRISE, connection_ref=ref
            )
            self.db.add(binding)
        else:
            binding.connection_ref = ref
            binding.tier = PLAN_ENTERPRISE
        self.db.commit()

        cert_ref = f"vault://tenants/{tenant.slug}/fnmt"
        return ProvisionResult(
            tenant_id=tenant_id,
            connection_ref=ref,
            cert_vault_ref=cert_ref,
            database_url_hint=url,
            engine=engine,
        )

    def healthcheck(self, result: ProvisionResult) -> bool:
        """Verifica que la DB provisionada responde (SELECT 1)."""
        engine = result.engine
        if engine is None:
            return False
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            return True
        except Exception as exc:
            logger.warning("[Provisioner] healthcheck failed: %s", exc)
            return False
