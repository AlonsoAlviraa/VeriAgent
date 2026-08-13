# VeriAgent (notas en español)

El README principal del repositorio está en inglés: es el envío a All Things Agentic.

VeriAgent / VeriFleet audita facturas VeriFactu. El kernel criptográfico (`core_engine`) es determinista. El fleet de agentes (`ai_agents/adk`) decide SIGN / ESCALATE / BLOCK y **nunca** escribe el hash.

Arranque local:

```bash
pip install -r requirements.txt
python -m uvicorn core_engine.main:app --reload --host 127.0.0.1 --port 8000
cd frontend && npm install && npm run dev
```

UI del concurso: http://localhost:3000/fleet  

```bash
python -m verifleet ingest frontend/public/demo-fixtures/valid_invoice.json
```

Disclosure y credenciales de juez: `CONTEST.md`
