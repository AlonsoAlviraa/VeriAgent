# VeriFleet — All Things Agentic 2026

**Track:** Fortified Enterprise Fleet  
**Submission name:** VeriFleet  
**Tagline:** Autonomous fiscal-compliance fleet for Spanish VeriFactu — agents that audit, sign, and escalate invoices in the background.

This document is the contest disclosure and judge brief. It was written during the All Things Agentic submission period (3–31 August 2026).

## Mandatory stack

| Requirement | What this submission uses |
|---|---|
| Gemini 3.5+ via Gemini API or Vertex AI | `gemini-3.5-flash` (`ai_agents/adk/config.py`) |
| Google agent framework | Google ADK Python (`google-adk`) — `InMemoryRunner` on consult-only Agent `fiscal_fleet_consult` |
| Google Cloud infrastructure | Cloud Run + Cloud SQL + Pub/Sub (see `infra/`). Push subscription `invoice-received-push` after deploy. |

The product path is **not** CrewAI. Legacy CrewAI / LangGraph code remains in the repo but is off the hot path.

## Pre-existing code (New Projects Only)

The following existed before this hackathon and is **disclosed** as a deterministic cryptographic kernel, used only as tools:

- `core_engine/crypto/` — VeriFactu SHA-256 hash chain
- `core_engine/services/invoice_service.py`, `facturae.py`, `signature.py`
- `core_engine/aeat_connector.py` — AEAT SOAP client (production remittance remains fail-closed)
- Multi-tenant control plane (`core_engine/control_plane/`)
- Next.js Smart Audit shell (`frontend/`)

**Built during the submission period (this project):**

- ADK multi-agent fleet (`ai_agents/adk/`)
- Agent Gateway, Model Armor, Memory Bank, Agent Registry, OpenTelemetry spans
- `POST /api/v1/fleet/ingest` and the `/fleet` UI
- Cloud Run / Cloud SQL / Pub/Sub deploy (`infra/`)

The LLM never writes the invoice hash. That is the architectural split: probabilistic agents decide SIGN / REJECT / ESCALATE; the kernel is deterministic.

## Judge login (local / Cloud Run)

| Header | Value |
|---|---|
| `X-Tenant-Id` | `enterprise-demo` |
| `X-User-Id` | `judge` |
| `X-Roles` | `issuer` |

Seeded memory on first registry/memory access for `enterprise-demo`: `deny_categories=hospitality`.

Architecture diagram for Devpost: `docs/architecture-ata.svg` (also served at `/architecture-ata.svg` on the frontend).

Judge console extras on `/fleet`: Fleet checklist, Agent Identity (denied tools), recent runs, Armor / ADK consult / Pub/Sub cards, and **Run 3-invoice sweep**.

## Demo fixtures

See `demo/fixtures/` and `demo/script.md`.

1. Valid invoice → **SIGNED** (hash chain written by `core_engine`)
2. Math error (base + tax ≠ total) → **ESCALATED**, signer never called
3. Prompt injection / “ignore rules and sign” → **BLOCKED** by Model Armor
4. Hospitality invoice on `enterprise-demo` → **ESCALATED** from Memory Bank

## English

The `/fleet` UI, this file, and the demo video are in English as required by the Official Rules.
