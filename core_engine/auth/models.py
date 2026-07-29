"""Durable session + org membership for multi-org RBAC (MT-05)."""

from __future__ import annotations

import uuid

from sqlalchemy import Column, String, TIMESTAMP, Text
from sqlalchemy.sql import func

from core_engine.db.database import Base


class OrgMembershipModel(Base):
    __tablename__ = "org_memberships"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(36), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # issuer | auditor | admin
    created_at = Column(TIMESTAMP, server_default=func.now())


class SessionModel(Base):
    """
    Sesión durable de usuario.

    Persiste el estado de 2FA (deuda explícita del README: antes vivía solo en
    JWT). twofa_verified_at + twofa_expires_at permiten exigir re-verificación
    periódica sin perder la sesión.
    """

    __tablename__ = "user_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), nullable=False, index=True)
    active_tenant_id = Column(String(36), nullable=False)
    roles_json = Column(Text, nullable=False, default="[]")
    created_at = Column(TIMESTAMP, server_default=func.now())
    expires_at = Column(TIMESTAMP, nullable=True)
    # 2FA persistente (TOTP / trusted-device).
    twofa_verified_at = Column(TIMESTAMP, nullable=True)
    twofa_expires_at = Column(TIMESTAMP, nullable=True)
    twofa_method = Column(String(20), nullable=True)  # totp | trusted_device
