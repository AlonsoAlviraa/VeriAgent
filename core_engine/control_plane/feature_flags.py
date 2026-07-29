"""Per-tenant feature flags stored in the control-plane DB."""

from __future__ import annotations

from sqlalchemy.orm import Session

from .models import FeatureFlagModel

# Canonical flag: production AEAT remittance (always default false at provision time)
PROD_AEAT_ENABLED = "PROD_AEAT_ENABLED"


class FeatureFlagService:
    def __init__(self, db: Session):
        self.db = db

    def get(self, tenant_id: str, flag_key: str, default: bool = False) -> bool:
        row = (
            self.db.query(FeatureFlagModel)
            .filter(
                FeatureFlagModel.tenant_id == tenant_id,
                FeatureFlagModel.flag_key == flag_key,
            )
            .one_or_none()
        )
        if row is None:
            return default
        return bool(row.enabled)

    def set(self, tenant_id: str, flag_key: str, enabled: bool) -> FeatureFlagModel:
        row = (
            self.db.query(FeatureFlagModel)
            .filter(
                FeatureFlagModel.tenant_id == tenant_id,
                FeatureFlagModel.flag_key == flag_key,
            )
            .one_or_none()
        )
        if row is None:
            row = FeatureFlagModel(
                tenant_id=tenant_id, flag_key=flag_key, enabled=enabled
            )
            self.db.add(row)
        else:
            row.enabled = enabled
        self.db.flush()
        return row

    def ensure_default(
        self, tenant_id: str, flag_key: str, enabled: bool = False
    ) -> FeatureFlagModel:
        existing = (
            self.db.query(FeatureFlagModel)
            .filter(
                FeatureFlagModel.tenant_id == tenant_id,
                FeatureFlagModel.flag_key == flag_key,
            )
            .one_or_none()
        )
        if existing is not None:
            return existing
        return self.set(tenant_id, flag_key, enabled)
