# VeriFleet — smallest increment to win All Things Agentic 2026

**Track:** Fortified Enterprise Fleet (not Taskmaster)  
**Deadline:** 31 August 2026 17:00 PT  
**Submission:** VeriFleet ADK layer (pre-existing `core_engine` disclosed, not redesigned)  
**Language:** English for judge-facing UI, README, video, and this spec  

This document is the implementation spec for the next coding sprint. It does not redesign the fleet. It closes the four gaps that still lose: Stage One can be argued instead of proven, ingest is sync, the live demo is JSON-only, and clone-and-run / judge-facing docs are thinner than a winning Devpost page.

Cloud billing, **running** `infra/deploy.sh`, the 4-minute video, the blog, and the `#AllThingsAgenticHackathon` post are **human ops**. Editing `deploy.sh` so a human run actually hosts the queue story **is** in scope (PR-02). Execution of the script is not.

---

## 1. Problem / context

Stage One is pass/fail on the mandatory stack: Gemini 3.5+, a Google agent framework (ADK / GenAI SDK / Antigravity / GenKit), and at least one GCP service. A judge who greps the repo today can prove the **strings** (`gemini-3.5-flash`, `google-adk`, Cloud Run / Cloud SQL / Pub/Sub in `infra/`) but not the **path**:

- `ai_agents/adk/agents.py` constructs `FiscalFleetOrchestrator` with four sub-agents.
- `ai_agents/adk/runtime.py` calls `build_adk_root()` and then ignores the object.
- The live Gemini call is `consult()` via `google.genai` / REST, not `google.adk.runners.InMemoryRunner`.
- `POST /api/v1/fleet/ingest` runs the fleet in the request thread. Pub/Sub publishes **after** the decision (`invoice.received` is a receipt, not a work queue).
- `/fleet` demo buttons POST JSON fixtures. `file_id` / `raw_text` exist in `_extract_payload` but no PDF fixture or UI control exercises them.
- `GET /api/v1/fleet/runs/{id}` drops `adk`, `denied_tools`, and `pubsub` — those fields live only on the in-memory `FleetResult` of the ingest response.
- `frontend/src/app/page.tsx` and `frontend/src/app/history/page.tsx` still render hardcoded 2023 Smart Audit rows. `layout.tsx` metadata is still `Create Next App`.
- There is no live `*.run.app` URL. That is a human deploy, not this sprint.
- `infra/deploy.sh` creates the topic and sets `PUBSUB_TOPIC` but creates **no push (or pull) subscription**, and never sets `DATABASE_URL` (process still targets localhost Postgres).

Judging weights:

| Criterion | Weight | What still loses |
|---|---|---|
| Innovation & Operational Utility | 40% | Sync ingest, post-hoc Pub/Sub, no PDF path, Runner not on-path |
| Architectural Discipline | 30% | Gates exist; persist/audit gaps; Runner constructed but unused |
| Demo & Production Readiness | 30% | No hosted URL, thin README vs Devpost, Spanish/mock homepage |

The product already has the hard parts: SIGNED / ESCALATED / BLOCKED gates, hospitality memory, auditor cannot sign, LLM cannot loosen a failed gate, LLM never writes the hash. This sprint makes that story **undeniable on a 4-minute live take** and **undeniable to a Stage One grep**.

---

## 2. Goals and non-goals

### Goals

1. **Stage One undeniable.** A judge who reads `/health`, `/api/v1/fleet/compliance`, and `ai_agents/adk/runner.py` sees `gemini-3.5-flash`, `google-adk`, and `InMemoryRunner` **invoked** on the fleet path (or an explicit skip reason: `VERIFLEET_SKIP_LLM`, no credentials, ADK import fail).
2. **Background workflow is real.** Ingest can return `202` + `QUEUED`; a worker (in-process FIFO thread locally, Pub/Sub **push subscription** on Cloud Run) drives the same `run_fleet`. The 3-invoice sweep can be async. Hosted `wait=false` must complete without a 15s timeout.
3. **PDF path in the live demo.** One committed text PDF whose `pypdf` extract `json.loads`s to the valid-invoice shape. `/fleet` has a “Valid invoice (PDF)” control that upload → ingest → same SIGNED gate. Repeats stamp `number`. No Document AI, no new OCR stack.
4. **Architecture is judge-auditable after refresh.** `GET /runs/{id}` returns armor, memory, spans, ADK/runner, denied tools, Pub/Sub. Checklist proof strings match code.
5. **Clone-and-run in 5 minutes.** English README + `CONTEST.md` + `demo/judge.md` take a Windows judge from clone to `/fleet` **with `DATABASE_URL=sqlite:///verifleet.db`** without guessing headers, ports, or which page is the submission.
6. **NORMAS.md split held.** `core_engine/crypto/` untouched. New work in `ai_agents/adk/`, fleet routes, `/fleet` UI, docs, `infra/`. `core_engine/main.py` and `core_engine/db/fleet_models.py` may grow fleet-only surface.

### Non-goals

- **Executing** `infra/deploy.sh`, creating a billed GCP project, or pasting a live Cloud Run URL (human ops). Completing the script so that execution works **is** a goal of PR-02.
- Recording the ≤4 min video, writing the blog, or posting `#AllThingsAgenticHackathon` (human ops).
- Rewriting CrewAI, ProductGraph, AEAT SOAP, or XAdES.
- Replacing deterministic gates with an LLM-driven tool loop (four-child graph with `invoice.sign` tools).
- Celery, Cloud Tasks, Redis, or a new queue product.
- Vertex Document AI / Gemma-as-required Armor (Gemma stays opt-in via `VERIFLEET_ENABLE_GEMMA`).
- Rewriting the Spanish Smart Audit product. Only stop it from being the first thing a judge sees.
- Changing hash, Facturae, or signature code.
- Loosening any existing gate.

### Success bar (end of sprint, before human deploy)

```
VERIFLEET_SKIP_LLM=1 python -m pytest tests/test_fleet_adk.py -q   # all green, including new cases
```

Local demo: set `DATABASE_URL=sqlite:///verifleet.db` and `VERIAGENT_AUTO_INIT_DB=1`, then `uvicorn` + `npm run dev` → `http://localhost:3000/fleet` → four fixture buttons + PDF + 3-invoice sweep produce SIGNED / ESCALATED / BLOCKED / hospitality ESCALATED. Role `auditor` cannot sign (sync **and** `wait=false`). Checklist shows `google-adk` + `gemini-3.5-flash`. No hardcoded 2023 invoices on `/`.

---

## 3. Current state

### What already ships (do not redesign)

| Piece | Path | Behavior |
|---|---|---|
| Model / framework strings | `ai_agents/adk/config.py` | `GEMINI_MODEL=gemini-3.5-flash`, `GOOGLE_AGENT_FRAMEWORK=google-adk`, `GCP_SERVICES=(Cloud Run, Cloud SQL, Pub/Sub, Secret Manager, Cloud Trace)` |
| ADK graph | `ai_agents/adk/agents.py`, `root_agent.py` | Four `Agent`s + orchestrator. `root_agent` export for `adk web`. Built, not run. |
| Consult | `ai_agents/adk/consult.py` | Gemini 3.5 via `google.genai` or REST. Skip if `VERIFLEET_SKIP_LLM` or no key (`reason` today is always `no_credentials`). |
| Deterministic runtime | `ai_agents/adk/runtime.py` | Armor → ingest → memory → auditor (math/NIF/hospitality) → consult tighten-only → gateway `invoice.sign` → `core_tools.create_and_sign` → webhook + **post-hoc** `invoice.received` |
| Gates (tested) | `tests/test_fleet_adk.py` (25) | valid SIGNED; math ESCALATED; injection BLOCKED; hospitality ESCALATED; auditor cannot sign; consult cannot loosen; consult can tighten; batch 3 decisions; tenant isolation |
| Gateway / Armor / Memory / Registry / OTel | `gateway.py`, `armor.py`, `memory.py`, `registry.py`, `otel.py` | Exist and are on the path |
| Pub/Sub | `pubsub.py` | No-op unless `PUBSUB_TOPIC`. `unwrap_push` already decodes the GCP envelope. `/api/v1/fleet/pubsub/push` already calls `run_fleet`. **No subscription in `deploy.sh`.** |
| Fleet API | `core_engine/main.py` | `/ingest`, `/ingest/batch`, `/runs`, `/runs/{id}`, `/registry`, `/memory`, `/compliance`, `/identity`, `/pubsub/push` |
| UI | `frontend/src/app/fleet/page.tsx` | English console, fixtures, sweep, checklist, identity, live history from `/runs` |
| OCR kernel | `core_engine/services/ocr.py` | `pypdf` + optional tesseract. Called from `core_tools.extract_text` and `_extract_payload(file_id=...)` |
| Upload | `POST /api/v1/invoices/upload` | PDF/XML, returns `file_id` |
| DB default | `core_engine/db/database.py` | `DATABASE_URL` defaults to `postgresql://veriagent:securepassword@localhost:5432/veriagent_core` |
| Deploy (unrun, incomplete) | `infra/deploy.sh`, `infra/README.md` | Topic + Cloud Run env `PUBSUB_TOPIC`. No `DATABASE_URL`. No push subscription. |
| Tests | `tests/conftest.py` | Forces `VERIFLEET_SKIP_LLM=1`, pops `PUBSUB_TOPIC` |

