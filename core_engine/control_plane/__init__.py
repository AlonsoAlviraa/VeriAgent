"""
Control plane for hybrid multi-tenant architecture (ADR arch-hybrid-dbpt-control).

Owns tenant registry, plans, feature flags, and data-plane routing metadata.
Does NOT touch invoice hash chains (those live in the data plane).
"""

from .feature_flags import FeatureFlagService, PROD_AEAT_ENABLED
from .registry import TenantRegistry

__all__ = [
    "FeatureFlagService",
    "PROD_AEAT_ENABLED",
    "TenantRegistry",
]
