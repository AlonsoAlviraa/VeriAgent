"""Agent Gateway: identity, tenant, tool allowlist.

Does not authenticate users (that is the existing RBAC/header contract).
It enforces which tools a role may call inside the fleet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from .config import TOOL_ALLOWLIST


@dataclass(frozen=True)
class GatewayDecision:
    allowed: bool
    tool: str
    roles: tuple
    reason: str = ""


def normalize_roles(roles: Iterable[str] | None) -> tuple:
    cleaned = tuple(r.strip() for r in (roles or ()) if r and r.strip())
    return cleaned or ("issuer",)


def allows(tool: str, roles: Sequence[str]) -> GatewayDecision:
    permitted = TOOL_ALLOWLIST.get(tool)
    if permitted is None:
        return GatewayDecision(False, tool, tuple(roles), f"unknown tool: {tool}")
    if any(r in permitted for r in roles):
        return GatewayDecision(True, tool, tuple(roles), "ok")
    return GatewayDecision(
        False,
        tool,
        tuple(roles),
        f"role {list(roles)} cannot invoke {tool}; requires {list(permitted)}",
    )


def require(tool: str, roles: Sequence[str]) -> GatewayDecision:
    return allows(tool, roles)


def denied_tools(roles: Sequence[str]) -> List[str]:
    return [t for t in TOOL_ALLOWLIST if not allows(t, roles).allowed]