### Exact gaps this sprint closes

1. `runtime.run_fleet` line ~254–256: `adk_root = build_adk_root()` then unused.
2. `consult._generate` is the only live Gemini call; no `InMemoryRunner`.
3. Ingest is request-scoped. `result.pubsub = pubsub.publish("invoice.received", …)` runs **after** COMPLETED (would loop if a push consumer existed).
4. `FleetRunModel` / `get_run` omit `adk`, `denied_tools`, `pubsub`. Model defaults `decision="ESCALATED"` even for QUEUED.
5. No PDF fixture; `/fleet` never sends `file_id`.
6. Homepage + `/history` are mock Smart Audit. Root layout title is `Create Next App`.
7. README / CONTEST / `demo/script.md` are accurate but not a 5-minute judge script, and they omit `DATABASE_URL`.
8. `deploy.sh` cannot host the async story (no consumer, no Cloud SQL URL).

---

## 4. Proposed design

One increment, four PRs. Prefer editing existing files. One new module for the Runner, one for the in-process queue.

```
UI /fleet  →  POST /fleet/ingest?wait=false
                 │
                 ├─ persist fleet_runs status=QUEUED decision=""
                 │   payload_json = {invoice, raw_text, file_id, roles, user_id}
                 │
                 ├─ if VERIFLEET_QUEUE_DISPATCH=0: stop (tests)
                 │
                 ├─ if PUBSUB_TOPIC and VERIFLEET_PUBSUB_PUSH=1:
                 │       ONLY enqueue publishes invoice.received
                 │       push sub → POST /api/v1/fleet/pubsub/push
                 │       → execute(run_id)   # roles from row, not headers
                 │
                 └─ else (local default): one FIFO worker thread
                         new SessionLocal() → execute(run_id)
                              │
                    Agent Gateway → Model Armor
                              │
                    ADK InMemoryRunner on consult-only Agent
                              │
                    Deterministic auditor / signer tools
                              │
                    core_engine hash chain (unchanged)
```

Default `wait=true` keeps today’s 200 + completed body so existing tests and the 5-minute local demo stay instant.

### 4.1 Stage One: ADK Runner on a consult-only Agent

**Do not** run `FiscalFleetOrchestrator` + four sub-agents through `InMemoryRunner`. Those instructions say “Call tools”, “invoice.create then invoice.sign”, “Delegate ingestion → auditor → signer”. Tools are intentionally not attached. Live outcome would be multi-turn transfer, 20s timeout, or first event text that fails `parse_recommendation` — the ADK card looks dead. The four-child graph stays for `adk web` / registry proof only.

**New file:** `ai_agents/adk/runner.py`

Also add `build_consult_agent()` in `ai_agents/adk/agents.py` (or in `runner.py` if that keeps `agents.py` smaller):

```python
def build_consult_agent() -> Any:
    """Single Agent, no sub_agents, no tools. Same job as consult()."""
    if not ADK_AVAILABLE or Agent is None:
        return None
    return Agent(
        name="fiscal_fleet_consult",
        model=GEMINI_MODEL,
        description="Tighten-only consult after the deterministic auditor.",
        instruction=(
            f"You are FiscalFleetOrchestrator ({GOOGLE_AGENT_FRAMEWORK}, {GEMINI_MODEL}). "
            "Background fiscal compliance. Do not chat. Do not invent hashes or XML. "
            "Do not call tools. Reply with exactly one of: SIGN, ESCALATE, REJECT — then one sentence why."
        ),
    )
```

`build_adk_root()` is unchanged (four published agents, `root_agent.py`, registry). `run_orchestrator()` calls `build_consult_agent()`, **not** `build_adk_root()`.

Public function:

```python
def run_orchestrator(
    *,
    redacted_invoice: str,
    memory: dict,
    auditor_draft: str,
) -> dict:
    """Drive the consult-only Agent via InMemoryRunner.

    Same contract as consult(): never raises into the hash path.
    """
```

Return shape (extends today’s consult dict):

```json
{
  "invoked": false,
  "model": "gemini-3.5-flash",
  "framework": "google-adk",
  "recommendation": null,
  "text": "",
  "reason": "no_credentials | skip_llm | adk_unavailable | ok | llm_error:...",
  "runner": "InMemoryRunner | none",
  "events": 0
}
```

**Shared skip helper** — put in `consult.py` (single source). Both `consult._enabled` and `run_orchestrator` call it. Today both skip cases return `reason="no_credentials"`. New contract splits them. Existing 25 tests do not assert that string; do not change those tests.

```python
def skip_reason() -> str | None:
    if os.getenv("VERIFLEET_SKIP_LLM", "").strip().lower() in {"1", "true", "yes"}:
        return "skip_llm"
    if not (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("GOOGLE_CLOUD_PROJECT")
    ):
        return "no_credentials"
    return None
```

Rules:

- `skip_reason()` is `skip_llm` → `invoked=false`, `runner=none`. Tests stay offline.
- `skip_reason()` is `no_credentials` → same, `reason=no_credentials`.
- Import `from google.adk.runners import InMemoryRunner` (fallback: `from google.adk.runners import Runner` + in-memory session service). If import or `build_consult_agent()` fails → `reason=adk_unavailable`, then **fall back to** existing `consult._generate` so a live Gemini key still produces a consult. Set `runner=none` and keep `framework=google-adk`. Wrap `_generate` in try/except: if it also has no key, return `reason=adk_unavailable;fallback_generate;no_credentials` — never raise.
- On success: short-lived session (`app_name="verifleet"`, `user_id="fleet"`), one user message = today’s consult prompt (auditor draft + memory + redacted invoice + SIGN / ESCALATE / REJECT). Collect **last** model text only. Reuse `parse_recommendation`. `runner=InMemoryRunner`, `invoked=true`.
- Timeout: 20s via `asyncio.wait_for` (Windows has no `signal.alarm`). Swallow all exceptions; never raise into `run_fleet`.

**Sync facade** (`consult()` and `fleet_ingest` are `def`, not `async`):

```python
from google.genai import types  # Content / Part; same SDK as consult._generate

async def _drive(agent, prompt: str) -> str:
    runner = InMemoryRunner(agent=agent, app_name="verifleet")
    session = await runner.session_service.create_session(
        app_name="verifleet", user_id="fleet"
    )
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    text = ""
    async for event in runner.run_async(
        user_id="fleet", session_id=session.id, new_message=msg
    ):
        content = getattr(event, "content", None)
        if not content:
            continue
        parts = getattr(content, "parts", None) or []
        chunk = "".join(getattr(p, "text", "") or "" for p in parts)
        if chunk.strip():
            text = chunk  # last non-empty model text
    return text

def _run_sync(coro, timeout: float = 20.0) -> str:
    try:
        asyncio.get_running_loop()
        running = True
    except RuntimeError:
        running = False
    if running:
        # FastAPI / uvicorn may already have a loop; do not asyncio.run on it.
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(
                lambda: asyncio.run(asyncio.wait_for(coro, timeout=timeout))
            ).result(timeout=timeout + 2)
    return asyncio.run(asyncio.wait_for(coro, timeout=timeout))
```

**Edit** `ai_agents/adk/consult.py`:

```python
def consult(...) -> dict:
    blocked = skip_reason()
    if blocked:
        return {..., "invoked": False, "reason": blocked, "runner": "none"}
    result = adk_runner.run_orchestrator(...)
    if result.get("invoked") or result.get("reason") in {"no_credentials", "skip_llm"}:
        return result
    # ADK missing or runner error: keep Gemini on-path via _generate
    try:
        fallback = _legacy_consult(...)  # today’s _generate + parse, must not raise
    except Exception as exc:
        return {**result, "reason": f"{result.get('reason')};fallback_generate;{exc}"}
    fallback["runner"] = result.get("runner") or "none"
    fallback["reason"] = f"{result.get('reason')};fallback_generate"
    return fallback
```

