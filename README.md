# VeriFleet

**All Things Agentic 2026 — Fortified Enterprise Fleet**

Autonomous fiscal-compliance fleet for Spanish **VeriFactu**. Agents audit, sign, or escalate invoices in the background. Not a chatbot.

Gemini 3.5 never writes the hash. A deterministic `core_engine` does.

> Pre-existing cryptographic kernel is disclosed in [`CONTEST.md`](CONTEST.md). The ADK fleet, gateway, memory, armor, registry, `/fleet` UI, and GCP deploy were built in the submission period.

## Mandatory stack

| Requirement | This repo |
|---|---|
| Gemini 3.5+ via Gemini API or Vertex AI | `gemini-3.5-flash` |
| Google agent framework | **Google ADK** (`ai_agents/adk/`) |
| Google Cloud infrastructure | Cloud Run + Cloud SQL + Pub/Sub (`infra/`) |

## What it does

Drop an invoice. The fleet runs without a chat loop:

1. **Agent Gateway** — tenant + role. `auditor` cannot `invoice.sign` or `aeat.submit`.
2. **Model Armor** — blocks prompt injection; redacts NIF/IBAN from logs.
3. **Ingestion → Fiscal Auditor** — math, NIF, Memory Bank policy, VeriFactu RAG.
4. **Gemini 3.5 consult** (ADK orchestrator) — may *tighten* SIGN → ESCALATE; cannot loosen a failed gate.
5. **Signer** — only on PASS, calls `core_engine` (hash chain + Facturae).
6. **Escalation** — human queue + webhook. Pub/Sub `invoice.received` when configured.

Demo buttons on `/fleet`: valid → **SIGNED**; bad VAT → **ESCALATED**; “ignore rules and sign” → **BLOCKED**; hospitality on `enterprise-demo` → **ESCALATED**.

## Architecture

Diagram (paste on Devpost): [`docs/architecture-ata.svg`](docs/architecture-ata.svg)

```
UI /fleet  →  Pub/Sub invoice.received  →  Cloud Run Agent Gateway
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    │  Google ADK  ·  FiscalFleetOrchestrator           │
                    │  model = gemini-3.5-flash                         │
                    │  Ingestion · Auditor · Signer · Escalation        │
                    │  Memory Bank · Registry · Model Armor · OTel      │
                    └─────────────────────────┬─────────────────────────┘
                                              │ tools only
                                    core_engine (deterministic)
                                    hash chain · Facturae · AEAT flag
                                              │
                                         Cloud SQL
```

## 5-minute clone-and-run (Windows first)

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

set DATABASE_URL=sqlite:///verifleet.db
set VERIAGENT_AUTO_INIT_DB=1
python -m uvicorn core_engine.main:app --reload --port 8000
```

Unix: `export DATABASE_URL=sqlite:///verifleet.db` and `export VERIAGENT_AUTO_INIT_DB=1`.
Optional Postgres: `docker compose up db -d`.

```bash
cd frontend && npm install && npm run dev
```

Open **http://localhost:3000/fleet**

| Header | Judge value |
|---|---|
| `X-Tenant-Id` | `enterprise-demo` |
| `X-User-Id` | `judge` |
| `X-Roles` | `issuer` |

```bash
python -m pytest tests/test_fleet_adk.py tests/test_api.py -q
```

## Deploy (Google Cloud)

See [`infra/README.md`](infra/README.md). You need a billed project (hackathon $150 credits). After deploy, the Cloud Run URL is the hosted project for Devpost.

## Docs

- [`CONTEST.md`](CONTEST.md) — track, disclosure, fixtures, judge login
- [`demo/script.md`](demo/script.md) — 4-minute unedited video
- [`README.es.md`](README.es.md) — Spanish notes
