"""
Tests para TenantProvisioner (PR-MT-04 / Sprint 7).

Verifica:
- Provisiona una DB dedicada para tenant enterprise (sqlite local).
- Inicializa el schema (tablas creadas y operativas).
- healthcheck responde SELECT 1.
- Rechaza tenants non-enterprise.
- Idempotente: reaprovisionar actualiza el binding.
"""

import os

import pytest
from sqlalchemy import text

from core_engine.control_plane.provisioner import TenantProvisioner
from core_engine.control_plane.registry import TenantRegistry, PLAN_ENTERPRISE
from core_engine.db.database import SessionLocal, init_db


@pytest.fixture
def db():
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _make_enterprise_tenant(db):
    reg = TenantRegistry(db)
    tenant = reg.create_tenant(name="Ent Tenant", slug=f"ent-{os.urandom(3).hex()}", plan_id=PLAN_ENTERPRISE)
    return tenant


class TestProvisioner:
    def test_provision_creates_engine_and_schema(self, db, tmp_path):
        tenant = _make_enterprise_tenant(db)
        sqlite_path = str(tmp_path / "tenant.db")
        prov = TenantProvisioner(db)
        result = prov.provision_enterprise_db(tenant.id, sqlite_path=sqlite_path)

        assert result.tenant_id == tenant.id
        assert result.engine is not None
        assert result.connection_ref.startswith("tenant:")
        assert result.cert_vault_ref.startswith("vault://")
        assert os.path.exists(sqlite_path)

        # El schema debe estar inicializado: la tabla chain_tips debe existir.
        with result.engine.connect() as conn:
            tables = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            ).fetchall()
            names = {t[0] for t in tables}
            assert "chain_tips" in names
            assert "invoices" in names

    def test_healthcheck_passes_after_provision(self, db, tmp_path):
        tenant = _make_enterprise_tenant(db)
        prov = TenantProvisioner(db)
        result = prov.provision_enterprise_db(tenant.id, sqlite_path=str(tmp_path / "h.db"))
        assert prov.healthcheck(result) is True

    def test_healthcheck_fails_without_engine(self, db, tmp_path):
        tenant = _make_enterprise_tenant(db)
        prov = TenantProvisioner(db)
        result = prov.provision_enterprise_db(
            tenant.id, sqlite_path=str(tmp_path / "x.db"), init_schema=False
        )
        assert result.engine is None
        assert prov.healthcheck(result) is False

    def test_rejects_non_enterprise_tenant(self, db):
        reg = TenantRegistry(db)
        tenant = reg.create_tenant(name="Std", slug=f"std-{os.urandom(3).hex()}", plan_id="standard")
        prov = TenantProvisioner(db)
        with pytest.raises(ValueError, match="enterprise"):
            prov.provision_enterprise_db(tenant.id, sqlite_path=":memory:")

    def test_provision_updates_binding_connection_ref(self, db, tmp_path):
        tenant = _make_enterprise_tenant(db)
        prov = TenantProvisioner(db)
        r1 = prov.provision_enterprise_db(tenant.id, sqlite_path=str(tmp_path / "a.db"))
        r2 = prov.provision_enterprise_db(tenant.id, sqlite_path=str(tmp_path / "b.db"))
        # El connection_ref regenera, pero el binding sigue siendo único.
        assert r1.connection_ref != r2.connection_ref
