"""
Tests para SessionService con 2FA persistente (MT-05 / Sprint 7).

Verifica:
- create_session persiste la sesión.
- mark_2fa_verified fija verificación con expiración según método.
- is_2fa_active refleja el estado y la expiración.
- revoke_2fa y require_2fa (guard).
"""

from datetime import datetime, timedelta, timezone

import pytest

from core_engine.auth.sessions import (
    SessionService,
    TRUSTED_DEVICE_TTL,
    TOTP_SESSION_TTL,
)
from core_engine.db.database import SessionLocal, init_db


@pytest.fixture
def db():
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        from core_engine.auth.models import SessionModel
        session.query(SessionModel).delete()
        session.commit()
        session.close()


class TestSession2FA:
    def test_session_without_2fa_is_not_active(self, db):
        svc = SessionService(db)
        s = svc.create_session("user-1", "tenant-1", ["issuer"])
        assert svc.is_2fa_active(s.id) is False

    def test_totp_verification_active_within_ttl(self, db):
        svc = SessionService(db)
        s = svc.create_session("user-1", "tenant-1", ["issuer"])
        svc.mark_2fa_verified(s.id, method="totp")
        assert svc.is_2fa_active(s.id) is True

    def test_trusted_device_ttl_is_30_days(self, db):
        svc = SessionService(db)
        s = svc.create_session("user-1", "tenant-1", ["admin"])
        svc.mark_2fa_verified(s.id, method="trusted_device")
        refreshed = svc.get(s.id)
        # La expiración debe estar ~30 días en el futuro.
        delta = refreshed.twofa_expires_at.replace(tzinfo=None) - datetime.utcnow()
        assert timedelta(days=29) < delta < timedelta(days=31)

    def test_expired_2fa_is_inactive(self, db):
        svc = SessionService(db)
        s = svc.create_session("user-1", "tenant-1", ["issuer"])
        # Marcar con TTL ya vencido.
        svc.mark_2fa_verified(s.id, method="totp", ttl=timedelta(seconds=-1))
        assert svc.is_2fa_active(s.id) is False

    def test_revoke_clears_2fa(self, db):
        svc = SessionService(db)
        s = svc.create_session("user-1", "tenant-1", ["issuer"])
        svc.mark_2fa_verified(s.id, method="totp")
        assert svc.is_2fa_active(s.id) is True
        svc.revoke_2fa(s.id)
        assert svc.is_2fa_active(s.id) is False

    def test_require_2fa_raises_when_not_active(self, db):
        svc = SessionService(db)
        s = svc.create_session("user-1", "tenant-1", ["issuer"])
        with pytest.raises(PermissionError, match="2FA_REQUIRED"):
            svc.require_2fa(s.id)

    def test_require_2fa_returns_session_when_active(self, db):
        svc = SessionService(db)
        s = svc.create_session("user-1", "tenant-1", ["issuer"])
        svc.mark_2fa_verified(s.id, method="totp")
        active = svc.require_2fa(s.id)
        assert active.id == s.id

    def test_ttl_constants(self):
        assert TRUSTED_DEVICE_TTL == timedelta(days=30)
        assert TOTP_SESSION_TTL == timedelta(hours=8)
