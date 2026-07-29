"""SQLAlchemy models for the multi-tenant control plane (DB-backed, no process maps)."""

from __future__ import annotations

import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    TIMESTAMP,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core_engine.db.database import Base


class PlanModel(Base):
    __tablename__ = "plans"

    id = Column(String(50), primary_key=True)  # standard | enterprise
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

    tenants = relationship("TenantModel", back_populates="plan")


class TenantModel(Base):
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    plan_id = Column(String(50), ForeignKey("plans.id"), nullable=False)
    status = Column(String(20), nullable=False, server_default="active")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now()
    )

    plan = relationship("PlanModel", back_populates="tenants")
    data_plane = relationship(
        "DataPlaneBindingModel",
        back_populates="tenant",
        uselist=False,
        cascade="all, delete-orphan",
    )
    feature_flags = relationship(
        "FeatureFlagModel",
        back_populates="tenant",
        cascade="all, delete-orphan",
    )


class DataPlaneBindingModel(Base):
    """Maps org/tenant → connection_ref + tier (shared RLS vs DB-per-tenant)."""

    __tablename__ = "data_plane_bindings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    tier = Column(String(20), nullable=False)  # standard | enterprise
    # Logical connection key (e.g. "shared-default" or "tenant:<uuid>"); not secrets
    connection_ref = Column(String(512), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    tenant = relationship("TenantModel", back_populates="data_plane")


class FeatureFlagModel(Base):
    __tablename__ = "feature_flags"
    __table_args__ = (
        UniqueConstraint("tenant_id", "flag_key", name="uq_tenant_flag"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    flag_key = Column(String(100), nullable=False)
    enabled = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now()
    )

    tenant = relationship("TenantModel", back_populates="feature_flags")


# ============================================
# WEBHOOKS (CORE-011) — durable outbox + retry + dead-letter
# ============================================

class WebhookSubscriptionModel(Base):
    __tablename__ = "webhook_subscriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(
        String(36),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url = Column(String(1024), nullable=False)
    # Lista de eventos a los que se suscribe (vacío = todos).
    events = Column(JSON, nullable=False, default=list)
    secret = Column(String(255))  # para HMAC signing del payload
    active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    deliveries = relationship(
        "WebhookDeliveryModel",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )


class WebhookDeliveryModel(Base):
    """Outbox de entregas: PENDING → DELIVERED | RETRY → DEAD_LETTER."""

    __tablename__ = "webhook_deliveries"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subscription_id = Column(
        String(36),
        ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default="PENDING", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=5)
    last_error = Column(Text)
    next_attempt_at = Column(TIMESTAMP)
    delivered_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    subscription = relationship("WebhookSubscriptionModel", back_populates="deliveries")