**Edit** `ai_agents/adk/agents.py` `adk_status()`:

```python
{
  "framework": "google-adk",
  "available": ADK_AVAILABLE,
  "model": GEMINI_MODEL,
  "import_error": _ADK_IMPORT_ERROR,
  "runner": "InMemoryRunner",  # class we call; skip_reason() may still skip
  "consult_agent": "fiscal_fleet_consult",
}
```

**Edit** `ai_agents/adk/runtime.py` consult span:

- Keep tighten-only: `SIGNED` + reco in `{ESCALATE, BLOCK}` → `ESCALATED`. Nothing else moves a decision.
- `result.adk` already merges consult. Add `root_built` (still from `build_adk_root()` for registry proof), `consult_agent`, `runner`, `runner_events`.
- Runtime may still call `build_adk_root()` so `root_built` stays true for the four-agent catalog. That object is **not** passed to `InMemoryRunner`.

**Edit** `ai_agents/adk/compliance.py`:

```python
{
  "id": "adk",
  "name": "Google ADK",
  "status": "implemented" if adk.get("available") else "wired",
  "proof": "ai_agents/adk/runner.py InMemoryRunner on consult-only Agent; model gemini-3.5-flash",
}
{
  "id": "runner",
  "name": "ADK Runner",
  "status": "implemented",
  "proof": "run_orchestrator() → InMemoryRunner(fiscal_fleet_consult); skipped when VERIFLEET_SKIP_LLM=1; cannot loosen gates",
}
```

`runtime` checklist item is **not** updated in PR-01 (still claims async). PR-02 updates that proof (see §4.2).

**Edit** `GET /health` in `core_engine/main.py` — import from config, do not hardcode a second list:

```python
from ai_agents.adk.config import GCP_SERVICES, GEMINI_MODEL, GOOGLE_AGENT_FRAMEWORK

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "core_engine",
        "version": "0.4.0",
        "fleet": "verifleet",
        "model": GEMINI_MODEL,
        "framework": GOOGLE_AGENT_FRAMEWORK,
        "runner": "InMemoryRunner",
        "gcp_services": list(GCP_SERVICES),
        "track": "Fortified Enterprise Fleet",
    }
```

`/health` hardcoding the class name is a Stage One grep target. Honesty: `/compliance` runner proof says it is skipped when `VERIFLEET_SKIP_LLM=1`.

Stage One grep targets after this PR:

- `gemini-3.5-flash` in `config.py`, `/health`, `/registry`, `/compliance`
- `google-adk` same
- `InMemoryRunner` in `runner.py` and `/health`
- `google.cloud.pubsub` in `pubsub.py`
- `infra/deploy.sh` Cloud Run + Cloud SQL

**PR-01 acceptance note:** `GET /runs/{id}` still omits `adk` until PR-02 persists extras. Sync ingest response body already includes `adk`. Refresh audit is PR-02.

### 4.2 Autonomous background: queue-first ingest

**New file:** `ai_agents/adk/queue.py`

In-process, thread-safe, no Redis. ProductGraph’s `ai_agents/graphs/jobs.py` is **not** reused (wrong domain, in-memory only, no tenant). Fleet queue is durable because the row lives in `fleet_runs`.

```python
def enqueue(
    *,
    db: Session,
    tenant_id: str,
    roles: Sequence[str] | None,
    user_id: str,
    invoice: dict | None,
    raw_text: str | None,
    file_id: str | None,
    run_id: str | None = None,
) -> FleetResult:
    """Persist QUEUED (decision=""). Dispatch per flags below."""

def execute(run_id: str, db: Session | None = None) -> FleetResult:
    """Idempotent resume. Roles come from the row envelope, never from headers."""
```

#### Envelope (roles survive Pub/Sub **and** `_persist`)

`fleet_runs` has no `roles` / `user_id` columns. Do **not** add them. `payload_json` is **always** this wrapper, including after `run_fleet` writes `RUNNING` / `COMPLETED`. Current `_persist` dumps `_extract_payload(...)` (a bare invoice). That would erase `roles` on the first persist, so a 60s lease resume would `normalize_roles(None)` → `("issuer",)` and an auditor crash-resume **signs**. Forbidden.

Canonical shape (every write):

```json
{
  "invoice": { },
  "raw_text": null,
  "file_id": null,
  "roles": ["auditor"],
  "user_id": "judge"
}
```

Helper in `runtime.py` (PR-02):

```python
def _wrap_payload(existing: dict | None, payload: dict, *, roles, user_id, raw_text=None, file_id=None) -> dict:
    """Merge. Never replace an envelope with a bare invoice."""
    prev = existing if isinstance(existing, dict) else {}
    if "roles" not in prev and "invoice" not in prev and prev.get("issuer_tax_id"):
        prev = {"invoice": prev}  # tolerate a pre-PR-02 row
    invoice = payload if "issuer_tax_id" in payload or "total_amount" in payload else payload.get("invoice") or prev.get("invoice") or payload
    return {
        "invoice": invoice,
        "raw_text": raw_text if raw_text is not None else prev.get("raw_text"),
        "file_id": file_id if file_id is not None else prev.get("file_id"),
        "roles": list(roles if roles is not None else prev.get("roles") or []),
        "user_id": user_id if user_id else prev.get("user_id") or "anonymous",
    }
```

`_persist` **must** load the current `payload_json` (if any), call `_wrap_payload`, and write that. RUNNING updates merge, never `json.dumps(extracted_invoice)` alone. Sync `wait=true` uses the same helper so `get_run` unwrap is one code path.

`execute` always reads wrapper keys (`roles`, `user_id`, `invoice`). `gateway.normalize_roles(None)` must never run on a resume path.

`get_run` returns `payload` = envelope `invoice` if present, else the raw object (judges see the invoice, not the wrapper).

#### Dispatch flags

| Env | Default | Meaning |
|---|---|---|
| `VERIFLEET_QUEUE_DISPATCH` | `1` (on) | `0`/`false`/`yes`-negated: persist + 202 only. No thread, no publish. **Tests set this to `0` in `tests/conftest.py`.** |
| `VERIFLEET_PUBSUB_PUSH` | `0` (off) | `1` on Cloud Run: publish only, do not start the local worker. Push subscription is the consumer. |
| `PUBSUB_TOPIC` | unset | Topic to publish `invoice.received`. Unset → no publish. |

Dispatch algorithm inside `enqueue` after persist:

1. If `VERIFLEET_QUEUE_DISPATCH` is off → return QUEUED. Tests call `execute(run_id, db)` on the fixture session.
2. If `PUBSUB_TOPIC` set **and** `VERIFLEET_PUBSUB_PUSH=1` → `pubsub.publish("invoice.received", {run_id, tenant_id, invoice, raw_text, file_id, roles, user_id})`. Do **not** start a thread.
3. Else → put `run_id` on the **single** in-process FIFO worker (one daemon thread for the process). Do **not** spawn one thread per invoice. Batch of three is sequential `execute`. Optionally still publish if `PUBSUB_TOPIC` is set (message sits unused when there is no subscription). Prefer **not** publishing when `VERIFLEET_PUBSUB_PUSH=0` so a stray local subscription cannot double-run; idempotent `execute` is the backstop if it does.

Local clone-and-run: topic unset, push flag 0, dispatch 1 → FIFO thread. Works without GCP.

Cloud Run (after PR-02 `deploy.sh`): topic set, `VERIFLEET_PUBSUB_PUSH=1` → publish only → push subscription hits `/pubsub/push`.

#### Who publishes what (no loop)

| Caller | May publish | Event name |
|---|---|---|
| `enqueue()` only | `invoice.received` | work item |
| `run_fleet` / `execute` | **never** `invoice.received` | — |
| `run_fleet` on sync `wait=true` | optional `invoice.completed` | receipt / Trace, not a consumer trigger |

**Remove** the existing `pubsub.publish("invoice.received", …)` at the end of `run_fleet` (`runtime.py` ~415–423). Leaving it in place plus a push subscription is a livelock: enqueue → push → execute → publish received → push → … At-least-once delivery plus a non-idempotent execute double-signs.

`test_pubsub_noop_without_topic` stays valid: no topic → `published` is false.

#### `execute()` idempotency

Lease: 60 seconds (same order as the push `--ack-deadline=60`).

| Row status | `execute()` | `/pubsub/push` HTTP |
|---|---|---|
| missing | raise / API 404 | 404 |
| `COMPLETED` (terminal, including BLOCKED) | return persisted result; **no** new `run_id`; **no** second sign | **200** (ack) |
| `RUNNING` and `updated_at` younger than 60s | return current row; **do not** run again | **503** (do **not** ack — Pub/Sub retries). A 200 here acks a corpse if Cloud Run died after writing RUNNING. |
| `RUNNING` and `updated_at` older than 60s | resume `run_fleet(run_id=…)` with **envelope** roles/invoice | 200 after resume completes |
| `QUEUED` | set `RUNNING` + `decision=""` + persist **envelope**, then `run_fleet(run_id=…)` | 200 after run |

