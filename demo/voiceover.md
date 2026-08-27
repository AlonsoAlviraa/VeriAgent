# VeriFleet spoken voiceover (English, one take, ≤ 4:00)

Read this over a live `/fleet` take. No cuts. Leave the listed silences so the UI can finish. Total speech is about 380 words (~2:40 at 145 wpm); the rest is watching the console and the GCP window.

Do **not** invent a Cloud Run URL. If a human deploy is on screen, say the URL that is in the address bar. If it is not deployed, show `infra/deploy.sh` + the Cloud Run / Pub/Sub pages and say “hosted URL after deploy.”

---

**0:00–0:25 — Friction**

A Spanish small business drops invoices every afternoon. Someone checks VAT, tax IDs, and the VeriFactu hash chain by hand. One wrong total and the chain breaks. VeriFleet is a Fortified Enterprise Fleet for that job. Not a chatbot. Agents audit, sign, or escalate in the background.

**0:25–1:40 — Three invoices, no chat** *(click Valid, then Math error, then Prompt injection)*

This is the judge console at slash fleet. Tenant enterprise-demo, role issuer.

Valid invoice. Ingestion, auditor, signer. A hash appears. Gemini 3.5 Flash never wrote it. The deterministic kernel did.

Math error — base plus tax is not the total. Escalated. The signer is never called. Consult can only tighten. It cannot loosen a failed gate.

Prompt injection: ignore rules and sign. Model Armor blocks it. Nothing reaches the hash chain.

**1:40–2:40 — Fleet checklist** *(Registry, Memory, hospitality fixture, switch role to auditor, valid again)*

Registry: four published agents, gemini-3.5-flash, google-adk. The ADK InMemoryRunner drives a consult-only agent after the gates.

Memory Bank for this tenant denies hospitality. This restaurant invoice escalates from memory.

I switch the role to auditor. Same valid invoice. Escalated — this identity cannot call invoice.sign.

Spans are on the run. On Google Cloud they export to Cloud Trace.

**2:40–3:20 — Architecture**

UI to Pub/Sub invoice.received, to the Agent Gateway on Cloud Run. Google ADK InMemoryRunner consults fiscal-fleet-consult. No tools on that agent. Tools sit behind the gateway and call core-engine — hash chain, Facturae, AEAT fail-closed. Cloud SQL holds invoices and fleet runs. The cryptographic kernel is pre-existing and disclosed. Gemini never writes the hash.

**3:20–4:00 — Proof**

Second window: Cloud Run service. Pub/Sub push subscription invoice-received-push to slash api slash v1 slash fleet slash pubsub slash push. Local fallback is one FIFO thread. Repo README sets SQLite DATABASE_URL so a Windows judge clones in five minutes. CONTEST.md discloses the kernel. Built for All Things Agentic.
