"""
Tests para el outbox durable de webhooks (CORE-011).

Verifica:
- El emisor durable encola entregas PENDING por suscripción activa del tenant.
- process_pending entrega, reintenta con backoff y marca DEAD_LETTER tras
  max_attempts.
- Filtrado por evento (events vacío = todos) y por suscripción inactiva.
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from core_engine.db.database import SessionLocal, init_db
from core_engine.control_plane.models import (
    PlanModel,
    TenantModel,
    WebhookDeliveryModel,
    WebhookSubscriptionModel,
)
from core_engine.services.webhooks import WebhookEmitter, _compute_backoff, _sign_payload


@pytest.fixture
def db():
    """DB sqlite en memoria para tests de outbox."""
    init_db()
    session = SessionLocal()
    # Sembrar plan + tenant para poder crear suscripciones.
    if session.get(PlanModel, "standard") is None:
        session.add(PlanModel(id="standard", name="Standard"))
    tenant = TenantModel(slug="wh-tenant", name="WH Tenant", plan_id="standard")
    session.add(tenant)
    session.commit()
    session.refresh(tenant)
    try:
        yield session, tenant.id
    finally:
        session.query(WebhookDeliveryModel).delete()
        session.query(WebhookSubscriptionModel).delete()
        session.query(TenantModel).delete()
        session.commit()
        session.close()


def _add_subscription(db, tenant_id, *, url="http://example.com/hook", events=None, active=True):
    sub = WebhookSubscriptionModel(
        tenant_id=tenant_id, url=url, events=events or [], active=active,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


class TestBackoffAndSign:
    def test_backoff_grows_exponentially(self):
        t0 = _compute_backoff(1)
        t3 = _compute_backoff(3)
        # attempt 3 debe programarse más lejos que attempt 1.
        assert t3 > t0

    def test_sign_payload_hmac(self):
        sig = _sign_payload(b"abc", "secret")
        # HMAC-SHA256 → 64 hex chars.
        assert len(sig) == 64
        assert sig != _sign_payload(b"abc", "other")


class TestEmitEnqueuesDeliveries:
    def test_emit_creates_pending_deliveries_for_active_subs(self, db):
        session, tenant_id = db
        _add_subscription(session, tenant_id)
        _add_subscription(session, tenant_id, url="http://example.com/other")

        emitter = WebhookEmitter(db=session)
        emitter.emit("invoice.validated", {"invoice_id": "1", "tenant_id": tenant_id})

        pendings = session.query(WebhookDeliveryModel).filter_by(status="PENDING").all()
        assert len(pendings) == 2
        for p in pendings:
            assert p.event == "invoice.validated"
            assert p.attempts == 0

    def test_emit_without_tenant_does_not_enqueue(self, db):
        session, _ = db
        emitter = WebhookEmitter(db=session)
        emitter.emit("invoice.validated", {"invoice_id": "1"})  # sin tenant_id
        assert session.query(WebhookDeliveryModel).count() == 0

    def test_inactive_subscription_is_skipped(self, db):
        session, tenant_id = db
        _add_subscription(session, tenant_id, active=False)
        emitter = WebhookEmitter(db=session)
        emitter.emit("invoice.signed", {"tenant_id": tenant_id})
        assert session.query(WebhookDeliveryModel).count() == 0

    def test_event_filter_excludes_non_matching(self, db):
        session, tenant_id = db
        # Suscripción solo a 'invoice.signed'.
        _add_subscription(session, tenant_id, events=["invoice.signed"])
        emitter = WebhookEmitter(db=session)
        # Emitimos un evento distinto → no se encola.
        emitter.emit("invoice.validated", {"tenant_id": tenant_id})
        assert session.query(WebhookDeliveryModel).count() == 0
        # Evento matching → se encola.
        emitter.emit("invoice.signed", {"tenant_id": tenant_id})
        assert session.query(WebhookDeliveryModel).count() == 1


class TestProcessPending:
    def test_successful_delivery(self, db):
        session, tenant_id = db
        sub = _add_subscription(session, tenant_id)
        emitter = WebhookEmitter(db=session)
        emitter.emit("invoice.signed", {"tenant_id": tenant_id})

        with patch("core_engine.services.webhooks._deliver_once", return_value=(True, None)):
            stats = emitter.process_pending()

        assert stats["delivered"] == 1
        d = session.query(WebhookDeliveryModel).one()
        assert d.status == "DELIVERED"
        assert d.delivered_at is not None
        assert d.attempts == 1

    def test_retry_then_succeed(self, db):
        session, tenant_id = db
        _add_subscription(session, tenant_id)
        emitter = WebhookEmitter(db=session)
        emitter.emit("invoice.signed", {"tenant_id": tenant_id})

        # Primera llamada falla, segunda ok.
        calls = {"i": 0}

        def fake_deliver(url, secret, event, payload):
            calls["i"] += 1
            return (True, None) if calls["i"] >= 2 else (False, "boom")

        with patch("core_engine.services.webhooks._deliver_once", side_effect=fake_deliver):
            stats1 = emitter.process_pending()
        assert stats1["retried"] == 1
        d = session.query(WebhookDeliveryModel).one()
        assert d.status == "RETRY"
        assert d.attempts == 1
        assert d.last_error == "boom"

        # Forzar que next_attempt_at esté en el pasado para procesar ahora.
        d.next_attempt_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        session.commit()

        with patch("core_engine.services.webhooks._deliver_once", side_effect=fake_deliver):
            stats2 = emitter.process_pending()
        assert stats2["delivered"] == 1
        session.refresh(d)
        assert d.status == "DELIVERED"
        assert d.attempts == 2

    def test_dead_letter_after_max_attempts(self, db):
        session, tenant_id = db
        sub = _add_subscription(session, tenant_id)
        emitter = WebhookEmitter(db=session)
        emitter.emit("invoice.signed", {"tenant_id": tenant_id})

        # Forzar max_attempts=2 para agotar rápido.
        d = session.query(WebhookDeliveryModel).one()
        d.max_attempts = 2
        session.commit()

        with patch("core_engine.services.webhooks._deliver_once", return_value=(False, "perm fail")):
            emitter.process_pending()  # attempt 1 → RETRY
            d.next_attempt_at = datetime.now(timezone.utc) - timedelta(minutes=1)
            session.commit()
            emitter.process_pending()  # attempt 2 → DEAD_LETTER

        session.refresh(d)
        assert d.status == "DEAD_LETTER"
        assert d.attempts == 2

    def test_process_pending_without_db_is_noop(self):
        emitter = WebhookEmitter(db=None)
        stats = emitter.process_pending()
        assert stats == {"delivered": 0, "retried": 0, "dead_lettered": 0, "errors": 0}
