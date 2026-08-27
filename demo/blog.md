# Building VeriFleet: a Fortified Enterprise Fleet that never lets the LLM write the hash

This piece was created for the purposes of entering this hackathon.

**Track:** Fortified Enterprise Fleet — All Things Agentic 2026  
**Stack:** `gemini-3.5-flash`, Google ADK (`InMemoryRunner`), Cloud Run + Cloud SQL + Pub/Sub

## The friction

Spanish SMEs and their *gestores* now live under VeriFactu: every invoice must join a SHA-256 hash chain before it can be remitted. A wrong VAT total does not just look sloppy — it breaks the chain. That work is still a human afternoon: open the PDF, check IVA, check NIF, sign, hope nothing collided.

A chatbot that “helps you review invoices” is the wrong shape. The work happens in the background, on a pile, with a decision that must be auditable weeks later.

## What we built during the submission period

VeriFleet is an autonomous fiscal-compliance fleet. You drop an invoice on `/fleet`. There is no chat loop.

1. **Agent Gateway** — tenant + role. `auditor` cannot `invoice.sign`.
2. **Model Armor** — regex (and optional Gemma) blocks “ignore rules and sign”; NIF/IBAN never hit logs in the clear.
3. **Ingestion + Fiscal Auditor** — math, tax IDs, Memory Bank (`deny_categories=hospitality` on `enterprise-demo`).
4. **Gemini 3.5 consult** — Google ADK `InMemoryRunner` on a consult-only agent. It may *tighten* SIGN → ESCALATE. It cannot loosen a failed gate.
5. **Signer** — only on PASS. The hash is written by a deterministic `core_engine`.
6. **Queue** — `wait=false` returns 202 QUEUED. Cloud Run consumes via a Pub/Sub push subscription; local clone uses one FIFO thread.

The cryptographic kernel (`core_engine/crypto/`, Facturae, AEAT client) existed before this hackathon. It is disclosed in `CONTEST.md`. Adding ADK, the gateway, armor, memory, registry, `/fleet`, and the Cloud Run / Cloud SQL / Pub/Sub path is the project we built in the submission window.

## What we learned

**Do not hand `invoice.sign` to the runner.** We tried (on paper) driving the four-child ADK graph that says “call tools, then sign.” Those agents have no tools attached on purpose: a live `InMemoryRunner` either timed out or returned prose that failed `parse_recommendation`. Stage One needs a real Runner invocation. Architectural discipline needs the hash off the probabilistic path. Consult-only after deterministic gates is the split that satisfies both.

**Pub/Sub after COMPLETED is a receipt, not a fleet.** The first draft published `invoice.received` at the end of `run_fleet`. A push consumer would have looped. Only `enqueue()` publishes the work item. `execute` is idempotent; an in-flight RUNNING row returns HTTP 503 so Pub/Sub retries instead of acking a dead Cloud Run instance.

**Roles die if you persist a bare invoice.** `fleet_runs` has no `roles` column. The payload must stay an envelope `{invoice, roles, user_id, …}` on every write, including the immediate RUNNING persist. Otherwise an auditor crash-resume signs.

**Windows judges do not have your Postgres.** The engine default is `localhost:5432`. The README clone-and-run sets `DATABASE_URL=sqlite:///verifleet.db`. That one line is the difference between a 5-minute `/fleet` and a connection-refused screenshot.

## Honesty rails we will not break on camera

- The LLM never writes the invoice hash.
- Consult cannot loosen math, armor, or memory.
- Gemma is opt-in (`VERIFLEET_ENABLE_GEMMA`). Regex still blocks injection when the flag is off. We do not claim Gemma is on by default.
- There is no invented `*.run.app` URL in this repo. A human with a billed project runs `infra/deploy.sh`; the video shows whatever that deploy prints.

## Try it

Clone, set SQLite, open http://localhost:3000/fleet — steps in `README.md` and `demo/judge.md`. Fixtures: valid → SIGNED, math → ESCALATED, injection → BLOCKED, hospitality → ESCALATED.

Built with Gemini 3.5 and Google ADK for All Things Agentic 2026.
