"""Fortified Enterprise Fleet checklist — what judges score."""

from __future__ import annotations

import os

from .agents import adk_status
from .config import GCP_SERVICES, GEMINI_MODEL, GOOGLE_AGENT_FRAMEWORK
from .pubsub import topic_name
from core_engine.aeat_connector import is_aeat_remitting


def checklist() -> dict:
    adk = adk_status()
    remitting = is_aeat_remitting()
    return {
        "track": "Fortified Enterprise Fleet",
        "model": GEMINI_MODEL,
        "framework": GOOGLE_AGENT_FRAMEWORK,
        "gcp_services": list(GCP_SERVICES),
        "items": [
            {
                "id": "registry",
                "name": "Agent Registry",
                "status": "implemented",
                "proof": "GET /api/v1/fleet/registry — four versioned agents",
            },
            {
                "id": "runtime",
                "name": "Agent Runtime (async background)",
                "status": "implemented",
                "proof": "POST /api/v1/fleet/ingest?wait=false → 202 QUEUED; queue.py FIFO or Pub/Sub push; execute() idempotent",
            },
            {
                "id": "memory",
                "name": "Memory Bank",
                "status": "implemented",
                "proof": "per-tenant agent_memories (hospitality deny on enterprise-demo)",
            },
            {
                "id": "identity",
                "name": "Agent Identity (zero-trust)",
                "status": "implemented",
                "proof": "X-Tenant-Id / X-Roles; tool allowlist; auditor cannot invoice.sign",
            },
            {
                "id": "gateway",
                "name": "Agent Gateway",
                "status": "implemented",
                "proof": "ai_agents/adk/gateway.py — policy before any tool",
            },
            {
                "id": "armor",
                "name": "Model Armor",
                "status": "implemented",
                "proof": "injection BLOCKED; NIF/IBAN redacted; Gemma opt-in",
            },
            {
                "id": "otel",
                "name": "Telemetry (OpenTelemetry)",
                "status": "implemented",
                "proof": "spans on every run; Cloud Trace when OTEL exporter is set",
            },
            {
                "id": "gemini",
                "name": "Gemini 3.5+",
                "status": "implemented",
                "proof": f"consult uses {GEMINI_MODEL} via Gemini API or Vertex",
            },
            {
                "id": "adk",
                "name": "Google ADK",
                "status": "implemented" if adk.get("available") else "wired",
                "proof": "ai_agents/adk/runner.py InMemoryRunner on consult-only Agent; model gemini-3.5-flash",
            },
            {
                "id": "runner",
                "name": "ADK Runner",
                "status": "implemented",
                "proof": "run_orchestrator() → InMemoryRunner(fiscal_fleet_consult); skipped when VERIFLEET_SKIP_LLM=1; cannot loosen gates",
            },
            {
                "id": "aeat",
                "name": "AEAT remittance",
                "status": "live" if remitting else "not_on_path",
                "proof": (
                    "fleet ingest is remitting to AEAT"
                    if remitting
                    else "aeat_remitting=false — fleet ingest signs locally and does not call AEAT"
                ),
            },
            {
                "id": "pubsub",
                "name": "Pub/Sub",
                "status": "live" if topic_name() else "ready",
                "proof": topic_name() or "set PUBSUB_TOPIC to publish invoice.received",
            },
        ],
        "llm_live": not _skip_llm(),
        "aeat_remitting": is_aeat_remitting(),
        "pubsub_topic": topic_name() or None,
        "project": os.getenv("GOOGLE_CLOUD_PROJECT") or None,
    }


def _skip_llm() -> bool:
    return os.getenv("VERIFLEET_SKIP_LLM", "").strip().lower() in {"1", "true", "yes"}


def identity(tenant_id: str, user_id: str, roles: list) -> dict:
    from . import gateway
    from .config import TOOL_ALLOWLIST

    roles_t = gateway.normalize_roles(roles)
    return {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "roles": list(roles_t),
        "allowed_tools": [t for t in TOOL_ALLOWLIST if gateway.allows(t, roles_t).allowed],
        "denied_tools": gateway.denied_tools(roles_t),
        "zero_trust": True,
    }
