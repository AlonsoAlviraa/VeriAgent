"""RBAC helpers for multi-org API (MT-05)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Optional

from fastapi import Header, HTTPException, status


class Role(str, Enum):
    ISSUER = "issuer"
    AUDITOR = "auditor"
    ADMIN = "admin"


@dataclass
class OrgContext:
    user_id: str
    tenant_id: str
    roles: List[str]

    def has_any(self, required: Iterable[str]) -> bool:
        return any(r in self.roles for r in required)


def parse_org_context(
    x_tenant_id: Optional[str] = None,
    x_user_id: Optional[str] = None,
    x_roles: Optional[str] = None,
) -> OrgContext:
    """
    Resolve org context from trusted gateway headers (or defaults for local/dev).
    Roles: comma-separated list.
    """
    tenant = x_tenant_id or "default"
    user = x_user_id or "anonymous"
    roles = [r.strip() for r in (x_roles or "issuer").split(",") if r.strip()]
    return OrgContext(user_id=user, tenant_id=tenant, roles=roles)


def require_roles(ctx: OrgContext, *roles: str) -> None:
    if not ctx.has_any(roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "RBAC_FORBIDDEN",
                "message": f"Requires one of roles: {roles}",
                "user_roles": ctx.roles,
            },
        )


def org_context_from_headers(
    x_tenant_id: Optional[str] = Header(default=None),
    x_user_id: Optional[str] = Header(default=None),
    x_roles: Optional[str] = Header(default=None),
) -> OrgContext:
    return parse_org_context(x_tenant_id, x_user_id, x_roles)
