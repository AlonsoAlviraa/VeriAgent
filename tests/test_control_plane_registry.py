"""PR-MT-01: Control-plane tenant registry, plans, feature flags, data-plane routing."""

from __future__ import annotations

import os
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core_engine.control_plane.feature_flags import PROD_AEAT_ENABLED, FeatureFlagService
from core_engine.control_plane.models import (
    DataPlaneBindingModel,
    FeatureFlagModel,
    PlanModel,
    TenantModel,
)
from core_engine.control_plane.registry import (
    PLAN_ENTERPRISE,
    PLAN_STANDARD,
    SHARED_CONNECTION_REF,
    TenantRegistry,
)
from core_engine.db.database import Base


@pytest.fixture()
def db_session():
    """In-memory SQLite control-plane only (no process maps, no Postgres required)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        PlanModel.__table__,
        TenantModel.__table__,
        DataPlaneBindingModel.__table__,
        FeatureFlagModel.__table__,
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine, tables=tables)
        engine.dispose()


def test_create_tenant_standard_tier(db_session):
    reg = TenantRegistry(db_session)
    tenant = reg.create_tenant(name="Acme SL", slug="acme", plan_id=PLAN_STANDARD)

    assert tenant.id
    assert tenant.plan_id == PLAN_STANDARD
    assert tenant.slug == "acme"

    resolution = reg.resolve_data_plane(tenant.id)
    assert resolution.tier == PLAN_STANDARD
    assert resolution.connection_ref == SHARED_CONNECTION_REF
    assert resolution.plan_id == PLAN_STANDARD


def test_create_tenant_enterprise_tier_binding(db_session):
    reg = TenantRegistry(db_session)
    tenant = reg.create_tenant(
        name="BigCorp SA",
        slug="bigcorp",
        plan_id=PLAN_ENTERPRISE,
        connection_ref="tenant:bigcorp-db-1",
    )

    resolution = reg.resolve_data_plane(tenant.id)
    assert resolution.tier == PLAN_ENTERPRISE
    assert resolution.connection_ref == "tenant:bigcorp-db-1"
    assert resolution.tenant_id == tenant.id


def test_feature_flag_prod_aeat_default_false(db_session):
    reg = TenantRegistry(db_session)
    standard = reg.create_tenant(name="Std Co", slug="std-co", plan_id=PLAN_STANDARD)
    enterprise = reg.create_tenant(
        name="Ent Co", slug="ent-co", plan_id=PLAN_ENTERPRISE
    )

    flags = FeatureFlagService(db_session)
    assert flags.get(standard.id, PROD_AEAT_ENABLED) is False
    # Enterprise also defaults false (fail-closed remittance)
    assert flags.get(enterprise.id, PROD_AEAT_ENABLED) is False

    # Explicit enable only via set()
    flags.set(enterprise.id, PROD_AEAT_ENABLED, True)
    db_session.commit()
    assert flags.get(enterprise.id, PROD_AEAT_ENABLED) is True
    assert flags.get(standard.id, PROD_AEAT_ENABLED) is False


def test_resolve_connection_ref_by_org_id(db_session):
    reg = TenantRegistry(db_session)
    tenant = reg.create_tenant(name="Route Me", slug="route-me")

    by_id = reg.resolve_data_plane(tenant.id)
    assert by_id.connection_ref == SHARED_CONNECTION_REF

    loaded = reg.get_tenant(tenant.id)
    assert loaded is not None
    assert loaded.slug == "route-me"

    with pytest.raises(KeyError):
        reg.resolve_data_plane("00000000-0000-0000-0000-000000000000")
