# Grok bot QA — VeriFleet end-to-end

Clone: `https://github.com/AlonsoAlviraa/VeriAgent.git`  
Branch: `main`  
Do **not** invent Cloud Run URLs. Do **not** print API keys. Do **not** scrape real invoices.

## Setup (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL = "sqlite:///verifleet.db"
$env:VERIAGENT_AUTO_INIT_DB = "1"
$env:VERIFLEET_SKIP_LLM = "1"
python -m uvicorn core_engine.main:app --reload --host 127.0.0.1 --port 8000
```

Second terminal:

```powershell
cd frontend
npm install
$env:AUTH_SECRET = "dev-only-not-for-prod"
npm run dev
```

Optional live consult: if the human has `XAI_API_KEY` or `GEMINI_API_KEY` in a local `.env`, unset `VERIFLEET_SKIP_LLM` for one consult sample. Never commit `.env`.

## Must pass

1. `curl http://localhost:8000/health` contains `gemini-3.5-flash`, `google-adk`, and `InMemoryRunner` (or an explicit skip reason).
2. `GET http://localhost:8000/api/v1/fleet/compliance` checklist is honest.
3. `python -m pytest tests/test_fleet_adk.py tests/test_corpus_campaign.py tests/test_api.py tests/test_tenant_isolation.py tests/test_schemas.py tests/test_fiscal_id.py -q`
4. Open `http://localhost:3000/fleet` (no login). Click every fixture:
   - Valid invoice → **SIGNED** + hash present
   - Math error → **ESCALATED**, no signed hash
   - Prompt injection → **BLOCKED**
   - Hospitality → **ESCALATED** (enterprise-demo memory)
   - Valid invoice (PDF) → upload → **SIGNED**
   - 3-invoice sweep → SIGNED / ESCALATED / BLOCKED
   - Role `auditor` + Valid invoice → cannot sign
5. Open `/` — upload `frontend/public/demo-fixtures/valid_invoice.pdf` (and `demo/fixtures/human_invoice.pdf`). Confirm no 500.
6. Open `/history` — mock ledger is labeled as mock; link to `/fleet` works.
7. Desktop and ~390px width: nav, fixture cards, and upload dropzone remain usable.
8. Hunt regressions: `/auth/login` still renders; no invented metrics; consult remains tighten-only.

## Report

Write a pass/fail table with the **command or click** and the **actual decision/status**. Quote hashes only as first/last 8 chars. List bugs with `file:line`. Do not flip any gate to make the report look greener.
