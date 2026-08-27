# Judge path (5 minutes local + 4-minute video)

## Local (no Docker)

```bash
set DATABASE_URL=sqlite:///verifleet.db
set VERIAGENT_AUTO_INIT_DB=1
python -m uvicorn core_engine.main:app --reload --port 8000
cd frontend && npm run dev
```

Open http://localhost:3000/fleet  
Headers the UI sets: `X-Tenant-Id: enterprise-demo`, `X-User-Id: judge`, `X-Roles: issuer`

1. Valid invoice → SIGNED (hash from `core_engine`).
2. Math error → ESCALATED, no hash row.
3. Prompt injection → BLOCKED (Model Armor).
4. Hospitality → ESCALATED (Memory Bank).
5. Role `auditor` + valid → cannot `invoice.sign`.
6. Valid invoice (PDF) → upload → SIGNED (number stamped).
7. Run 3-invoice sweep → 202 QUEUED then SIGNED / ESCALATED / BLOCKED.
8. Checklist: `google-adk`, `gemini-3.5-flash`, `InMemoryRunner`.

`curl http://localhost:8000/health` must include those three strings.

## Video beats (`demo/script.md` + spoken `demo/voiceover.md`)

Keep one unedited English take ≤ 4:00. Add 15s PDF and 20s background sweep. Overlay: consult-only Runner; kernel hashes. Hosted take: Cloud Run console + Pub/Sub subscription `invoice-received-push`. Do not invent a live URL.

Paste-ready Devpost / blog / social: `demo/devpost.md`, `demo/blog.md`, `demo/social.md`.