Push handler maps `execute` “in-flight” to 503 via a small result flag or exception (`FleetInFlight`) so the HTTP layer does not have to re-read the row. Tests that POST `/pubsub/push` against a fresh RUNNING row expect 503, not 200.

`run_fleet(run_id=…)`:

- Reuse the id. Do not mint a second UUID.
- Load envelope when `invoice` / `raw_text` / `file_id` arguments are empty.
- Use envelope `roles` / `user_id` when the caller did not pass them. After the immediate RUNNING persist, those keys must still be on the row (`_wrap_payload`).
- On entry: `status=RUNNING`, persist immediately **as an envelope merge**.
- On exit: today’s COMPLETED path, persist `adk` / `pubsub` / `denied_tools`, still envelope-shaped `payload_json`.
- **Must not** publish `invoice.received`.

**Worker session rule:** the request `Session` cannot be used in the FIFO thread. The worker opens a **new** `SessionLocal()`, commits, closes. **`try/except` around each `execute`** so one failed row does not kill the drain of the other sweep invoices; log the exception, mark that `run_id` `COMPLETED`/`ESCALATED` with `reason="worker error: …"` only if still `RUNNING` (do not overwrite a COMPLETED row). Tests never start that thread (`VERIFLEET_QUEUE_DISPATCH=0`) and call `execute(run_id, db)` on the fixture session (the process `DATABASE_URL` is a different empty SQLite than `conftest`’s StaticPool).

#### Cloud Run consumer (`infra/deploy.sh` — PR-02, required)

Chicken-and-egg: deploy the service, read its URL, then create the push subscription.

After `gcloud run deploy` (and after setting env — see §4.6 / PR-02):

```bash
SERVICE_URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')
gcloud pubsub subscriptions create invoice-received-push \
  --topic=invoice.received \
  --push-endpoint="${SERVICE_URL}/api/v1/fleet/pubsub/push" \
  --ack-deadline=60 \
  || true   # idempotent re-run
```

`--allow-unauthenticated` is already on the service. Push endpoint is the same. Do not require OIDC for the hackathon demo (one less broken live take). Document in `infra/README.md` that this is demo-grade.

Also set on the service (script is incomplete today without these):

- `VERIFLEET_PUBSUB_PUSH=1`
- `DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@/${DB_NAME}?host=/cloudsql/${PROJECT_ID}:${REGION}:${INSTANCE}`
- `POSTGRES` password created or read, stored in Secret Manager, interpolated into `DATABASE_URL` (or `--set-secrets`)
- Existing: `PUBSUB_TOPIC`, `VERIFLEET_GEMINI_MODEL`, `GOOGLE_CLOUD_PROJECT`, `VERIAGENT_AUTO_INIT_DB=1`, Cloud SQL instance attach

Human still **runs** the script. The script must be sufficient; “run deploy.sh then /health works” is a lie until this patch lands.

#### API (`core_engine/main.py`)

`POST /api/v1/fleet/ingest?wait=true|false`  
`wait` default **`true`** (back-compat).

Request body unchanged:

```json
{ "invoice": { ... } }
{ "raw_text": "..." }
{ "file_id": "<uuid from /api/v1/invoices/upload>" }
```

`wait=true` → `200` + full `FleetResult.to_dict()` (today). Sync path may publish `invoice.completed` only.

`wait=false` → `202`:

```json
{
  "run_id": "uuid",
  "tenant_id": "enterprise-demo",
  "status": "QUEUED",
  "decision": null,
  "poll": "/api/v1/fleet/runs",
  "queue": "pubsub" | "thread" | "test"
}
```

`decision` is JSON `null` on the 202 body. The **row** stores `decision=""` (empty string), **not** the model default `ESCALATED`. `GET /runs` / `GET /runs/{id}` during QUEUED must not look like a failed audit.

`POST /api/v1/fleet/ingest/batch?wait=true|false`

- `wait=true` (default): today’s `{count, decisions, runs}`.
- `wait=false`: `202` `{count, run_ids, status: "QUEUED", poll: "/api/v1/fleet/runs"}`. Each row is its own `enqueue`. One FIFO worker (or one Pub/Sub message per row) drains them. Do not start three daemon threads.

`POST /api/v1/fleet/pubsub/push`

- If unwrapped body has `run_id` → `queue.execute(run_id)` **only**. Ignore `org.roles` / `org.user_id` for resume. Roles come from the envelope.
- Else today’s `run_fleet(...)` (new run from a raw invoice payload).
- Empty payload → `{status: ignored}` (200).
- HTTP: `COMPLETED` redelivery → **200**; `QUEUED` / expired `RUNNING` → run then **200**; in-flight `RUNNING` younger than 60s → **503** so Pub/Sub retries instead of acking a dead instance. Do not return 200 for “still running.”

**UI:** fixture buttons stay `wait=true`. Checkbox **“Background (202)”** on `/fleet`. The 3-invoice sweep **always** uses `wait=false` and polls `GET /api/v1/fleet/runs` (list, tenant-scoped, already includes `status` + `decision` + `run_id`) every 400ms until each sweep `run_id` has `status` not in `{QUEUED, RUNNING}` or 15s timeout. Do not poll `/runs/{id}` three times; the list is enough if `status` is trustworthy.

Empty `decision` on a QUEUED/RUNNING row: UI `decisionClass("")` is slate/neutral, **not** amber ESCALATED. Treat `""` / `null` as “not finished.”

#### Checklist (PR-02, not PR-04)

```python
{
  "id": "runtime",
  "name": "Agent Runtime (async background)",
  "status": "implemented",
  "proof": "POST /api/v1/fleet/ingest?wait=false → 202 QUEUED; queue.py FIFO or Pub/Sub push; execute() idempotent",
}
```

### 4.3 Persist the audit surface

**Edit** `core_engine/db/fleet_models.py` — add nullable `Text` columns:

- `adk_json`
- `pubsub_json`
- `denied_tools_json`

Do **not** invent a migration framework. `_ensure_fleet_columns(db)` in `runtime.py`:

```python
for col in ("adk_json", "pubsub_json", "denied_tools_json"):
    try:
        db.execute(text(f"ALTER TABLE fleet_runs ADD COLUMN IF NOT EXISTS {col} TEXT"))
        db.commit()
    except Exception:
        db.rollback()  # SQLite too old for IF NOT EXISTS, or column exists
        try:
            db.execute(text(f"ALTER TABLE fleet_runs ADD COLUMN {col} TEXT"))
            db.commit()
        except Exception:
            db.rollback()  # already exists / no table (create_all will handle)
```

Catch `sqlalchemy.exc.OperationalError` and `ProgrammingError`. After ALTER, the running process must use mapped attributes that exist on the class; if ALTER failed on an old file DB the next persist of those keys is skipped (`hasattr` / try setattr), never 500. Fresh DBs: `create_all` + `schema.sql`.

`VERIAGENT_AUTO_INIT_DB=1` already used on Cloud Run.

**Edit** `_persist` / `get_run` / `list_runs`:

- Persist `adk`, `pubsub`, `denied_tools`.
- **`payload_json` is always the envelope.** `_persist` loads the existing row (if any), calls `_wrap_payload`, writes the merge. A RUNNING or COMPLETED update must not collapse the column to a bare invoice. Sync ingest uses the same helper.
- `get_run` unwraps `payload` to the invoice; also returns `adk`, `pubsub`, `denied_tools`.
- `list_runs` stays lean (`run_id, tenant_id, status, decision, reason, invoice_hash, signed, created_at`). Sweep polls this list.

This persist work lives in **PR-02** together with the queue. PR-01 does not add columns.

### 4.4 PDF / OCR demo path

Reuse, do not replace, `OCRService` + `_extract_payload`.

**New fixture:** `demo/fixtures/valid_invoice.pdf`  
**Copy:** `frontend/public/demo-fixtures/valid_invoice.pdf`

Constraint: a **text** PDF (not a scan). `PdfReader` extract of **the committed file** must `json.loads` into the same **keys** as `demo/fixtures/valid_invoice.json` (`issuer_tax_id`, `total_base`, `total_tax`, `total_amount`, `series`, `number`, `customer`, `lines`). Produce the file so extractors that insert whitespace still parse (pretty-printed JSON is fine; `json.loads` ignores extra whitespace. Do **not** wrap the JSON in prose).

