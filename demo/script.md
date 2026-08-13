# VeriFleet demo script (≤ 4 minutes, one live take, English)

Record the `/fleet` UI and a second window with Cloud Run + Cloud Trace. No cuts.

0:00–0:25 — Friction  
A Spanish SME drops invoices every afternoon. A human checks IVA, NIF, and VeriFactu chaining. One wrong total and the hash chain breaks. VeriFleet does this in the background. Not a chatbot.

0:25–1:40 — Three invoices, no chat  
Tenant `enterprise-demo`. Drop `valid_invoice.json` → timeline shows ingestion → auditor → signer. Hash appears. Drop `math_error.json` → ESCALATED, signer never called. Drop `injection.json` → Model Armor BLOCKED.

1:40–2:40 — Fleet checklist  
Open Registry: four published agents, `gemini-3.5-flash`, google-adk. Memory Bank: `deny_categories=hospitality`. Drop `hospitality.json` → ESCALATED from memory. Gateway: switch role to auditor, valid invoice ESCALATES (cannot `invoice.sign`). Show Cloud Trace spans.

2:40–3:20 — Architecture overlay  
UI → Pub/Sub → Gateway → ADK orchestrator → tools → `core_engine` (hash/XML) → Cloud SQL. Gemini never writes the hash.

3:20–4:00 — Proof  
Browser URL `*.run.app/fleet`. GCP console Cloud Run service. Repo + CONTEST.md disclosure. “Built for All Things Agentic.”
