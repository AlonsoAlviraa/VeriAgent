# Product Backlog & Roadmap: VeriAgent MVP (3 Meses)

**Technical Product Owner:** Antigravity
**Objetivo:** Lanzamiento del MVP "Auditor Fiscal Proactivo" conforme a Ley Crea y Crece / VeriFactu.

## Glosario de Equipos
| Equipo | Propiedad | Tecnologías |
|--------|-----------|-------------|
| **[TEAM-A]** | `/core_engine`, `/shared`, `/api` | Python, FastAPI, PostgreSQL, XAdES |
| **[TEAM-B]** | `/ai_agents` | LangGraph, CrewAI, ChromaDB |

---

## Roadmap del MVP (6 Sprints)

| Sprint | Objetivo | [TEAM-A] Entregables | [TEAM-B] Entregables | Dependencias | Hito Git |
|--------|----------|---------------------|---------------------|--------------|----------|
| **1** | Cimientos | [CORE-001] Schemas, [CORE-002] DDL, [CORE-003] Docker | [AGENT-001] LangGraph, [AGENT-002] VectorDB | B espera Schemas de A | Merge `develop` Viernes S2 |
| **2** | Ingesta | [CORE-004] Upload API, [CORE-005] OCR | [AGENT-003] Ingest Agent, [AGENT-004] Validation | B espera API Upload | Merge `develop` Viernes S4 |
| **3** | Cumplimiento | [CORE-006] XML Facturae, [CORE-007] Hash Chain | [AGENT-005] Compliance RAG, [AGENT-006] Rules Graph | B espera XML Generator | Merge `develop` Viernes S6 |
| **4** | Transacción | [CORE-008] Firma XAdES, [CORE-009] Mock AEAT | [AGENT-007] Transaction Agent | B espera `/internal/sign` | Merge `develop` Viernes S8 |
| **5** | Orquestación | [CORE-010] REST API, [CORE-011] Webhooks | [AGENT-009] Orchestrator, [AGENT-010] State Mgmt | A expone triggers para B | Merge `develop` Viernes S10 |
| **6** | Hardening | [CORE-012] Security Audit, [CORE-013] Deploy | [AGENT-011] Eval Framework, [AGENT-012] Cost Opt | Sin bloqueos | Release `main` v1.0 |

---

## Tickets Detallados

### Sprint 1-2 (Completados)
- [x] [TEAM-A][CORE-001] Definir Schemas Pydantic en `/shared/schemas.py`
- [x] [TEAM-A][CORE-003] Setup PostgreSQL (Docker)
- [x] [TEAM-A][CORE-004] POST `/upload` endpoint
- [x] [TEAM-A][CORE-005] OCR Service
- [x] [TEAM-B][AGENT-001] LangGraph Setup
- [x] [TEAM-B][AGENT-002] ChromaDB VectorDB
- [x] [TEAM-B][AGENT-003] Ingestion Agent Graph

### Sprint 3-4 (En Progreso)
- [x] [TEAM-A][CORE-006] XML Facturae Generator
- [x] [TEAM-A][CORE-007] Hash Chaining (VeriFactu)
- [x] [TEAM-A][CORE-008] Digital Signature Stub
- [x] [TEAM-B][AGENT-004] CrewAI Agents (Auditor, Connector)
- [x] [TEAM-B][AGENT-005] SearchRegulationTool (RAG)
- [ ] [TEAM-A][CORE-002] DDL SQL (invoices, audit_logs)
- [ ] [TEAM-A][CORE-009] POST `/internal/sign` endpoint
- [ ] [TEAM-A][CORE-010] Hash Integrity Validation (409 Conflict)

### Sprint 5-6 (Pendiente)
- [ ] [TEAM-A][CORE-011] Webhooks de Estado
- [ ] [TEAM-B][AGENT-009] LangGraph Orchestrator Completo