Committed artifact is required. Tests must not substitute a synthetic in-memory PDF for extractability.

**Stamp `number` after file_id parse** (runtime, not only UI). JSON fixture buttons already call `stampNumber()` so repeats miss `unique(tenant, series, number, issuer)`. The PDF is frozen `number: "001"`. Second PDF click would ESCALATE on the unique constraint and look broken.

In `_extract_payload`, after a successful `json.loads` from `file_id` (or `raw_text` that came from a file):

```python
base = str(parsed.get("number") or "001")
parsed["number"] = f"{base}-{int(time.time() * 1000) % 1_000_000:06d}"
```

Hash still comes from `core_engine` on the stamped payload. Document this in `/fleet` caption: “PDF text extract; number stamped so repeats do not collide. Gemini does not write the hash.”

Do **not** stamp JSON `invoice` bodies twice (UI already stamps). Only stamp when the source is `file_id` (and optionally `raw_text` that parsed as an invoice **and** a query/flag says so). Simplest rule: stamp only when `file_id` is set.

**UI** (`frontend/src/app/fleet/page.tsx`):

- New button **Valid invoice (PDF)**.
- Load the static PDF from the Next origin: `fetch("/demo-fixtures/valid_invoice.pdf")` (this is a static file on :3000; that part is correct).
- Upload and ingest go through `apiClient` so `baseURL` is `NEXT_PUBLIC_API_URL || http://localhost:8000`. **Do not** `fetch("/api/v1/invoices/upload")` — there is no Next rewrite; that hits the frontend and 404s. **Do not** set `Content-Type: multipart/form-data` by hand (breaks the boundary).

```ts
const blob = await (await fetch("/demo-fixtures/valid_invoice.pdf")).blob();
const form = new FormData();
form.append("file", blob, "valid_invoice.pdf");
const up = await apiClient.post("/api/v1/invoices/upload", form, {
  headers: { ...headers(), "Content-Type": undefined }, // drop JSON default; browser sets multipart boundary
});
await apiClient.post(
  "/api/v1/fleet/ingest",
  { file_id: up.data.file_id },
  { headers: headers() },
);
```

`wait=true` for the PDF button (instant SIGNED). Caption as above.

No image/tesseract in the live take. Scanned OCR remains the existing `OCRService._extract_from_image` for later; out of this sprint.

### 4.5 Judge-facing UI cleanup

`/fleet` is the submission. Do not rewrite Smart Audit.

| File | Change |
|---|---|
| `frontend/src/app/layout.tsx` | `title: "VeriFleet — Fortified Enterprise Fleet"`, `description` English one-liner. `lang="en"`. |
| `frontend/src/app/page.tsx` | Delete `RECENT_HISTORY`. Replace that panel with **only** an English banner: “Judges: the contest console is /fleet” + link/button. Do **not** fetch live `/runs` on the homepage. Keep Spanish Smart Audit upload if cheap; do not translate the whole page. |
| `frontend/src/app/history/page.tsx` | Out of the judge video. Add a one-line English note + link to `/fleet`. Leave `FULL_HISTORY` mock. `/fleet` already has live “Recent runs”. |
| `frontend/src/app/fleet/page.tsx` | PDF button (apiClient upload), background checkbox, sweep poll on **list** `/runs`, runner card, `decisionClass("")` neutral. |

No new frameworks. No new CSS system.

### 4.6 Docs that make Stage One and the 5-minute clone real

Edit, do not invent a docs site.

**`README.md`** — keep English. Required sections, in this order:

1. Title + track + one sentence (already there).
2. Mandatory stack table (already there) — add a **Proof** column: `/health`, `ai_agents/adk/runner.py`, `infra/deploy.sh`.
3. **5-minute clone-and-run** (replace “Quick start”). Windows-first. **Must set SQLite** — default engine is localhost Postgres (`core_engine/db/database.py`) and a Windows judge without Docker gets connection refused.

```bash
git clone <repo>
cd VeriAgent
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt

set DATABASE_URL=sqlite:///verifleet.db
set VERIAGENT_AUTO_INIT_DB=1
# optional live Gemini: set GEMINI_API_KEY
python -m uvicorn core_engine.main:app --reload --port 8000
```

Unix:

```bash
source .venv/bin/activate
export DATABASE_URL=sqlite:///verifleet.db
export VERIAGENT_AUTO_INIT_DB=1
python -m uvicorn core_engine.main:app --reload --port 8000
```

Optional Postgres: `docker compose up db -d` then `DATABASE_URL=postgresql://veriagent:securepassword@localhost:5432/veriagent_core`.

```bash
# other terminal
cd frontend && npm install && npm run dev
```

Open http://localhost:3000/fleet  
Headers (UI sets them): `X-Tenant-Id: enterprise-demo`, `X-User-Id: judge`, `X-Roles: issuer`

```bash
curl -s http://localhost:8000/health
curl -s -H "X-Tenant-Id: enterprise-demo" -H "X-Roles: issuer" http://localhost:8000/api/v1/fleet/compliance
python -m pytest tests/test_fleet_adk.py -q
```

4. What you will see (four buttons + PDF + sweep + auditor role).
5. Architecture ASCII + link to `docs/architecture-ata.svg`.
6. Disclosure pointer to `CONTEST.md`.
7. Deploy pointer to `infra/README.md` — **“hosted URL is filled after human deploy; this README is valid offline.”**

**`CONTEST.md`** — add:

- Stack proof table with file + endpoint + string.
- Explicit: “ADK `InMemoryRunner` runs a **consult-only** Agent after deterministic gates. Deterministic `run_fleet` owns math, armor, and `invoice.sign`. The LLM never writes the hash.”
- Judge click path: `/fleet` only.
- Pre-existing vs submission-period list — add `runner.py`, `queue.py`, PDF fixture, async ingest, `deploy.sh` push subscription + `DATABASE_URL`.

**New** `demo/judge.md` — click-by-click, 5 min local (including the two `set`/`export` lines) + 4 min video beats.

**Edit** `demo/script.md` — insert a 15-second PDF beat and a 20-second background-sweep beat. Keep total ≤ 4:00. Architecture overlay: “Consult-only Runner; kernel hashes” and “Pub/Sub push subscription is the work queue on Cloud Run; local fallback is one FIFO thread.”

**Edit** `docs/architecture-ata.svg` — ADK box: `InMemoryRunner → fiscal_fleet_consult (no tools)`. Pub/Sub box: `push sub → /pubsub/push (Cloud Run) / FIFO thread (local)`. Copy to `frontend/public/architecture-ata.svg`.

**Edit** `infra/README.md` — blocking, not optional. First paragraph:

> `bash infra/deploy.sh` is **not** run in CI. A human with a billed project runs it **after PR-02**. The script is incomplete until it sets `DATABASE_URL` (Cloud SQL unix socket), a DB password/secret, `VERIFLEET_PUBSUB_PUSH=1`, `CORS_ORIGINS`, and a **push subscription** to `/api/v1/fleet/pubsub/push`. Then paste `https://<service>-<hash>.<region>.run.app` into Devpost and `CONTEST.md`. Frontend: `NEXT_PUBLIC_API_URL` = that backend URL.

### 4.7 API / file contract (implementers)

| Method | Path | Change |
|---|---|---|
| GET | `/health` | `model`/`framework`/`gcp_services` from `config.py`; add `runner` |
| POST | `/api/v1/fleet/ingest?wait=` | `wait=false` → 202 QUEUED, `decision` null |
| POST | `/api/v1/fleet/ingest/batch?wait=` | same; sequential enqueue |
| GET | `/api/v1/fleet/runs` | Sweep poll target; `status` trustworthy; empty `decision` = not finished |
| GET | `/api/v1/fleet/runs/{id}` | Return `adk`, `pubsub`, `denied_tools` (PR-02) |
| GET | `/api/v1/fleet/compliance` | `runner` item; `runtime` proof updated in PR-02 |
| POST | `/api/v1/fleet/pubsub/push` | `run_id` → `execute` only; ignore header roles; in-flight → 503 |
| POST | `/api/v1/invoices/upload` | Unchanged; used by PDF button via apiClient |

