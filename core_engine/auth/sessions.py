"""
[MT-05 / Sprint 7] Durable session service with persistent 2FA state.

Reemplaza el estado 2FA efímero en JWT por persistencia en tabla user_sessions.
Permite exigir 2FA por sesión con expiración (trusted devices: 30 días; TOTP:
por sesión).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from core_engine.auth.models import SessionModel

# Trusted-device: 30 días. TOTP por sesión: sin expiración larga por defecto.
TRUSTED_DEVICE_TTL = timedelta(days=30)
TOTP_SESSION_TTL = timedelta(hours=8)


class SessionService:
    def __init__(self, db: Session):
        self.db = db

    def create_session(
        self,
        user_id: str,
        active_tenant_id: str,
        roles: List[str],
        *,
        expires_at: Optional[datetime] = None,
    ) -> SessionModel:
        session = SessionModel(
            user_id=user_id,
            active_tenant_id=active_tenant_id,
            roles_json=json.dumps(roles),
            expires_at=expires_at,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get(self, session_id: str) -> Optional[SessionModel]:
        return self.db.get(SessionModel, session_id)

    def mark_2fa_verified(
        self,
        session_id: str,
        method: str = "totp",
        *,
        ttl: Optional[timedelta] = None,
    ) -> Optional[SessionModel]:
        """
        Marca la sesión como verificada con 2FA.

        Args:
            method: 'totp' o 'trusted_device'.
            ttl: validez de la verificación. Default según método.
        """
        session = self.get(session_id)
        if session is None:
            return None
        if ttl is None:
            ttl = TRUSTED_DEVICE_TTL if method == "trusted_device" else TOTP_SESSION_TTL
        now = datetime.now(timezone.utc)
        session.twofa_verified_at = now
        session.twofa_expires_at = now + ttl
        session.twofa_method = method
        self.db.commit()
        self.db.refresh(session)
        return session

    def is_2fa_active(self, session_id: str) -> bool:
        """True si la sesión tiene 2FA verificado y no expirado."""
        session = self.get(session_id)
        return self._is_active(session)

    @staticmethod
    def _is_active(session: Optional[SessionModel]) -> bool:
        if session is None or session.twofa_verified_at is None:
            return False
        if session.twofa_expires_at is None:
            return True
        # Comparar en UTC aware.
        exp = session.twofa_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) < exp

    def revoke_2fa(self, session_id: str) -> None:
        session = self.get(session_id)
        if session is not None:
            session.twofa_verified_at = None
            session.twofa_expires_at = None
            self.db.commit()

    def require_2fa(self, session_id: str) -> SessionModel:
        """
        Devuelve la sesión si 2FA está activo; lanza ValueError en caso contrario.
        Útil como guard en endpoints sensibles.
        """
        session = self.get(session_id)
        if not self._is_active(session):
            raise PermissionError("2FA_REQUIRED")
        return session  # type: ignore[return-value]
