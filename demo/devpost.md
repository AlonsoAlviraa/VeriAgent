# Devpost paste — VeriFleet (All Things Agentic 2026)

Copy these fields into the Devpost submission form. Do **not** invent a live
`*.run.app` URL. Paste the Cloud Run URL only after a human runs `infra/deploy.sh`.

## Category

**Fortified Enterprise Fleet**

## Project name

VeriFleet

## Tagline

Autonomous fiscal-compliance fleet for Spanish VeriFactu — agents that audit, sign, or escalate invoices in the background.

## Hosted project URL

Leave blank until a human deploy prints a Cloud Run URL. Proof of Google Cloud in the video is the Cloud Run service + Pub/Sub subscription `invoice-received-push`, not a placeholder.

## Repository

https://github.com/AlonsoAlviraa/VeriAgent

## Text description

A Spanish SME drops invoices every afternoon. A human checks VAT (IVA), tax IDs (NIF), and VeriFactu hash chaining. One wrong total breaks the chain and the filing. VeriFleet does this without a chat loop.

Drop an invoice on `/fleet`. **Agent Gateway** checks tenant and role. **Model Armor** blocks “ignore rules and sign” and redacts NIF/IBAN. **Ingestion → Fiscal Auditor** checks math, tax IDs, and **Memory Bank** policy (`deny_categories=hospitality` on `enterprise-demo`). Gemini 3.5, via Google ADK `InMemoryRunner` on a consult-only agent `fiscal_fleet_consult`, may *tighten* SIGN → ESCALATE. It cannot loosen a failed gate. It never writes the hash. A deterministic `core_engine` does — disclosed as a **pre-existing cryptographic kernel**.

On Cloud Run the work queue is Pub/Sub: `wait=false` persists `QUEUED`, publishes `invoice.received`, and the push subscription hits `/api/v1/fleet/pubsub/push`. Locally the same row is drained by one FIFO thread. `execute` is idempotent. An in-flight run returns HTTP 503 so Pub/Sub retries instead of acking a dead instance.

Built for the Fortified Enterprise Fleet track: Agent Registry, async Agent Runtime, Memory Bank, Agent Identity, Agent Gateway, Model Armor, OpenTelemetry.

## Features and functionality

- Background ingest: `POST /api/v1/fleet/ingest?wait=false` → 202 QUEUED, then SIGNED / ESCALATED / BLOCKED.
- Four committed fixtures: valid → **SIGNED** (hash from `core_engine`); math error → **ESCALATED**; prompt injection → **BLOCKED**; hospitality on `enterprise-demo` → **ESCALATED**.
- PDF path: committed text PDF upload → `file_id` → same SIGNED gate (number stamped so repeats do not collide).
- Zero-trust identity: role `auditor` cannot `invoice.sign`.
- Tighten-only consult: Gemini 3.5 may escalate a SIGN; it cannot override a failed math/armor/memory gate.
- Judge console at `/fleet` (English): checklist, registry, memory, identity, recent runs, 3-invoice sweep.

## Technologies used

| Requirement | This project |
|---|---|
| Gemini 3.5+ via Gemini API or Vertex AI | `gemini-3.5-flash` |
| Google agent framework | Google ADK (`google-adk`) — `InMemoryRunner` on `fiscal_fleet_consult` |
| Google Cloud | Cloud Run + Cloud SQL + Pub/Sub (`infra/deploy.sh`) |
| Optional Stage Three | Gemma armor classifier when `VERIFLEET_ENABLE_GEMMA=1` (regex remains fail-closed if unset) |

## Other data sources

- Synthetic VeriFactu-shaped fixtures in `demo/fixtures/` (valid, math error, injection, hospitality).
- Committed text PDF `demo/fixtures/valid_invoice.pdf` (JSON extract, not a scan).
- Public MIT invoice2data sample PDFs in `demo/fixtures/live/` (German/Dutch/French VAT). These are **not** VeriFactu; the fleet escalates and does not invent a Spanish NIF. Sources listed in `demo/fixtures/live/SOURCES.md`.
- No real-company invoices were scraped.

## Findings and learnings

- Putting the ADK `InMemoryRunner` on the four-child “call tools / sign” graph timed out or missed `SIGN`/`ESCALATE`. A consult-only agent after deterministic gates returns a usable recommendation in 20s and keeps the kernel off the LLM path.
- Pub/Sub as a receipt (publish after COMPLETED) is not a work queue. Only `enqueue()` publishes `invoice.received`; a push subscription is the Cloud Run consumer.
- Roles must live in the `fleet_runs` payload envelope. If `_persist` dumps a bare invoice, an auditor crash-resume would sign.
- Judges clone on Windows without Docker. Default `DATABASE_URL` is localhost Postgres; the README **must** set `sqlite:///verifleet.db`.

## Testing instructions (spin-up)

See `README.md` and `demo/judge.md`. Windows-first:

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
set DATABASE_URL=sqlite:///verifleet.db
set VERIAGENT_AUTO_INIT_DB=1
python -m uvicorn core_engine.main:app --reload --port 8000
```

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:3000/fleet

| Header | Value |
|---|---|
| `X-Tenant-Id` | `enterprise-demo` |
| `X-User-Id` | `judge` |
| `X-Roles` | `issuer` |

`GET /health` must include `gemini-3.5-flash`, `google-adk`, and `InMemoryRunner`.

## Architecture diagram

`docs/architecture-ata.svg` (also `/architecture-ata.svg` on the frontend).

## Video

One unedited English take ≤ 4 minutes. Spoken words: `demo/voiceover.md`. Beats: `demo/script.md`. Must show Cloud Run / Pub/Sub after a human deploy — do not fake a URL.

## Optional extras

- Blog draft: `demo/blog.md` (states it was created for entering this hackathon).
- Social draft: `demo/social.md` (`#AllThingsAgenticHackathon`).
- Gemma: opt-in via `VERIFLEET_ENABLE_GEMMA`; regex still blocks injection when the flag is off.