| Path | Action |
|---|---|
| `ai_agents/adk/runner.py` | **Create** — consult-only Agent + sync facade |
| `ai_agents/adk/queue.py` | **Create** — enqueue / execute / FIFO worker |
| `ai_agents/adk/consult.py` | `skip_reason()`; prefer runner; wrap `_generate` |
| `ai_agents/adk/agents.py` | `build_consult_agent()`; `adk_status.runner` |
| `ai_agents/adk/runtime.py` | `run_id` resume; **remove** `invoice.received` publish; persist extras; `_ensure_fleet_columns`; stamp `file_id` number |
| `ai_agents/adk/compliance.py` | Checklist (`runner` in PR-01; `runtime` proof in PR-02) |
| `ai_agents/adk/pubsub.py` | Queue payload (`run_id`, roles, invoice) |
| `core_engine/main.py` | Query `wait`, 202, health imports, push → execute |
| `core_engine/db/fleet_models.py` | Three columns |
| `core_engine/db/schema.sql` | Same three columns |
| `infra/deploy.sh` | `DATABASE_URL`, `VERIFLEET_PUBSUB_PUSH=1`, push subscription (PR-02) |
| `tests/conftest.py` | `VERIFLEET_QUEUE_DISPATCH=0` |
| `tests/test_fleet_adk.py` | New cases (below) |
| `frontend/src/app/fleet/page.tsx` | PDF via apiClient, background, sweep list-poll, runner card |
| `frontend/src/app/page.tsx` | Delete `RECENT_HISTORY`; banner + `/fleet` only |
| `frontend/src/app/layout.tsx` | Title |
| `demo/fixtures/valid_invoice.pdf` | **Create** (must parse) |
| `frontend/public/demo-fixtures/valid_invoice.pdf` | Copy |
| `demo/judge.md` | **Create** |
| `README.md`, `CONTEST.md`, `demo/script.md`, `docs/architecture-ata.svg`, `infra/README.md` | Edit |

**Do not touch:** `core_engine/crypto/**`, `core_engine/services/invoice_service.py` sign/hash, `core_engine/aeat_connector.py`, `ai_agents/crew.py`, `ai_agents/graphs/**`, ProductGraph routes.

---

## 5. Alternatives considered

| Alternative | Why rejected |
|---|---|
| **Let ADK Runner own the whole pipeline via function tools** (`invoice.sign` as an ADK tool). Authentic “agents drive the fleet.” | Flaky under `VERIFLEET_SKIP_LLM`, can skip auditor, fights NORMAS (probabilistic code writing a hash). Architectural Discipline scores **higher** if the kernel stays deterministic. |
| **`InMemoryRunner` on `FiscalFleetOrchestrator` + four children, no tools.** | Instructions say “call tools / delegate / sign.” No tools attached → multi-turn, 20s timeout, or `parse_recommendation` miss. Stage One grep would pass; the live ADK card would look dead. **Consult-only Agent is the chosen path.** |
| **Replace consult() entirely and fail when ADK is missing.** | Local/Windows judges and CI would fail Stage One appearance if `google-adk` import breaks. Fallback `_generate` keeps Gemini on-path. |
| **Celery / Cloud Tasks / Redis queue.** | New ops surface, not 5-minute clone-and-run. `fleet_runs` + one FIFO thread + existing Pub/Sub push is enough for the 40% story. |
| **Default `wait=false`.** | Breaks 25 existing tests and the instant demo. Default stays sync; async is opt-in and used by the sweep. |
| **Vertex Document AI / Gemma OCR for the PDF beat.** | Extra billing, extra failure mode in a live take. Text PDF + existing `pypdf` is honest and cloneable. |
| **Redirect `/` → `/fleet`.** | Breaks Smart Audit for the home team. Banner + link is enough. |
| **Live `/runs` on the homepage.** | Extra request, extra failure if the API is down. Banner is cheaper and clearer. |
| **Rewrite homepage to English and delete mocks.** | Scope creep. Judges are told `/fleet` is the submission. |
| **Claim Cloud Run is live in README before deploy.** | Honesty rail. Docs say “URL after human deploy.” |
| **Leave `deploy.sh` untouched (docs-only).** | Hosted `wait=false` would stay QUEUED forever (no consumer) and `/health` would die on localhost Postgres. Completing the script is in PR-02; running it stays human. |

---

## 6. Risks / honesty rails

These are project-specific. They override cleverness.

1. **LLM never writes the hash.** `create_and_sign` remains the only writer. Runner output is a recommendation string. Tests assert `invoice_hash` exists only on SIGNED after `core_engine` sign.
2. **Tighten, never loosen.** `SIGNED` + `ESCALATE|BLOCK` → `ESCALATED`. `ESCALATED|BLOCKED` + `SIGN` stays failed. Existing `test_consult_cannot_loosen_math_gate` and `test_consult_can_tighten_sign` stay, plus a runner-mocked twin.
3. **`core_engine/crypto/` is frozen.** No PR in this plan opens that tree. `fleet_models.py`, `schema.sql`, `main.py` fleet routes, and `infra/deploy.sh` are the only infra/core edits.
4. **Do not claim Runner signs.** README, CONTEST, `/fleet` copy, video script: “InMemoryRunner consults on `fiscal_fleet_consult`; `core_engine` hashes.”
5. **Do not claim a live Cloud Run URL** until a human pastes one. Checklist Pub/Sub item stays `ready` when `PUBSUB_TOPIC` is unset (`live` when set).
6. **Do not claim ingest is async by default.** Default is sync. The sweep demonstrates 202.
7. **Do not claim Gemma Armor or scanned OCR** in the video.
8. **`VERIFLEET_SKIP_LLM=1` in tests** remains. No test calls Gemini or ADK for real. `/health` may still say `InMemoryRunner` (grep); `/compliance` says skipped.
9. **Thread + SQLite:** worker opens its own session. Tests set `VERIFLEET_QUEUE_DISPATCH=0` and call `execute()` on the fixture session. Never race the daemon against StaticPool.
10. **Pub/Sub payload may carry the invoice for the worker.** Armor still inspects before consult. Consult still receives redacted text. Do not log envelope NIFs in application logs.
11. **One submission, one prize.** Do not split VeriFleet vs Taskmaster. Do not mention CrewAI on the judge path.
12. **New Projects Only.** Keep the CONTEST.md disclosure. Adding `runner.py` / `queue.py` does not make the kernel “new.”
13. **Only `enqueue()` publishes `invoice.received`.** `run_fleet` / `execute` never do. Prevents the push livelock.
14. **`execute` is idempotent.** COMPLETED → return stored row. No second sign.
15. **Resume roles come from the envelope, and `_persist` must not erase it.** Header `X-Roles` on `/pubsub/push` is ignored. Auditor + Background (202) and auditor crash-resume must ESCALATE. In-flight push is **503**, not 200.
16. **Do not claim `deploy.sh` is sufficient until PR-02 lands** (`DATABASE_URL` + push subscription + `VERIFLEET_PUBSUB_PUSH=1`).

---

## 7. Testing plan

Update `tests/conftest.py`:

```python
os.environ.setdefault("VERIFLEET_SKIP_LLM", "1")
os.environ.setdefault("VERIFLEET_QUEUE_DISPATCH", "0")
os.environ.pop("PUBSUB_TOPIC", None)
os.environ.pop("VERIFLEET_PUBSUB_PUSH", None)
```

Do **not** keep conftest “as-is.” Dispatch must be off or TestClient `?wait=false` starts a worker against the process engine (empty `sqlite:///:memory:`), then the test calls `execute` on the fixture session (double-run / wrong DB).

All existing 25 cases in `tests/test_fleet_adk.py` must stay green. Do not rewrite their assertions except additive `get_run` fields. `test_compliance_and_identity_api` uses a subset of item ids; adding `runner` is safe. `tests/test_api.py` `test_health_check` is additive-safe if it only checks `status`.

### New cases (same file unless noted)

