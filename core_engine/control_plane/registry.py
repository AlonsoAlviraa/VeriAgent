"""
Tenant registry: create/read orgs and resolve data-plane routing metadata.

Does not read or write invoice hash chains (data-plane concern).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from .feature_flags import PROD_AEAT_ENABLED, FeatureFlagService
from .models import DataPlaneBindingModel, PlanModel, TenantModel

PLAN_STANDARD = "standard"
PLAN_ENTERPRISE = "enterprise"
SHARED_CONNECTION_REF = "shared-default"


@dataclass(frozen=True)
class DataPlaneResolution:
    tenant_id: str
    plan_id: str
    tier: str
    connection_ref: str


class TenantRegistry:
    def __init__(self, db: Session):
        self.db = db
        self.flags = FeatureFlagService(db)

    def ensure_plans_seeded(self) -> None:
        """Idempotent seed of standard/enterprise plan rows."""
        seeds = [
            (PLAN_STANDARD, "Standard", "Shared Postgres + RLS multi-tenant tier"),
            (
                PLAN_ENTERPRISE,
                "Enterprise",
                "DB-per-tenant data plane for regulated cohorts",
            ),
        ]
        for plan_id, name, desc in seeds:
            if self.db.get(PlanModel, plan_id) is None:
                self.db.add(
                    PlanModel(id=plan_id, name=name, description=desc)
                )
        self.db.flush()

    def create_tenant(
        self,
        *,
        name: str,
        slug: str,
        plan_id: str = PLAN_STANDARD,
        connection_ref: Optional[str] = None,
    ) -> TenantModel:
        """
        Create a tenant with plan, data-plane binding, and default feature flags.

        PROD_AEAT_ENABLED is always defaulted to False (including enterprise).
        Non-enterprise tiers cannot enable production remittance without explicit
        promotion controls (later PR).
        """
        self.ensure_plans_seeded()
        if plan_id not in (PLAN_STANDARD, PLAN_ENTERPRISE):
            raise ValueError(f"Unknown plan_id: {plan_id}")
        if self.db.get(PlanModel, plan_id) is None:
            raise ValueError(f"Plan not found: {plan_id}")

        existing = (
            self.db.query(TenantModel)
            .filter(TenantModel.slug == slug)
            .one_or_none()
        )
        if existing is not None:
            raise ValueError(f"Tenant slug already exists: {slug}")

        tier = PLAN_ENTERPRISE if plan_id == PLAN_ENTERPRISE else PLAN_STANDARD
        if connection_ref is None:
            if tier == PLAN_ENTERPRISE:
                # Placeholder; PR-MT-04 provisioner will allocate a real DB ref.
                connection_ref = f"tenant-pending:{slug}"
            else:
                connection_ref = SHARED_CONNECTION_REF

        tenant = TenantModel(name=name, slug=slug, plan_id=plan_id, status="active")
        self.db.add(tenant)
        self.db.flush()

        binding = DataPlaneBindingModel(
            tenant_id=tenant.id,
            tier=tier,
            connection_ref=connection_ref,
        )
        self.db.add(binding)

        # Fail-closed default for production AEAT (all tiers)
        self.flags.ensure_default(tenant.id, PROD_AEAT_ENABLED, enabled=False)

        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[TenantModel]:
        return self.db.get(TenantModel, tenant_id)

    def get_tenant_by_slug(self, slug: str) -> Optional[TenantModel]:
        return (
            self.db.query(TenantModel)
            .filter(TenantModel.slug == slug)
            .one_or_none()
        )

    def resolve_data_plane(self, tenant_id: str) -> DataPlaneResolution:
        tenant = self.get_tenant(tenant_id)
        if tenant is None:
            raise KeyError(f"Unknown tenant_id: {tenant_id}")
        binding = (
            self.db.query(DataPlaneBindingModel)
            .filter(DataPlaneBindingModel.tenant_id == tenant_id)
            .one_or_none()
        )
        if binding is None:
            raise RuntimeError(f"No data_plane_binding for tenant {tenant_id}")
        return DataPlaneResolution(
            tenant_id=tenant.id,
            plan_id=tenant.plan_id,
            tier=binding.tier,
            connection_ref=binding.connection_ref,
        )