| Test | Acceptance |
|---|---|
| `test_runner_skipped_when_llm_disabled` | `consult()` / `run_orchestrator()` returns `invoked=False`, `reason=="skip_llm"` (conftest sets the flag), `runner=none`, `model=gemini-3.5-flash`, `framework=google-adk` |
| `test_runner_invoked_shape` | Monkeypatch `run_orchestrator` to return `invoked=True`, `runner=InMemoryRunner`, `recommendation=SIGN`. Valid invoice still SIGNED. `result.adk["consult"]["runner"] == "InMemoryRunner"` |
| `test_runner_cannot_loosen_math_gate` | Monkeypatch runner to `recommendation=SIGN`. Math-fail invoice stays ESCALATED, `signed is False`, no `InvoiceModel` row |
| `test_runner_can_tighten_sign` | Monkeypatch runner to `ESCALATE`. Valid invoice ESCALATED, `"tightened"` in reason |
| `test_get_run_returns_adk_and_pubsub` | After sync ingest, `get_run` includes `adk`, `pubsub`, `denied_tools` (PR-02) |
| `test_async_ingest_api_202` | TestClient `POST /api/v1/fleet/ingest?wait=false` → 202, `status=QUEUED`, `decision` is null, `run_id` set. Row `decision==""`. **No worker started.** Then `queue.execute(run_id, db)` → SIGNED. `GET /runs/{id}` COMPLETED |
| `test_batch_async_queues_three` | `wait=false` batch of the three fixtures → 202, three `run_ids`. Execute each in order. Decisions `SIGNED, ESCALATED, BLOCKED` |
| `test_async_auditor_cannot_sign` | Headers/roles `auditor`, `wait=false`, then `execute` → `ESCALATED`, `"invoice.sign"` in reason, no `InvoiceModel` row |
| `test_execute_completed_is_noop` | SIGNED run; second `execute` returns same `run_id`, same hash, still one `InvoiceModel` row |
| `test_pubsub_push_inflight_is_503` | Persist envelope + `status=RUNNING` + fresh `updated_at`; POST `/pubsub/push` `{run_id}` → 503; row still RUNNING; no new `InvoiceModel` |
| `test_execute_resume_keeps_auditor_after_running_persist` | Persist QUEUED envelope `roles=["auditor"]`. Simulate a crash persist: `status=RUNNING`, `updated_at` older than 60s, `payload_json` still the envelope (and a second variant that `_persist` would have written via `_wrap_payload` after extract). `execute` → `ESCALATED`, `"invoice.sign"` in reason, no sign |
| `test_pubsub_push_resumes_run_id` | Persist QUEUED envelope (include `roles`); POST `/pubsub/push` with `{run_id}` only (no roles header / wrong header) → COMPLETED same `run_id`, roles from envelope |
| `test_committed_pdf_extracts_valid_json` | `PdfReader("demo/fixtures/valid_invoice.pdf")` → `json.loads(extract)` → required keys match `valid_invoice.json`. **No synthetic PDF.** |
| `test_pdf_file_id_signs` | Copy **that committed file** into `UPLOAD_DIR` as `{file_id}.pdf`. `run_fleet(file_id=...)` → SIGNED. Second call with the same file also SIGNED (stamped number) |
| `test_health_stage_one_strings` | `/health` contains `gemini-3.5-flash`, `google-adk`, `InMemoryRunner`, track `Fortified Enterprise Fleet` |
| `test_compliance_includes_runner` | Checklist item ids include `runner`; `framework == google-adk` |

Runner unit test may live at the top of `test_fleet_adk.py`. Do not add a live-network test.

Manual (not CI): with `GEMINI_API_KEY` and `VERIFLEET_SKIP_LLM` unset, one valid ingest shows `adk.consult.invoked=true` and `runner=InMemoryRunner` **or** a fallback reason — never a 500.

---

## 8. Human ops (not implementation PRs)

Do these after PR-01…PR-04 merge. They are the remaining 30% demo score. They are **out of coding scope**.

**Blocking env the human must have (PR-02 makes the script consume them; the human still supplies the project):**

| Item | Why |
|---|---|
| Billed `PROJECT_ID` | Cloud Run / SQL / Pub/Sub |
| `DATABASE_URL` via Cloud SQL socket + password/secret | Process default is localhost Postgres; without this `/health` dies after deploy |
| `PUBSUB_TOPIC` + push subscription to `/api/v1/fleet/pubsub/push` | Without the subscription, hosted `wait=false` stays QUEUED |
| `VERIFLEET_PUBSUB_PUSH=1` | Stops the in-process thread on Cloud Run (scale-to-zero) |
| `CORS_ORIGINS` | Frontend origin |
| `NEXT_PUBLIC_API_URL` | Frontend → backend |
| `GEMINI_API_KEY` or Vertex on the service | Live consult |

Checklist:

1. **GCP:** billed project (hackathon credits). `export PROJECT_ID=...` and `bash infra/deploy.sh` **after PR-02**. Confirm `/health` on `*.run.app` returns `model`, `framework`, `runner`. Confirm a Pub/Sub **subscription** `invoice-received-push` exists. Confirm one `wait=false` ingest leaves `QUEUED` and then `COMPLETED` (not stuck).
2. **Frontend host:** Cloud Run or equivalent with `NEXT_PUBLIC_API_URL` pointing at the backend. `CORS_ORIGINS` includes that origin.
3. **Paste URL** into Devpost “Hosted Project URL” and a one-line “Live: https://…” at the top of `CONTEST.md`.
4. **Video:** one unedited English take ≤ 4:00 following `demo/script.md`. Second window: Cloud Run + Cloud Trace + Pub/Sub subscription. End on the live URL + CONTEST disclosure.
5. **Blog + `#AllThingsAgenticHackathon`** post. One submission, Grand $50k target, Fleet $20k fallback.
6. **Devpost page:** paste README architecture, CONTEST disclosure, stack table, judge login, demo GIF/video. Do not invent a second product.

---

## Key Decisions

1. **Consult-only Agent under `InMemoryRunner`, not the four-child graph.** `build_consult_agent()` has no `sub_agents` and no tools; instruction matches today’s consult prompt. `build_adk_root()` stays for registry / `adk web`. Tighten-only still applies. Rationale: Stage One needs a real Runner invocation that returns `SIGN`/`ESCALATE` in 20s; running the tool-less four-agent graph will timeout or miss `parse_recommendation`. Full tool-calling is still rejected (NORMAS + flaky tests).

2. **`consult()` stays the public function.** Runtime does not grow a second LLM path. Runner is the preferred backend; `_generate` is the fallback and must not raise. `skip_reason()` is shared. Rationale: one tighten-only policy, one mock point, no flake between skip strings.

3. **Async is opt-in (`wait=false` → 202).** Default ingest stays sync. Rationale: 25 tests and the 5-minute clone stay green; the sweep + checkbox prove background work for the 40% score.

4. **Durability is `fleet_runs`. Consumer is explicit.** Local: one FIFO worker thread (`VERIFLEET_PUBSUB_PUSH=0`). Cloud Run: **only** `enqueue()` publishes `invoice.received`; a push subscription created by `deploy.sh` hits `/pubsub/push`. Tests: `VERIFLEET_QUEUE_DISPATCH=0`. Rationale: today’s script has a topic and no consumer; leaving that would fail the hosted sweep. Celery is out of scope.

5. **PDF is a committed text fixture, not an OCR product.** Tests parse **that file**. Runtime stamps `number` on `file_id` parses. Upload uses `apiClient` + unset `Content-Type`. Rationale: `_extract_payload` already `json.loads`s; repeats must not hit the unique constraint; relative `fetch` would hit Next, not uvicorn.

6. **Persist ADK / Pub/Sub / denied tools on the run row (PR-02).** Rationale: judges refresh and screenshot `/runs/{id}`; today those fields vanish after the POST response. PR-01 acceptance does not include refresh audit.

7. **Homepage is a banner + `/fleet` link only.** Delete `RECENT_HISTORY`. Do not fetch live runs on `/`. Rationale: cheapest way to stop judges seeing 2023 mocks; `/fleet` already has history.

8. **Docs over new frameworks.** README 5-minute path **sets `DATABASE_URL=sqlite:///verifleet.db`**. `demo/judge.md`. Honest “URL after human deploy.” `deploy.sh` is completed in PR-02, executed by a human.

9. **NORMAS split is a hard gate.** No `core_engine/crypto` edits. Fleet tables, fleet routes, and `infra/deploy.sh` are the allowed core/infra surface. CrewAI / ProductGraph / AEAT SOAP stay off the hot path.

10. **Human ops stay off the PR list except script completeness.** Running deploy, video, social, Devpost paste are human. A deploy script that cannot host the queue or reach Cloud SQL is not “out of scope” — it is a PR-02 bug.

11. **QUEUED rows store `decision=""`.** Model default `ESCALATED` must not flash on the sweep. UI treats empty decision as “not finished.” Sweep polls `GET /api/v1/fleet/runs`.

12. **`execute` is idempotent and role-safe.** COMPLETED is a no-op (HTTP 200). In-flight RUNNING younger than 60s is HTTP **503** so Pub/Sub does not ack a dead instance. Roles live in the `payload_json` envelope; `_persist` merges that wrapper on every write, including the immediate RUNNING persist. FIFO worker `try/except` per `run_id`.

---

## Open Questions

None that block implementation. The following were open in the first draft and are **closed** here:

| Topic | Decision |
|---|---|
| Runner vs full tool loop | Runner-as-consult (unchanged) |
| Four-child graph vs consult-only Agent | **Consult-only Agent** (`fiscal_fleet_consult`). Four-child graph stays for registry / `adk web` only. |
| Default wait | `true` |
| Queue product | `fleet_runs` + one FIFO thread / Pub/Sub push |
| How tests suppress the worker | `VERIFLEET_QUEUE_DISPATCH=0` in `tests/conftest.py`; tests call `execute(run_id, db)` |
| Who creates the push subscription | `infra/deploy.sh` after `gcloud run deploy` (PR-02). Human runs the script. |
| Who publishes `invoice.received` | **Only `enqueue()`**. `run_fleet` never does. |
| Envelope vs `_persist` | Every write is `_wrap_payload` merge. RUNNING persist must keep `roles`. |
| In-flight push HTTP | **503** (retry). COMPLETED → 200. |
| PDF | Committed text fixture; required parse test; stamp `number` on `file_id` |
| Homepage | Banner + `/fleet` only (no live `/runs`) |
| `InMemoryRunner` import drift | Try `InMemoryRunner` then `Runner`+in-memory session; else `adk_unavailable` + fallback |

No user input required.

---

## PR Plan

Four PRs, independently reviewable, each mergeable with tests green. Implement in order. Do not combine 1+2 (Runner vs queue are different risk). Docs come last so they describe merged behavior.

### PR-01 — Stage One: ADK InMemoryRunner on the consult-only Agent

- **Title:** `fleet: invoke ADK InMemoryRunner on consult-only Agent (tighten-only)`
- **Dependencies:** none
- **Files / components:**
  - `ai_agents/adk/runner.py` (new)
  - `ai_agents/adk/consult.py` (`skip_reason()`, prefer runner, wrap `_generate`)
  - `ai_agents/adk/agents.py` (`build_consult_agent()`, `adk_status`)
  - `ai_agents/adk/runtime.py` (adk payload only; **no** queue, **no** schema)
  - `ai_agents/adk/compliance.py` (`runner` item + ADK proof; do **not** change `runtime` proof yet)
  - `core_engine/main.py` (`/health` imports `GEMINI_MODEL`, `GOOGLE_AGENT_FRAMEWORK`, `GCP_SERVICES`; add `runner`)
  - `tests/test_fleet_adk.py` (runner skip / mock tighten / mock loosen / health / compliance)
- **Description:** Add `build_consult_agent()` (no sub-agents, no tools) and `run_orchestrator()` wrapping `InMemoryRunner` with the sync facade (`asyncio.run` / `wait_for` 20s / worker thread if a loop is running). Collect last model text; reuse `parse_recommendation`. Wire `consult()` to prefer it and fall back to wrapped `_generate`. Do not attach sign tools. Do not change ingest sync behavior. Tests stay on `VERIFLEET_SKIP_LLM=1` and monkeypatch. **Refresh audit of runner fields is PR-02** (no new columns here).
- **Acceptance:** `/health` and `/compliance` expose `google-adk`, `gemini-3.5-flash`, `InMemoryRunner`; math-fail + mocked `SIGN` still ESCALATED; `skip_reason()` is `skip_llm` under conftest; existing 25 tests green.

### PR-02 — Background ingest: 202 + durable queue + Pub/Sub consumer

- **Title:** `fleet: async ingest (wait=false) with fleet_runs queue and Pub/Sub push`
- **Dependencies:** **PR-01** (both edit `runtime.py`, `compliance.py`, `main.py`, `tests/test_fleet_adk.py`). Rebase on PR-01. Do not land PR-02 first.
- **Files / components:**
  - `ai_agents/adk/queue.py` (new) — enqueue / execute / one FIFO worker
  - `ai_agents/adk/runtime.py` (`run_id` resume, envelope, **delete** `invoice.received` publish, `_ensure_fleet_columns` with `IF NOT EXISTS` + `OperationalError`)
  - `ai_agents/adk/pubsub.py` (richer `invoice.received` payload)
  - `ai_agents/adk/compliance.py` (`runtime` proof → `wait=false` + `queue.py`)
  - `core_engine/db/fleet_models.py` (`adk_json`, `pubsub_json`, `denied_tools_json`)
  - `core_engine/db/schema.sql` (same columns)
  - `core_engine/main.py` (`wait` query, 202, push → `execute` only)
  - `infra/deploy.sh` — `DATABASE_URL` (Cloud SQL socket + password/secret), `VERIFLEET_PUBSUB_PUSH=1`, push subscription after deploy
  - `tests/conftest.py` — `VERIFLEET_QUEUE_DISPATCH=0`
  - `tests/test_fleet_adk.py` (202, batch async, auditor async, execute noop, in-flight 503, resume keeps auditor roles, push resume, `get_run` extras)
- **Description:** Default `wait=true` remains 200 + completed. `wait=false` persists `QUEUED` with `decision=""` and an envelope `{invoice, raw_text, file_id, roles, user_id}`. `_persist` / RUNNING updates **merge** that envelope (never dump a bare invoice). Dispatch: tests off; Cloud Run publish-only; local one FIFO thread with `try/except` per row. **Only `enqueue()` publishes `invoice.received`.** `execute` is idempotent and reads roles from the row. `/pubsub/push`: COMPLETED → 200; in-flight → **503**; expired RUNNING / QUEUED → run. Persist ADK / Pub/Sub / denied tools. Keep queue + schema in this one PR.
- **Acceptance:** TestClient 202 → `execute()` → SIGNED on same `run_id`; auditor + 202 + execute → ESCALATED; auditor resume after a RUNNING persist still ESCALATED; in-flight push is 503; second execute on COMPLETED is a no-op; three-fixture async batch yields SIGNED / ESCALATED / BLOCKED; no Gemini in CI; no worker thread under conftest.

### PR-03 — Judge console: PDF fixture, background sweep, kill mock history

- **Title:** `fleet: PDF fixture + async sweep UI; remove Smart Audit mock history`
- **Dependencies:** PR-02 (sweep poll + 202). PDF ingest via `file_id` also needs the runtime stamp from this PR (or a tiny `_extract_payload` change here).
- **Files / components:**
  - `demo/fixtures/valid_invoice.pdf` (new)
  - `frontend/public/demo-fixtures/valid_invoice.pdf` (copy)
  - `ai_agents/adk/runtime.py` (`file_id` number stamp after JSON parse)
  - `frontend/src/app/fleet/page.tsx` (PDF via **apiClient** + `Content-Type: undefined`, Background checkbox, sweep polls `GET /runs`, runner card, neutral empty decision)
  - `frontend/src/app/page.tsx` (delete `RECENT_HISTORY`; banner + `/fleet` only)
  - `frontend/src/app/layout.tsx` (title/description/lang)
  - `tests/test_fleet_adk.py` (`test_committed_pdf_extracts_valid_json`, `test_pdf_file_id_signs` using the committed file twice)
- **Description:** Commit a text PDF that `pypdf` extracts to the valid-invoice JSON keys. Tests parse **that** file. `/fleet` uploads via `apiClient` (port 8000) and ingests `{file_id}`. Runtime stamps `number` so the second click still SIGNED. Sweep uses `wait=false` and polls the list. Homepage is a judge banner only.
- **Acceptance:** Committed PDF parses; PDF path SIGNED twice; fixture buttons still instant; layout title is VeriFleet; `page.tsx` has no `RECENT_HISTORY` constant.

### PR-04 — Judge docs: 5-minute clone, script, architecture, honest deploy

- **Title:** `docs: 5-minute judge path and Stage One proof`
- **Dependencies:** PR-01, PR-02, PR-03 (docs must match merged APIs).
- **Files / components:**
  - `README.md` (SQLite `set`/`export` in the 5-minute block; optional `docker compose up db`)
  - `CONTEST.md`
  - `demo/judge.md` (new)
  - `demo/script.md`
  - `docs/architecture-ata.svg`
  - `frontend/public/architecture-ata.svg`
  - `infra/README.md` (blocking env list: `DATABASE_URL`, password, `CORS_ORIGINS`, `PUBSUB_TOPIC`, push subscription, `VERIFLEET_PUBSUB_PUSH`, `NEXT_PUBLIC_API_URL`)
- **Description:** Rewrite the clone-and-run so a Windows judge without Docker hits `/fleet` in five minutes. Add `demo/judge.md`. Update the 4-minute script with PDF + background beats without exceeding 4:00. Diagram labels consult-only Runner and Pub/Sub-as-push-queue. Infra README states the script is complete after PR-02 and execution is human. No application logic unless a proof string drifted (then a one-line `compliance.py` fix is allowed).
- **Acceptance:** a reviewer can follow README without opening this design doc and without Postgres; CONTEST.md lists Runner + async + PDF + push subscription as submission-period work and still discloses `core_engine`.

**After PR-04 (human, not a PR):** run the completed `deploy.sh`, confirm subscription + one async ingest, paste URL, record video, Devpost, blog, hashtag.
